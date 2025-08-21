import sys
import types
from pathlib import Path
import importlib
import json


class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get(self, key):
        return getattr(self, key, None)


# In-memory data for stubs
job_types = {
    "OPL Job": {"default_price": 150, "time_minutes": 30},
    "Internal Job": {"default_price": None, "time_minutes": 45},
    "Fallback Job": {"default_price": None, "time_minutes": 60},
}

job_type_items = {
    "Internal Job": [types.SimpleNamespace(parent="Internal Job", qty=1, rate=200, amount=None)]
}

service_price_list = {
    ("Job Type", "Fallback Job", "Retail"): types.SimpleNamespace(rate=50, tax_template=None)
}


class DB:
    def get_value(self, doctype, name, fieldname, *args, **kwargs):
        if doctype == "Job Type" and fieldname == "default_price":
            data = job_types.get(name)
            return data.get("default_price") if data else None
        return None


def get_all(doctype, filters=None, fields=None, **kwargs):
    if doctype == "Job Type":
        names = filters.get("name")[1] if filters else []
        return [
            types.SimpleNamespace(
                name=n,
                default_price=job_types[n]["default_price"],
                time_minutes=job_types[n]["time_minutes"],
            )
            for n in names
        ]

    if doctype == "Job Type Item":
        parents = []
        if filters and isinstance(filters.get("parent"), list):
            parents = filters.get("parent")[1]
        elif filters:
            parents = [filters.get("parent")]
        result = []
        for p in parents:
            result.extend(job_type_items.get(p, []))
        return result

    if doctype == "Service Price List":
        key = (
            filters.get("reference_type"),
            filters.get("reference_name"),
            filters.get("price_list"),
        )
        entry = service_price_list.get(key)
        return [entry] if entry else []

    return []


frappe_utils = types.ModuleType("frappe.utils")
frappe_utils.today = lambda: "2024-01-01"

frappe_stub = types.SimpleNamespace(
    db=DB(),
    get_all=get_all,
    utils=frappe_utils,
    throw=lambda *args, **kwargs: (_ for _ in ()).throw(Exception(args[0] if args else "")),
    _=lambda m: m,
    whitelist=lambda *args, **kwargs: (lambda f: f),
    as_json=lambda obj, sort_keys=True: json.dumps(obj, sort_keys=sort_keys, default=str),
)

frappe_stub.model = types.SimpleNamespace(
    document=types.SimpleNamespace(Document=Document)
)

frappe_stub.get_doc = lambda doctype, name: Document(price_list="Retail")

sys.modules["frappe"] = frappe_stub
sys.modules["frappe.model"] = frappe_stub.model
sys.modules["frappe.model.document"] = frappe_stub.model.document
sys.modules["frappe.utils"] = frappe_utils

# Ensure package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.service_package.service_package import ServicePackage


def test_service_package_pricing_with_opl_and_internal_jobs():
    sys.modules["frappe"] = frappe_stub
    sys.modules["frappe.utils"] = frappe_utils
    sp = ServicePackage(
        price_list="Retail",
        details=[
            types.SimpleNamespace(item_type="Job", job_type="OPL Job", quantity=1, amount=0, rate=0),
            types.SimpleNamespace(item_type="Job", job_type="Internal Job", quantity=1, amount=0, rate=0),
        ],
    )
    sp.calculate_totals()

    assert sp.price == 350
    assert sp.details[0].amount == 150
    assert sp.details[1].amount == 200
    assert sp.total_time_minutes == 75
    assert sp.estimated_time == "1 hr 15 mins"


def test_get_job_type_rate_uses_service_price_list_when_missing():
    sys.modules["frappe"] = frappe_stub
    sys.modules["frappe.utils"] = frappe_utils
    # Reload service price list module to ensure it uses our frappe stub
    sys.modules.pop(
        "car_workshop.car_workshop.doctype.service_price_list.get_active_service_price",
        None,
    )
    import car_workshop.car_workshop.doctype.service_price_list.get_active_service_price as g
    importlib.reload(g)

    sp = ServicePackage(price_list="Retail")
    assert sp.get_job_type_rate("Fallback Job") == 50


def test_service_package_is_modified_flag_set_on_changes():
    sys.modules["frappe"] = frappe_stub
    sys.modules["frappe.utils"] = frappe_utils
    sp = ServicePackage(
        price_list="Retail",
        details=[
            types.SimpleNamespace(
                item_type="Job", job_type="OPL Job", quantity=1, amount=0, rate=0
            )
        ],
    )
    sp.calculate_totals()
    sp.has_value_changed = lambda field: True
    sp.before_save()
    assert sp.is_modified == 1


def test_details_have_changed_ignores_metadata_and_unserializable_fields():
    sys.modules["frappe"] = frappe_stub
    sys.modules["frappe.utils"] = frappe_utils

    prev_detail = types.SimpleNamespace(
        item_type="Job",
        job_type="OPL Job",
        part=None,
        quantity=1,
        rate=150,
        amount=150,
        remarks="note",
        creation=object(),
        modified=object(),
    )

    new_detail = types.SimpleNamespace(
        item_type="Job",
        job_type="OPL Job",
        part=None,
        quantity=1,
        rate=150,
        amount=150,
        remarks="note",
        creation=object(),
        modified=object(),
    )

    previous_doc = ServicePackage(price_list="Retail", details=[prev_detail])
    sp = ServicePackage(price_list="Retail", details=[new_detail])
    sp.get_doc_before_save = lambda: previous_doc

    assert not sp._details_have_changed()

    sp.details[0].remarks = "changed"
    assert sp._details_have_changed()


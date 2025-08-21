import sys
import types
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def setup_frappe_stub(processed, docs):
    frappe = types.ModuleType("frappe")
    frappe._ = lambda m: m

    def get_all(doctype, filters=None, fields=None):
        assert doctype == "Return Material"
        if filters and filters.get("status") == "Pending":
            return [{"name": "RM-1"}, {"name": "RM-2"}]
        return []

    class Doc:
        def __init__(self, name):
            self.name = name
            self.status = "Pending"
            docs[name] = self

        def make_stock_entry_for_return(self):
            processed.append(self.name)

        def set_status(self):
            self.status = "Submitted"

        def save(self):
            pass

    def get_doc(doctype, name):
        return docs.get(name) or Doc(name)

    frappe.get_all = get_all
    frappe.get_doc = get_doc
    frappe.log_error = lambda *args, **kwargs: None
    frappe.logger = lambda: types.SimpleNamespace(info=lambda *args, **kwargs: None)
    frappe.whitelist = lambda *args, **kwargs: (lambda f: f)
    frappe.msgprint = lambda *args, **kwargs: None
    frappe.get_desk_link = lambda doctype, name: name

    utils = types.ModuleType("frappe.utils")
    utils.flt = float
    utils.cint = int
    utils.getdate = lambda v: v
    utils.nowdate = lambda: "2024-01-01"
    utils.nowtime = lambda: "00:00:00"
    frappe.utils = utils

    model = types.ModuleType("frappe.model")
    document = types.ModuleType("frappe.model.document")

    class Document:
        def db_set(self, fieldname, value):
            setattr(self, fieldname, value)

    document.Document = Document
    model.document = document

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    sys.modules["frappe.model"] = model
    sys.modules["frappe.model.document"] = document


def import_doctype(module_name):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_process_pending_returns_processes_documents():
    processed = []
    docs = {}
    setup_frappe_stub(processed, docs)
    module = import_doctype(
        "car_workshop.car_workshop.doctype.return_material.return_material"
    )
    module.process_pending_returns()
    assert processed == ["RM-1", "RM-2"]
    assert all(docs[name].status == "Submitted" for name in ["RM-1", "RM-2"])

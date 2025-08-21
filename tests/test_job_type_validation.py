import sys
import types
from pathlib import Path
import pytest

class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get(self, name):
        return getattr(self, name, None)

frappe_stub = types.SimpleNamespace(
    _=lambda m: m,
    throw=lambda msg: (_ for _ in ()).throw(Exception(msg)),
    db=types.SimpleNamespace(get_value=lambda *a, **k: 0),
    get_all=lambda *a, **k: [],
    log_error=lambda *a, **k: None,
)

sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = types.SimpleNamespace(document=types.SimpleNamespace(Document=Document))
sys.modules['frappe.model.document'] = types.SimpleNamespace(Document=Document)

# Ensure package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.job_type.job_type import JobType


def test_opl_requires_vendor_and_item_code():
    jt = JobType(is_opl=1, items=[], default_price=None)
    with pytest.raises(Exception):
        jt.validate()

    jt = JobType(is_opl=1, opl_vendor='SUP-001', items=[], default_price=None)
    with pytest.raises(Exception):
        jt.validate()

    jt = JobType(is_opl=1, opl_vendor='SUP-001', opl_item_code='ITEM-001', items=[], default_price=None)
    jt.validate()

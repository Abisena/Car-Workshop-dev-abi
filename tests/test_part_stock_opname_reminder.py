import sys
import types
from pathlib import Path

# Create a stub Document class
class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

sent_emails = []
notification_logs = []


def sendmail(recipients=None, subject=None, message=None, **kwargs):
    sent_emails.append({
        "recipients": recipients,
        "subject": subject,
        "message": message,
    })


def get_doc(data):
    doc = types.SimpleNamespace(**data)

    def insert(ignore_permissions=True):
        notification_logs.append(doc)
        return doc

    doc.insert = insert
    return doc


frappe_stub = types.SimpleNamespace(
    get_all=lambda *args, **kwargs: [],
    sendmail=sendmail,
    get_doc=get_doc,
    _=lambda msg: msg,
    whitelist=lambda *args, **kwargs: (lambda fn: fn),
)

frappe_utils_stub = types.SimpleNamespace(
    flt=lambda x: x,
    cint=lambda x: int(x),
    getdate=lambda x: x,
    now_datetime=lambda: None,
    nowdate=lambda: None,
)

frappe_stub.utils = frappe_utils_stub

frappe_stub.model = types.SimpleNamespace(
    document=types.SimpleNamespace(Document=Document)
)

sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_stub.model
sys.modules['frappe.model.document'] = frappe_stub.model.document
sys.modules['frappe.utils'] = frappe_utils_stub

# Ensure the package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname import remind_pending_opnames


def test_remind_pending_opnames_sends_notifications():
    captured = {}

    def mock_get_all(*args, **kwargs):
        captured['filters'] = kwargs.get('filters')
        return [
            {"name": "OPN-001", "owner": "user1@example.com"},
            {"name": "OPN-002", "owner": "user2@example.com"},
        ]

    frappe_stub.get_all = mock_get_all

    remind_pending_opnames()

    assert captured['filters'] == {"status": "Submitted", "docstatus": 1}
    assert len(sent_emails) == 2
    assert {email["recipients"][0] for email in sent_emails} == {"user1@example.com", "user2@example.com"}
    assert len(notification_logs) == 2
    assert {log.for_user for log in notification_logs} == {"user1@example.com", "user2@example.com"}

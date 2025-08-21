import sys
import types

def setup_frappe_stub():
    frappe = types.ModuleType("frappe")
    frappe._ = lambda m: m

    class DB:
        def __init__(self):
            self.data = {}

        def insert(self, doctype, doc):
            self.data.setdefault(doctype, []).append(doc)

        def get_all(self, doctype, filters):
            def match(doc):
                return all(doc.get(k) == v for k, v in filters.items())
            return [doc for doc in self.data.get(doctype, []) if match(doc)]

    frappe.db = DB()

    desk = types.ModuleType("frappe.desk")
    notifications = types.ModuleType("frappe.desk.notifications")

    def get_open_count(doctype, name):
        links = {
            "Work Order": [
                ("Workshop Material Issue", "work_order"),
                ("Workshop Purchase Order", "work_order"),
            ]
        }
        counts = {}
        for linked_doctype, field in links.get(doctype, []):
            counts[linked_doctype] = len(
                frappe.db.get_all(linked_doctype, {field: name})
            )
        return counts

    notifications.get_open_count = get_open_count
    desk.notifications = notifications
    frappe.desk = desk

    sys.modules["frappe"] = frappe
    sys.modules["frappe.desk"] = desk
    sys.modules["frappe.desk.notifications"] = notifications

    return frappe


def test_work_order_open_count():
    frappe = setup_frappe_stub()

    # Insert a Work Order and related records
    frappe.db.insert("Work Order", {"name": "WO-001"})
    frappe.db.insert(
        "Workshop Material Issue", {"name": "WMI-001", "work_order": "WO-001"}
    )
    frappe.db.insert(
        "Workshop Purchase Order", {"name": "WPO-001", "work_order": "WO-001"}
    )

    counts = frappe.desk.notifications.get_open_count("Work Order", "WO-001")
    assert counts["Workshop Material Issue"] == 1
    assert counts["Workshop Purchase Order"] == 1

import frappe


def execute():
    """Add time_minutes column to Job Type and backfill existing records"""
    frappe.reload_doc("car_workshop", "doctype", "job_type")
    frappe.db.sql("""update `tabJob Type` set time_minutes = 0 where time_minutes is null""")


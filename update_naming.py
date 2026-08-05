import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def run():
    frappe.init(site="uotelafer-lm.localhost")
    frappe.connect()
    try:
        # We will add fields directly to the json files, this is just a test script if needed.
        pass
    finally:
        frappe.destroy()

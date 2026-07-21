import frappe
def test():
    mappings = frappe.db.get_all("Leave Approver Mapping", filters={"user": "omar.almolaa@uotelafer.edu.iq"}, fields=["*"])
    print("DB MAPPINGS:", mappings)

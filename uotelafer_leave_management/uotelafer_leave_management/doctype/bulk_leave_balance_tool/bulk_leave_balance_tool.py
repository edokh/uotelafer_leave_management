# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BulkLeaveBalanceTool(Document):
	def on_submit(self):
		count = 0
		for row in self.employees:
			if not row.employee:
				continue
				
			tx_type = self.transaction_type or "Addition"
			
			frappe.get_doc({
				"doctype": "Leave Balance Transaction",
				"employee": row.employee,
				"employee_full_name": row.employee_fullname,
				"leave_type": self.leave_type,
				"transaction_type": tx_type,
				"balance": row.balance_to_add,
				"date": frappe.utils.today()
			}).insert(ignore_permissions=True)
			count += 1
			
		frappe.msgprint(f"Created {count} Leave Balance Transactions")

@frappe.whitelist()
def get_all_employees():
	# Return list shaped for the child table: use `employee` as the link field
	employees = frappe.get_all("User", fields=["name", "full_name"])
	return [{
		"employee": e.get("name"),
		"employee_fullname": e.get("full_name")
	} for e in employees]
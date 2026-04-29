# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class BulkLeaveBalanceTool(Document):
	pass

@frappe.whitelist()
def get_all_employees():
	# Return list shaped for the child table: use `employee` as the link field
	employees = frappe.get_all("User", fields=["name", "full_name"])
	return [{
		"employee": e.get("name"),
		"employee_fullname": e.get("full_name")
	} for e in employees]


@frappe.whitelist()
def create_leave_balances(doc):
	# `doc` may be passed as a JSON string from the client; parse it first.
	if isinstance(doc, str):
		try:
			doc = json.loads(doc)
		except Exception:
			# leave as-is and let `frappe.get_doc` raise if it's invalid
			pass

	doc = frappe.get_doc(doc)
	count = 0
	errors = []

	try:
		for row in doc.employees:
			# Support both dict (RPC) and object row types
			employee = getattr(row, 'employee', None)
			if isinstance(row, dict):
				employee = row.get('employee', employee)
			if not employee:
				continue

			selected = getattr(row, 'selected', None)
			if isinstance(row, dict):
				selected = row.get('selected', selected)
			# Only create transactions for rows explicitly selected (truthy)
			if not selected:
				continue

			# Resolve fullname from available keys
			fullname = getattr(row, 'employee_fullname', None)
			if isinstance(row, dict):
				fullname = row.get('employee_fullname', fullname)
			if not fullname:
				fullname = getattr(row, 'employee_name', None)
				if isinstance(row, dict):
					fullname = row.get('employee_name', fullname)

			# Determine transaction type: prefer the document value, but validate
			tx_type = getattr(doc, 'transaction_type', None)
			if isinstance(doc, dict):
				tx_type = doc.get('transaction_type', tx_type)
			if tx_type not in ("Addition", "Consumption"):
				# fallback to Addition for compatibility
				tx_type = "Addition"

			frappe.get_doc({
				"doctype": "Leave Balance Transaction",
				"employee": employee,
				"employee_full_name": fullname,
				"leave_type": doc.leave_type,
				"transaction_type": tx_type,
				"balance": doc.balance,
				"date": doc.date
			}).insert(ignore_permissions=True)
			count += 1
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'bulk_leave_balance_tool.create_leave_balances')
		errors.append(str(e))

	frappe.db.commit()

	return {"created": count, "errors": errors}
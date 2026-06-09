# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LeaveSettings(Document):
	def on_update(self):
		self.update_page_roles()
		self.update_workflow_roles()

	def update_page_roles(self):
		# Sync roles to the Page
		if not frappe.db.exists("Page", "leave-managment"):
			return

		page = frappe.get_doc("Page", "leave-managment")
		
		roles = [
			"University Employee",
			"Follow Up Employee",
			"System Manager"
		]

		if self.department_head_role and self.department_head_role not in roles:
			roles.append(self.department_head_role)
		
		if self.presidant_role and self.presidant_role not in roles:
			roles.append(self.presidant_role)

		if self.presidant_office_role and self.presidant_office_role not in roles:
			roles.append(self.presidant_office_role)

		if self.hr_employee_role and self.hr_employee_role not in roles:
			roles.append(self.hr_employee_role)

		page.roles = []
		for role in roles:
			page.append("roles", {"role": role})

		page.save(ignore_permissions=True)

	def update_workflow_roles(self):
		# Standard Frappe workflow allows one role per transition. We will just add transitions for all configured roles.
		if not frappe.db.exists("Workflow", "Leave Approval"):
			return
		
		# Since we handle approval logic in python with ignore_permissions=True,
		# updating the Workflow DB is optional, but good for completeness.
		pass


# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class LeaveSettings(Document):
	def validate(self):
		self.validate_approval_levels()
		self.validate_approver_mappings()

	def on_update(self):
		self.update_page_roles()
		self.update_citizen_affairs_page_roles()

	def validate_approval_levels(self):
		"""Ensure approval levels are sequential starting from 1 with no gaps."""
		if not self.approval_levels:
			frappe.throw(_("At least one approval level is required."))

		levels = sorted([row.level for row in self.approval_levels])
		expected = list(range(1, len(levels) + 1))
		if levels != expected:
			frappe.throw(_("Approval levels must be sequential starting from 1 with no gaps. Got: {0}").format(levels))

	def validate_approver_mappings(self):
		"""Ensure each approver mapping references a valid approval level."""
		if not self.approval_levels:
			return

		valid_levels = {row.level for row in self.approval_levels}
		for mapping in self.approver_mappings or []:
			if mapping.approval_level not in valid_levels:
				frappe.throw(
					_("Approver mapping for {0} references level {1}, which is not defined in Approval Levels.").format(
						mapping.user, mapping.approval_level
					)
				)

	def update_page_roles(self):
		"""Sync roles to the Page based on configured approval levels."""
		if not frappe.db.exists("Page", "leave-managment"):
			return

		page = frappe.get_doc("Page", "leave-managment")

		roles = {
			"University Employee",
			"Follow Up Employee",
			"System Manager",
		}

		# Add roles from all approval levels
		for level in self.approval_levels or []:
			if level.role:
				roles.add(level.role)

		# Add HR role
		if self.hr_employee_role:
			roles.add(self.hr_employee_role)

		page.roles = []
		for role in roles:
			page.append("roles", {"role": role})

		page.save(ignore_permissions=True)

	def update_citizen_affairs_page_roles(self):
		"""Sync roles to the Citizens Affairs Management page based on Leave Settings."""
		if not frappe.db.exists("Page", "citizens-affairs-mgm"):
			return

		page = frappe.get_doc("Page", "citizens-affairs-mgm")

		roles = ["System Manager"]

		# Add the citizens affairs admin role defined in Leave Settings
		if self.citizens_affairs_admin_role and self.citizens_affairs_admin_role not in roles:
			roles.append(self.citizens_affairs_admin_role)

		# Add all approval-level roles (in case leave approvers also handle citizen requests)
		for level in self.approval_levels or []:
			if level.role and level.role not in roles:
				roles.append(level.role)

		page.roles = []
		for role in roles:
			page.append("roles", {"role": role})

		page.save(ignore_permissions=True)


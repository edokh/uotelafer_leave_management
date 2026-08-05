# Copyright (c) 2026, Computer Center of UoT and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, add_days
from uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave import get_leave_balance

class TestLeave(FrappeTestCase):
	def setUp(self):
		# Create a test formation if it doesn't exist
		if not frappe.db.exists("Leave Formation", "Test Formation"):
			frappe.get_doc({
				"doctype": "Leave Formation",
				"formation_name": "Test Formation"
			}).insert(ignore_permissions=True)

		# Create a test department if it doesn't exist
		if not frappe.db.exists("Leave Department", "Test Dept"):
			self.dept = frappe.get_doc({
				"doctype": "Leave Department",
				"department_name": "Test Dept",
				"formation": "Test Formation",
				"department_head": "Administrator"
			}).insert(ignore_permissions=True)
		else:
			self.dept = frappe.get_doc("Leave Department", "Test Dept")
			if not self.dept.formation:
				self.dept.formation = "Test Formation"
				self.dept.save(ignore_permissions=True)

		# Ensure "إلغاء إجازة" leave type exists
		if not frappe.db.exists("Leave Type", "إلغاء إجازة"):
			frappe.get_doc({
				"doctype": "Leave Type",
				"leave_type": "إلغاء إجازة",
				"has_balance": 0
			}).insert(ignore_permissions=True)

		# Ensure "اجازة اعتيادية" leave type exists
		if not frappe.db.exists("Leave Type", "اجازة اعتيادية"):
			frappe.get_doc({
				"doctype": "Leave Type",
				"leave_type": "اجازة اعتيادية",
				"has_balance": 1
			}).insert(ignore_permissions=True)

		# Delete existing leaves and transactions to ensure clean state
		frappe.db.delete("Leave", {"employee": "Administrator"})
		frappe.db.delete("Leave Balance Transaction", {"employee": "Administrator"})

		# Give Administrator 30 days of "اجازة اعتيادية" balance
		frappe.get_doc({
			"doctype": "Leave Balance Transaction",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"transaction_type": "Addition",
			"balance": 30.0,
			"date": frappe.utils.today(),
			"note": "Initial Balance Setup"
		}).insert(ignore_permissions=True)

	def insert_doc_without_workflow(self, doc):
		orig_in_install = frappe.flags.in_install
		frappe.flags.in_install = "frappe"
		try:
			doc.insert(ignore_permissions=True)
		finally:
			frappe.flags.in_install = orig_in_install
		return doc

	def submit_doc_without_workflow(self, doc):
		orig_in_install = frappe.flags.in_install
		frappe.flags.in_install = "frappe"
		try:
			doc.submit()
		finally:
			frappe.flags.in_install = orig_in_install
		return doc

	def cancel_doc_without_workflow(self, doc):
		orig_in_install = frappe.flags.in_install
		frappe.flags.in_install = "frappe"
		try:
			doc.cancel()
		finally:
			frappe.flags.in_install = orig_in_install
		return doc

	def test_standard_leave_creation_and_balance(self):
		"""Test standard leave submission deducts balance correctly"""
		# Create leave for 5 days
		leave = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-06-01",
			"to_date": "2026-06-05",
			"dep": "Test Dept",
			"reason": "Regular holiday"
		})
		self.insert_doc_without_workflow(leave)
		self.assertEqual(leave.days, 5)

		# Submit it
		self.submit_doc_without_workflow(leave)

		# Verify a consumption transaction is created
		txn = frappe.db.get_value("Leave Balance Transaction", 
			{"employee": "Administrator", "leave_type": "اجازة اعتيادية", "transaction_type": "Consumption"}, 
			["balance", "name"], as_dict=True)
		self.assertIsNotNone(txn)
		self.assertEqual(txn.balance, 5)

		# Verify balance in get_leave_balance (30 - 5 = 25)
		bal = get_leave_balance("Administrator", "اجازة اعتيادية")
		self.assertEqual(bal.get("total_balance"), 25)

	def test_cancellation_validation_rules(self):
		"""Test all validation rules for cancellation requests"""
		# Create a non-approved original leave first
		orig_pending = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-05-01",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Pending vacation"
		})
		self.insert_doc_without_workflow(orig_pending)

		# Try to cancel a non-approved leave
		cancel_leave = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "إلغاء إجازة",
			"original_leave": orig_pending.name,
			"from_date": "2026-05-03",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Stopping early"
		})
		self.assertRaises(frappe.ValidationError, self.insert_doc_without_workflow, cancel_leave)

		# Delete the pending leave to free the dates
		frappe.delete_doc("Leave", orig_pending.name, force=True)

		# Create and approve/submit a valid original leave (May 1 to May 5)
		orig_leave = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-05-01",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Original vacation",
			"status": "Approved"
		})
		self.insert_doc_without_workflow(orig_leave)
		self.submit_doc_without_workflow(orig_leave)

		# Create a cancellation for a different employee
		cancel_mismatch = frappe.get_doc({
			"doctype": "Leave",
			"employee": "SomeOtherUser", # Mismatch
			"leave_type": "إلغاء إجازة",
			"original_leave": orig_leave.name,
			"from_date": "2026-05-03",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Stopping early"
		})
		self.assertRaises(frappe.ValidationError, self.insert_doc_without_workflow, cancel_mismatch)

		# Create cancellation with dates outside original leave range
		cancel_out_of_bounds = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "إلغاء إجازة",
			"original_leave": orig_leave.name,
			"from_date": "2026-04-30", # Out of bounds
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Stopping early"
		})
		self.assertRaises(frappe.ValidationError, self.insert_doc_without_workflow, cancel_out_of_bounds)

		# Create valid cancellation
		cancel_valid = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "إلغاء إجازة",
			"original_leave": orig_leave.name,
			"from_date": "2026-05-03",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Stopping early"
		})
		self.insert_doc_without_workflow(cancel_valid) # Should succeed

		# Try to create an overlapping cancellation request
		cancel_overlap = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "إلغاء إجازة",
			"original_leave": orig_leave.name,
			"from_date": "2026-05-04", # Overlaps with May 3-5
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Duplicate stop"
		})
		self.assertRaises(frappe.ValidationError, self.insert_doc_without_workflow, cancel_overlap)

	def test_cancellation_balance_refund(self):
		"""Test that submitting cancellation refunds balance and cancelling cancellation reverses it"""
		# Create and submit original leave for 5 days (May 1 to May 5)
		orig_leave = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-05-01",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Original vacation",
			"status": "Approved"
		})
		self.insert_doc_without_workflow(orig_leave)
		self.submit_doc_without_workflow(orig_leave)

		# Verify balance is 25
		bal_info = get_leave_balance("Administrator", "اجازة اعتيادية")
		self.assertEqual(bal_info.get("total_balance"), 25)

		# Create cancellation request for May 3 to May 5 (3 days)
		cancel_leave = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "إلغاء إجازة",
			"original_leave": orig_leave.name,
			"from_date": "2026-05-03",
			"to_date": "2026-05-05",
			"dep": "Test Dept",
			"reason": "Stopping early",
			"status": "Approved"
		})
		self.insert_doc_without_workflow(cancel_leave)
		self.assertEqual(cancel_leave.days, 3)

		# Submit the cancellation request
		self.submit_doc_without_workflow(cancel_leave)

		# Verify addition transaction of 3 days was created
		txn = frappe.db.get_value("Leave Balance Transaction", 
			{"employee": "Administrator", "leave_type": "اجازة اعتيادية", "transaction_type": "Addition", "note": ["like", f"%{cancel_leave.name}%"]}, 
			["balance"], as_dict=True)
		self.assertIsNotNone(txn)
		self.assertEqual(txn.balance, 3)

		# Verify available balance is now 28 (30 - 5 + 3)
		bal_info = get_leave_balance("Administrator", "اجازة اعتيادية")
		self.assertEqual(bal_info.get("total_balance"), 28)

		# Cancel the cancellation request
		self.cancel_doc_without_workflow(cancel_leave)

		# Verify addition transaction was deleted
		txn_exists = frappe.db.exists("Leave Balance Transaction", 
			{"employee": "Administrator", "leave_type": "اجازة اعتيادية", "transaction_type": "Addition", "note": ["like", f"%{cancel_leave.name}%"]})
		self.assertFalse(txn_exists)

		# Verify balance is back to 25
		bal_info = get_leave_balance("Administrator", "اجازة اعتيادية")
		self.assertEqual(bal_info.get("total_balance"), 25)

	def test_overlapping_regular_leaves_with_cancellation(self):
		"""Test that overlaps are blocked generally, but allowed for cancelled intervals"""
		# Create and submit a 5-day leave (June 1 to June 5)
		leave1 = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-06-01",
			"to_date": "2026-06-05",
			"dep": "Test Dept",
			"reason": "First leave",
			"status": "Approved"
		})
		self.insert_doc_without_workflow(leave1)
		self.submit_doc_without_workflow(leave1)

		# Try to create a second overlapping leave (June 4 to June 8)
		leave2_overlap = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-06-04",
			"to_date": "2026-06-08",
			"dep": "Test Dept",
			"reason": "Overlapping leave"
		})
		self.assertRaises(frappe.ValidationError, self.insert_doc_without_workflow, leave2_overlap)

		# Cancel June 3 to June 5 (3 days)
		cancel = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "إلغاء إجازة",
			"original_leave": leave1.name,
			"from_date": "2026-06-03",
			"to_date": "2026-06-05",
			"dep": "Test Dept",
			"reason": "Cancel latter half",
			"status": "Approved"
		})
		self.insert_doc_without_workflow(cancel)
		self.submit_doc_without_workflow(cancel)

		# Now trying to create a leave for June 4 to June 8 should succeed because June 4-5 are cancelled!
		leave2_valid = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-06-04",
			"to_date": "2026-06-08",
			"dep": "Test Dept",
			"reason": "Leave in cancelled period"
		})
		self.insert_doc_without_workflow(leave2_valid) # Should succeed

	def test_approval_recording(self):
		"""Test that approval registers who and when approved the leave"""
		leave = frappe.get_doc({
			"doctype": "Leave",
			"employee": "Administrator",
			"leave_type": "اجازة اعتيادية",
			"from_date": "2026-07-01",
			"to_date": "2026-07-05",
			"dep": "Test Dept",
			"reason": "Testing approval logging"
		})
		self.insert_doc_without_workflow(leave)
		leave.status = "Draft"
		leave.save()

		# Approve using apply_workflow_action (custom API page action)
		from uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment import process_leave_action
		
		# Set session user to Administrator
		frappe.set_user("Administrator")
		
		# Run workflow action
		process_leave_action(leave.name, "Apply")
		leave.reload()
		for _ in range((leave.max_required_level or 1) + 1):
			if leave.status == "Approved":
				break
			process_leave_action(leave.name, "Approve")
			leave.reload()

		# Reload document and verify
		leave.reload()
		self.assertEqual(leave.status, "Approved")
		self.assertEqual(leave.approved_by, "Administrator")
		self.assertEqual(leave.approved_by_name, frappe.db.get_value("User", "Administrator", "full_name"))
		self.assertEqual(leave.approved_by_email, frappe.db.get_value("User", "Administrator", "email"))
		self.assertIsNotNone(leave.approved_on)

	def test_formation_level_routing_uses_sibling_department_mappings(self):
		"""A leave should advance to the next formation level before final approval."""
		from uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment import process_leave_action

		if not frappe.db.exists("Leave Department", "Sibling Dept"):
			frappe.get_doc({
				"doctype": "Leave Department",
				"department_name": "Sibling Dept",
				"formation": "Test Formation",
				"department_head": "Administrator"
			}).insert(ignore_permissions=True)

		settings = frappe.get_doc("Leave Settings")
		original_levels = [
			{
				"level": row.level,
				"level_name": row.level_name,
				"min_days": row.min_days,
				"max_days": row.max_days,
				"role": row.role,
			}
			for row in (settings.approval_levels or [])
		]
		original_mappings = [
			{
				"user": row.user,
				"formation": row.formation,
				"approval_level": row.approval_level,
			}
			for row in (settings.approver_mappings or [])
		]

		try:
			settings.set("approval_levels", [])
			settings.append("approval_levels", {
				"level": 1,
				"level_name": "Supervisor",
				"min_days": 0,
				"max_days": 3,
				"role": "System Manager",
			})
			settings.append("approval_levels", {
				"level": 2,
				"level_name": "President",
				"min_days": 4,
				"max_days": 0,
				"role": "System Manager",
			})

			settings.set("approver_mappings", [])
			settings.append("approver_mappings", {
				"user": "Administrator",
				"formation": "Test Formation",
				"approval_level": 1,
			})
			settings.append("approver_mappings", {
				"user": "Administrator",
				"formation": "Test Formation",
				"approval_level": 2,
			})
			settings.save(ignore_permissions=True)

			leave = frappe.get_doc({
				"doctype": "Leave",
				"employee": "Administrator",
				"leave_type": "اجازة اعتيادية",
				"from_date": "2026-07-10",
				"to_date": "2026-07-14",
				"dep": "Test Dept",
				"reason": "Formation routing test"
			})
			self.insert_doc_without_workflow(leave)
			leave.status = "Draft"
			leave.save(ignore_permissions=True)

			frappe.set_user("Administrator")
			process_leave_action(leave.name, "Apply")
			process_leave_action(leave.name, "Approve")

			leave.reload()
			self.assertEqual(leave.status, "Pending")
			self.assertEqual(leave.current_approval_level, 1)

			process_leave_action(leave.name, "Approve")

			leave.reload()
			self.assertEqual(leave.status, "Approved")
			self.assertEqual(leave.current_approval_level, 2)
		finally:
			settings.reload()
			settings.set("approval_levels", [])
			for row in original_levels:
				settings.append("approval_levels", row)
			settings.set("approver_mappings", [])
			for row in original_mappings:
				settings.append("approver_mappings", row)
			settings.save(ignore_permissions=True)

	def test_final_approval_without_next_level_keeps_workflow_valid(self):
		"""If no next level exists, approval should still finalize without invalid transition errors."""
		from uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment import process_leave_action

		settings = frappe.get_doc("Leave Settings")
		original_levels = [
			{
				"level": row.level,
				"level_name": row.level_name,
				"min_days": row.min_days,
				"max_days": row.max_days,
				"role": row.role,
			}
			for row in (settings.approval_levels or [])
		]
		original_mappings = [
			{
				"user": row.user,
				"formation": row.formation,
				"approval_level": row.approval_level,
			}
			for row in (settings.approver_mappings or [])
		]

		try:
			settings.set("approval_levels", [])
			settings.append("approval_levels", {
				"level": 1,
				"level_name": "Supervisor",
				"min_days": 0,
				"max_days": 3,
				"role": "System Manager",
			})
			settings.append("approval_levels", {
				"level": 2,
				"level_name": "President",
				"min_days": 4,
				"max_days": 0,
				"role": "System Manager",
			})

			settings.set("approver_mappings", [])
			settings.append("approver_mappings", {
				"user": "Administrator",
				"formation": "Test Formation",
				"approval_level": 1,
			})
			settings.save(ignore_permissions=True)

			leave = frappe.get_doc({
				"doctype": "Leave",
				"employee": "Administrator",
				"leave_type": "اجازة اعتيادية",
				"from_date": "2026-07-20",
				"to_date": "2026-07-25",
				"dep": "Test Dept",
				"reason": "No-next-level finalization test"
			})
			self.insert_doc_without_workflow(leave)
			leave.status = "Draft"
			leave.save(ignore_permissions=True)

			frappe.set_user("Administrator")
			process_leave_action(leave.name, "Apply")
			process_leave_action(leave.name, "Approve")

			leave.reload()
			self.assertEqual(leave.status, "Approved")
			self.assertEqual(leave.current_approval_level, 1)
		finally:
			settings.reload()
			settings.set("approval_levels", [])
			for row in original_levels:
				settings.append("approval_levels", row)
			settings.set("approver_mappings", [])
			for row in original_mappings:
				settings.append("approver_mappings", row)
			settings.save(ignore_permissions=True)

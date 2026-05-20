# Copyright (c) 2026, Computer Center of UoT and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, add_days
from uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave import get_leave_balance

class TestLeave(FrappeTestCase):
	def setUp(self):
		# Create a test department if it doesn't exist
		if not frappe.db.exists("Leave Department", "Test Dept"):
			self.dept = frappe.get_doc({
				"doctype": "Leave Department",
				"department_name": "Test Dept",
				"department_head": "Administrator"
			}).insert(ignore_permissions=True)
		else:
			self.dept = frappe.get_doc("Leave Department", "Test Dept")

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
			"workflow_state": "Approved"
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
			"workflow_state": "Approved"
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
			"workflow_state": "Approved"
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
			"workflow_state": "Approved"
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
			"workflow_state": "Approved"
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

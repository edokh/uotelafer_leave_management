# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta

def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)
	if "System Manager" in roles:
		return ""

	if "Department Head" in roles:
		departments = frappe.get_all("Leave Department", filters={"department_head": user}, pluck="name")
		if departments:
			departments_str = ", ".join([frappe.db.escape(d) for d in departments])
			return f"`tabLeave`.dep IN ({departments_str})"
		else:
			return "1=0"

	return ""

class Leave(Document):
	def on_update(self):
		if not self.employee:
			return
			
		leave_employee_name = frappe.db.get_value("Leave Employee", {"user": self.employee}, "name")
		if not leave_employee_name:
			if not self.dep:
				frappe.throw(_("Department is required for your first leave application to setup your profile. Please select a Department."))
			leave_employee = frappe.new_doc("Leave Employee")
			leave_employee.user = self.employee
		else:
			leave_employee = frappe.get_doc("Leave Employee", leave_employee_name)
			
		if self.employee_fullname:
			leave_employee.full_name = self.employee_fullname
		if self.dep:
			leave_employee.leave_department = self.dep
			
		leave_employee.save(ignore_permissions=True)

	def before_save(self):
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if old_doc and old_doc.workflow_state != self.workflow_state:
				if self.workflow_state == "Approved By Department" or (old_doc.workflow_state == "Applied" and self.workflow_state == "Rejected"):
					self.date_of_supervisor_action = frappe.utils.today()
				elif self.workflow_state == "Approved" or (old_doc.workflow_state == "Approved By Department" and self.workflow_state == "Rejected"):
					self.date_of_presidant_action = frappe.utils.today()

	def validate(self):
		"""Validate and calculate leave days, excluding holidays and weekends"""
		# Calculate days first (excluding holidays and weekends)
		if self.from_date and self.to_date:
			self.days = calculate_leave_days(self.from_date, self.to_date)
		
		# If this is a Cancellation request
		if self.leave_type == "إلغاء إجازة":
			if not self.original_leave:
				frappe.throw(_("Original Leave is required for a cancellation request."))
				
			original_leave_doc = frappe.get_doc("Leave", self.original_leave)
			
			# Validate employee matches
			if original_leave_doc.employee != self.employee:
				frappe.throw(_("The original leave must belong to the same employee."))
				
			# Validate original leave is approved
			if original_leave_doc.workflow_state != "Approved":
				frappe.throw(_("Only approved leaves can be cancelled. The original leave is currently {0}.").format(original_leave_doc.workflow_state))
				
			# Validate cancellation dates fall within original leave dates
			from frappe.utils import getdate
			orig_from = getdate(original_leave_doc.from_date)
			orig_to = getdate(original_leave_doc.to_date)
			cancel_from = getdate(self.from_date)
			cancel_to = getdate(self.to_date)
			
			if cancel_from < orig_from or cancel_to > orig_to:
				frappe.throw(_("Cancellation dates must fall within the original leave period ({0} to {1}).").format(
					original_leave_doc.from_date,
					original_leave_doc.to_date
				))
				
			# Check for overlapping cancellation requests for the same original leave
			overlapping = frappe.get_all(
				"Leave",
				filters={
					"original_leave": self.original_leave,
					"name": ["!=", self.name],
					"workflow_state": ["!=", "Rejected"],
					"from_date": ["<=", self.to_date],
					"to_date": [">=", self.from_date]
				}
			)
			if overlapping:
				frappe.throw(_("This cancellation period overlaps with an existing cancellation request for the same leave."))
		else:
			# Check for overlapping leaves for the same employee
			check_overlapping_leaves(self.employee, self.from_date, self.to_date, self.name)
		
		# Validate that the employee has sufficient leave balance if the type requires it
		if self.employee and self.leave_type and self.days:
			has_balance = frappe.db.get_value("Leave Type", self.leave_type, "has_balance")
			
			if has_balance:
				# Get the leave balance for the selected leave type
				balance_info = get_leave_balance(self.employee, self.leave_type, self.name)
				total_balance = balance_info.get("total_balance", 0)
				
				# Check if balance is sufficient
				if total_balance < self.days:
					frappe.throw(
						_("Insufficient leave balance for {0}. Requested: {1} days, Available: {2} days").format(
							self.leave_type,
							self.days,
							total_balance
						)
					)
	
	def before_submit(self):
		"""Validate that status is not Rejected before submission"""
		if self.status == "Rejected":
			frappe.throw(_("Cannot submit a Rejected leave request"))

	def on_submit(self):
		"""Create a Leave Balance Transaction after submission"""
		if not self.days:
			return

		if self.leave_type == "إلغاء إجازة":
			# For Cancellation, create an Addition transaction for the original leave type
			original_leave_doc = frappe.get_doc("Leave", self.original_leave)
			has_balance = frappe.db.get_value("Leave Type", original_leave_doc.leave_type, "has_balance")
			if not has_balance:
				return

			transaction = frappe.new_doc("Leave Balance Transaction")
			transaction.employee = self.employee
			transaction.leave_type = original_leave_doc.leave_type
			transaction.transaction_type = "Addition"
			transaction.balance = self.days
			transaction.date = frappe.utils.today()
			transaction.note = f"Addition from Leave Cancellation {self.name} (Original Leave: {self.original_leave})"
			transaction.insert(ignore_permissions=True)
			
			frappe.msgprint(_("Leave Balance Transaction created for Addition (Cancellation)."))
		else:
			# For standard leaves, create a Consumption transaction
			has_balance = frappe.db.get_value("Leave Type", self.leave_type, "has_balance")
			if not has_balance:
				return

			transaction = frappe.new_doc("Leave Balance Transaction")
			transaction.employee = self.employee
			transaction.leave_type = self.leave_type
			transaction.transaction_type = "Consumption"
			transaction.balance = self.days
			transaction.date = frappe.utils.today()
			transaction.note = f"Consumption from Leave {self.name}"
			transaction.insert(ignore_permissions=True)
			
			frappe.msgprint(_("Leave Balance Transaction created for Consumption."))

	def on_cancel(self):
		"""Delete the corresponding Leave Balance Transaction if cancelled"""
		frappe.db.delete("Leave Balance Transaction", {"note": ["like", f"%{self.name}%"]})



@frappe.whitelist()
def get_all_leave_balances(employee, current_leave_name=None):
	"""
	Get leave balance for all leave types for an employee.
	Returns a dictionary with leave_type as key and balance as value.
	Excludes the current leave being edited if current_leave_name is provided.
	"""
	if not employee:
		return {}
	
	# Get all leave types
	leave_types = frappe.get_all("Leave Type", filters={"has_balance": 1}, fields=["name"])
	
	balances = {}
	for leave_type_doc in leave_types:
		leave_type = leave_type_doc.get("name")
		
		# Get all leave balance transactions for this employee and leave type
		transactions = frappe.get_all(
			"Leave Balance Transaction",
			filters={
				"employee": employee,
				"leave_type": leave_type
			},
			fields=["transaction_type", "balance"]
		)
		
		total_balance = 0
		for transaction in transactions:
			if transaction.get("transaction_type") == "Addition":
				total_balance += transaction.get("balance", 0)
			elif transaction.get("transaction_type") == "Consumption":
				total_balance -= transaction.get("balance", 0)
		
		# Get all leave applications for this employee and leave type
		filters = {
			"employee": employee,
			"leave_type": leave_type,
			"docstatus": 0,
		}
		
		# Exclude current leave if provided
		if current_leave_name:
			filters["name"] = ["!=", current_leave_name]
		
		leave_applications = frappe.get_all(
			"Leave",
			filters=filters,
			fields=["days", "status", "name"]
		)
		
		# Sum all days from leaves and subtract from balance
		taken_days = 0
		for application in leave_applications:
			status = application.get("status")
			# Count leaves that are not Rejected
			if status != "Rejected":
				taken_days += application.get("days", 0)
		
		total_balance -= taken_days
		
		# Always include all leave types, even with 0 balance
		balances[leave_type] = total_balance
	
	return balances

@frappe.whitelist()
def get_leave_balance(employee, leave_type, current_leave_name=None):
	"""
	Calculate the leave balance for an employee for a specific leave type.
	Excludes the current leave being edited if current_leave_name is provided.
	"""
	if not employee or not leave_type:
		return {'total_balance': 0, 'applications': []}
	
	# Get all leave balance transactions for this employee and leave type
	transactions = frappe.get_all(
		"Leave Balance Transaction",
		filters={
			"employee": employee,
			"leave_type": leave_type
		},
		fields=["transaction_type", "balance"]
	)
	
	total_balance = 0
	for transaction in transactions:
		if transaction.get("transaction_type") == "Addition":
			total_balance += transaction.get("balance", 0)
		elif transaction.get("transaction_type") == "Consumption":
			total_balance -= transaction.get("balance", 0)
	
	# Get all leave applications for this employee and leave type
	filters = {
		"employee": employee,
		"leave_type": leave_type,
		"docstatus": 0,
	}
	
	# Exclude current leave if provided
	if current_leave_name:
		filters["name"] = ["!=", current_leave_name]
	
	leave_applications = frappe.get_all(
		"Leave",
		filters=filters,
		fields=["days","status"]
	)
	
	# Sum all days from leaves and subtract from balance
	taken_days = 0
	for application in leave_applications:
		status = application.get("status")
		# Count leaves that are not Rejected
		if status != "Rejected":
			taken_days += application.get("days", 0)
	
	total_balance -= taken_days
	return {'total_balance': total_balance, 'applications': leave_applications}

@frappe.whitelist()
def calculate_leave_days(from_date, to_date):
	"""
	Calculate leave days excluding:
	1. Holidays from Holiday DocType that fall within the date range
	
	Returns: Number of leave days
	"""
	from frappe.utils import getdate
	
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	
	if from_date > to_date:
		return 0
	
	# Get all holidays that fall within the date range
	holidays = frappe.get_all(
		"Holiday",
		filters=[
			["from_date", "<=", to_date],
			["to_date", ">=", from_date]
		],
		fields=["from_date", "to_date"]
	)
	
	# Create a set of holiday dates
	holiday_dates = set()
	for holiday in holidays:
		current_date = getdate(holiday["from_date"])
		holiday_end = getdate(holiday["to_date"])
		while current_date <= holiday_end:
			holiday_dates.add(current_date)
			current_date += timedelta(days=1)
	
	# Count days
	working_days = 0
	current_date = from_date
	
	while current_date <= to_date:
		# If it's not a holiday, count it
		if current_date not in holiday_dates:
			working_days += 1
		
		current_date += timedelta(days=1)
	
	return working_days


def check_overlapping_leaves(employee, from_date, to_date, exclude_leave_name=None):
	from frappe.utils import getdate
	
	from_date = getdate(from_date)
	to_date = getdate(to_date)
	
	# Fetch all leaves of this employee that overlap with the date range and are not Rejected
	leaves = frappe.get_all(
		"Leave",
		filters={
			"employee": employee,
			"name": ["!=", exclude_leave_name] if exclude_leave_name else None,
			"workflow_state": ["!=", "Rejected"],
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date]
		},
		fields=["name", "from_date", "to_date", "leave_type", "original_leave"]
	)
	
	if not leaves:
		return
		
	# Categorize regular leaves and cancellation leaves
	regular_leaves = []
	cancellation_leaves = []
	for l in leaves:
		if l.leave_type == "إلغاء إجازة":
			cancellation_leaves.append(l)
		else:
			regular_leaves.append(l)
			
	if not regular_leaves:
		return
		
	# Build a set of all cancelled dates for this employee
	# Fetch any cancellations that might fall within this period
	all_cancellations = frappe.get_all(
		"Leave",
		filters={
			"employee": employee,
			"leave_type": "إلغاء إجازة",
			"workflow_state": ["!=", "Rejected"]
		},
		fields=["from_date", "to_date"]
	)
	
	cancelled_dates = set()
	for cl in all_cancellations:
		curr = getdate(cl.from_date)
		end = getdate(cl.to_date)
		while curr <= end:
			cancelled_dates.add(curr)
			curr += timedelta(days=1)
			
	# Build a set of active leave dates
	leave_dates = set()
	for rl in regular_leaves:
		curr = getdate(rl.from_date)
		end = getdate(rl.to_date)
		while curr <= end:
			if curr not in cancelled_dates:
				leave_dates.add(curr)
			curr += timedelta(days=1)
			
	# Check if any date in the proposed range is an active leave date
	curr = from_date
	while curr <= to_date:
		if curr in leave_dates:
			frappe.throw(_("Employee is already on leave on {0}").format(curr.strftime("%Y-%m-%d")))
		curr += timedelta(days=1)

# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from pypika import Order
from frappe.query_builder.functions import Sum


def execute(filters=None):
	if not filters:
		filters = {}
	
	columns = get_columns(filters)
	data = get_data(filters)
	
	return columns, data


def get_columns(filters):
	columns = [
		{
			"label": _("Employee Name"),
			"fieldname": "employee_full_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Leave Type"),
			"fieldname": "leave_type",
			"fieldtype": "Link",
			"options": "Leave Type",
			"width": 120
		},
		{
			"label": _("Pending Days"),
			"fieldname": "pending_days",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Available Days"),
			"fieldname": "available_days",
			"fieldtype": "Float",
			"width": 120
		},
		{
			"label": _("Used Days"),
			"fieldname": "used_days",
			"fieldtype": "Float",
			"width": 100
		}
	]
	
	return columns


def get_data(filters):
	data = []
	
	# Get filter values
	employee = filters.get("employee")
	leave_type = filters.get("leave_type")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	
	# Fetch all Leave Balance Transactions
	transaction_filters = {}
	if employee:
		transaction_filters["employee"] = employee
	if leave_type:
		transaction_filters["leave_type"] = leave_type
	if from_date:
		transaction_filters["date"] = [">=", from_date]
	if to_date:
		transaction_filters["date"] = ["<=", to_date]
	
	transactions = frappe.get_all("Leave Balance Transaction", 
		filters=transaction_filters, 
		fields=["employee", "employee_full_name", "leave_type", "transaction_type", "balance"]
	)
	
	# Group by employee and leave_type
	emp_leave_map = {}
	for t in transactions:
		key = (t.employee, t.leave_type)
		if key not in emp_leave_map:
			emp_leave_map[key] = {
				"employee_full_name": t.employee_full_name,
				"addition": 0,
				"consumption": 0
			}
		
		if t.transaction_type == "Addition":
			emp_leave_map[key]["addition"] += t.balance
		elif t.transaction_type == "Consumption":
			emp_leave_map[key]["consumption"] += t.balance
			
	# Fetch Pending Leaves
	pending_filters = {"status": "Open"}
	if employee:
		pending_filters["employee"] = employee
	if leave_type:
		pending_filters["leave_type"] = leave_type
	if from_date:
		pending_filters["from_date"] = [">=", from_date]
	if to_date:
		pending_filters["to_date"] = ["<=", to_date]
		
	pending_leaves = frappe.get_all("Leave", filters=pending_filters, fields=["employee", "leave_type", "days"])
	
	pending_map = {}
	for p in pending_leaves:
		key = (p.employee, p.leave_type)
		if key not in pending_map:
			pending_map[key] = 0
		pending_map[key] += p.days

	for key, stats in emp_leave_map.items():
		emp, ltype = key
		used_days = stats["consumption"]
		total_allocated = stats["addition"]
		
		pending_days = pending_map.get(key, 0)
		available_days = total_allocated - used_days - pending_days
		
		data.append({
			"employee_full_name": stats["employee_full_name"],
			"leave_type": ltype,
			"pending_days": pending_days,
			"available_days": available_days,
			"used_days": used_days
		})

	return data

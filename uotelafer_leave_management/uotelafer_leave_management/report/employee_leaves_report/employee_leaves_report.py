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
	status = filters.get("status")
	
	# Get all unique employee-leave_type combinations from Leave Balance Transaction
	query = frappe.qb.from_("Leave Balance Transaction")
	
	if employee:
		query = query.where(frappe.qb.Field("employee") == employee)
	if leave_type:
		query = query.where(frappe.qb.Field("leave_type") == leave_type)
	
	# Get latest balance transactions for each employee-leave_type combo
	balance_records = query.select(
		"employee",
		"employee_full_name",
		"leave_type",
		"balance",
		"date"
	).orderby(frappe.qb.Field("date"), order=Order.desc).run(as_dict=True)
	
	# Group by employee-leave_type to get unique employees and types
	employee_leave_dict = {}
	for record in balance_records:
		key = (record.get("employee"), record.get("leave_type"))
		if key not in employee_leave_dict:
			employee_leave_dict[key] = {
				"employee": record.get("employee"),
				"employee_full_name": record.get("employee_full_name"),
				"leave_type": record.get("leave_type")
			}
	
	from uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave import get_leave_balance

	# For each employee-leave_type combination, get usage stats
	for key, record in employee_leave_dict.items():
		emp = record.get("employee")
		ltype = record.get("leave_type")
		
		used_days = get_used_leaves(emp, ltype, from_date, to_date, status)
		pending_days = get_pending_leaves(emp, ltype, from_date, to_date)
		
		# Get true available balance using the exact same logic as Leave doctype
		balance_info = get_leave_balance(emp, ltype)
		available_days = balance_info.get("total_balance", 0)
		
		row = {
			"employee_full_name": record.get("employee_full_name"),
			"leave_type": ltype,
			"used_days": used_days,
			"pending_days": pending_days,
			"available_days": available_days
		}
		
		data.append(row)
	
	return data


def get_used_leaves(employee, leave_type, from_date=None, to_date=None, status=None):
	"""Get count of used leaves for an employee and leave type"""
	query = frappe.qb.from_("Leave")
	
	if from_date:
		query = query.where(frappe.qb.Field("from_date") >= getdate(from_date))
	if to_date:
		query = query.where(frappe.qb.Field("to_date") <= getdate(to_date))
	
	if status:
		query = query.where(frappe.qb.Field("status") == status)
	else:
		# By default, get only approved leaves
		query = query.where(frappe.qb.Field("status").isin(["Approved", "Submitted"]))
	
	result = query.select(
		Sum(frappe.qb.Field("days"))
	).where(
		frappe.qb.Field("employee") == employee
	).where(
		frappe.qb.Field("leave_type") == leave_type
	).run()
	
	return result[0][0] or 0


def get_pending_leaves(employee, leave_type, from_date=None, to_date=None):
	"""Get count of pending leave applications"""
	query = frappe.qb.from_("Leave")
	
	if from_date:
		query = query.where(frappe.qb.Field("from_date") >= getdate(from_date))
	if to_date:
		query = query.where(frappe.qb.Field("to_date") <= getdate(to_date))
	
	result = query.select(
		Sum(frappe.qb.Field("days"))
	).where(
		frappe.qb.Field("employee") == employee
	).where(
		frappe.qb.Field("leave_type") == leave_type
	).where(
		frappe.qb.Field("status") == "Open"
	).run()
	
	return result[0][0] or 0

// Copyright (c) 2026, Computer Center of UoT and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Leaves Report"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "User",
			"reqd": 0
		},
		{
			"fieldname": "leave_type",
			"label": __("Leave Type"),
			"fieldtype": "Link",
			"options": "Leave Type",
			"reqd": 0
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 0
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nApproved\nPending\nRejected",
			"reqd": 0
		}
	]
};

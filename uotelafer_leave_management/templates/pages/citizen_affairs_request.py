import frappe

no_cache = 1

def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = "شؤون المواطنين - تقديم طلب"

	# Get departments for the dropdown that have accept_citzen_requests checked
	departments = frappe.get_all(
		"Leave Department",
		filters={"accept_citzen_requests": 1},
		fields=["name", "department_name"],
		order_by="department_name asc",
		ignore_permissions=True
	)
	context.departments = departments

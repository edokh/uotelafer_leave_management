import frappe
from frappe import _


@frappe.whitelist()
def get_employee_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves for the current logged-in employee"""
    user = frappe.session.user
    filters = {"employee": user}

    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
    if status:
        filters["workflow_state"] = status

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "from_date", "to_date", "days",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment"
        ],
        order_by="date_of_application desc",
        limit_page_length=100,
    )
    return leaves


@frappe.whitelist()
def get_department_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves for the department head's department"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "Department Head" not in roles and "System Manager" not in roles:
        frappe.throw(_("Access Denied"))

    # Get departments this user heads
    departments = frappe.get_all(
        "Leave Department",
        filters={"department_head": user},
        pluck="name"
    )

    if not departments and "System Manager" not in roles:
        return []

    filters = {}
    if departments and "System Manager" not in roles:
        filters["dep"] = ["in", departments]

    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
    if status:
        filters["workflow_state"] = status
    else:
        # Default: show Applied leaves for department head
        filters["workflow_state"] = "Applied"

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "from_date", "to_date", "days",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment"
        ],
        order_by="date_of_application desc",
        limit_page_length=200,
    )
    return leaves


@frappe.whitelist()
def get_president_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves awaiting president approval"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "University President" not in roles and "System Manager" not in roles:
        frappe.throw(_("Access Denied"))

    filters = {}

    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
    if status:
        filters["workflow_state"] = status
    else:
        # Default: show leaves approved by department, awaiting president
        filters["workflow_state"] = "Approved By Department"

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "from_date", "to_date", "days",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment"
        ],
        order_by="date_of_application desc",
        limit_page_length=200,
    )
    return leaves


@frappe.whitelist()
def get_all_leaves(from_date=None, to_date=None, leave_type=None, status=None, dep=None, employee_name=None):
    """Get all leaves for Follow Up Employee"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    if "Follow Up Employee" not in roles and "System Manager" not in roles:
        frappe.throw(_("Access Denied"))

    filters = {}
    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
        
    if status == "Submitted":
        filters["workflow_state"] = ["in", ["Pending", "Applied", "Approved By Department"]]
    elif status == "Approved":
        filters["workflow_state"] = "Approved"
    elif status:
        filters["workflow_state"] = status
    else:
        # Default for Follow Up: show all Submitted and Approved (exclude Rejected)
        filters["workflow_state"] = ["in", ["Pending", "Applied", "Approved By Department", "Approved"]]
        
    if dep:
        filters["dep"] = dep
    if employee_name:
        filters["employee"] = employee_name

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "from_date", "to_date", "days",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment"
        ],
        order_by="date_of_application desc",
        limit_page_length=500,
    )
    return leaves


@frappe.whitelist()
def apply_workflow_action(leave_name, action, comment=None):
    """Apply workflow action (Approve/Reject) with optional comment"""
    doc = frappe.get_doc("Leave", leave_name)

    if comment:
        doc.add_comment("Comment", comment)

    frappe.model.workflow.apply_workflow(doc, action)
    doc.save(ignore_permissions=True)

    return {"status": "success", "new_state": doc.workflow_state}


@frappe.whitelist()
def get_leave_types():
    """Get all leave types"""
    return frappe.get_all("Leave Type", fields=["name", "leave_type", "has_balance"])


@frappe.whitelist()
def get_departments():
    """Get all departments"""
    return frappe.get_all("Leave Department", fields=["name", "department_name"])


@frappe.whitelist()
def get_user_roles():
    """Get current user's roles relevant to this page"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    return {
        "is_employee": "University Employee" in roles,
        "is_dept_head": "Department Head" in roles,
        "is_president": "University President" in roles,
        "is_follow_up": "Follow Up Employee" in roles,
        "is_admin": "System Manager" in roles,
        "user": user,
    }


@frappe.whitelist()
def get_leave_comments(leave_name):
    """Get comments for a leave"""
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "Leave",
            "reference_name": leave_name,
            "comment_type": "Comment",
        },
        fields=["comment_by", "content", "creation"],
        order_by="creation asc",
    )
    return comments


@frappe.whitelist()
def create_leave(leave_type, from_date, to_date, reason, dep, alternative_employee=None, attachment=None):
    """Create a new leave request and apply the workflow"""
    user = frappe.session.user

    # Get employee full name
    employee_fullname = frappe.db.get_value("User", user, "full_name") or user
    # Try to get from Leave Employee first
    le_name = frappe.db.get_value("Leave Employee", user, "full_name")
    if le_name:
        employee_fullname = le_name

    doc = frappe.new_doc("Leave")
    doc.employee = user
    doc.employee_fullname = employee_fullname
    doc.leave_type = leave_type
    doc.from_date = from_date
    doc.to_date = to_date
    doc.reason = reason
    doc.dep = dep
    doc.date_of_application = frappe.utils.today()

    if alternative_employee:
        doc.alternative_employee = alternative_employee
    if attachment:
        doc.attachment = attachment

    doc.insert()

    # Apply the "Apply" workflow action to move from Pending -> Applied
    try:
        frappe.model.workflow.apply_workflow(doc, "Apply")
        doc.save(ignore_permissions=True)
    except Exception:
        pass

    return doc.name

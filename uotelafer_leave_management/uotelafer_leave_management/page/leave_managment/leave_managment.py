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
    if status and status != "All":
        filters["workflow_state"] = status

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "original_leave", "from_date", "to_date", "days",
            "is_time_leave", "number_of_hours",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment", "personal_email"
        ],
        order_by="modified desc",
        limit_page_length=100,
    )
    return leaves


@frappe.whitelist()
def get_department_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves for the department head's department"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    settings = frappe.get_cached_doc("Leave Settings")
    dept_head_role = settings.department_head_role or "Department Head"

    if dept_head_role not in roles and "System Manager" not in roles:
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
    if status and status != "All":
        filters["workflow_state"] = status

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "original_leave", "from_date", "to_date", "days",
            "is_time_leave", "number_of_hours",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment", "personal_email"
        ],
        order_by="modified desc",
        limit_page_length=200,
    )
    return leaves


@frappe.whitelist()
def get_president_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves awaiting president approval"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    settings = frappe.get_cached_doc("Leave Settings")
    pres_role = settings.presidant_role or "University President"
    pres_office_role = settings.presidant_office_role or "Presidant Office"

    is_pres = pres_role in roles or "System Manager" in roles
    is_office = pres_office_role in roles

    if not is_pres and not is_office:
        frappe.throw(_("Access Denied"))

    filters = {}

    if not is_pres and is_office:
        max_days = settings.number_of_days_for_presidant_approval or 3
        filters["days"] = ["<=", max_days]

    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
    if status and status != "All":
        filters["workflow_state"] = status

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "original_leave", "from_date", "to_date", "days",
            "is_time_leave", "number_of_hours",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment", "personal_email"
        ],
        order_by="modified desc",
        limit_page_length=200,
    )
    return leaves


@frappe.whitelist()
def get_all_leaves(from_date=None, to_date=None, leave_type=None, status=None, dep=None, employee_name=None, printed=None):
    """Get all leaves for Follow Up / HR Employee"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    settings = frappe.get_cached_doc("Leave Settings")
    hr_role = settings.hr_employee_role or "HR Employee"

    if "Follow Up Employee" not in roles and hr_role not in roles and "System Manager" not in roles:
        frappe.throw(_("Access Denied"))

    filters = {}

    # Filter by formation for HR/Follow Up employees
    if "System Manager" not in roles:
        leave_emp = frappe.db.get_value("Leave Employee", {"user": user}, "leave_department")
        if leave_emp:
            formation = frappe.db.get_value("Leave Department", leave_emp, "formation")
            if formation:
                allowed_departments = frappe.get_all("Leave Department", filters={"formation": formation}, pluck="name")
                if allowed_departments:
                    filters["dep"] = ["in", allowed_departments]
                else:
                    return []

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
        if "dep" in filters and isinstance(filters["dep"], list) and filters["dep"][0] == "in":
            if dep in filters["dep"][1]:
                filters["dep"] = dep
            else:
                return [] # Dep requested not in allowed
        else:
            filters["dep"] = dep
    if employee_name:
        filters["employee"] = employee_name

    if printed == "Printed":
        filters["printed"] = 1
    elif printed == "Not Printed":
        filters["printed"] = 0

    try:
        leaves = frappe.get_all(
            "Leave",
            filters=filters,
            fields=[
                "name", "employee", "employee_fullname", "dep",
                "leave_type", "original_leave", "from_date", "to_date", "days",
                "is_time_leave", "number_of_hours",
                "reason", "workflow_state", "status",
                "date_of_application", "alternative_employee",
                "supervisor", "attachment", "personal_email", "printed", "is_read"
            ],
            order_by="modified desc",
            limit_page_length=500,
        )
    except Exception:
        leaves = frappe.get_all(
            "Leave",
            filters=filters,
            fields=[
                "name", "employee", "employee_fullname", "dep",
                "leave_type", "original_leave", "from_date", "to_date", "days",
                "is_time_leave", "number_of_hours",
                "reason", "workflow_state", "status",
                "date_of_application", "alternative_employee",
                "supervisor", "attachment", "personal_email", "printed"
            ],
            order_by="modified desc",
            limit_page_length=500,
        )
    return leaves


@frappe.whitelist()
def apply_workflow_action(leave_name, action, comment=None):
    """Apply workflow action (Approve/Reject) with optional comment"""
    doc = frappe.get_doc("Leave", leave_name)

    if comment:
        doc.add_comment("Comment", comment)

    user = frappe.session.user
    roles = frappe.get_roles(user)
    settings = frappe.get_cached_doc("Leave Settings")

    if doc.workflow_state == "Applied" and action in ["Approve", "Reject"]:
        dept_head_role = settings.department_head_role or "Department Head"
        if dept_head_role not in roles and "System Manager" not in roles:
            frappe.throw(_("Only Department Heads can approve leaves at this stage."))
            
        if "System Manager" not in roles and doc.dep:
            dept_head = frappe.db.get_value("Leave Department", doc.dep, "department_head")
            if dept_head != user:
                frappe.throw(_("Access Denied: You are not the Department Head for this employee's department."))

    elif doc.workflow_state == "Approved By Department" and action in ["Approve", "Reject"]:
        pres_role = settings.presidant_role or "University President"
        pres_office_role = settings.presidant_office_role or "Presidant Office"
        max_days = settings.number_of_days_for_presidant_approval or 3

        is_pres = pres_role in roles or "System Manager" in roles
        is_office = pres_office_role in roles

        # Check if user has the single-approval approver_role for this leave's formation
        is_single_approver = _is_user_single_approver_for_leave(user, roles, doc)

        if not is_pres and not is_office and not is_single_approver:
            frappe.throw(_("Access Denied for approval"))

        if doc.days > max_days and not is_pres and not is_single_approver:
            frappe.throw(_("Only the University President can approve leaves longer than {0} days").format(max_days))
            
    else:
        if not (doc.workflow_state == "Pending" and action == "Apply" and (user == doc.employee or user == doc.owner)):
            if "System Manager" not in roles:
                frappe.throw(_("Access Denied or invalid workflow transition via this endpoint."))

    frappe.set_user("Administrator")
    try:
        frappe.model.workflow.apply_workflow(doc, action)
        if doc.workflow_state == "Approved":
            doc.approved_by = user
            doc.approved_by_name = frappe.db.get_value("User", user, "full_name") or user
            doc.approved_by_email = frappe.db.get_value("User", user, "email") or user
            doc.approved_on = frappe.utils.now_datetime()
        doc.save(ignore_permissions=True)
    finally:
        frappe.set_user(user)

    return {"status": "success", "new_state": doc.workflow_state}


@frappe.whitelist()
def get_leave_types():
    """Get all leave types"""
    return frappe.get_all("Leave Type", fields=["name", "leave_type", "has_balance"])


@frappe.whitelist()
def get_departments():
    """Get all departments"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    filters = {}
    
    settings = frappe.get_cached_doc("Leave Settings")
    hr_role = settings.hr_employee_role or "HR Employee"

    if "System Manager" not in roles and (hr_role in roles or "Follow Up Employee" in roles):
        leave_emp = frappe.db.get_value("Leave Employee", {"user": user}, "leave_department")
        if leave_emp:
            formation = frappe.db.get_value("Leave Department", leave_emp, "formation")
            if formation:
                filters["formation"] = formation

    return frappe.get_all("Leave Department", filters=filters, fields=["name", "department_name"])


@frappe.whitelist()
def get_leave_employees():
    """Get all employees, filtered by formation if applicable"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    filters = {}
    
    settings = frappe.get_cached_doc("Leave Settings")
    hr_role = settings.hr_employee_role or "HR Employee"

    if "System Manager" not in roles and (hr_role in roles or "Follow Up Employee" in roles):
        leave_emp = frappe.db.get_value("Leave Employee", {"user": user}, "leave_department")
        if leave_emp:
            formation = frappe.db.get_value("Leave Department", leave_emp, "formation")
            if formation:
                allowed_departments = frappe.get_all("Leave Department", filters={"formation": formation}, pluck="name")
                if allowed_departments:
                    filters["leave_department"] = ["in", allowed_departments]

    return frappe.get_all("Leave Employee", filters=filters, fields=["name", "full_name"], limit_page_length=0)


def ensure_proxy_role_exists():
    if not frappe.db.exists("Role", "Leave Proxy Submitter"):
        role = frappe.new_doc("Role")
        role.role_name = "Leave Proxy Submitter"
        role.insert(ignore_permissions=True)


@frappe.whitelist()
def get_user_roles():
    """Get current user's roles relevant to this page"""
    ensure_proxy_role_exists()
    user = frappe.session.user
    roles = frappe.get_roles(user)
    is_dept_head = False

    settings = frappe.get_single("Leave Settings")
    dept_head_role = settings.department_head_role or "Department Head"
    pres_role = settings.presidant_role or "University President"
    pres_office_role = settings.presidant_office_role or "Presidant Office"
    hr_role = settings.hr_employee_role or "HR Employee"

    if dept_head_role in roles:
        is_dept_head = bool(frappe.db.exists("Leave Department", {"department_head": user}))

    # Check if user has any single-approval approver_role
    is_single_approver = False
    single_approver_role = None
    single_approval_formations = frappe.get_all(
        "Leave Formation",
        filters={"single_approval": 1, "approver_role": ["is", "set"]},
        fields=["name", "approver_role"]
    )
    for f in single_approval_formations:
        if f.approver_role in roles:
            is_single_approver = True
            single_approver_role = f.approver_role
            break

    return {
        "is_employee": "University Employee" in roles,
        "is_dept_head": is_dept_head,
        "is_president": pres_role in roles,
        "is_president_office": pres_office_role in roles,
        "is_follow_up": "Follow Up Employee" in roles or hr_role in roles or "System Manager" in roles,
        "is_admin": "System Manager" in roles,
        "is_proxy_submitter": "Leave Proxy Submitter" in roles or "System Manager" in roles,
        "is_single_approver": is_single_approver or "System Manager" in roles,
        "single_approver_role": single_approver_role,
        "user": user,
    }


@frappe.whitelist()
def get_proxy_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves submitted by the current user on behalf of others"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if "Leave Proxy Submitter" not in roles and "System Manager" not in roles:
        frappe.throw(_("Access Denied"))

    filters = {"owner": user, "employee": ["!=", user]}

    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
    if status and status != "All":
        filters["workflow_state"] = status

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "original_leave", "from_date", "to_date", "days",
            "is_time_leave", "number_of_hours",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment", "personal_email"
        ],
        order_by="modified desc",
        limit_page_length=100,
    )
    return leaves


@frappe.whitelist()
def get_leave_comments(leave_name):
    """Get comments for a leave"""
    if not frappe.has_permission("Leave", doc=leave_name, ptype="read"):
        frappe.throw(_("Access Denied"))

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
def create_leave(leave_type, from_date, to_date, reason, dep, employee=None, employee_fullname=None, alternative_employee=None, attachment=None, personal_email=None, original_leave=None, is_time_leave=0, number_of_hours=0, from_time=None, to_time=None):
    """Create a new leave request and apply the workflow"""
    user = frappe.session.user

    # Determine target employee
    target_employee = user
    if employee and employee != user:
        roles = frappe.get_roles(user)
        if "Leave Proxy Submitter" in roles or "System Manager" in roles:
            target_employee = employee
        else:
            frappe.throw(_("You are not authorized to submit leaves on behalf of other employees."))

    if not employee_fullname or target_employee != user:
        # Get employee full name
        employee_fullname = frappe.db.get_value("User", target_employee, "full_name") or target_employee
        # Try to get from Leave Employee first
        le_name = frappe.db.get_value("Leave Employee", {"user": target_employee}, "full_name")
        if le_name:
            employee_fullname = le_name

    doc = frappe.new_doc("Leave")
    doc.employee = target_employee
    doc.employee_fullname = employee_fullname
    doc.leave_type = leave_type
    doc.from_date = from_date
    doc.to_date = to_date
    doc.is_time_leave = int(is_time_leave)
    doc.number_of_hours = int(number_of_hours)
    if from_time:
        doc.from_time = from_time
    if to_time:
        doc.to_time = to_time
    doc.reason = reason
    doc.dep = dep
    doc.date_of_application = frappe.utils.today()

    if alternative_employee:
        doc.alternative_employee = alternative_employee
    if attachment:
        doc.attachment = attachment
    if personal_email:
        doc.personal_email = personal_email
    if original_leave:
        doc.original_leave = original_leave

    doc.insert()

    # Apply the "Apply" workflow action to move from Pending -> Applied
    try:
        frappe.model.workflow.apply_workflow(doc, "Apply")
        doc.save(ignore_permissions=True)
    except Exception:
        pass

    # Auto-advance for single-approval formations:
    # If the employee's department belongs to a formation with single_approval=1,
    # automatically approve at department level
    if doc.workflow_state == "Applied" and doc.dep:
        try:
            formation = frappe.db.get_value("Leave Department", doc.dep, "formation")
            if formation:
                is_single = frappe.db.get_value("Leave Formation", formation, "single_approval")
                if is_single:
                    frappe.set_user("Administrator")
                    try:
                        frappe.model.workflow.apply_workflow(doc, "Approve")
                        doc.date_of_supervisor_action = frappe.utils.today()
                        doc.save(ignore_permissions=True)
                        doc.add_comment("Comment", "تمت الموافقة التلقائية من القسم - نظام الموافقة الواحدة")
                    finally:
                        frappe.set_user(user)
        except Exception:
            pass

    return doc.name


@frappe.whitelist()
def get_bulk_print_html(leave_names):
    """Get the combined print HTML for multiple leaves"""
    import json
    if isinstance(leave_names, str):
        leave_names = json.loads(leave_names)
    
    html_content = ""
    for name in leave_names:
        if not frappe.has_permission("Leave", doc=name, ptype="read"):
            frappe.throw(_("Access Denied to view leave {0}").format(name))
            
        doc = frappe.get_doc("Leave", name)
        # Render leave using standard print format
        rendered = frappe.get_print(
            doctype="Leave",
            name=name,
            print_format="Leave Print Form",
            no_letterhead=True
        )
        # Add print format style page break
        html_content += f'<div class="bulk-print-page" style="page-break-after: always; padding: 20px;">{rendered}</div>'
    
    return html_content


@frappe.whitelist()
def mark_leaves_as_printed(leave_names):
    """Mark a list of leaves as printed"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    settings = frappe.get_cached_doc("Leave Settings")
    hr_role = settings.hr_employee_role or "HR Employee"
    if "System Manager" not in roles and "Follow Up Employee" not in roles and hr_role not in roles:
        frappe.throw(_("Access Denied"))

    import json
    if isinstance(leave_names, str):
        leave_names = json.loads(leave_names)
        
    for name in leave_names:
        frappe.db.set_value("Leave", name, "printed", 1)
    
    frappe.db.commit()
    return {"status": "success"}


def _is_user_single_approver_for_leave(user, roles, leave_doc):
    """Check if user has the approver_role for the leave's formation (single_approval mode)"""
    if not leave_doc.dep:
        return False

    formation = frappe.db.get_value("Leave Department", leave_doc.dep, "formation")
    if not formation:
        return False

    formation_doc = frappe.get_cached_doc("Leave Formation", formation)
    if not formation_doc.single_approval or not formation_doc.approver_role:
        return False

    return formation_doc.approver_role in roles


@frappe.whitelist()
def get_single_approval_leaves(from_date=None, to_date=None, leave_type=None, status=None):
    """Get leaves awaiting final approval from single-approval formations"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    # Find all single-approval formations where the user has the approver_role
    formations = frappe.get_all(
        "Leave Formation",
        filters={"single_approval": 1, "approver_role": ["is", "set"]},
        fields=["name", "approver_role"]
    )

    allowed_formations = []
    for f in formations:
        if f.approver_role in roles or "System Manager" in roles:
            allowed_formations.append(f.name)

    if not allowed_formations:
        return []

    # Get departments belonging to these formations
    departments = frappe.get_all(
        "Leave Department",
        filters={"formation": ["in", allowed_formations]},
        pluck="name"
    )

    if not departments:
        return []

    filters = {
        "dep": ["in", departments]
    }

    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type
    if status and status != "All":
        filters["workflow_state"] = status
    else:
        # Default: show leaves awaiting approval and already approved
        filters["workflow_state"] = ["in", ["Approved By Department", "Approved", "Rejected"]]

    leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=[
            "name", "employee", "employee_fullname", "dep",
            "leave_type", "original_leave", "from_date", "to_date", "days",
            "is_time_leave", "number_of_hours",
            "reason", "workflow_state", "status",
            "date_of_application", "alternative_employee",
            "supervisor", "attachment", "personal_email"
        ],
        order_by="modified desc",
        limit_page_length=200,
    )
    return leaves

@frappe.whitelist()
def remove_wrong_department_leave(leave_name):
    """Remove a leave if the employee does not belong to the department (department head action)"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    
    doc = frappe.get_doc("Leave", leave_name)
    
    # Verify user is the department head of doc.dep
    if "System Manager" not in roles:
        dept_head = frappe.db.get_value("Leave Department", doc.dep, "department_head")
        if dept_head != user:
            frappe.throw(_("Access Denied: You are not the Department Head for this department."))
            
    # Remove the leave completely
    frappe.delete_doc("Leave", leave_name, force=1)
    
    return {"status": "success"}

@frappe.whitelist()
def withdraw_leave(leave_name):
    """Allows an employee to withdraw/cancel their own leave before department approval"""
    user = frappe.session.user
    
    doc = frappe.get_doc("Leave", leave_name)
    
    # Verify ownership
    if doc.employee != user and doc.owner != user:
        roles = frappe.get_roles(user)
        if "System Manager" not in roles and "Leave Proxy Submitter" not in roles:
            frappe.throw(_("Access Denied: You can only withdraw your own leaves."))
            
    # Check state
    if doc.workflow_state not in ["Pending", "Applied"]:
        frappe.throw(_("You can only withdraw leaves that have not yet been approved by the department."))
        
    frappe.set_user("Administrator")
    try:
        if doc.docstatus == 1:
            # Need to cancel it if it's already submitted
            doc.cancel()
            
        frappe.db.set_value("Leave", leave_name, "workflow_state", "Rejected")
        frappe.db.set_value("Leave", leave_name, "status", "Rejected")
        
        # Add comment
        doc.add_comment("Comment", "تم سحب الإجازة من قبل الموظف")
        
        # Explicitly delete any balance transactions (consumption) for this leave just in case
        frappe.db.delete("Leave Balance Transaction", {"note": ["like", f"%{leave_name}%"]})
        
    finally:
        frappe.set_user(user)
        
    return {"status": "success"}

@frappe.whitelist()
def toggle_leave_read(leave_name, is_read):
    """Toggle the read state of a leave"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    settings = frappe.get_cached_doc("Leave Settings")
    hr_role = settings.hr_employee_role or "HR Employee"
    if "System Manager" not in roles and "Follow Up Employee" not in roles and hr_role not in roles:
        frappe.throw(_("Access Denied"))

    try:
        frappe.db.set_value("Leave", leave_name, "is_read", int(is_read))
    except Exception:
        # Create field if missing
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
        create_custom_field('Leave', dict(
            fieldname='is_read',
            label='Is Read',
            fieldtype='Check',
            default='0'
        ))
        frappe.db.set_value("Leave", leave_name, "is_read", int(is_read))

    return {"status": "success"}


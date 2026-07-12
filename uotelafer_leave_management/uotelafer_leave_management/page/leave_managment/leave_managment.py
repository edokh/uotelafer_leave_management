import frappe
from frappe import _
import json


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Settings & Approval Level Resolution
# ─────────────────────────────────────────────────────────────────────────────

def _get_settings():
    """Return the cached Leave Settings singleton."""
    return frappe.get_cached_doc("Leave Settings")


def _get_approval_levels():
    """Return approval levels sorted by level number."""
    settings = _get_settings()
    return sorted(settings.approval_levels or [], key=lambda r: r.level)


def _compute_max_required_level(days):
    """
    Given the number of leave days, determine the maximum approval level required.

    Logic:
    - Walk through levels from lowest to highest.
    - A level applies if days >= level.min_days (or min_days == 0).
    - A level is the *final* level if days <= level.max_days (and max_days > 0).
    - If no level caps the days, the highest level that applies is used.
    """
    levels = _get_approval_levels()
    if not levels:
        return 0

    max_level = 0
    for lvl in levels:
        min_d = lvl.min_days or 0
        max_d = lvl.max_days or 0

        if min_d == 0 or days >= min_d:
            max_level = lvl.level
            # If max_days is set and days falls within range, this is the final level
            if max_d > 0 and days <= max_d:
                return lvl.level

    return max_level


def _get_level_name(level_number):
    """Get the display name for a given approval level number."""
    levels = _get_approval_levels()
    for lvl in levels:
        if lvl.level == level_number:
            return lvl.level_name
    return f"المستوى {level_number}"


def _get_department_formation(department):
    """Return the formation assigned to a department, if any."""
    if not department:
        return None
    return frappe.db.get_value("Leave Department", department, "formation")


def _get_scope_departments_for_approval(department):
    """Return the departments that share the approval path for a leave department."""
    if not department:
        return []

    formation = _get_department_formation(department)
    if not formation:
        return [department]

    departments = frappe.get_all(
        "Leave Department",
        filters={"formation": formation},
        pluck="name",
    )
    return departments or [department]


def _get_department_mapped_levels(department):
    """Return sorted unique approval levels configured for a department."""
    settings = _get_settings()
    levels = {
        row.approval_level
        for row in (settings.approver_mappings or [])
        if row.department == department and row.approval_level
    }
    return sorted(levels)


def _get_scope_mapped_levels(department):
    """Return approval levels available to a department's whole approval scope."""
    scope_departments = set(_get_scope_departments_for_approval(department))
    if not scope_departments:
        return []

    settings = _get_settings()
    levels = {
        row.approval_level
        for row in (settings.approver_mappings or [])
        if row.department in scope_departments and row.approval_level
    }
    return sorted(levels)


def _get_next_required_approval_level(department, current_level, max_required_level):
    """
    Return the next actionable approval level for a leave in a department.

    This allows gaps in global level sequence for specific departments,
    e.g. a department can move from level 1 directly to level 3 when
    level 2 is not mapped for that department.
    """
    current_level = current_level or 0
    max_required_level = max_required_level or 1

    if current_level >= max_required_level:
        return None

    mapped_levels = _get_scope_mapped_levels(department)
    if not mapped_levels:
        return current_level + 1 if current_level < max_required_level else None

    next_mapped = [lvl for lvl in mapped_levels if current_level < lvl <= max_required_level]
    if next_mapped:
        return next_mapped[0]

    # If no mapped level exists in the bounded range, jump to the next mapped
    # level after current (supports departments that intentionally skip levels).
    next_after_current = [lvl for lvl in mapped_levels if lvl > current_level]
    if next_after_current:
        return next_after_current[0]

    return None


def _is_same_approval_scope(source_department, target_department):
    """Check whether two departments share the same approval scope."""
    if not source_department or not target_department:
        return False
    if source_department == target_department:
        return True

    source_formation = _get_department_formation(source_department)
    target_formation = _get_department_formation(target_department)
    return bool(source_formation and source_formation == target_formation)


def _should_limit_user_to_direct_departments(user):
    """Department Head should be restricted to their directly mapped departments."""
    roles = set(frappe.get_roles(user))
    has_department_head_role = "Department Head" in roles
    has_global_approval_role = (
        "System Manager" in roles
        or "University President" in roles
        or "University Presedent" in roles
    )
    return has_department_head_role and not has_global_approval_role


def _user_can_approve_level_for_department(user, department, approval_level):
    """Return True when the user can approve the target level for the leave department."""
    if not user or not department or not approval_level:
        return False

    direct_department_only = _should_limit_user_to_direct_departments(user)

    for info in _get_user_approver_info(user):
        if info.get("approval_level") != approval_level:
            continue
        if direct_department_only:
            if info.get("department") == department:
                return True
            continue

        if _is_same_approval_scope(info.get("department"), department):
            return True

    return False


def _annotate_next_approval_levels(leaves):
    """Attach next_approval_level to each leave row for UI/status rendering."""
    for row in leaves:
        current_level = row.get("current_approval_level") or 0
        max_level = row.get("max_required_level") or 1
        row["next_approval_level"] = _get_next_required_approval_level(
            row.get("dep"), current_level, max_level
        )
    return leaves


def _resolve_employee_user(employee_value):
    """Resolve an employee filter value to a User id when possible."""
    if not employee_value:
        return None

    employee_value = str(employee_value).strip()
    if not employee_value:
        return None

    user = frappe.db.get_value("Leave Employee", {"user": employee_value}, "user")
    if user:
        return user

    user = frappe.db.get_value("Leave Employee", {"full_name": employee_value}, "user")
    if user:
        return user

    if frappe.db.exists("User", employee_value):
        return employee_value

    return None


def _get_user_approver_info(user):
    """
    Return a list of dicts: [{department, approval_level}, ...]
    for all departments/levels this user can approve.
    """
    settings = _get_settings()
    roles = frappe.get_roles(user)

    results = []
    for mapping in settings.approver_mappings or []:
        if mapping.user == user:
            results.append({
                "department": mapping.department,
                "approval_level": mapping.approval_level
            })

    return results


def _get_user_visible_departments(user):
    """
    Return list of department names that a Follow Up / HR user can see.
    If the user has no entries in department_visibility, they see ALL departments.
    """
    settings = _get_settings()
    departments = []
    for row in settings.department_visibility or []:
        if row.user == user:
            departments.append(row.department)
    return departments  # empty list = all departments


def _get_workflow_state_for_level(current_level, max_level):
    """Map the current approval level to a workflow state string."""
    if current_level == 0:
        return "Applied"
    elif current_level >= max_level:
        return "Approved"
    else:
        return "Approved By Department"


def _get_workflow_display(workflow_state, current_level, max_level):
    """Get the display label for the current state, incorporating level info."""
    if workflow_state == "Pending":
        return "قيد الإنتظار"
    elif workflow_state == "Applied":
        next_level = 1
        level_name = _get_level_name(next_level)
        return f"بانتظار موافقة {level_name}"
    elif workflow_state == "Rejected":
        return "مرفوضة"
    elif workflow_state == "Approved":
        return "مقبولة"
    elif workflow_state == "Approved By Department":
        # Intermediate approval — show which level is next
        next_level = (current_level or 0) + 1
        level_name = _get_level_name(next_level)
        return f"بانتظار موافقة {level_name}"
    return workflow_state


# ─────────────────────────────────────────────────────────────────────────────
# API: Data Fetching
# ─────────────────────────────────────────────────────────────────────────────

LEAVE_FIELDS = [
    "name", "employee", "employee_fullname", "dep",
    "leave_type", "original_leave", "from_date", "to_date", "days",
    "is_time_leave", "number_of_hours",
    "reason", "workflow_state", "status",
    "date_of_application", "alternative_employee",
    "supervisor", "attachment", "personal_email",
    "current_approval_level", "max_required_level", "level_approvals"
]

LEAVE_FIELDS_FOLLOWUP = LEAVE_FIELDS + ["printed", "is_read"]


@frappe.whitelist()
def get_employee_leaves(from_date=None, to_date=None, leave_type=None, status=None, dep=None, employee_name=None, printed=None):
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
        fields=LEAVE_FIELDS,
        order_by="modified desc",
        limit_page_length=100,
    )
    return _annotate_next_approval_levels(leaves)


@frappe.whitelist()
def get_pending_approval_leaves(from_date=None, to_date=None, leave_type=None, status=None, dep=None, employee_name=None, printed=None):
    """
    Get leaves awaiting approval from the current user.
    Uses the Leave Approver Mapping to determine which departments/levels this user approves.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    is_admin = "System Manager" in roles

    approver_info = _get_user_approver_info(user)

    if not approver_info and not is_admin:
        return []

    dept_level_map = {}  # {department in approval scope: {levels}}

    if is_admin and not approver_info:
        # Admin sees all pending leaves
        all_filters = {}
        if status and status != "All":
            all_filters["workflow_state"] = status
        else:
            all_filters["workflow_state"] = ["in", ["Applied", "Approved By Department"]]

        if from_date:
            all_filters["from_date"] = [">=", from_date]
        if to_date:
            all_filters["to_date"] = ["<=", to_date]
        if leave_type:
            all_filters["leave_type"] = leave_type

        if employee_name:
            resolved_user = _resolve_employee_user(employee_name)
            if resolved_user:
                all_filters["employee"] = resolved_user
            else:
                all_filters["employee_fullname"] = employee_name

        leaves = frappe.get_all(
            "Leave",
            filters=all_filters,
            fields=LEAVE_FIELDS,
            order_by="modified desc",
            limit_page_length=200,
        )
        return _annotate_next_approval_levels(leaves)

    direct_department_only = _should_limit_user_to_direct_departments(user)

    for info in approver_info:
        dept = info["department"]
        level = info["approval_level"]
        scoped_departments = [dept] if direct_department_only else _get_scope_departments_for_approval(dept)
        for scoped_dept in scoped_departments:
            if scoped_dept not in dept_level_map:
                dept_level_map[scoped_dept] = set()
            dept_level_map[scoped_dept].add(level)

    if not dept_level_map:
        return []

    # Base filters for candidate leaves in departments this user can approve.
    filters = {"dep": ["in", list(dept_level_map.keys())]}

    # Status filtering
    if status and status != "All":
        filters["workflow_state"] = status
    else:
        filters["workflow_state"] = ["in", ["Applied", "Approved By Department"]]

    # Date and leave type filtering
    if from_date:
        filters["from_date"] = [">=", from_date]
    if to_date:
        filters["to_date"] = ["<=", to_date]
    if leave_type:
        filters["leave_type"] = leave_type

    resolved_user = _resolve_employee_user(employee_name) if employee_name else None

    candidate_leaves = frappe.get_all(
        "Leave",
        filters=filters,
        fields=LEAVE_FIELDS,
        order_by="modified desc",
        limit_page_length=500,
    )

    leaves = []
    for leave in candidate_leaves:
        if employee_name:
            if resolved_user and leave.employee != resolved_user:
                continue
            if not resolved_user and leave.employee_fullname != employee_name:
                continue

        dept_levels = dept_level_map.get(leave.dep, set())
        next_level = _get_next_required_approval_level(
            leave.dep,
            leave.current_approval_level or 0,
            leave.max_required_level or 1,
        )
        if next_level and next_level in dept_levels:
            leave["next_approval_level"] = next_level
            leaves.append(leave)

    # If admin, also add leaves they haven't already covered
    if is_admin:
        existing_names = {l.name for l in leaves}
        admin_filters = {"workflow_state": ["in", ["Applied", "Approved By Department"]]}
        if from_date:
            admin_filters["from_date"] = [">=", from_date]
        if to_date:
            admin_filters["to_date"] = ["<=", to_date]
        if leave_type:
            admin_filters["leave_type"] = leave_type
        admin_leaves = frappe.get_all("Leave", filters=admin_filters, fields=LEAVE_FIELDS, limit_page_length=200)
        for al in admin_leaves:
            if al.name not in existing_names:
                leaves.append(al)

    return _annotate_next_approval_levels(leaves)


@frappe.whitelist()
def get_all_leaves(from_date=None, to_date=None, leave_type=None, status=None, dep=None, employee_name=None, printed=None):
    """Get all leaves for Follow Up / HR Employee — filtered by department visibility."""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    settings = _get_settings()
    hr_role = settings.hr_employee_role or "HR Employee"

    if "Follow Up Employee" not in roles and hr_role not in roles and "System Manager" not in roles:
        frappe.throw(_("Access Denied"))

    filters = {}

    # Apply department visibility restrictions
    if "System Manager" not in roles:
        visible_depts = _get_user_visible_departments(user)
        if visible_depts:
            filters["dep"] = ["in", visible_depts]

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
        filters["workflow_state"] = ["in", ["Pending", "Applied", "Approved By Department", "Approved"]]

    if dep:
        if "dep" in filters and isinstance(filters["dep"], list) and filters["dep"][0] == "in":
            if dep in filters["dep"][1]:
                filters["dep"] = dep
            else:
                return []
        else:
            filters["dep"] = dep
    if employee_name:
        resolved_user = _resolve_employee_user(employee_name)
        if resolved_user:
            filters["employee"] = resolved_user
        else:
            filters["employee_fullname"] = employee_name

    if printed == "Printed":
        filters["printed"] = 1
    elif printed == "Not Printed":
        filters["printed"] = 0

    try:
        leaves = frappe.get_all(
            "Leave",
            filters=filters,
            fields=LEAVE_FIELDS_FOLLOWUP,
            order_by="modified desc",
            limit_page_length=500,
        )
    except Exception:
        leaves = frappe.get_all(
            "Leave",
            filters=filters,
            fields=LEAVE_FIELDS,
            order_by="modified desc",
            limit_page_length=500,
        )
    return _annotate_next_approval_levels(leaves)


@frappe.whitelist()
def get_proxy_leaves(from_date=None, to_date=None, leave_type=None, status=None, dep=None, employee_name=None, printed=None):
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
        fields=LEAVE_FIELDS,
        order_by="modified desc",
        limit_page_length=100,
    )
    return _annotate_next_approval_levels(leaves)


# ─────────────────────────────────────────────────────────────────────────────
# API: Action Log Helper
# ─────────────────────────────────────────────────────────────────────────────

def _append_action_log(doc, message, user=None):
    if not user:
        user = frappe.session.user
    if user == "System":
        user_display = "النظام التلقائي (System)"
    else:
        user_name = frappe.db.get_value("User", user, "full_name") or user
        user_display = f"{user_name} ({user})"
    timestamp = frappe.utils.now()
    current_log = doc.action_log or ""
    entry = f"[{timestamp}] - {message} - {user_display}\n"
    doc.action_log = current_log + entry


# ─────────────────────────────────────────────────────────────────────────────
# API: Workflow Actions
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def apply_workflow_action(leave_name, action, comment=None):
    """Apply workflow action (Approve/Reject) with optional comment — multi-level aware."""
    doc = frappe.get_doc("Leave", leave_name)

    if comment:
        doc.add_comment("Comment", comment)

    user = frappe.session.user
    roles = frappe.get_roles(user)
    is_admin = "System Manager" in roles

    if action == "Apply":
        # Employee or proxy applying/re-applying leave
        can_apply = False
        if doc.workflow_state in ["Pending", "Rejected"]:
            if user in [doc.employee, doc.owner] or "Leave Proxy Submitter" in roles or "HR Employee" in roles or is_admin:
                can_apply = True
        if not can_apply:
            frappe.throw(_("Access Denied or invalid workflow transition."))

        doc.workflow_state = "Applied"
        doc.status = "Pending"
        _append_action_log(doc, "تقديم الطلب للتدقيق", user)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_workflow_validation = True
        doc.save(ignore_permissions=True)
        return {"status": "success", "new_state": doc.workflow_state}

    if action not in ["Approve", "Reject"]:
        frappe.throw(_("Invalid action"))

    # Determine the next actionable level for this department.
    next_level = _get_next_required_approval_level(
        doc.dep,
        doc.current_approval_level or 0,
        doc.max_required_level or 1,
    )

    if not next_level:
        frappe.throw(_("No further approval level is available for this request."))

    # Check if user is authorized to approve at the next level for this department
    if not is_admin:
        if not _user_can_approve_level_for_department(user, doc.dep, next_level):
            frappe.throw(_("Access Denied: You are not authorized to approve at level {0} for department {1}.").format(
                next_level, doc.dep
            ))

    if action == "Approve":
        # Record the level approval
        level_log = json.loads(doc.level_approvals or "[]")
        level_log.append({
            "level": next_level,
            "level_name": _get_level_name(next_level),
            "user": user,
            "user_name": frappe.db.get_value("User", user, "full_name") or user,
            "date": str(frappe.utils.today()),
            "datetime": str(frappe.utils.now())
        })
        doc.level_approvals = json.dumps(level_log, ensure_ascii=False)
        doc.current_approval_level = next_level

        _append_action_log(doc, f"موافقة المستوى {next_level} ({_get_level_name(next_level)})", user)

        upcoming_level = _get_next_required_approval_level(
            doc.dep,
            doc.current_approval_level or 0,
            doc.max_required_level or 1,
        )

        if not upcoming_level or doc.current_approval_level >= (doc.max_required_level or 1):
            # Final approval
            # When workflow requires an intermediate state for multi-level requests,
            # pass through it internally before final approval to keep transitions valid.
            if doc.workflow_state == "Applied" and (doc.max_required_level or 1) > 1:
                doc.workflow_state = "Approved By Department"
                doc.status = "Pending"
                if not doc.date_of_supervisor_action:
                    doc.date_of_supervisor_action = frappe.utils.today()
                doc.flags.ignore_permissions = True
                doc.flags.ignore_workflow_validation = True
                doc.save(ignore_permissions=True)

            doc.workflow_state = "Approved"
            doc.status = "Approved"
            doc.approved_by = user
            doc.approved_by_name = frappe.db.get_value("User", user, "full_name") or user
            doc.approved_by_email = frappe.db.get_value("User", user, "email") or user
            doc.approved_on = frappe.utils.now_datetime()
            doc.date_of_presidant_action = frappe.utils.today()
            _append_action_log(doc, "الموافقة النهائية", user)
            doc.flags.ignore_permissions = True
            doc.flags.ignore_workflow_validation = True
            doc.submit()
        else:
            # Intermediate approval — keep in intermediate state
            if next_level == 1:
                doc.workflow_state = "Approved By Department"
                doc.date_of_supervisor_action = frappe.utils.today()
            else:
                doc.workflow_state = "Approved By Department"
            doc.status = "Pending"
            doc.flags.ignore_permissions = True
            doc.flags.ignore_workflow_validation = True
            doc.save(ignore_permissions=True)

    elif action == "Reject":
        if doc.current_approval_level == 0:
            doc.date_of_supervisor_action = frappe.utils.today()
        else:
            doc.date_of_presidant_action = frappe.utils.today()
        doc.workflow_state = "Rejected"
        doc.status = "Rejected"
        _append_action_log(doc, "رفض الطلب", user)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_workflow_validation = True
        doc.save(ignore_permissions=True)

    return {"status": "success", "new_state": doc.workflow_state}


# ─────────────────────────────────────────────────────────────────────────────
# API: Metadata & Roles
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_leave_types():
    """Get all leave types"""
    return frappe.get_all("Leave Type", fields=["name", "leave_type", "has_balance"])


@frappe.whitelist()
def get_departments():
    """Get departments — filtered by visibility for Follow Up / HR users."""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    filters = {}

    settings = _get_settings()
    hr_role = settings.hr_employee_role or "HR Employee"

    if "System Manager" not in roles and (hr_role in roles or "Follow Up Employee" in roles):
        visible_depts = _get_user_visible_departments(user)
        if visible_depts:
            filters["name"] = ["in", visible_depts]

    return frappe.get_all("Leave Department", filters=filters, fields=["name", "department_name"])


@frappe.whitelist()
def get_leave_employees():
    """Get employees filtered by role scope and department visibility."""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    filters = {}

    settings = _get_settings()
    hr_role = settings.hr_employee_role or "HR Employee"

    if "System Manager" in roles:
        return frappe.get_all("Leave Employee", filters=filters, fields=["name", "user", "full_name"], limit_page_length=0)

    # University President should always see all employees.
    # Keep both spellings for backward compatibility with existing role data.
    if "University President" in roles or "University Presedent" in roles:
        return frappe.get_all("Leave Employee", filters=filters, fields=["name", "user", "full_name"], limit_page_length=0)

    # Top approval role (highest configured level) can see all employees.
    approval_levels = _get_approval_levels()
    highest_level = max([lvl.level for lvl in approval_levels], default=0)
    top_approver_roles = {
        lvl.role for lvl in approval_levels
        if lvl.level == highest_level and lvl.role
    }
    if top_approver_roles.intersection(set(roles)):
        return frappe.get_all("Leave Employee", filters=filters, fields=["name", "user", "full_name"], limit_page_length=0)

    allowed_departments = None

    # Department approvers are limited to departments from approver mappings.
    approver_info = _get_user_approver_info(user)
    if approver_info:
        approver_departments = {row.get("department") for row in approver_info if row.get("department")}
        allowed_departments = approver_departments

    # Follow Up / HR visibility is applied as an additional restriction when configured.
    if hr_role in roles or "Follow Up Employee" in roles:
        visible_depts = set(_get_user_visible_departments(user) or [])
        if visible_depts:
            if allowed_departments is None:
                allowed_departments = visible_depts
            else:
                allowed_departments = allowed_departments.intersection(visible_depts)

    if allowed_departments is not None:
        if not allowed_departments:
            return []
        filters["leave_department"] = ["in", sorted(allowed_departments)]

    return frappe.get_all("Leave Employee", filters=filters, fields=["name", "user", "full_name"], limit_page_length=0)


def ensure_proxy_role_exists():
    if not frappe.db.exists("Role", "Leave Proxy Submitter"):
        role = frappe.new_doc("Role")
        role.role_name = "Leave Proxy Submitter"
        role.insert(ignore_permissions=True)


@frappe.whitelist()
def get_user_roles():
    """Get current user's roles relevant to this page — settings-driven."""
    ensure_proxy_role_exists()
    user = frappe.session.user
    roles = frappe.get_roles(user)

    settings = _get_settings()
    hr_role = settings.hr_employee_role or "HR Employee"

    # Check if user is an approver (has any mapping)
    approver_info = _get_user_approver_info(user)
    is_approver = len(approver_info) > 0

    # Get approval levels information for this user
    approval_departments = []
    for info in approver_info:
        approval_departments.append({
            "department": info["department"],
            "level": info["approval_level"],
            "level_name": _get_level_name(info["approval_level"])
        })

    return {
        "is_employee": "University Employee" in roles,
        "is_approver": is_approver or "System Manager" in roles,
        "approval_departments": approval_departments,
        "is_follow_up": "Follow Up Employee" in roles or hr_role in roles or "System Manager" in roles,
        "is_admin": "System Manager" in roles,
        "is_proxy_submitter": "Leave Proxy Submitter" in roles or "System Manager" in roles,
        "user": user,
    }


@frappe.whitelist()
def get_approval_level_names():
    """Get all configured approval level names for status display."""
    levels = _get_approval_levels()
    return [{"level": lvl.level, "name": lvl.level_name} for lvl in levels]


# ─────────────────────────────────────────────────────────────────────────────
# API: Leave Creation
# ─────────────────────────────────────────────────────────────────────────────

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
        employee_fullname = frappe.db.get_value("User", target_employee, "full_name") or target_employee
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

    # Calculate max_required_level based on days (will be recalculated in validate)
    # but set it here so it's available before save
    doc.current_approval_level = 0
    doc.max_required_level = 0  # Will be set in validate

    doc.workflow_state = "Pending"
    doc.status = "Draft"
    _append_action_log(doc, "إنشاء طلب الإجازة", user)
    doc.insert()

    # Apply the "Apply" workflow action to move from Pending -> Applied
    try:
        doc.workflow_state = "Applied"
        doc.status = "Pending"
        _append_action_log(doc, "تقديم الطلب للتدقيق", user)
        doc.flags.ignore_permissions = True
        doc.flags.ignore_workflow_validation = True
        doc.save(ignore_permissions=True)
    except Exception:
        pass

    return doc.name


# ─────────────────────────────────────────────────────────────────────────────
# API: Printing
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_bulk_print_html(leave_names):
    """Get the combined print HTML for multiple leaves"""
    if isinstance(leave_names, str):
        leave_names = json.loads(leave_names)

    html_content = ""
    for name in leave_names:
        if not frappe.has_permission("Leave", doc=name, ptype="read"):
            frappe.throw(_("Access Denied to view leave {0}").format(name))

        rendered = frappe.get_print(
            doctype="Leave",
            name=name,
            print_format="Leave Print Form",
            no_letterhead=True
        )
        html_content += f'<div class="bulk-print-page" style="page-break-after: always; padding: 20px;">{rendered}</div>'

    return html_content


@frappe.whitelist()
def mark_leaves_as_printed(leave_names):
    """Mark a list of leaves as printed"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    settings = _get_settings()
    hr_role = settings.hr_employee_role or "HR Employee"
    if "System Manager" not in roles and "Follow Up Employee" not in roles and hr_role not in roles:
        frappe.throw(_("Access Denied"))

    if isinstance(leave_names, str):
        leave_names = json.loads(leave_names)

    for name in leave_names:
        frappe.db.set_value("Leave", name, "printed", 1)

    frappe.db.commit()
    return {"status": "success"}


# ─────────────────────────────────────────────────────────────────────────────
# API: Leave Comments
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# API: Miscellaneous Actions
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def remove_wrong_department_leave(leave_name):
    """Remove a leave if the employee does not belong to the department (approver action)"""
    user = frappe.session.user
    roles = frappe.get_roles(user)

    doc = frappe.get_doc("Leave", leave_name)

    if "System Manager" not in roles:
        # Check if user is an approver for this department at the next required level
        approver_info = _get_user_approver_info(user)
        authorized = False
        for info in approver_info:
            if info["department"] == doc.dep:
                authorized = True
                break
        if not authorized:
            frappe.throw(_("Access Denied: You are not an approver for this department."))

    frappe.delete_doc("Leave", leave_name, force=1)
    return {"status": "success"}


@frappe.whitelist()
def withdraw_leave(leave_name):
    """Allows an employee to withdraw/cancel their own leave before approval"""
    user = frappe.session.user

    doc = frappe.get_doc("Leave", leave_name)

    # Verify ownership
    if doc.employee != user and doc.owner != user:
        roles = frappe.get_roles(user)
        if "System Manager" not in roles and "Leave Proxy Submitter" not in roles:
            frappe.throw(_("Access Denied: You can only withdraw your own leaves."))

    # Check state
    if doc.workflow_state not in ["Pending", "Applied"]:
        frappe.throw(_("You can only withdraw leaves that have not yet been approved by any level."))

    if doc.docstatus == 1:
        doc.flags.ignore_permissions = True
        doc.flags.ignore_workflow_validation = True
        doc.cancel()

    frappe.db.set_value("Leave", leave_name, "workflow_state", "Rejected")
    frappe.db.set_value("Leave", leave_name, "status", "Rejected")

    current_log = frappe.db.get_value("Leave", leave_name, "action_log") or ""
    user_name = frappe.db.get_value("User", user, "full_name") or user
    entry = f"[{frappe.utils.now()}] - سحب الطلب وإلغاؤه - {user_name} ({user})\n"
    frappe.db.set_value("Leave", leave_name, "action_log", current_log + entry)

    doc.add_comment("Comment", "تم سحب الإجازة من قبل الموظف")

    frappe.db.delete("Leave Balance Transaction", {"note": ["like", f"%{leave_name}%"]})

    return {"status": "success"}


@frappe.whitelist()
def toggle_leave_read(leave_name, is_read):
    """Toggle the read state of a leave"""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    settings = _get_settings()
    hr_role = settings.hr_employee_role or "HR Employee"
    if "System Manager" not in roles and "Follow Up Employee" not in roles and hr_role not in roles:
        frappe.throw(_("Access Denied"))

    try:
        frappe.db.set_value("Leave", leave_name, "is_read", int(is_read))
    except Exception:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
        create_custom_field('Leave', dict(
            fieldname='is_read',
            label='Is Read',
            fieldtype='Check',
            default='0'
        ))
        frappe.db.set_value("Leave", leave_name, "is_read", int(is_read))

    return {"status": "success"}

# Copyright (c) 2026, Computer Center of UoT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta


def _get_settings():
    """Return the cached Leave Settings singleton."""
    return frappe.get_cached_doc("Leave Settings")


def _compute_max_required_level(days):
    """
    Given the number of leave days, determine the maximum approval level required.
    Mirrors the logic in leave_managment.py for consistency.
    """
    settings = _get_settings()
    levels = sorted(settings.approval_levels or [], key=lambda r: r.level)
    if not levels:
        return 1  # fallback: at least 1 level

    max_level = 0
    for lvl in levels:
        min_d = lvl.min_days or 0
        max_d = lvl.max_days or 0

        if min_d == 0 or days >= min_d:
            max_level = lvl.level
            if max_d > 0 and days <= max_d:
                return lvl.level

    return max_level if max_level > 0 else 1


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)
    if "System Manager" in roles:
        return ""

    conditions = []

    # University Employee or Leave Proxy Submitter should see leaves they own OR leaves where they are the target employee
    if "University Employee" in roles or "Leave Proxy Submitter" in roles:
        conditions.append(f"(`tabLeave`.employee = {frappe.db.escape(user)} OR `tabLeave`.owner = {frappe.db.escape(user)})")

    # Approvers: check Leave Approver Mapping — resolve formations to departments
    settings = _get_settings()
    approver_formations = set()
    approver_explicit_departments = set()
    for mapping in settings.approver_mappings or []:
        if mapping.user == user:
            if mapping.get("department"):
                approver_explicit_departments.add(mapping.department)
            elif mapping.formation:
                approver_formations.add(mapping.formation)

    allowed_approver_departments = set(approver_explicit_departments)
    if approver_formations:
        formation_depts = frappe.get_all(
            "Leave Department",
            filters={"formation": ["in", list(approver_formations)]},
            pluck="name",
        )
        allowed_approver_departments.update(formation_depts)

    if allowed_approver_departments:
        departments_str = ", ".join([frappe.db.escape(d) for d in allowed_approver_departments])
        conditions.append(f"`tabLeave`.dep IN ({departments_str})")

    # Follow Up / HR: check formation-based visibility
    hr_role = settings.hr_employee_role or "HR Employee"
    if "Follow Up Employee" in roles or hr_role in roles:
        visible_formations = set()
        visible_explicit_departments = set()
        for row in settings.department_visibility or []:
            if row.user == user:
                if row.get("department"):
                    visible_explicit_departments.add(row.department)
                elif row.formation:
                    visible_formations.add(row.formation)

        allowed_visible_departments = set(visible_explicit_departments)
        if visible_formations:
            formation_depts = frappe.get_all(
                "Leave Department",
                filters={"formation": ["in", list(visible_formations)]},
                pluck="name",
            )
            allowed_visible_departments.update(formation_depts)

        if allowed_visible_departments:
            depts_str = ", ".join([frappe.db.escape(d) for d in allowed_visible_departments])
            conditions.append(f"`tabLeave`.dep IN ({depts_str})")
        else:
            # No visibility restrictions = see all
            return ""

    if conditions:
        return " OR ".join(conditions)

    return f"(`tabLeave`.employee = {frappe.db.escape(user)} OR `tabLeave`.owner = {frappe.db.escape(user)})"


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
            if self.employee_fullname:
                leave_employee.full_name = self.employee_fullname
            if self.dep:
                leave_employee.leave_department = self.dep
            leave_employee.save(ignore_permissions=True)

        if self.status == "Rejected":
            frappe.db.delete("Leave Balance Transaction", {"note": ["like", f"%{self.name}%"]})

    def on_update_after_submit(self):
        if self.status == "Rejected":
            frappe.db.delete("Leave Balance Transaction", {"note": ["like", f"%{self.name}%"]})

    def autoname(self):
        # Get formation from department
        formation = "General"
        if self.dep:
            formation = frappe.db.get_value("Leave Department", self.dep, "formation") or "General"

        year = frappe.utils.today()[:4]
        series_key = f"LEAVE-{formation}-{year}"

        # Increment and fetch counter manually to avoid left zero padding
        frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, 1) ON DUPLICATE KEY UPDATE current = current + 1", (series_key,))
        counter = frappe.db.sql("SELECT current FROM `tabSeries` WHERE name = %s", (series_key,))[0][0]

        # Generate the standard western string with formation to prevent duplicate names across formations
        formation_display = "عام" if formation == "General" else formation
        standard_name = f"أ-{formation_display}-{year}-{counter}"

        # Convert digits to eastern arabic numerals
        translation_table = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
        self.name = standard_name.translate(translation_table)

    def before_save(self):
        # Calculate max_required_level based on days
        if self.from_date and self.to_date:
            if self.is_time_leave:
                days = 1  # Time leaves count as 1 day for level calculation
            else:
                days = calculate_leave_days(self.from_date, self.to_date)
            self.max_required_level = _compute_max_required_level(days)

        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.status != self.status:
                if self.status == "Approved":
                    if not self.approved_by or self.approved_by == "Administrator":
                        u = frappe.session.user
                        self.approved_by = u
                        self.approved_by_name = frappe.db.get_value("User", u, "full_name") or u
                        self.approved_by_email = frappe.db.get_value("User", u, "email") or u
                        self.approved_on = frappe.utils.now_datetime()

    def validate(self):
        """Validate and calculate leave days, excluding holidays and weekends"""
        # Calculate days first (excluding holidays and weekends)
        if self.from_date and self.to_date:
            if self.is_time_leave:
                self.days = 0
            else:
                self.days = calculate_leave_days(self.from_date, self.to_date)

        # Calculate max_required_level
        if self.days is not None:
            effective_days = 1 if self.is_time_leave else (self.days or 1)
            self.max_required_level = _compute_max_required_level(effective_days)

        # If this is a Cancellation request
        if self.leave_type == "إلغاء إجازة":
            if not self.original_leave:
                frappe.throw(_("Original Leave is required for a cancellation request."))

            original_leave_doc = frappe.get_doc("Leave", self.original_leave)

            # Validate employee matches
            if original_leave_doc.employee != self.employee:
                frappe.throw(_("The original leave must belong to the same employee."))

            # Validate original leave is approved
            if original_leave_doc.status != "Approved":
                frappe.throw(_("Only approved leaves can be cancelled. The original leave is currently {0}.").format(original_leave_doc.status))

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
                    "status": ["!=", "Rejected"],
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
        if self.employee and self.leave_type and (self.days > 0 or self.is_time_leave):
            has_balance = frappe.db.get_value("Leave Type", self.leave_type, "has_balance")

            if has_balance:
                # Get the leave balance for the selected leave type
                balance_info = get_leave_balance(self.employee, self.leave_type, self.name)
                total_balance = balance_info.get("total_balance", 0)

                # Check if balance is sufficient
                required_balance = (self.number_of_hours / 7.0) if self.is_time_leave else self.days
                if total_balance < required_balance:
                    frappe.throw(
                        _("Insufficient leave balance for {0}. Requested: {1}, Available: {2} days").format(
                            self.leave_type,
                            f"{self.number_of_hours} hours" if self.is_time_leave else f"{self.days} days",
                            total_balance
                        )
                    )

    def before_submit(self):
        """Validate that status is not Rejected before submission"""
        if self.status == "Rejected":
            frappe.throw(_("Cannot submit a Rejected leave request"))

    def on_submit(self):
        if self.status == "Rejected":
            return

        """Create a Leave Balance Transaction after submission"""
        if not self.days and not self.is_time_leave:
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
            transaction.balance = (original_leave_doc.number_of_hours / 7.0) if original_leave_doc.is_time_leave else self.days
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
            transaction.balance = (self.number_of_hours / 7.0) if self.is_time_leave else self.days
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
    """
    if not employee:
        return {}

    user = frappe.session.user
    roles = frappe.get_roles(user)

    # Access check: user can view their own, or if they are admin/HR/Follow Up/Approver
    if employee != user and "System Manager" not in roles:
        settings = _get_settings()
        hr_role = settings.hr_employee_role or "HR Employee"
        
        if hr_role not in roles and "Follow Up Employee" not in roles:
            # Check if user is an approver for the employee's department
            is_authorized = False
            emp_dep = frappe.db.get_value("Leave Employee", {"user": employee}, "leave_department")
            emp_formation = None
            if emp_dep:
                emp_formation = frappe.db.get_value("Leave Department", emp_dep, "formation")
            if emp_dep or emp_formation:
                for mapping in settings.approver_mappings or []:
                    if mapping.user == user:
                        if mapping.get("department") and mapping.department == emp_dep:
                            is_authorized = True
                            break
                        elif not mapping.get("department") and mapping.formation == emp_formation:
                            is_authorized = True
                            break
            
            if not is_authorized and current_leave_name:
                leave_dep = frappe.db.get_value("Leave", current_leave_name, "dep")
                leave_formation = None
                if leave_dep:
                    leave_formation = frappe.db.get_value("Leave Department", leave_dep, "formation")
                if leave_dep or leave_formation:
                    for mapping in settings.approver_mappings or []:
                        if mapping.user == user:
                            if mapping.get("department") and mapping.department == leave_dep:
                                is_authorized = True
                                break
                            elif not mapping.get("department") and mapping.formation == leave_formation:
                                is_authorized = True
                                break

            if not is_authorized:
                frappe.throw(_("Access Denied: You cannot view balances for this employee."))

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

        if current_leave_name:
            filters["name"] = ["!=", current_leave_name]

        leave_applications = frappe.get_all(
            "Leave",
            filters=filters,
            fields=["days", "status", "name", "is_time_leave", "number_of_hours"]
        )

        taken_days = 0
        for application in leave_applications:
            status = application.get("status")
            if status != "Rejected":
                if application.get("is_time_leave"):
                    taken_days += (application.get("number_of_hours", 0) / 7.0)
                else:
                    taken_days += application.get("days", 0)

        total_balance -= taken_days
        balances[leave_type] = total_balance

    return balances

@frappe.whitelist()
def get_leave_balance(employee, leave_type, current_leave_name=None):
    """
    Calculate the leave balance for an employee for a specific leave type.
    """
    if not employee or not leave_type:
        return {'total_balance': 0, 'applications': []}

    # For cancellation requests, balance should be computed against the
    # original leave type (not the synthetic "إلغاء إجازة" type).
    effective_leave_type = leave_type
    if leave_type == "إلغاء إجازة" and current_leave_name:
        original_leave_name = frappe.db.get_value("Leave", current_leave_name, "original_leave")
        if original_leave_name:
            original_type = frappe.db.get_value("Leave", original_leave_name, "leave_type")
            if original_type:
                effective_leave_type = original_type

    user = frappe.session.user
    roles = frappe.get_roles(user)

    if employee != user and "System Manager" not in roles:
        settings = _get_settings()
        hr_role = settings.hr_employee_role or "HR Employee"
        
        if hr_role not in roles and "Follow Up Employee" not in roles:
            is_authorized = False
            emp_dep = frappe.db.get_value("Leave Employee", {"user": employee}, "leave_department")
            emp_formation = None
            if emp_dep:
                emp_formation = frappe.db.get_value("Leave Department", emp_dep, "formation")
            if emp_formation:
                for mapping in settings.approver_mappings or []:
                    if mapping.user == user and mapping.formation == emp_formation:
                        is_authorized = True
                        break

            if not is_authorized and current_leave_name:
                leave_dep = frappe.db.get_value("Leave", current_leave_name, "dep")
                leave_formation = None
                if leave_dep:
                    leave_formation = frappe.db.get_value("Leave Department", leave_dep, "formation")
                if leave_formation:
                    for mapping in settings.approver_mappings or []:
                        if mapping.user == user and mapping.formation == leave_formation:
                            is_authorized = True
                            break

            if not is_authorized:
                frappe.throw(_("Access Denied: You cannot view balances for this employee."))

    # Get all leave balance transactions for this employee and leave type
    transactions = frappe.get_all(
        "Leave Balance Transaction",
        filters={
            "employee": employee,
            "leave_type": effective_leave_type
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
        "leave_type": effective_leave_type,
        "docstatus": 0,
    }

    if current_leave_name:
        filters["name"] = ["!=", current_leave_name]

    leave_applications = frappe.get_all(
        "Leave",
        filters=filters,
        fields=["days", "status", "is_time_leave", "number_of_hours"]
    )

    taken_days = 0
    for application in leave_applications:
        status = application.get("status")
        if status != "Rejected":
            if application.get("is_time_leave"):
                taken_days += (application.get("number_of_hours", 0) / 7.0)
            else:
                taken_days += application.get("days", 0)

    total_balance -= taken_days
    return {
        'total_balance': total_balance,
        'applications': leave_applications,
        'effective_leave_type': effective_leave_type,
    }

@frappe.whitelist()
def calculate_leave_days(from_date, to_date):
    """
    Calculate leave days excluding holidays from Holiday DocType.
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
            "status": ["!=", "Rejected"],
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
    all_cancellations = frappe.get_all(
        "Leave",
        filters={
            "employee": employee,
            "leave_type": "إلغاء إجازة",
            "status": ["!=", "Rejected"]
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

import frappe
from frappe.utils import today
import json

@frappe.whitelist()
def get_data(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    else:
        filters = filters or {}

    user_filters = {"user_type": "System User"}
    if filters.get("user"):
        user_filters["name"] = filters.get("user")

    # Formation-based access control (skip for System Manager)
    allowed_departments = None
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        current_le = frappe.get_value(
            "Leave Employee", {"user": frappe.session.user}, ["leave_department"], as_dict=True
        )
        if current_le and current_le.leave_department:
            formation = frappe.get_value(
                "Leave Department", current_le.leave_department, "formation"
            )
            if formation:
                dept_docs = frappe.get_all(
                    "Leave Department",
                    filters={"formation": formation},
                    fields=["name"]
                )
                allowed_departments = [d.name for d in dept_docs]
            else:
                # Department exists but has no formation — only show own department
                allowed_departments = [current_le.leave_department]
        else:
            # Current user has no Leave Employee record — show nothing
            allowed_departments = []

    # users
    users = frappe.get_all("User", filters=user_filters, fields=["name", "full_name", "first_name", "middle_name", "last_name", "email"], order_by="name asc")
    
    # profiles
    emails = [u.email for u in users if u.email]
    profiles = {}
    if emails:
        profile_docs = frappe.get_all("Profile", filters={"email": ["in", emails], "cv_language": "Arabic"}, fields=["email", "first_name", "second_name", "third_name", "family_name"])
        for p in profile_docs:
            name_parts = [p.first_name, p.second_name, p.third_name, p.family_name]
            profiles[p.email] = " ".join([n for n in name_parts if n])
            
    # leave employees
    user_names = [u.name for u in users]
    leave_employees = {}
    if user_names:
        le_docs = frappe.get_all("Leave Employee", filters={"user": ["in", user_names]}, fields=["name", "user", "full_name", "leave_department", "type"])
        for le in le_docs:
            leave_employees[le.user] = le
            
    # leave types
    leave_types = frappe.get_all("Leave Type", filters={"has_balance": 1}, fields=["name"], order_by="name asc")
    
    # balances
    balances = {}
    if user_names:
        txns = frappe.get_all("Leave Balance Transaction", filters={"employee": ["in", user_names]}, fields=["employee", "leave_type", "transaction_type", "balance"])
        for t in txns:
            if t.employee not in balances:
                balances[t.employee] = {}
            if t.leave_type not in balances[t.employee]:
                balances[t.employee][t.leave_type] = 0.0
                
            if t.transaction_type == "Addition":
                balances[t.employee][t.leave_type] += t.balance
            elif t.transaction_type == "Consumption":
                balances[t.employee][t.leave_type] -= t.balance

    data = []
    for u in users:
        p_name = profiles.get(u.email, "")
        le_name = leave_employees.get(u.name, {}).get("full_name", "")
        le_dept = leave_employees.get(u.name, {}).get("leave_department", "")
        le_type = leave_employees.get(u.name, {}).get("type", "")
        
        # Apply python-side filters for joined fields
        if filters.get("profile_full_name") and filters.get("profile_full_name").lower() not in p_name.lower():
            continue
        if filters.get("leave_employee_name") and filters.get("leave_employee_name").lower() not in le_name.lower():
            continue
        if filters.get("leave_department") and filters.get("leave_department") != le_dept:
            continue
        if filters.get("leave_employee_type") and filters.get("leave_employee_type") != le_type:
            continue
        if filters.get("no_balance") and int(filters.get("no_balance")):
            if balances.get(u.name):  # has at least one leave type with a transaction
                continue
        # Formation access control: only show employees in allowed departments
        if allowed_departments is not None and le_dept not in allowed_departments:
            continue

        row = {
            "user": u.name,
            "user_full_name": u.full_name,
            "first_name": u.first_name or "",
            "middle_name": u.middle_name or "",
            "last_name": u.last_name or "",
            "profile_full_name": p_name,
            "leave_employee_name": le_name,
            "leave_department": le_dept,
            "leave_employee_type": le_type,
            "balances": balances.get(u.name, {})
        }
        data.append(row)
        
    return {
        "users": data,
        "leave_types": [lt.name for lt in leave_types]
    }
 
@frappe.whitelist()
def save_user_row(user, leave_employee_name, leave_department, balances, first_name=None, middle_name=None, last_name=None, leave_employee_type=None):
    if isinstance(balances, str):
        balances = json.loads(balances)
        
    if leave_employee_name == 'null' or leave_employee_name is None:
        leave_employee_name = ''
    if leave_department == 'null' or leave_department is None:
        leave_department = ''
    if leave_employee_type == 'null' or leave_employee_type is None:
        leave_employee_type = ''
        
    # Handle User Document fields
    user_doc = frappe.get_doc("User", user)
    user_changed = False
    if first_name is not None and user_doc.first_name != first_name:
        user_doc.first_name = first_name
        user_changed = True
    if middle_name is not None and user_doc.middle_name != middle_name:
        user_doc.middle_name = middle_name
        user_changed = True
    if last_name is not None and user_doc.last_name != last_name:
        user_doc.last_name = last_name
        user_changed = True
        
    if user_changed:
        user_doc.flags.ignore_permissions = True
        user_doc.save(ignore_permissions=True)
 
    if not leave_employee_name and (leave_department or leave_employee_type):
        # User specified department/type but no employee name. We default to User full name.
        leave_employee_name = frappe.get_value("User", user, "full_name") or user
 
    # Handle Leave Employee Document
    le = frappe.get_value("Leave Employee", {"user": user}, "name")
    if le:
        # Update existing
        if leave_employee_name:
            current_name = frappe.get_value("Leave Employee", le, "full_name")
            if current_name != leave_employee_name:
                frappe.flags.ignore_permissions = True
                frappe.rename_doc("Leave Employee", le, leave_employee_name)
                frappe.flags.ignore_permissions = False
                frappe.db.set_value("Leave Employee", leave_employee_name, "full_name", leave_employee_name)
                le = leave_employee_name
        
        frappe.db.set_value("Leave Employee", le, "leave_department", leave_department)
        frappe.db.set_value("Leave Employee", le, "type", leave_employee_type)
    else:
        # Create new
        if leave_employee_name or leave_department or leave_employee_type:
            if not leave_employee_name:
                frappe.throw("Leave Employee Name is required to save.")
            doc = frappe.get_doc({
                "doctype": "Leave Employee",
                "user": user,
                "full_name": leave_employee_name,
                "leave_department": leave_department,
                "type": leave_employee_type
            })
            doc.insert(ignore_permissions=True)

    # Handle Balances
    if balances:
        for lt, new_balance_str in balances.items():
            if new_balance_str == '':
                new_balance = 0.0
            else:
                new_balance = float(new_balance_str)
                
            # Calculate current balance
            txns = frappe.get_all("Leave Balance Transaction", 
                                  filters={"employee": user, "leave_type": lt}, 
                                  fields=["transaction_type", "balance"])
            
            current = 0.0
            for t in txns:
                if t.transaction_type == "Addition":
                    current += t.balance
                else:
                    current -= t.balance
                    
            diff = new_balance - current
            diff = round(diff, 2)
            
            if diff != 0:
                doc = frappe.get_doc({
                    "doctype": "Leave Balance Transaction",
                    "employee": user,
                    "leave_type": lt,
                    "transaction_type": "Addition" if diff > 0 else "Consumption",
                    "balance": abs(diff),
                    "date": today(),
                    "note": "Balance updated via Balance and Employee control panel"
                })
                doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return "success"

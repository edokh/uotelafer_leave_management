import frappe
from frappe.utils import today

@frappe.whitelist()
def get_data():
    # users
    users = frappe.get_all("User", filters={"user_type": "System User"}, fields=["name", "full_name", "email"], order_by="name asc")
    
    # profiles
    emails = [u.email for u in users if u.email]
    profiles = {}
    if emails:
        profile_docs = frappe.get_all("Profile", filters={"email": ["in", emails]}, fields=["email", "first_name", "second_name", "third_name", "family_name"])
        for p in profile_docs:
            name_parts = [p.first_name, p.second_name, p.third_name, p.family_name]
            profiles[p.email] = " ".join([n for n in name_parts if n])
            
    # leave employees
    user_names = [u.name for u in users]
    leave_employees = {}
    if user_names:
        le_docs = frappe.get_all("Leave Employee", filters={"user": ["in", user_names]}, fields=["name", "user", "full_name", "leave_department"])
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
        row = {
            "user": u.name,
            "user_full_name": u.full_name,
            "profile_full_name": profiles.get(u.email, ""),
            "leave_employee_name": leave_employees.get(u.name, {}).get("full_name", ""),
            "leave_department": leave_employees.get(u.name, {}).get("leave_department", ""),
            "balances": balances.get(u.name, {})
        }
        data.append(row)
        
    return {
        "users": data,
        "leave_types": [lt.name for lt in leave_types]
    }

@frappe.whitelist()
def update_user_data(user, field, value, leave_type=None):
    # Ensure value is parsed correctly for empty strings vs None
    if value == 'null' or value is None:
        value = ''
        
    if field == "leave_employee_name":
        if not value:
            frappe.throw("Leave Employee Name cannot be empty.")
            
        le = frappe.get_value("Leave Employee", {"user": user}, "name")
        if le:
            # Check if name is changing, maybe need to rename document? No, autoname is field:full_name. 
            # In frappe, if we change a field that is used for autoname (and allow_rename is 1), 
            # we should use frappe.rename_doc
            current_name = frappe.get_value("Leave Employee", le, "full_name")
            if current_name != value:
                frappe.rename_doc("Leave Employee", le, value, ignore_permissions=True)
                # the rename changes both name and full_name (if it's tied) but let's be safe
                frappe.db.set_value("Leave Employee", value, "full_name", value)
        else:
            doc = frappe.get_doc({
                "doctype": "Leave Employee",
                "user": user,
                "full_name": value
            })
            doc.insert(ignore_permissions=True)
                
    elif field == "leave_department":
        le = frappe.get_value("Leave Employee", {"user": user}, "name")
        if le:
            frappe.db.set_value("Leave Employee", le, "leave_department", value)
        else:
            if value:
                user_full_name = frappe.get_value("User", user, "full_name") or user
                doc = frappe.get_doc({
                    "doctype": "Leave Employee",
                    "user": user,
                    "full_name": user_full_name,
                    "leave_department": value
                })
                doc.insert(ignore_permissions=True)
                
    elif field == "balance" and leave_type:
        if value == '':
            value = 0.0
        new_balance = float(value)
        
        # Calculate current balance
        txns = frappe.get_all("Leave Balance Transaction", 
                              filters={"employee": user, "leave_type": leave_type}, 
                              fields=["transaction_type", "balance"])
        
        current = 0.0
        for t in txns:
            if t.transaction_type == "Addition":
                current += t.balance
            else:
                current -= t.balance
                
        diff = new_balance - current
        
        # We need to round to handle float imprecision
        diff = round(diff, 2)
        
        if diff != 0:
            doc = frappe.get_doc({
                "doctype": "Leave Balance Transaction",
                "employee": user,
                "leave_type": leave_type,
                "transaction_type": "Addition" if diff > 0 else "Consumption",
                "balance": abs(diff),
                "date": today(),
                "note": "Balance updated via Balance and Employee control panel"
            })
            doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return "success"

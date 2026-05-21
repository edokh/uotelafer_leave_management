import frappe
import json
from uotelafer_leave_management.uotelafer_leave_management.page.leave_managment.leave_managment import get_bulk_print_html, mark_leaves_as_printed, get_all_leaves

def run():
    print("Initializing bulk print test...")
    # Set user to Administrator
    frappe.set_user("Administrator")
    
    # 1. Fetch some approved or submitted leaves to test with
    leaves = frappe.get_all("Leave", limit_page_length=5)
    if not leaves:
        print("No leaves found in the database. Creating dummy leaves...")
        # Create a couple of dummy leaves to test
        l1 = frappe.get_doc({
            "doctype": "Leave",
            "employee": "Administrator",
            "employee_fullname": "Administrator",
            "leave_type": "اجازة اعتيادية",
            "from_date": "2026-06-01",
            "to_date": "2026-06-02",
            "reason": "Bulk print test 1",
            "dep": "مركز الحاسبة الالكترونية",
            "date_of_application": frappe.utils.today()
        }).insert(ignore_permissions=True)
        l2 = frappe.get_doc({
            "doctype": "Leave",
            "employee": "Administrator",
            "employee_fullname": "Administrator",
            "leave_type": "اجازة اعتيادية",
            "from_date": "2026-06-03",
            "to_date": "2026-06-04",
            "reason": "Bulk print test 2",
            "dep": "مركز الحاسبة الالكترونية",
            "date_of_application": frappe.utils.today()
        }).insert(ignore_permissions=True)
        names = [l1.name, l2.name]
    else:
        names = [l["name"] for l in leaves[:2]]

    print(f"Testing with leaves: {names}")
    
    # 2. Test get_bulk_print_html
    print("Testing get_bulk_print_html...")
    html = get_bulk_print_html(names)
    assert html is not None, "get_bulk_print_html returned None"
    assert "bulk-print-page" in html, "get_bulk_print_html result does not contain page div"
    print("get_bulk_print_html check passed! Rendered HTML length:", len(html))
    
    # 3. Test mark_leaves_as_printed
    print("Testing mark_leaves_as_printed...")
    # Ensure they are not printed first
    for name in names:
        frappe.db.set_value("Leave", name, "printed", 0)
    frappe.db.commit()
    
    res = mark_leaves_as_printed(names)
    assert res.get("status") == "success", f"mark_leaves_as_printed failed: {res}"
    
    # Verify DB values
    for name in names:
        printed = frappe.db.get_value("Leave", name, "printed")
        assert printed == 1, f"Expected printed=1 for {name}, got {printed}"
    print("mark_leaves_as_printed check passed!")
    
    # 4. Test get_all_leaves printed filter
    print("Testing get_all_leaves printed filtering...")
    # Printed leaves
    printed_leaves = get_all_leaves(printed="Printed")
    printed_names = [l["name"] for l in printed_leaves]
    for name in names:
        assert name in printed_names, f"Expected printed leave {name} to be in printed_leaves filter"
        
    # Not Printed leaves
    not_printed_leaves = get_all_leaves(printed="Not Printed")
    not_printed_names = [l["name"] for l in not_printed_leaves]
    for name in names:
        assert name not in not_printed_names, f"Expected printed leave {name} NOT to be in not_printed_leaves filter"
    
    print("get_all_leaves printed filtering check passed!")
    
    # Clean up if dummy docs were created
    if not leaves:
        for name in names:
            frappe.delete_doc("Leave", name, force=True)
        print("Cleaned up dummy leaves.")
        
    print("All backend bulk printing tests passed successfully!")

if __name__ == "__main__":
    run()

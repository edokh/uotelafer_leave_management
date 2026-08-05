"""
One-time migration patch to convert existing leave management data to the new
settings-driven multi-level approval system.

Run via: bench --site <site> execute uotelafer_leave_management.patches.restructure_approval_levels.execute
"""
import frappe
from frappe import _
import json


def execute():
    """
    1. Read existing Leave Department department_head mappings → create Leave Approver Mapping at level 1
    2. Read existing Leave Settings president/office config → create levels 2/3
    3. Set current_approval_level on existing leaves based on workflow_state
    4. Create default Leave Department Visibility from existing Leave Employee formation-based assignments
    """
    print("Starting migration: Restructure Approval Levels...")

    settings = frappe.get_doc("Leave Settings")

    # -------------------------------------------------------------------
    # Step 1: Create default approval levels if none exist
    # -------------------------------------------------------------------
    if not settings.approval_levels or len(settings.approval_levels) == 0:
        print("Creating default approval levels...")

        # Level 1: Department Head
        settings.append("approval_levels", {
            "level": 1,
            "level_name": "رئيس القسم",
            "min_days": 0,
            "max_days": 0,
            "role": "Department Head"
        })

        # Level 2: Final approver (was President Office / President)
        # Check if we had a president office role for ≤3 days
        old_max_days = 3
        try:
            old_max_days = frappe.db.get_single_value("Leave Settings", "number_of_days_for_presidant_approval") or 3
        except Exception:
            pass

        old_pres_office_role = None
        old_pres_role = None
        try:
            old_pres_office_role = frappe.db.get_single_value("Leave Settings", "presidant_office_role")
        except Exception:
            pass
        try:
            old_pres_role = frappe.db.get_single_value("Leave Settings", "presidant_role")
        except Exception:
            pass

        if old_pres_office_role and old_pres_role and old_pres_office_role != old_pres_role:
            # Two-tier final approval: office for ≤N days, president for >N days
            settings.append("approval_levels", {
                "level": 2,
                "level_name": "مكتب الرئيس",
                "min_days": 0,
                "max_days": int(old_max_days),
                "role": old_pres_office_role
            })
            settings.append("approval_levels", {
                "level": 3,
                "level_name": "رئيس الجامعة",
                "min_days": int(old_max_days) + 1,
                "max_days": 0,
                "role": old_pres_role
            })
        elif old_pres_role:
            settings.append("approval_levels", {
                "level": 2,
                "level_name": "رئيس الجامعة",
                "min_days": 0,
                "max_days": 0,
                "role": old_pres_role
            })
        else:
            # Fallback: just create a generic level 2
            settings.append("approval_levels", {
                "level": 2,
                "level_name": "الموافقة النهائية",
                "min_days": 0,
                "max_days": 0,
                "role": "System Manager"
            })

        print(f"  Created {len(settings.approval_levels)} approval levels")

    # -------------------------------------------------------------------
    # Step 2: Create approver mappings from Leave Department.department_head
    # -------------------------------------------------------------------
    if not settings.approver_mappings or len(settings.approver_mappings) == 0:
        print("Creating approver mappings from existing department heads...")

        departments = frappe.get_all(
            "Leave Department",
            fields=["name", "department_head", "formation"]
        )

        for dept in departments:
            if dept.department_head:
                settings.append("approver_mappings", {
                    "user": dept.department_head,
                    "department": dept.name,
                    "approval_level": 1
                })
                print(f"  Mapped {dept.department_head} → {dept.name} at level 1")

        # For formations with single_approval, map the approver_role users
        formations = frappe.get_all(
            "Leave Formation",
            filters={"single_approval": 1, "approver_role": ["is", "set"]},
            fields=["name", "approver_role"]
        )
        for formation in formations:
            # Find all departments in this formation
            formation_depts = frappe.get_all(
                "Leave Department",
                filters={"formation": formation.name},
                pluck="name"
            )
            # Find all users with this role
            role_users = frappe.get_all(
                "Has Role",
                filters={"role": formation.approver_role, "parenttype": "User"},
                pluck="parent"
            )
            for user in role_users:
                if user and user not in ("Administrator", "Guest"):
                    for dept_name in formation_depts:
                        # Check if mapping already exists
                        existing = False
                        for m in settings.approver_mappings:
                            if m.user == user and m.department == dept_name:
                                existing = True
                                break
                        if not existing:
                            settings.append("approver_mappings", {
                                "user": user,
                                "department": dept_name,
                                "approval_level": 2  # Single approval = final level
                            })
                            print(f"  Mapped single-approval {user} → {dept_name} at level 2")

        print(f"  Created {len(settings.approver_mappings)} approver mappings")

    # -------------------------------------------------------------------
    # Step 3: Create department visibility from existing Leave Employee formation logic
    # -------------------------------------------------------------------
    if not settings.department_visibility or len(settings.department_visibility) == 0:
        print("Creating department visibility entries...")

        # Find all Follow Up / HR employees
        hr_role = settings.hr_employee_role or "HR Employee"
        follow_up_users = frappe.get_all(
            "Has Role",
            filters={"role": ["in", ["Follow Up Employee", hr_role]], "parenttype": "User"},
            pluck="parent"
        )
        follow_up_users = list(set(follow_up_users))

        for user in follow_up_users:
            if user in ("Administrator", "Guest"):
                continue

            # Get the user's Leave Employee record to determine their formation
            leave_emp = frappe.db.get_value("Leave Employee", {"user": user}, "leave_department")
            if leave_emp:
                formation = frappe.db.get_value("Leave Department", leave_emp, "formation")
                if formation:
                    # Get all departments in this formation
                    formation_depts = frappe.get_all(
                        "Leave Department",
                        filters={"formation": formation},
                        pluck="name"
                    )
                    for dept_name in formation_depts:
                        settings.append("department_visibility", {
                            "user": user,
                            "department": dept_name
                        })
                    print(f"  {user} can see {len(formation_depts)} departments in formation '{formation}'")

        print(f"  Created {len(settings.department_visibility)} visibility entries")

    # Save the settings
    settings.flags.ignore_validate = True
    settings.save(ignore_permissions=True)
    print("Saved Leave Settings")

    # -------------------------------------------------------------------
    # Step 4: Set current_approval_level on existing leaves
    # -------------------------------------------------------------------
    print("Updating existing leaves with approval level tracking...")

    # Get the max level from settings
    max_levels = {lvl.level: lvl for lvl in settings.approval_levels}
    highest_level = max(max_levels.keys()) if max_levels else 1

    # Update Applied leaves (level 0 - awaiting first approval)
    count = frappe.db.sql("""
        UPDATE `tabLeave`
        SET current_approval_level = 0,
            max_required_level = CASE
                WHEN days <= 0 THEN 1
                ELSE %s
            END
        WHERE workflow_state = 'Applied'
        AND (current_approval_level IS NULL OR current_approval_level = 0)
    """, (highest_level,))
    print(f"  Updated Applied leaves")

    # Update Approved By Department leaves (level 1 completed)
    frappe.db.sql("""
        UPDATE `tabLeave`
        SET current_approval_level = 1,
            max_required_level = CASE
                WHEN days <= 0 THEN %s
                ELSE %s
            END
        WHERE workflow_state = 'Approved By Department'
        AND (current_approval_level IS NULL OR current_approval_level = 0)
    """, (highest_level, highest_level))
    print(f"  Updated Approved By Department leaves")

    # Update Approved leaves (fully approved)
    frappe.db.sql("""
        UPDATE `tabLeave`
        SET max_required_level = CASE
                WHEN max_required_level IS NULL OR max_required_level = 0 THEN %s
                ELSE max_required_level
            END,
            current_approval_level = CASE
                WHEN current_approval_level IS NULL OR current_approval_level = 0 THEN
                    CASE WHEN max_required_level IS NULL OR max_required_level = 0 THEN %s ELSE max_required_level END
                ELSE current_approval_level
            END
        WHERE workflow_state = 'Approved'
    """, (highest_level, highest_level))
    print(f"  Updated Approved leaves")

    # Update Pending leaves
    frappe.db.sql("""
        UPDATE `tabLeave`
        SET current_approval_level = 0,
            max_required_level = %s
        WHERE workflow_state = 'Pending'
        AND (current_approval_level IS NULL OR current_approval_level = 0)
    """, (highest_level,))
    print(f"  Updated Pending leaves")

    frappe.db.commit()
    print("Migration complete!")

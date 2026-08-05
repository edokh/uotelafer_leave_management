"""
Migration patch to convert department-based Leave Settings mappings
to formation-based mappings, eliminating per-department duplication.

Run via: bench --site <site> execute uotelafer_leave_management.patches.restructure_to_formation_based.execute

This patch:
1. Reads existing Leave Approver Mapping rows (department + user + level)
2. Resolves each department → its formation
3. Creates deduplicated formation-based rows (user + formation + level)
4. Does the same for Leave Department Visibility rows
"""
import frappe


def execute():
    print("Starting migration: Department-based → Formation-based Leave Settings...")

    if not frappe.db.table_exists("Leave Approver Mapping"):
        print("  Leave Approver Mapping table does not exist, skipping.")
        return

    # -------------------------------------------------------------------
    # Step 1: Migrate Approver Mappings from department → formation
    # -------------------------------------------------------------------
    print("Migrating Approver Mappings...")

    # Check if the old 'department' column still exists
    old_col_exists = frappe.db.has_column("Leave Approver Mapping", "department")
    new_col_exists = frappe.db.has_column("Leave Approver Mapping", "formation")

    if old_col_exists and new_col_exists:
        # Both columns exist (migration in progress). Read from old, write to new.
        old_mappings = frappe.db.sql("""
            SELECT user, department, approval_level
            FROM `tabLeave Approver Mapping`
            WHERE department IS NOT NULL AND department != ''
        """, as_dict=True)

        # Resolve department → formation, deduplicate
        seen = set()
        new_mappings = []
        for row in old_mappings:
            formation = frappe.db.get_value("Leave Department", row.department, "formation")
            if not formation:
                print(f"  WARNING: Department '{row.department}' has no formation, skipping.")
                continue

            key = (row.user, formation, row.approval_level)
            if key in seen:
                continue
            seen.add(key)
            new_mappings.append({
                "user": row.user,
                "formation": formation,
                "approval_level": row.approval_level,
            })

        print(f"  Reduced {len(old_mappings)} department-based mappings → {len(new_mappings)} formation-based mappings")

        # Clear old data and write new
        settings = frappe.get_doc("Leave Settings")
        settings.approver_mappings = []
        for m in new_mappings:
            settings.append("approver_mappings", m)

        # -------------------------------------------------------------------
        # Step 2: Migrate Department Visibility from department → formation
        # -------------------------------------------------------------------
        print("Migrating Department Visibility...")

        old_vis_col_exists = frappe.db.has_column("Leave Department Visibility", "department")
        new_vis_col_exists = frappe.db.has_column("Leave Department Visibility", "formation")

        if old_vis_col_exists and new_vis_col_exists:
            old_visibility = frappe.db.sql("""
                SELECT user, department
                FROM `tabLeave Department Visibility`
                WHERE department IS NOT NULL AND department != ''
            """, as_dict=True)

            vis_seen = set()
            new_visibility = []
            for row in old_visibility:
                formation = frappe.db.get_value("Leave Department", row.department, "formation")
                if not formation:
                    print(f"  WARNING: Department '{row.department}' has no formation, skipping.")
                    continue

                key = (row.user, formation)
                if key in vis_seen:
                    continue
                vis_seen.add(key)
                new_visibility.append({
                    "user": row.user,
                    "formation": formation,
                })

            print(f"  Reduced {len(old_visibility)} department-based visibility rows → {len(new_visibility)} formation-based rows")

            settings.department_visibility = []
            for v in new_visibility:
                settings.append("department_visibility", v)

        settings.flags.ignore_validate = True
        settings.save(ignore_permissions=True)
        print("Saved Leave Settings with formation-based mappings.")

    elif new_col_exists and not old_col_exists:
        print("  'department' column already removed, 'formation' column exists. Migration likely already done.")
    elif old_col_exists and not new_col_exists:
        print("  ERROR: 'formation' column not found. Run bench migrate first to sync schema.")
    else:
        print("  Neither column exists. Skipping migration.")

    frappe.db.commit()
    print("Migration complete!")

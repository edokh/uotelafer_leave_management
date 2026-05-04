app_name = "uotelafer_leave_management"
app_title = "Uotelafer Leave Management"
app_publisher = "Computer Center of UoT"
app_description = "This app for managing the leaves of employees"
app_email = "eido.khudyda@gmail.com"
app_license = "mit"

ppermission_query_conditions = {
    "Leave": "uotelafer_leave_management.uotelafer_leave_management.doctype.leave.leave.get_permission_query_conditions"
}

fixtures = [
    {
        "dt": "Translation",
        "filters": [["language", "in", ["ar", "en"]]]
    },
    {
        "dt": "Workspace"
    },
    {
        "dt": "Workflow"
    },
    {
        "dt": "Custom HTML Block"
    },
    {
        "dt": "Workflow State"
    },
    {
        "dt": "Workflow Action"
    },
    {
        "dt": "Role",
        "filters": [["name", "in", ["University Employee", "Department Head", "Follow Up Employee", "HR Employee"]]]
    }
]



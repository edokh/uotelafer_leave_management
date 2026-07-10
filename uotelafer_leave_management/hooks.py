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
        "dt": "Custom HTML Block",
        "filters": [["name", "=", "اضافة اجازة جديدة"]]
    },
    {
        "dt": "Workflow State"
    },
    {
        "dt": "Workflow Action Master"
    },    
    {
        "dt": "Leave Type"
    },
    {
        "dt": "Role",
        "filters": [["name", "in", ["University Employee", "University President", "Department Head", "Follow Up Employee", "HR Employee", "Leave Proxy Submitter", "Citizen Affairs Manager"]]]
    }
]
jinja = {
    "methods": [
        "uotelafer_leave_management.utils.get_qr_code"
    ]
}

# Allow guest access to citizen affairs request page
website_route_rules = [
    {"from_route": "/citizen-affairs-request", "to_route": "citizen_affairs_request"},
]

# Guest access for citizen affairs APIs
guest_methods = [
    "uotelafer_leave_management.citizen_affairs.doctype.citizens_affairs_request.citizens_affairs_request.submit_citizen_request"
]

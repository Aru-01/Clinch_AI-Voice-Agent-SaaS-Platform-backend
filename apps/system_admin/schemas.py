from drf_yasg import openapi

# Tags
SYSTEM_TAG = "System Administration - User Management"

# Common Responses
error_response = openapi.Response(
    description="Error response",
    examples={
        "application/json": {"error": "Detailed error message", "code": "error_code"}
    },
)

# System User List Schema
system_user_list_schema = {
    "operation_summary": "List System Admins",
    "operation_description": "Retrieves a list of all system administrators. Restricted to System Admins.",
    "tags": [SYSTEM_TAG],
    "responses": {
        200: openapi.Response(
            description="List of system admins",
            examples={
                "application/json": [
                    {
                        "id": "uuid",
                        "name": "Admin Name",
                        "email": "admin@example.com",
                        "phone": "01700000000",
                        "roles": ["system_admin"],
                        "is_verified": True,
                    }
                ]
            },
        ),
        403: error_response,
    },
}

# Business Admin List Schema
business_admin_list_schema = {
    "operation_summary": "List Business Admins",
    "operation_description": "Retrieves a list of all business administrators with join dates and subscription metrics. Restricted to System Admins.",
    "tags": [SYSTEM_TAG],
    "responses": {
        200: openapi.Response(
            description="List of business admins",
            examples={
                "application/json": [
                    {
                        "id": "uuid",
                        "name": "Business Owner",
                        "email": "owner@example.com",
                        "phone": "01700000000",
                        "join_date": "2026-05-08",
                        "plan": "Free",
                        "total_leads": 0,
                        "conversation_rate": 0.0,
                    }
                ]
            },
        ),
        403: error_response,
    },
}

# System Admin Create Schema
system_admin_create_schema = {
    "operation_summary": "Create System Admin",
    "operation_description": "Creates a new system administrator and sends a verification OTP. Restricted to existing System Admins.",
    "tags": [SYSTEM_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["name", "email", "phone", "password"],
        properties={
            "name": openapi.Schema(type=openapi.TYPE_STRING, example="New Admin"),
            "email": openapi.Schema(
                type=openapi.TYPE_STRING, format="email", example="newadmin@example.com"
            ),
            "phone": openapi.Schema(type=openapi.TYPE_STRING, example="01700000001"),
            "password": openapi.Schema(
                type=openapi.TYPE_STRING, min_length=8, example="securepassword123"
            ),
        },
    ),
    "responses": {
        201: openapi.Response(
            description="System Admin created successfully",
            examples={
                "application/json": {
                    "user": {
                        "id": "uuid",
                        "name": "New Admin",
                        "email": "newadmin@example.com",
                    },
                    "message": "New System Admin created. A verification OTP has been sent to their email.",
                }
            },
        ),
        400: error_response,
        403: error_response,
    },
}

# System Admin Delete Schema
system_admin_delete_schema = {
    "operation_summary": "Delete System Admin",
    "operation_description": "Removes a system administrator. Cannot delete self or root superusers. Restricted to System Admins.",
    "tags": [SYSTEM_TAG],
    "responses": {
        200: openapi.Response(
            description="Admin deleted successfully",
            examples={
                "application/json": {"message": "System Admin successfully removed."}
            },
        ),
        400: error_response,
        403: error_response,
        404: error_response,
    },
}

# Stats Schema
stats_schema = {
    "operation_summary": "Get System Dashboard Stats",
    "operation_description": "Retrieves comprehensive statistics for the system admin dashboard including user growth, plan purchases, and registration graph data.",
    "tags": [SYSTEM_TAG],
    "responses": {
        200: openapi.Response(
            description="Dashboard statistics",
            examples={
                "application/json": {
                    "overview": {
                        "total_business_admin": {"count": 150, "growth_percentage": 10.5},
                        "total_plan_purchase_user": {"count": 80, "growth_percentage": 5.2}
                    },
                    "graph": {
                        "this_month": {"1": 5, "2": 8, "3": 12},
                        "prev_month": {"1": 4, "2": 7, "3": 10}
                    },
                    "recent_users": [{"id": "uuid", "name": "Recent User"}]
                }
            },
        ),
        403: error_response,
    },
}

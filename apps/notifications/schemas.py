from drf_yasg import openapi
from apps.notifications.serializers import NotificationSerializer

NOTIFICATION_TAG = "Notifications"

_error = openapi.Response(
    description="Error",
    examples={"application/json": {"detail": "Error message"}},
)

_unread_count_response = openapi.Response(
    description="Unread notification count",
    schema=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"unread_count": openapi.Schema(type=openapi.TYPE_INTEGER, example=5)},
    ),
)

notification_list_schema = {
    "operation_summary": "List Notifications",
    "operation_description": (
        "Returns all notifications for the authenticated user, newest first.\n\n"
        "**Query params:**\n"
        "- `?unread=true` — return only unread notifications\n\n"
        "**Role behaviour:**\n"
        "- System admins receive platform-level events (new registrations, payments, support tickets)\n"
        "- Business admins receive operational events (call logs, appointments, subscription alerts)"
    ),
    "tags": [NOTIFICATION_TAG],
    "manual_parameters": [
        openapi.Parameter(
            "unread",
            openapi.IN_QUERY,
            description="Filter to unread only",
            type=openapi.TYPE_BOOLEAN,
            required=False,
        )
    ],
    "responses": {
        200: openapi.Response(
            description="List of notifications",
            schema=NotificationSerializer(many=True),
        ),
        401: _error,
    },
}

mark_read_schema = {
    "operation_summary": "Mark Notification as Read",
    "operation_description": "Marks a single notification as read. The notification must belong to the authenticated user.",
    "tags": [NOTIFICATION_TAG],
    "responses": {
        200: openapi.Response(
            description="Marked as read",
            examples={"application/json": {"detail": "Marked as read."}},
        ),
        404: _error,
    },
}

mark_all_read_schema = {
    "operation_summary": "Mark All Notifications as Read",
    "operation_description": "Marks every unread notification for the authenticated user as read in a single call.",
    "tags": [NOTIFICATION_TAG],
    "responses": {
        200: openapi.Response(
            description="All marked as read",
            examples={"application/json": {"detail": "All notifications marked as read."}},
        ),
    },
}

unread_count_schema = {
    "operation_summary": "Get Unread Notification Count",
    "operation_description": (
        "Returns the number of unread notifications for the authenticated user.\n\n"
        "Use this endpoint for **frontend polling** (e.g. every 30 seconds) to show a badge count."
    ),
    "tags": [NOTIFICATION_TAG],
    "responses": {
        200: _unread_count_response,
        401: _error,
    },
}

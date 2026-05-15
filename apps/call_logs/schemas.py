from drf_yasg import openapi
from apps.call_logs.serializers import CallLogListSerializer, CallLogDetailSerializer

CALL_LOG_TAG = "Call Logs"

call_log_list_schema = {
    "operation_description": "Retrieve a list of call logs for the business. Supports filtering (location, status, date), searching (name, phone, location, status), and dynamic pagination via 'page_size'.",
    "tags": [CALL_LOG_TAG],
    "responses": {
        200: openapi.Response(
            description="A list of call logs with basic info.",
            schema=CallLogListSerializer(many=True),
        ),
        401: "Unauthorized access",
    },
}

call_log_create_schema = {
    "operation_description": "Create a new call log entry for the business.",
    "tags": [CALL_LOG_TAG],
    "request_body": CallLogDetailSerializer,
    "responses": {
        201: openapi.Response(
            description="Call log created successfully.",
            schema=CallLogDetailSerializer(),
        ),
        400: "Invalid data provided",
    },
}

call_log_detail_schema = {
    "operation_description": "Retrieve full details of a specific call log including transcript and summary.",
    "tags": [CALL_LOG_TAG],
    "responses": {
        200: openapi.Response(
            description="Full details of the call log.",
            schema=CallLogDetailSerializer(),
        ),
        404: "Call log not found",
    },
}

call_log_delete_schema = {
    "operation_description": "Delete a specific call log permanently.",
    "tags": [CALL_LOG_TAG],
    "responses": {
        204: "Call log deleted successfully",
        404: "Call log not found",
    },
}

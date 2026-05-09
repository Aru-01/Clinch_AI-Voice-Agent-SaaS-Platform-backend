from drf_yasg import openapi
from apps.support.serializers import SupportTicketSerializer, TicketMessageSerializer

SUPPORT_TAG = "Support Tickets"

error_response = openapi.Response(
    description="Error response",
    examples={"application/json": {"detail": "Error message"}},
)

ticket_list_schema = {
    "operation_summary": "List Support Tickets",
    "operation_description": "Retrieves a list of support tickets. Business admins see their own, System admins see all.",
    "tags": [SUPPORT_TAG],
    "responses": {200: SupportTicketSerializer(many=True)},
}

ticket_create_schema = {
    "operation_summary": "Create Support Ticket",
    "operation_description": "Creates a new support ticket with an initial message. Business admins only.",
    "tags": [SUPPORT_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["subject", "message"],
        properties={
            "subject": openapi.Schema(
                type=openapi.TYPE_STRING, example="Payment Issue"
            ),
            "message": openapi.Schema(
                type=openapi.TYPE_STRING, example="I cannot pay my bill."
            ),
        },
    ),
    "responses": {201: SupportTicketSerializer(), 400: error_response},
}

ticket_retrieve_schema = {
    "operation_summary": "Retrieve Support Ticket",
    "operation_description": "Gets full details of a support ticket including messages and notes.",
    "tags": [SUPPORT_TAG],
    "responses": {200: SupportTicketSerializer(), 404: error_response},
}

ticket_update_schema = {
    "operation_summary": "Update Support Ticket (System Admin)",
    "operation_description": "Allows System Admins to update ticket status and add/update notes.",
    "tags": [SUPPORT_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "status": openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=["pending", "discussed", "solved", "failed"],
                example="solved",
            ),
            "notes": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Update the internal note for the ticket.",
                example="Issues resolved after investigation.",
            ),
        },
    ),
    "responses": {
        200: SupportTicketSerializer(),
        400: error_response,
        403: error_response,
    },
}

add_message_schema = {
    "operation_summary": "Add Message to Ticket",
    "operation_description": "Adds a new message to an existing support ticket conversation.",
    "tags": [SUPPORT_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["message"],
        properties={
            "message": openapi.Schema(
                type=openapi.TYPE_STRING, example="Here is more info..."
            ),
        },
    ),
    "responses": {201: TicketMessageSerializer(), 400: error_response},
}

ticket_delete_schema = {
    "operation_summary": "Delete Support Ticket",
    "operation_description": "Support tickets cannot be deleted. This endpoint will return a 405 Method Not Allowed.",
    "tags": [SUPPORT_TAG],
    "responses": {405: error_response},
}

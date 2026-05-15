from drf_yasg import openapi
from apps.bookings.serializers import BookingSerializer

BOOKING_TAG = "Bookings"

booking_list_schema = {
    "operation_description": "Retrieve a list of all bookings for the business. Supports filtering by status and date, searching by customer info, and dynamic pagination.",
    "tags": [BOOKING_TAG],
    "responses": {
        200: openapi.Response(
            description="A list of bookings.", schema=BookingSerializer(many=True)
        ),
        401: "Unauthorized access",
    },
}

booking_create_schema = {
    "operation_description": "Create a new booking (Meeting). This endpoint is public for AI services to send data.",
    "tags": [BOOKING_TAG],
    "request_body": BookingSerializer,
    "responses": {
        201: openapi.Response(
            description="Booking created successfully.", schema=BookingSerializer()
        ),
        400: "Invalid data provided",
    },
}

booking_detail_schema = {
    "operation_description": "Retrieve, update, or delete a specific booking.",
    "tags": [BOOKING_TAG],
    "responses": {
        200: openapi.Response(
            description="Details of the booking.", schema=BookingSerializer()
        ),
        404: "Booking not found",
    },
}

booking_delete_schema = {
    "operation_description": "Delete a booking permanently.",
    "tags": [BOOKING_TAG],
    "responses": {
        204: "Booking deleted successfully",
        404: "Booking not found",
    },
}

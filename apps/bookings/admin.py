from django.contrib import admin
from apps.bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "meeting_date",
        "meeting_time",
        "status",
        "business",
    )
    list_filter = ("status", "meeting_date", "business")
    search_fields = ("customer_name", "customer_email", "customer_phone")
    ordering = ("-meeting_date", "-meeting_time")

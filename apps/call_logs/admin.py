from django.contrib import admin
from apps.call_logs.models import CallLog


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "status",
        "duration",
        "call_date_time",
        "business",
    )
    list_filter = ("status", "call_date_time", "business")
    search_fields = ("name", "phone_number", "location")
    ordering = ("-call_date_time",)

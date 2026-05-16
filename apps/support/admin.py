from django.contrib import admin
from apps.support.models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_number",
        "subject",
        "status",
        "business",
        "creator",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["subject", "business__name", "creator__email", "ticket_number"]
    readonly_fields = ["ticket_number"]

from django.contrib import admin
from apps.support.models import SupportTicket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0


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
    inlines = [TicketMessageInline]
    readonly_fields = ["ticket_number"]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ["ticket", "sender", "created_at"]
    search_fields = ["message", "ticket__subject"]

from django.contrib import admin
from .models import SupportTicket, TicketMessage, TicketNote

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0

class TicketNoteInline(admin.TabularInline):
    model = TicketNote
    extra = 0

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "status", "business", "creator", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["subject", "business__name", "creator__email"]
    inlines = [TicketMessageInline, TicketNoteInline]

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ["ticket", "sender", "created_at"]
    search_fields = ["message", "ticket__subject"]

@admin.register(TicketNote)
class TicketNoteAdmin(admin.ModelAdmin):
    list_display = ["ticket", "sender", "created_at"]
    search_fields = ["note", "ticket__subject"]

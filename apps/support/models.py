import uuid
from django.db import models
from django.conf import settings
from apps.accounts.models import Business

class SupportTicket(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        DISCUSSED = "discussed", "Discussed"
        SOLVED = "solved", "Solved"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="support_tickets"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_tickets"
    )
    subject = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    ticket_number = models.PositiveIntegerField(unique=True, editable=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last_ticket = SupportTicket.objects.order_by("ticket_number").last()
            if last_ticket and last_ticket.ticket_number:
                self.ticket_number = last_ticket.ticket_number + 1
            else:
                self.ticket_number = 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        db_table = "support_tickets"

    def __str__(self):
        return f"{self.subject} ({self.status})"

class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ticket_messages"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "ticket_messages"

    def __str__(self):
        return f"Message on {self.ticket.subject} by {self.sender}"

class TicketNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE, related_name="notes"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ticket_notes"
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "ticket_notes"

    def __str__(self):
        return f"Note on {self.ticket.subject} by {self.sender}"

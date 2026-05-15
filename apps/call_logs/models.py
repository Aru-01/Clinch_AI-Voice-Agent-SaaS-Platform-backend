from django.db import models
from apps.accounts.models import Business

class CallLog(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='call_logs')
    name = models.CharField(max_length=255, help_text="Name of the caller/lead")
    phone_number = models.CharField(max_length=20)
    location = models.CharField(max_length=255, blank=True, null=True)
    duration = models.CharField(max_length=50, blank=True, null=True, help_text="Duration of the call (e.g., 02:30)")
    status = models.CharField(max_length=100, blank=True, null=True, help_text="Status decided by AI")
    call_date_time = models.DateTimeField(auto_now_add=True)
    audio_url = models.URLField(max_length=500, blank=True, null=True)
    transcript = models.JSONField(blank=True, null=True, help_text="Conversation transcript in array format")
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Call with {self.name} ({self.phone_number}) - {self.status}"

    class Meta:
        ordering = ['-call_date_time']

import uuid
from django.db import models
from apps.accounts.models import Business
from core.encryption import encrypt_value, decrypt_value

# ---------------------------------------------------------------------------
# EncryptedField – transparent encrypt-on-save / decrypt-on-read
# ---------------------------------------------------------------------------


class EncryptedTextField(models.TextField):
    """
    A TextField that transparently encrypts the value before saving to DB
    and decrypts it when accessed via Python.
    """

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return decrypt_value(value)

    def to_python(self, value):
        if value is None or value == "":
            return value
        return value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return encrypt_value(value)


class APIConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="api_config",
    )

    openai_key = EncryptedTextField(blank=True, null=True)
    deepgram_key = EncryptedTextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "API Config"
        verbose_name_plural = "API Configs"

    def __str__(self):
        return f"APIConfig – {self.business.name}"


class CRMConfig(models.Model):
    class Provider(models.TextChoices):
        GOHIGHLEVEL = "gohighlevel", "GoHighLevel"
        HUBSPOT = "hubspot", "HubSpot"
        ZOHO = "zoho", "Zoho"
        SALESFORCE = "salesforce", "Salesforce"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="crm_config",
    )

    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        default=Provider.GOHIGHLEVEL,
    )
    token = EncryptedTextField(
        blank=True, null=True, help_text="API token / OAuth token"
    )
    location_id = EncryptedTextField(
        blank=True, null=True, help_text="CRM Location / Account ID"
    )
    # webhook_secret = EncryptedTextField(
    #     blank=True, null=True, help_text="Webhook signing secret"
    # )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CRM Config"
        verbose_name_plural = "CRM Configs"

    def __str__(self):
        return f"CRMConfig({self.provider}) – {self.business.name}"


class TwilioConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="twilio_config",
    )

    twilio_sid = EncryptedTextField(
        blank=True, null=True, help_text="Twilio Account SID"
    )
    twilio_token = EncryptedTextField(
        blank=True, null=True, help_text="Twilio Auth Token"
    )
    twilio_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="Outbound caller ID, e.g. +1234567890",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Twilio Config"
        verbose_name_plural = "Twilio Configs"

    def __str__(self):
        return f"TwilioConfig – {self.business.name}"


class VoiceConfig(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class Tone(models.TextChoices):
        PROFESSIONAL = "professional", "Professional"
        FRIENDLY = "friendly", "Friendly"
        FORMAL = "formal", "Formal"
        CASUAL = "casual", "Casual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="voice_config",
    )

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.FEMALE,
    )
    tone = models.CharField(
        max_length=20,
        choices=Tone.choices,
        default=Tone.PROFESSIONAL,
    )
    voice_template = models.FileField(
        upload_to="voice_templates/",
        blank=True,
        null=True,
        help_text="Optional audio sample file (mp3/wav)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voice Config"
        verbose_name_plural = "Voice Configs"

    def __str__(self):
        return f"VoiceConfig({self.gender}/{self.tone}) – {self.business.name}"


class KnowledgeFile(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="knowledge_files",
    )

    name = models.CharField(max_length=255, help_text="Friendly display name")
    file = models.FileField(
        upload_to="knowledge_files/",
        help_text="Accepted: pdf, json, csv, txt, docx",
    )
    file_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Auto-detected from file extension",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Populated when status=failed",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Knowledge File"
        verbose_name_plural = "Knowledge Files"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.file and not self.file_type:
            import os

            _, ext = os.path.splitext(self.file.name)
            self.file_type = ext.lstrip(".").lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status}) – {self.business.name}"

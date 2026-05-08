import os
from rest_framework import serializers
from core.encryption import mask_value
from apps.configuration.models import (
    APIConfig,
    CRMConfig,
    TwilioConfig,
    VoiceConfig,
    KnowledgeFile,
)

# ---------------------------------------------------------------------------
# Helper mixin — masks encrypted fields on read
# ---------------------------------------------------------------------------


class MaskedReadMixin:
    """
    Subclass this mixin and define `masked_fields` as a list of field names
    that should be masked when the serializer is used for reading (GET).
    The raw value is accepted on write (POST/PATCH) and stored encrypted.
    """

    masked_fields: list[str] = []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in self.masked_fields:
            raw = data.get(field)
            if raw:
                data[field] = mask_value(raw)
        return data


class APIConfigSerializer(MaskedReadMixin, serializers.ModelSerializer):
    masked_fields = ["openai_key", "deepgram_key"]

    class Meta:
        model = APIConfig
        fields = [
            "id",
            "business",
            "openai_key",
            "deepgram_key",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "created_at", "updated_at"]
        extra_kwargs = {
            "openai_key": {"write_only": False},
            "deepgram_key": {"write_only": False},
        }


class CRMConfigSerializer(MaskedReadMixin, serializers.ModelSerializer):
    masked_fields = [
        "token",
        "location_id",
        #  "webhook_secret"
    ]

    class Meta:
        model = CRMConfig
        fields = [
            "id",
            "business",
            "provider",
            "token",
            "location_id",
            # "webhook_secret",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "created_at", "updated_at"]


class TwilioConfigSerializer(MaskedReadMixin, serializers.ModelSerializer):
    masked_fields = ["twilio_sid", "twilio_token"]

    class Meta:
        model = TwilioConfig
        fields = [
            "id",
            "business",
            "twilio_sid",
            "twilio_token",
            "twilio_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "created_at", "updated_at"]


class VoiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceConfig
        fields = [
            "id",
            "business",
            "gender",
            "tone",
            "voice_template",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "created_at", "updated_at"]


class KnowledgeFileSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeFile
        fields = [
            "id",
            "business",
            "name",
            "file",
            "file_name",
            "file_type",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "business",
            "file_type",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_file_name(self, obj):
        if obj.file:
            return os.path.basename(obj.file.name)
        return None

    def validate_file(self, value):
        allowed = {"pdf", "json", "csv", "txt", "docx", "xlsx"}
        _, ext = os.path.splitext(value.name)
        if ext.lstrip(".").lower() not in allowed:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}"
            )
        return value


class KnowledgeFileStatusSerializer(serializers.ModelSerializer):
    """Used by system/task workers to update file processing status."""

    class Meta:
        model = KnowledgeFile
        fields = ["status", "error_message"]

import os
from rest_framework import serializers
from core.encryption import mask_value
from apps.configuration.models import (
    APIConfig,
    TwilioConfig,
    VoiceConfig,
    KnowledgeFile,
)

MAX_AUDIO_SIZE_MB = 120
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "webm"}


# ---------------------------------------------------------------------------
# Helper mixin — masks encrypted fields on GET responses
# ---------------------------------------------------------------------------


class MaskedReadMixin:
    masked_fields: list = []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in self.masked_fields:
            raw = data.get(field)
            if raw:
                data[field] = mask_value(raw)
        return data


class APIConfigSerializer(MaskedReadMixin, serializers.ModelSerializer):
    masked_fields = ["openai_key", "deepgram_key"]
    openai_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    deepgram_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

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

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def create(self, validated_data):
        business_id = validated_data.pop("business_id", None)
        instance = APIConfig(business_id=business_id)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



class TwilioConfigSerializer(MaskedReadMixin, serializers.ModelSerializer):
    masked_fields = ["twilio_sid", "twilio_token"]

    twilio_sid = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    twilio_token = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

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

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def create(self, validated_data):
        business_id = validated_data.pop("business_id", None)
        instance = TwilioConfig(business_id=business_id)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


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

    def validate_voice_template(self, value):
        if not value:
            return value
        _, ext = os.path.splitext(value.name)
        ext_clean = ext.lstrip(".").lower()
        if ext_clean not in ALLOWED_AUDIO_EXTENSIONS:
            raise serializers.ValidationError(
                f"Only audio files accepted ({', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}). Got: .{ext_clean}"
            )
        if value.size > MAX_AUDIO_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File too large ({value.size // (1024*1024)} MB). Max: {MAX_AUDIO_SIZE_MB} MB."
            )
        return value


class KnowledgeFileSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeFile
        fields = [
            "id",
            "business",
            "name",
            "file",
            "file_url",
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
            "file_url",
            "file_type",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_file_name(self, obj):
        return os.path.basename(obj.file.name) if obj.file else None

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url

    def validate_file(self, value):
        allowed = {"pdf", "json", "csv", "txt", "docx", "xlsx"}
        _, ext = os.path.splitext(value.name)
        if ext.lstrip(".").lower() not in allowed:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(sorted(allowed))}"
            )
        return value


class KnowledgeFileStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeFile
        fields = ["status", "error_message"]

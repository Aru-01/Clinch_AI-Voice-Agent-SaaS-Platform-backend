from django.contrib import admin
from apps.configuration.models import (
    APIConfig, CRMConfig, TwilioConfig, VoiceConfig, KnowledgeFile
)


@admin.register(APIConfig)
class APIConfigAdmin(admin.ModelAdmin):
    list_display = ["business", "created_at", "updated_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]
    # Don't show raw encrypted blobs — keep plain through the model property
    fields = ["id", "business", "openai_key", "deepgram_key", "created_at", "updated_at"]


@admin.register(CRMConfig)
class CRMConfigAdmin(admin.ModelAdmin):
    list_display = ["business", "provider", "created_at", "updated_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]
    list_filter = ["provider"]


@admin.register(TwilioConfig)
class TwilioConfigAdmin(admin.ModelAdmin):
    list_display = ["business", "twilio_number", "created_at", "updated_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]


@admin.register(VoiceConfig)
class VoiceConfigAdmin(admin.ModelAdmin):
    list_display = ["business", "gender", "tone", "created_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]
    list_filter = ["gender", "tone"]


@admin.register(KnowledgeFile)
class KnowledgeFileAdmin(admin.ModelAdmin):
    list_display = ["name", "business", "file_type", "status", "created_at"]
    readonly_fields = ["id", "business", "file_type", "created_at", "updated_at"]
    list_filter = ["status", "file_type"]
    search_fields = ["name", "business__name"]

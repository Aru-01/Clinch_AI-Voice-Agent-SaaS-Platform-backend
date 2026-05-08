from django import forms
from django.contrib import admin
from apps.configuration.models import (
    APIConfig,
    CRMConfig,
    TwilioConfig,
    VoiceConfig,
    KnowledgeFile,
)
from core.encryption import mask_value


class MaskedAdminForm(forms.ModelForm):
    """
    A custom ModelForm that renders sensitive fields as password inputs
    and masks the existing values so they aren't visible in plain text.
    If the user enters a new value, it will be saved. If they leave the
    masked value, we must ensure we don't save the masked string back.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            for field_name in self.Meta.masked_fields:
                if field_name in self.initial and self.initial[field_name]:
                    self.fields[field_name].widget = forms.PasswordInput(
                        render_value=True
                    )
                    self.initial[field_name] = ""
                    self.fields[field_name].widget = forms.PasswordInput(
                        render_value=False
                    )
                    self.fields[field_name].required = False
                    self.fields[field_name].help_text = (
                        "Leave blank to keep the current key/token. Enter a new value to update it."
                    )

    def save(self, commit=True):
        instance = super().save(commit=False)
        for field_name in self.Meta.masked_fields:
            value = self.cleaned_data.get(field_name)
            if not value and getattr(instance, f"_{field_name}", None):
                continue
            elif value:
                setattr(instance, field_name, value)
        if commit:
            instance.save()
        return instance


class APIConfigAdminForm(MaskedAdminForm):
    class Meta:
        model = APIConfig
        fields = "__all__"
        masked_fields = ["openai_key", "deepgram_key"]

    openai_key = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )
    deepgram_key = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )


@admin.register(APIConfig)
class APIConfigAdmin(admin.ModelAdmin):
    form = APIConfigAdminForm
    list_display = ["business", "created_at", "updated_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]
    fields = [
        "id",
        "business",
        "openai_key",
        "deepgram_key",
        "created_at",
        "updated_at",
    ]


class CRMConfigAdminForm(MaskedAdminForm):
    class Meta:
        model = CRMConfig
        fields = "__all__"
        masked_fields = ["token", "location_id", "webhook_secret"]

    token = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )
    location_id = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )
    webhook_secret = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )


@admin.register(CRMConfig)
class CRMConfigAdmin(admin.ModelAdmin):
    form = CRMConfigAdminForm
    list_display = ["business", "provider", "created_at", "updated_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]
    fields = [
        "id",
        "business",
        "provider",
        "token",
        "location_id",
        "webhook_secret",
        "created_at",
        "updated_at",
    ]
    list_filter = ["provider"]


class TwilioConfigAdminForm(MaskedAdminForm):
    class Meta:
        model = TwilioConfig
        fields = "__all__"
        masked_fields = ["twilio_sid", "twilio_token"]

    twilio_sid = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )
    twilio_token = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=False)
    )


@admin.register(TwilioConfig)
class TwilioConfigAdmin(admin.ModelAdmin):
    form = TwilioConfigAdminForm
    list_display = ["business", "twilio_number", "created_at", "updated_at"]
    readonly_fields = ["id", "business", "created_at", "updated_at"]
    fields = [
        "id",
        "business",
        "twilio_sid",
        "twilio_token",
        "twilio_number",
        "created_at",
        "updated_at",
    ]


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

from django.urls import path
from apps.configuration.views import (
    APIConfigView,
    CRMConfigView,
    TwilioConfigView,
    VoiceConfigView,
    KnowledgeFileListCreateView,
    KnowledgeFileDetailView,
)

urlpatterns = [
    # API Config (OpenAI / Deepgram keys)
    path("api-config/", APIConfigView.as_view(), name="api-config"),

    # CRM Config (GoHighLevel / HubSpot / Zoho …)
    path("crm-config/", CRMConfigView.as_view(), name="crm-config"),

    # Twilio Config
    path("twilio-config/", TwilioConfigView.as_view(), name="twilio-config"),

    # Voice personality config
    path("voice-config/", VoiceConfigView.as_view(), name="voice-config"),

    # Knowledge base files
    path("knowledge-files/", KnowledgeFileListCreateView.as_view(), name="knowledge-files"),
    path("knowledge-files/<uuid:pk>/", KnowledgeFileDetailView.as_view(), name="knowledge-file-detail"),
]

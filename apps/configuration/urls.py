from django.urls import path
from apps.configuration.views import (
    TwilioConfigView,
    VoiceConfigView,
    KnowledgeFileListCreateView,
    KnowledgeFileDetailView,
)

urlpatterns = [
    # Twilio Config
    path("twilio-config/", TwilioConfigView.as_view(), name="twilio-config"),

    # Voice personality config
    path("voice-config/", VoiceConfigView.as_view(), name="voice-config"),

    # Knowledge base files
    path("knowledge-files/", KnowledgeFileListCreateView.as_view(), name="knowledge-files"),
    path("knowledge-files/<uuid:pk>/", KnowledgeFileDetailView.as_view(), name="knowledge-file-detail"),
]

from django.urls import path
from apps.crm_integration import views

urlpatterns = [
    path("leads/", views.TestCRMLeadsView.as_view(), name="test-crm-leads"),
    path("webhook/<str:crm_type>/", views.CRMWebhookView.as_view(), name="crm-webhook"),
]

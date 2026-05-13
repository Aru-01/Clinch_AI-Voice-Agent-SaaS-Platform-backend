from django.urls import path
from . import views

urlpatterns = [
    path('test-leads/', views.TestCRMLeadsView.as_view(), name='test-crm-leads'),
    path('webhook/<str:crm_type>/', views.CRMWebhookView.as_view(), name='crm-webhook'),
]

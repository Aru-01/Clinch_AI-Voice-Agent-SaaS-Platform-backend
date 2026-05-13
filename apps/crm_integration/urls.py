from django.urls import path
from . import views

urlpatterns = [
    path('test-leads/', views.TestCRMLeadsView.as_view(), name='test-crm-leads'),
]

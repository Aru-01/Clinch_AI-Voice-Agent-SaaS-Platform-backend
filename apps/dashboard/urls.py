from django.urls import path
from apps.dashboard import views

urlpatterns = [
    path(
        "business-admin/",
        views.BusinessAdminDashboardView.as_view(),
        name="business-admin-dashboard",
    ),
]

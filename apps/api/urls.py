from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("system-admin/", include("apps.system_admin.urls")),
]

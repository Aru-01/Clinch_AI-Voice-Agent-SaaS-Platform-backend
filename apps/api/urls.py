from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("api/system-admin/", include("apps.system_admin.urls")),
    path("api/config/", include("apps.configuration.urls")),
    path("api/support/", include("apps.support.urls")),
]

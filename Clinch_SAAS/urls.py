from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from debug_toolbar.toolbar import debug_toolbar_urls

# Main API schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Clinch SAAS API",
        default_version="v1",
        description="API documentation for Clinch AI Voice Agent SAAS Platform",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@clinchsaas.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # All APIs prefixed with /api/
    path("", include("apps.api.urls")),
    # Swagger UI with UI configuration to show full paths
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
] + debug_toolbar_urls()

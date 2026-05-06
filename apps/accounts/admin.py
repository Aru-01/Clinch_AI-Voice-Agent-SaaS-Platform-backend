from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.accounts.models import (
    CustomUser,
    Business,
    Role,
    UserRole,
    OTPCode,
    RolePermission,
)


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "name", "phone", "business", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "business")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "phone", "profile_image", "business")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login",)}),
    )
    search_fields = ("email", "name", "phone")
    ordering = ("email",)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Business)
admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(OTPCode)
admin.site.register(RolePermission)

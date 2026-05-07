from rest_framework import permissions


class IsSystemAdmin(permissions.BasePermission):
    """
    Allows access only to users with the 'system_admin' role.
    """

    message = (
        "You do not have permission to perform this action. System Admin role required."
    )

    def has_permission(self, request, view):
        if not (
            request.user and request.user.is_authenticated and request.user.is_verified
        ):
            return False

        if not hasattr(request.user, "_is_system_admin"):
            request.user._is_system_admin = request.user.user_roles.filter(
                role__name="system_admin"
            ).exists()

        return request.user._is_system_admin

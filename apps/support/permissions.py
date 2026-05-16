from rest_framework import permissions


class IsVerifiedBusinessUser(permissions.BasePermission):
    """
    Allows access only to users who:
    1. Are authenticated
    2. Have verified their email
    3. Have a business profile
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            self.message = "Authentication required."
            return False

        if not hasattr(request.user, "_is_system_admin"):
            request.user._is_system_admin = (
                request.user.is_superuser
                or request.user.user_roles.filter(role__name="system_admin").exists()
            )

        if request.user._is_system_admin:
            return True

        if not request.user.is_verified:
            self.message = "Your email is not verified. Please verify your email to access support tickets."
            return False

        if not request.user.business_id:
            self.message = "You must have a business profile to access support tickets."
            return False

        return True

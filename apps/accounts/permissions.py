from rest_framework import permissions

class IsVerifiedUser(permissions.BasePermission):
    """
    Allows access only to verified users.
    """
    message = "Your email is not verified. Please verify your email to access this resource."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_verified)

from rest_framework.permissions import BasePermission


class IsBusinessAdmin(BasePermission):
    """
    Allows access only to authenticated users who belong to a business
    (i.e. business_id is not NULL → they are a business admin).
    """
    message = "You must be a business admin to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
            and request.user.business_id is not None
        )


class IsSystemAdmin(BasePermission):
    """
    Allows access only to authenticated users who have NO business assigned
    (i.e. system-level admins).
    """
    message = "You must be a system admin to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
            and request.user.business_id is None
        )


class IsSameBusiness(BasePermission):
    """
    Object-level permission: the requested object must belong to the
    same business as the currently authenticated user.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        return str(obj.business_id) == str(request.user.business_id)

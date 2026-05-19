from rest_framework.permissions import BasePermission
from django.utils import timezone


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


class HasActiveSubscription(BasePermission):
    """
    Allows access only when the user's business has an active, non-expired subscription.
    Used to gate CRM connections and other premium features.
    """
    message = "An active subscription is required to use this feature."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.business_id):
            return False
        from apps.billing.models import Subscription, SubscriptionStatus
        return Subscription.objects.filter(
            business_id=request.user.business_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_end__gt=timezone.now(),
        ).exists()


class IsSameBusiness(BasePermission):
    """
    Object-level permission: the requested object must belong to the
    same business as the currently authenticated user.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        return str(obj.business_id) == str(request.user.business_id)

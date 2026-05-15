from django.contrib.auth import get_user_model
from apps.notifications.models import Notification

User = get_user_model()


def notify_system_admins(notification_type, title, message, data=None):
    """Create a notification for every active system admin."""
    admins = User.objects.filter(
        user_roles__role__name="system_admin",
        is_active=True,
    )
    _bulk_create(admins, notification_type, title, message, data)


def notify_business_admins(business, notification_type, title, message, data=None):
    """Create a notification for every active business admin of the given business."""
    admins = User.objects.filter(
        business=business,
        user_roles__role__name="business_admin",
        is_active=True,
    )
    _bulk_create(admins, notification_type, title, message, data)


def _bulk_create(recipients, notification_type, title, message, data):
    Notification.objects.bulk_create([
        Notification(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        )
        for user in recipients
    ])

from django.urls import path
from apps.notifications import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", views.unread_count, name="notification-unread-count"),
    path("read-all/", views.mark_all_read, name="notification-read-all"),
    path("<uuid:pk>/read/", views.mark_notification_read, name="notification-read"),
]

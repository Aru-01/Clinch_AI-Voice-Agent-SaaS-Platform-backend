import os
import sys
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        import apps.notifications.services.signals  # noqa: F401

        management_only = {"migrate", "makemigrations", "shell", "test", "collectstatic"}
        if len(sys.argv) > 1 and sys.argv[1] in management_only:
            return
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        from apps.notifications.services.scheduler import start
        start()

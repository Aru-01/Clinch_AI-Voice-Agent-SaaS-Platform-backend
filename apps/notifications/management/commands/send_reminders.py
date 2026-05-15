from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Manually trigger notification scheduler jobs (useful for testing)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--job",
            choices=["reminders", "expiry", "cleanup", "all"],
            default="all",
            help="Which job to run (default: all)",
        )

    def handle(self, *args, **options):
        job = options["job"]
        self.stdout.write(f"[{timezone.now().strftime('%H:%M:%S UTC')}] Running: {job}\n")

        if job in ("reminders", "all"):
            self.stdout.write("  [reminders] send_meeting_reminders ... ", ending="")
            from apps.notifications.services.scheduler import send_meeting_reminders
            from unittest.mock import patch
            with patch("apps.notifications.services.scheduler._acquire_lock", return_value=True):
                send_meeting_reminders()
            self.stdout.write(self.style.SUCCESS("done"))

        if job in ("expiry", "all"):
            self.stdout.write("  [expiry] send_subscription_expiry_warnings ... ", ending="")
            from apps.notifications.services.scheduler import send_subscription_expiry_warnings
            from unittest.mock import patch
            with patch("apps.notifications.services.scheduler._acquire_lock", return_value=True):
                send_subscription_expiry_warnings()
            self.stdout.write(self.style.SUCCESS("done"))

        if job in ("cleanup", "all"):
            self.stdout.write("  [cleanup] cleanup_old_notifications ... ", ending="")
            from apps.notifications.services.scheduler import cleanup_old_notifications
            from unittest.mock import patch
            with patch("apps.notifications.services.scheduler._acquire_lock", return_value=True):
                cleanup_old_notifications()
            self.stdout.write(self.style.SUCCESS("done"))

        self.stdout.write(self.style.SUCCESS("\nFinished. Check /api/notifications/ for results."))

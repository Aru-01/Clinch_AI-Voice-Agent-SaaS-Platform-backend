from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, UserRole
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Seed initial admin user and roles"

    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")

        with transaction.atomic():
            # 1. Create Roles
            system_admin_role, _ = Role.objects.get_or_create(name="system_admin")
            business_admin_role, _ = Role.objects.get_or_create(name="business_admin")

            self.stdout.write(f"Roles created/verified: system_admin, business_admin")

            # 2. Create System Admin User
            admin_email = "admin@gmail.com"
            admin_password = "12345678"

            if not User.objects.filter(email=admin_email).exists():
                admin_user = User.objects.create_superuser(
                    email=admin_email,
                    password=admin_password,
                    name="System Admin",
                    phone="01700000000",
                )
                admin_user.is_verified = True
                admin_user.save()

                # Assign Role
                UserRole.objects.get_or_create(user=admin_user, role=system_admin_role)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created admin user: {admin_email}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Admin user {admin_email} already exists.")
                )

        self.stdout.write(self.style.SUCCESS("Seeding completed."))

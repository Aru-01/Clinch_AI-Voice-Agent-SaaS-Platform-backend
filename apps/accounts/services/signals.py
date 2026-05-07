from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps


@receiver(post_migrate)
def setup_initial_data(sender, **kwargs):
    if sender.name == "apps.accounts":
        Role = apps.get_model("accounts", "Role")
        CustomUser = apps.get_model("accounts", "CustomUser")
        UserRole = apps.get_model("accounts", "UserRole")

        roles = ["system_admin", "business_admin"]
        role_objs = {}
        for role_name in roles:
            role, _ = Role.objects.get_or_create(name=role_name)
            role_objs[role_name] = role

        admin_email = "admin@gmail.com"
        if not CustomUser.objects.filter(email=admin_email).exists():
            admin_user = CustomUser.objects.create_superuser(
                email=admin_email,
                password="12345678",
                name="System Admin",
                phone="01700000000",
            )
            admin_user.is_verified = True
            admin_user.save()
            UserRole.objects.get_or_create(
                user=admin_user, role=role_objs["system_admin"]
            )

            print(f"Initial Admin created: {admin_email}")

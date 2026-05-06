from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps

@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    if sender.name == 'apps.accounts':
        Role = apps.get_model('accounts', 'Role')
        roles = ['system_admin', 'business_admin']
        for role_name in roles:
            Role.objects.get_or_create(name=role_name)

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'

    def ready(self):
        import apps.accounts.services.signals

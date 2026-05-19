from decouple import config
from .base import BaseOAuthService


class GHLService(BaseOAuthService):
    """GoHighLevel - Placeholder for later"""
    CLIENT_ID = config("GHL_CLIENT_ID", default=None)
    CLIENT_SECRET = config("GHL_CLIENT_SECRET", default=None)

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.redirect_uri = redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/ghl/"

    def get_oauth_url(self, state):
        raise NotImplementedError("GHL OAuth not implemented yet")

    def exchange_code_for_token(self, code, **_):
        raise NotImplementedError("GHL OAuth not implemented yet")

    def refresh_access_token(self) -> bool:
        raise NotImplementedError("GHL OAuth not implemented yet")

    def verify_webhook_signature(self, body, signature) -> bool:
        return True

    def configure_webhook(self, webhook_url) -> dict:
        raise NotImplementedError("GHL OAuth not implemented yet")

    def fetch_leads(self):
        raise NotImplementedError("GHL OAuth not implemented yet")

    def sync_leads_to_db(self) -> dict:
        raise NotImplementedError("GHL OAuth not implemented yet")

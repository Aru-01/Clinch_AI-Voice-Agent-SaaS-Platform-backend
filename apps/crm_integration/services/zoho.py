import requests
from datetime import timedelta
from urllib.parse import urlencode
from decouple import config
from django.utils import timezone
from .base import BaseOAuthService

REGION = config("ZOHO_REGION", default="com")


class ZohoService(BaseOAuthService):
    CLIENT_ID = config("ZOHO_CLIENT_ID", default=None)
    CLIENT_SECRET = config("ZOHO_CLIENT_SECRET", default=None)

    OAUTH_URL = f"https://accounts.zoho.{REGION}/oauth/v2/auth"
    TOKEN_URL = f"https://accounts.zoho.{REGION}/oauth/v2/token"
    API_BASE_URL = f"https://www.zohoapis.{REGION}/crm/v3"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.redirect_uri = redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/zoho/"

    def get_oauth_url(self, state):
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "ZohoCRM.modules.leads.ALL ZohoCRM.modules.contacts.READ",
            "access_type": "offline",
        }
        return f"{self.OAUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code, **_):
        resp = requests.post(self.TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.redirect_uri,
            "code": code,
        })
        if resp.status_code == 200:
            d = resp.json()
            return {"success": True, "access_token": d.get("access_token"), "refresh_token": d.get("refresh_token"), "expires_in": d.get("expires_in", 3600)}
        return {"success": False, "error": resp.text}

    def refresh_access_token(self) -> bool:
        if not self.refresh_token:
            return False
        resp = requests.post(self.TOKEN_URL, data={
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
        })
        if resp.status_code == 200:
            d = resp.json()
            self.access_token = d.get("access_token")
            if self.crm_connection:
                self.crm_connection.access_token = self.access_token
                self.crm_connection.access_token_expires_at = timezone.now() + timedelta(seconds=d.get("expires_in", 3600))
                self.crm_connection.save(update_fields=["access_token", "access_token_expires_at"])
            return True
        return False

    def verify_webhook_signature(self, body, signature) -> bool:
        return True

    def configure_webhook(self, webhook_url) -> dict:
        return {"success": True, "message": "Zoho webhook via developer console"}

    def fetch_leads(self):
        if not self._ensure_valid_token():
            return {"error": "Could not refresh token"}
        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
        resp = requests.get(f"{self.API_BASE_URL}/Leads", headers=headers, params={"fields": "First_Name,Last_Name,Email,Phone,Company,Lead_Status"})
        if resp.status_code == 200:
            return resp.json().get("data", [])
        return {"error": f"Zoho fetch failed: {resp.status_code} {resp.text}"}

    def sync_leads_to_db(self) -> dict:
        if not self.crm_connection:
            return {"success": False, "error": "No CRM connection"}
        leads = self.fetch_leads()
        if isinstance(leads, dict):
            return {"success": False, "error": leads.get("error")}
        saved, updated = 0, 0
        for lead in leads:
            first = (lead.get("First_Name") or "").strip()
            last = (lead.get("Last_Name") or "").strip()
            created = self._save_lead(lead.get("id"), {
                "crm_object_type": "lead",
                "name": " ".join(filter(None, [first, last])) or None,
                "email": lead.get("Email") or None,
                "phone": lead.get("Phone") or None,
                "raw_data": lead,
            })
            if created: saved += 1
            else: updated += 1
        return self._finish_sync(saved, updated)

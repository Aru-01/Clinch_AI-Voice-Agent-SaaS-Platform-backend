import requests
from datetime import timedelta
from urllib.parse import urlencode
from decouple import config
from django.utils import timezone
from .base import BaseOAuthService


class PipedriveService(BaseOAuthService):
    CLIENT_ID = config("PIPEDRIVE_CLIENT_ID", default=None)
    CLIENT_SECRET = config("PIPEDRIVE_CLIENT_SECRET", default=None)

    OAUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
    TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"
    API_BASE_URL = "https://api.pipedrive.com/v1"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.redirect_uri = redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/pipedrive/"

    def get_oauth_url(self, state):
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "leads:read deals:read persons:read contacts:read",
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
        if not self._ensure_valid_token():
            return {"success": False, "error": "No access token"}
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        resp = requests.post(
            f"{self.API_BASE_URL}/webhooks",
            json={"subscription_url": webhook_url, "event_action": "*", "event_object": "*"},
            headers=headers,
        )
        if resp.status_code in [200, 201]:
            d = resp.json().get("data") or {}
            return {"success": True, "webhook_id": str(d.get("id", "")), "webhook_secret": d.get("http_auth_password")}
        return {"success": False, "error": resp.text}

    def fetch_leads(self):
        if not self._ensure_valid_token():
            return {"error": "Could not refresh token"}
        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Try leads endpoint first, fallback to persons
        resp = requests.get(f"{self.API_BASE_URL}/leads", headers=headers, params={"limit": 100})
        if resp.status_code == 200:
            leads = resp.json().get("data", []) or []
            if leads:
                return leads

        resp = requests.get(f"{self.API_BASE_URL}/persons", headers=headers, params={"limit": 100})
        if resp.status_code == 200:
            return resp.json().get("data", []) or []

        return {"error": f"Pipedrive fetch failed: {resp.status_code} {resp.text}"}

    def fetch_person_by_id(self, person_id) -> dict:
        """Fetch person details by ID"""
        if not self._ensure_valid_token():
            return {}
        resp = requests.get(
            f"{self.API_BASE_URL}/persons/{person_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        return resp.json().get("data") or {} if resp.status_code == 200 else {}

    def _extract_person_fields(self, item) -> dict:
        """Extract name/email/phone from a Pipedrive lead or person record"""
        person_obj = item.get("person_id")

        # person_id is an integer — fetch details from API
        if isinstance(person_obj, int):
            person_obj = self.fetch_person_by_id(person_obj)

        # person_id is an object {id, name, email, phone}
        if isinstance(person_obj, dict) and person_obj:
            name_parts = (person_obj.get("name") or "").split(" ", 1)
            emails = person_obj.get("email") or []
            phones = person_obj.get("phone") or []
            return {
                "first_name": name_parts[0] if name_parts else "",
                "last_name": name_parts[1] if len(name_parts) > 1 else "",
                "email": emails[0].get("value") if isinstance(emails, list) and emails else None,
                "phone": phones[0].get("value") if isinstance(phones, list) and phones else None,
            }

        # Persons API or fallback — use title as first_name
        name_parts = (item.get("name") or item.get("title") or "").split(" ", 1)
        emails = item.get("email") or []
        phones = item.get("phone") or []
        return {
            "first_name": name_parts[0] if name_parts else "",
            "last_name": name_parts[1] if len(name_parts) > 1 else "",
            "email": emails[0].get("value") if isinstance(emails, list) and emails else None,
            "phone": phones[0].get("value") if isinstance(phones, list) and phones else None,
        }

    def sync_leads_to_db(self) -> dict:
        if not self.crm_connection:
            return {"success": False, "error": "No CRM connection"}
        leads = self.fetch_leads()
        if isinstance(leads, dict):
            return {"success": False, "error": leads.get("error")}
        saved, updated = 0, 0
        for item in leads:
            fields = self._extract_person_fields(item)
            created = self._save_lead(item.get("id"), {
                "crm_object_type": "lead",
                "raw_data": item,
                **fields,
            })
            if created: saved += 1
            else: updated += 1
        return self._finish_sync(saved, updated)

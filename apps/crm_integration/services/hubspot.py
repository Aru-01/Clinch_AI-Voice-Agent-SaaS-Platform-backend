import requests
import hmac
import hashlib
from datetime import timedelta
from urllib.parse import urlencode
from decouple import config
from django.utils import timezone
from .base import BaseOAuthService, generate_pkce_pair


class HubSpotService(BaseOAuthService):
    CLIENT_ID = config("HUBSPOT_CLIENT_ID", default=None)
    CLIENT_SECRET = config("HUBSPOT_CLIENT_SECRET", default=None)

    OAUTH_URL = "https://mcp-na2.hubspot.com/oauth/authorize/user"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    API_BASE_URL = "https://api.hubapi.com"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.redirect_uri = redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/hubspot/"

    def get_oauth_url(self, state):
        code_verifier, code_challenge = generate_pkce_pair()
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        return f"{self.OAUTH_URL}?{urlencode(params)}", code_verifier

    def exchange_code_for_token(self, code, code_verifier=None, **_):
        data = {
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.redirect_uri,
            "code": code,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        resp = requests.post(self.TOKEN_URL, data=data)
        if resp.status_code == 200:
            d = resp.json()
            return {"success": True, "access_token": d.get("access_token"), "refresh_token": d.get("refresh_token"), "expires_in": d.get("expires_in")}
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
        if not self.crm_connection or not self.crm_connection.webhook_secret:
            return True
        expected = hmac.new(self.crm_connection.webhook_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    def configure_webhook(self, webhook_url) -> dict:
        if not self.access_token:
            return {"success": False, "error": "No access token"}
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        resp = requests.post(
            f"{self.API_BASE_URL}/crm/v3/objects/contacts/webhooks",
            json={"targetUrl": webhook_url, "events": ["contacts.propertyChange", "contact.creation"]},
            headers=headers,
        )
        if resp.status_code in [200, 201]:
            d = resp.json()
            return {"success": True, "webhook_secret": d.get("secret"), "webhook_id": d.get("id")}
        return {"success": False, "error": resp.text}

    def fetch_contact_by_id(self, contact_id):
        """Fetch single contact details by ID (used in webhook handler)"""
        if not self._ensure_valid_token():
            return None
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"properties": "firstname,lastname,email,phone"}
        resp = requests.get(f"{self.API_BASE_URL}/crm/v3/objects/contacts/{contact_id}", headers=headers, params=params)
        return resp.json() if resp.status_code == 200 else None

    def fetch_leads(self):
        if not self._ensure_valid_token():
            return {"error": "Could not refresh token"}
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"properties": "firstname,lastname,email,phone,company,lifecyclestage", "limit": 100}
        resp = requests.get(f"{self.API_BASE_URL}/crm/v3/objects/contacts", headers=headers, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return {"error": f"HubSpot fetch failed: {resp.status_code} {resp.text}"}

    def sync_leads_to_db(self) -> dict:
        if not self.crm_connection:
            return {"success": False, "error": "No CRM connection"}
        leads = self.fetch_leads()
        if isinstance(leads, dict):
            return {"success": False, "error": leads.get("error")}
        saved, updated = 0, 0
        for c in leads:
            p = c.get("properties", {})
            first = (p.get("firstname") or "").strip()
            last = (p.get("lastname") or "").strip()
            created = self._save_lead(c.get("id"), {
                "crm_object_type": "contact",
                "name": " ".join(filter(None, [first, last])) or None,
                "email": p.get("email") or None,
                "phone": p.get("phone") or None,
                "raw_data": c,
            })
            if created: saved += 1
            else: updated += 1
        return self._finish_sync(saved, updated)

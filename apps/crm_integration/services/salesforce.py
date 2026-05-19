import requests
from datetime import timedelta
from urllib.parse import urlencode
from decouple import config
from django.utils import timezone
from .base import BaseOAuthService

INSTANCE_URL = config("SALESFORCE_INSTANCE_URL", default="https://login.salesforce.com")


class SalesforceService(BaseOAuthService):
    CLIENT_ID = config("SALESFORCE_CLIENT_ID", default=None)
    CLIENT_SECRET = config("SALESFORCE_CLIENT_SECRET", default=None)

    OAUTH_URL = f"{INSTANCE_URL}/services/oauth2/authorize"
    TOKEN_URL = f"{INSTANCE_URL}/services/oauth2/token"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.redirect_uri = redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/salesforce/"
        # Use instance_url from saved config if available
        if crm_connection and crm_connection.raw_config.get("instance_url"):
            self.api_base = crm_connection.raw_config["instance_url"]
        else:
            self.api_base = INSTANCE_URL

    def get_oauth_url(self, state):
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "api refresh_token",
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
            return {"success": True, "access_token": d.get("access_token"), "refresh_token": d.get("refresh_token"), "expires_in": 7200, "instance_url": d.get("instance_url")}
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
                self.crm_connection.access_token_expires_at = timezone.now() + timedelta(hours=2)
                self.crm_connection.save(update_fields=["access_token", "access_token_expires_at"])
            return True
        return False

    def verify_webhook_signature(self, body, signature) -> bool:
        return True

    def configure_webhook(self, webhook_url) -> dict:
        return {"success": True, "message": "Salesforce webhook via outbound message"}

    def _query(self, soql) -> list:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = requests.get(f"{self.api_base}/services/data/v60.0/query/", headers=headers, params={"q": soql})
        if resp.status_code == 200:
            return resp.json().get("records", [])
        return []

    def fetch_leads(self, since=None):
        if not self._ensure_valid_token():
            return {"error": "Could not refresh token"}
        where = f" WHERE LastModifiedDate >= {since.strftime('%Y-%m-%dT%H:%M:%SZ')}" if since else ""
        leads = self._query(f"SELECT Id, FirstName, LastName, Email, Phone FROM Lead{where} LIMIT 200")
        contacts = self._query(f"SELECT Id, FirstName, LastName, Email, Phone FROM Contact{where} LIMIT 200")
        for r in leads:
            r["_sf_type"] = "Lead"
        for r in contacts:
            r["_sf_type"] = "Contact"
        combined = leads + contacts
        if not combined:
            return {"error": "No leads or contacts found in Salesforce"}
        return combined

    def sync_leads_to_db(self) -> dict:
        if not self.crm_connection:
            return {"success": False, "error": "No CRM connection"}
        since = self.crm_connection.last_sync_at if self.crm_connection.last_sync_at else None
        records = self.fetch_leads(since=since)
        if isinstance(records, dict):
            return {"success": False, "error": records.get("error")}
        saved, updated = 0, 0
        for r in records:
            created = self._save_lead(r.get("Id"), {
                "crm_object_type": r.get("_sf_type", "lead").lower(),
                "first_name": r.get("FirstName") or "",
                "last_name": r.get("LastName") or "",
                "email": r.get("Email"),
                "phone": r.get("Phone"),
                "raw_data": {k: v for k, v in r.items() if k != "_sf_type"},
            })
            if created: saved += 1
            else: updated += 1
        return self._finish_sync(saved, updated)

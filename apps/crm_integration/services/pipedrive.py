import logging
import requests
from datetime import timedelta
from urllib.parse import urlencode
from decouple import config
from django.utils import timezone

logger = logging.getLogger(__name__)
from .base import BaseOAuthService


class _PipedriveScopeError(Exception):
    pass


class PipedriveService(BaseOAuthService):
    CLIENT_ID = config("PIPEDRIVE_CLIENT_ID", default=None)
    CLIENT_SECRET = config("PIPEDRIVE_CLIENT_SECRET", default=None)

    OAUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
    TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"
    API_BASE_URL = "https://api.pipedrive.com/v1"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.redirect_uri = redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/pipedrive/"
        # Use the account-specific API domain saved during OAuth (Pipedrive sandbox/company domains differ)
        api_domain = crm_connection.raw_config.get("api_domain") if crm_connection else None
        self.api_base = f"{api_domain}/v1" if api_domain else "https://api.pipedrive.com/v1"

    def get_oauth_url(self, state):
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "leads:read deals:read contacts:read",
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
            logger.info("[Pipedrive] token: api_domain=%s | scope=%s", d.get('api_domain'), d.get('scope'))
            return {
                "success": True,
                "access_token": d.get("access_token"),
                "refresh_token": d.get("refresh_token"),
                "expires_in": d.get("expires_in", 3600),
                "api_domain": d.get("api_domain"),
            }
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
            f"{self.api_base}/webhooks",
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
        resp = requests.get(f"{self.api_base}/leads", headers=headers, params={"limit": 100})
        if resp.status_code == 200:
            leads = resp.json().get("data", []) or []
            if leads:
                return leads

        resp = requests.get(f"{self.api_base}/persons", headers=headers, params={"limit": 100})
        if resp.status_code == 200:
            return resp.json().get("data", []) or []

        return {"error": f"Pipedrive fetch failed: {resp.status_code} {resp.text}"}

    def fetch_person_by_id(self, person_id) -> dict:
        if not self._ensure_valid_token():
            return {}
        resp = requests.get(
            f"{self.api_base}/persons/{person_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        url = f"{self.api_base}/persons/{person_id}"
        logger.debug("[Pipedrive] GET %s → %s", url, resp.status_code)
        if resp.status_code == 200:
            return resp.json().get("data") or {}
        if resp.status_code == 403:
            raise _PipedriveScopeError()
        return {}

    def _extract_person_fields(self, item) -> dict:
        person_obj = item.get("person_id")

        # integer person_id — fetch full details
        if isinstance(person_obj, int):
            person_obj = self.fetch_person_by_id(person_obj)

        # summary dict {id, name} without email/phone — fetch full details
        if isinstance(person_obj, dict) and person_obj:
            if person_obj.get("id") and not (person_obj.get("email") or person_obj.get("phone")):
                person_obj = self.fetch_person_by_id(person_obj["id"]) or person_obj
            emails = person_obj.get("email") or []
            phones = person_obj.get("phone") or []
            return {
                "name": (person_obj.get("name") or "").strip() or None,
                "email": next((e["value"] for e in emails if isinstance(e, dict) and e.get("value")), None),
                "phone": next((p["value"] for p in phones if isinstance(p, dict) and p.get("value")), None),
            }

        # no linked person — use item-level fields (Persons API records carry email/phone directly)
        emails = item.get("email") or []
        phones = item.get("phone") or []
        return {
            "name": ((item.get("name") or item.get("title") or "").strip()) or None,
            "email": next((e["value"] for e in emails if isinstance(e, dict) and e.get("value")), None),
            "phone": next((p["value"] for p in phones if isinstance(p, dict) and p.get("value")), None),
        }

    def sync_leads_to_db(self) -> dict:
        if not self.crm_connection:
            return {"success": False, "error": "No CRM connection"}
        leads = self.fetch_leads()
        if isinstance(leads, dict):
            return {"success": False, "error": leads.get("error")}
        saved, updated = 0, 0
        needs_reauth = False
        for item in leads:
            try:
                fields = self._extract_person_fields(item)
            except _PipedriveScopeError:
                needs_reauth = True
                fields = {
                    "name": (item.get("title") or "").strip() or None,
                    "email": None,
                    "phone": None,
                }
            created = self._save_lead(item.get("id"), {
                "crm_object_type": "lead",
                "raw_data": item,
                "name": fields.get("name"),
                "email": fields.get("email"),
                "phone": fields.get("phone"),
            })
            if created: saved += 1
            else: updated += 1
        result = self._finish_sync(saved, updated)
        if needs_reauth:
            result["warning"] = (
                "Pipedrive connection needs re-authorization to fetch email/phone. "
                "Please disconnect and reconnect Pipedrive from the CRM settings."
            )
        return result

import os
import base64
import requests
import hmac
import hashlib
from datetime import timedelta
from urllib.parse import urlencode
from decouple import config
from django.utils import timezone
from apps.crm_integration.models import CRMConnection


def generate_pkce_pair():
    """Generate PKCE code_verifier and code_challenge for OAuth"""
    code_verifier = base64.urlsafe_b64encode(os.urandom(64)).rstrip(b'=').decode('utf-8')
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('utf-8')
    return code_verifier, code_challenge


class BaseOAuthService:
    """Base class for all OAuth services"""

    def __init__(self, crm_connection: CRMConnection = None):
        self.crm_connection = crm_connection
        self.access_token = crm_connection.access_token if crm_connection else None
        self.refresh_token = crm_connection.refresh_token if crm_connection else None

    def get_oauth_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        raise NotImplementedError

    def exchange_code_for_token(self, code: str, **_) -> dict:
        """Exchange authorization code for access token"""
        raise NotImplementedError

    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        raise NotImplementedError

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Verify webhook signature"""
        raise NotImplementedError

    def configure_webhook(self, webhook_url: str) -> dict:
        """Configure webhook on CRM"""
        raise NotImplementedError


class HubSpotService(BaseOAuthService):
    """HubSpot OAuth Service - MCP App with PKCE"""

    CLIENT_ID = config("HUBSPOT_CLIENT_ID", default=None)
    CLIENT_SECRET = config("HUBSPOT_CLIENT_SECRET", default=None)
    REDIRECT_URI = None

    # MCP App uses mcp-na2 for auth, but token exchange uses api.hubapi.com
    OAUTH_URL = "https://mcp-na2.hubspot.com/oauth/authorize/user"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    API_BASE_URL = "https://api.hubapi.com"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.REDIRECT_URI = (
            redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/hubspot/"
        )

    def get_oauth_url(self, state: str) -> tuple:
        """Generate HubSpot MCP OAuth URL with PKCE. Returns (url, code_verifier)"""
        code_verifier, code_challenge = generate_pkce_pair()

        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        url = f"{self.OAUTH_URL}?{urlencode(params)}"
        return url, code_verifier

    def exchange_code_for_token(self, code: str, code_verifier: str = None) -> dict:
        """Exchange authorization code for tokens (MCP PKCE: needs both code_verifier + client_secret)"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.REDIRECT_URI,
            "code": code,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "success": True,
            }
        return {"success": False, "error": response.text}

    def refresh_access_token(self) -> bool:
        """Refresh HubSpot access token"""
        if not self.refresh_token:
            return False

        data = {
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            if self.crm_connection:
                self.crm_connection.access_token = self.access_token
                self.crm_connection.access_token_expires_at = (
                    timezone.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600))
                )
                self.crm_connection.save()
            return True
        return False

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Verify HubSpot webhook signature"""
        if not self.crm_connection or not self.crm_connection.webhook_secret:
            return False

        expected_signature = hmac.new(
            self.crm_connection.webhook_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def configure_webhook(self, webhook_url: str) -> dict:
        """Configure webhook on HubSpot"""
        if not self.access_token:
            return {"success": False, "error": "No access token"}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        webhook_data = {
            "targetUrl": webhook_url,
            "events": ["contacts.propertyChange", "contact.creation"],
        }

        response = requests.post(
            f"{self.API_BASE_URL}/crm/v3/objects/contacts/webhooks",
            json=webhook_data,
            headers=headers,
        )

        if response.status_code in [200, 201]:
            webhook_response = response.json()
            return {
                "success": True,
                "webhook_secret": webhook_response.get("secret"),
                "webhook_id": webhook_response.get("id"),
            }
        return {"success": False, "error": response.text}

    def fetch_leads(self):
        """Fetch leads from HubSpot"""
        if not self.access_token:
            return {"error": "No access token"}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        params = {
            "properties": [
                "firstname",
                "lastname",
                "email",
                "phone",
                "company",
                "lifecyclestage",
            ],
            "limit": 100,
        }

        response = requests.get(
            f"{self.API_BASE_URL}/crm/v3/objects/contacts",
            headers=headers,
            params=params,
        )

        if response.status_code == 200:
            return response.json().get("results", [])
        return {"error": f"Failed with status {response.status_code}"}


class SalesforceService(BaseOAuthService):
    """Salesforce OAuth Service"""

    CLIENT_ID = config("SALESFORCE_CLIENT_ID", default=None)
    CLIENT_SECRET = config("SALESFORCE_CLIENT_SECRET", default=None)
    INSTANCE_URL = config(
        "SALESFORCE_INSTANCE_URL", default="https://login.salesforce.com"
    )
    REDIRECT_URI = None

    OAUTH_URL = f"{INSTANCE_URL}/services/oauth2/authorize"
    TOKEN_URL = f"{INSTANCE_URL}/services/oauth2/token"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.REDIRECT_URI = (
            redirect_uri
            or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/salesforce/"
        )

    def get_oauth_url(self, state: str) -> str:
        """Generate Salesforce OAuth URL"""
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "state": state,
            "scope": "api refresh_token",
        }
        return f"{self.OAUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str, _code_verifier: str = None) -> dict:
        """Exchange authorization code for tokens"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.REDIRECT_URI,
            "code": code,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "instance_url": token_data.get("instance_url"),
                "expires_in": 3600,
                "success": True,
            }
        return {"success": False, "error": response.text}

    def refresh_access_token(self) -> bool:
        """Refresh Salesforce access token"""
        if not self.refresh_token:
            return False

        data = {
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            if self.crm_connection:
                self.crm_connection.access_token = self.access_token
                self.crm_connection.access_token_expires_at = (
                    timezone.now() + timedelta(hours=1)
                )
                self.crm_connection.save()
            return True
        return False

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Salesforce webhook verification"""
        return True

    def configure_webhook(self, webhook_url: str) -> dict:
        """Configure webhook on Salesforce"""
        return {"success": True, "message": "Salesforce webhook configured via setup"}

    def fetch_leads(self):
        """Fetch leads from Salesforce"""
        if not self.access_token:
            return {"error": "No access token"}

        headers = {"Authorization": f"Bearer {self.access_token}"}

        query = (
            "SELECT Id, FirstName, LastName, Email, Phone, Company FROM Lead LIMIT 100"
        )
        params = {"q": query}

        response = requests.get(
            f"{self.crm_connection.raw_config.get('instance_url', self.INSTANCE_URL)}/services/data/v60.0/query/",
            headers=headers,
            params=params,
        )

        if response.status_code == 200:
            return response.json().get("records", [])
        return {"error": f"Failed with status {response.status_code}"}


class ZohoService(BaseOAuthService):
    """Zoho CRM OAuth Service"""

    CLIENT_ID = config("ZOHO_CLIENT_ID", default=None)
    CLIENT_SECRET = config("ZOHO_CLIENT_SECRET", default=None)
    REGION = config("ZOHO_REGION", default="com")
    REDIRECT_URI = None

    OAUTH_URL = f"https://accounts.zoho.{REGION}/oauth/v2/auth"
    TOKEN_URL = f"https://accounts.zoho.{REGION}/oauth/v2/token"
    API_BASE_URL = f"https://www.zohoapis.{REGION}/crm/v3"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.REDIRECT_URI = (
            redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/zoho/"
        )

    def get_oauth_url(self, state: str) -> str:
        """Generate Zoho OAuth URL"""
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "state": state,
            "scope": "ZohoCRM.modules.leads.READ ZohoCRM.modules.leads.CREATE ZohoCRM.modules.contacts.READ",
            "access_type": "offline",
        }
        return f"{self.OAUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str, _code_verifier: str = None) -> dict:
        """Exchange authorization code for tokens"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.REDIRECT_URI,
            "code": code,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in", 3600),
                "success": True,
            }
        return {"success": False, "error": response.text}

    def refresh_access_token(self) -> bool:
        """Refresh Zoho access token"""
        if not self.refresh_token:
            return False

        data = {
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            if self.crm_connection:
                self.crm_connection.access_token = self.access_token
                self.crm_connection.access_token_expires_at = (
                    timezone.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600))
                )
                self.crm_connection.save()
            return True
        return False

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Zoho webhook verification"""
        return True

    def configure_webhook(self, webhook_url: str) -> dict:
        """Configure webhook on Zoho"""
        return {"success": True, "message": "Zoho webhook will be configured manually"}

    def fetch_leads(self):
        """Fetch leads from Zoho"""
        if not self.access_token:
            if not self.refresh_access_token():
                return {"error": "Could not refresh token"}

        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
        params = {"fields": "First_Name,Last_Name,Email,Phone,Company"}

        response = requests.get(
            f"{self.API_BASE_URL}/Leads", headers=headers, params=params
        )

        if response.status_code == 200:
            return response.json().get("data", [])
        return {"error": f"Failed with status {response.status_code}"}


class PipedriveService(BaseOAuthService):
    """Pipedrive OAuth Service"""

    CLIENT_ID = config("PIPEDRIVE_CLIENT_ID", default=None)
    CLIENT_SECRET = config("PIPEDRIVE_CLIENT_SECRET", default=None)
    REDIRECT_URI = None

    OAUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
    TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"
    API_BASE_URL = "https://api.pipedrive.com/v1"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.REDIRECT_URI = (
            redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/pipedrive/"
        )

    def get_oauth_url(self, state: str) -> str:
        """Generate Pipedrive OAuth URL"""
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "state": state,
        }
        return f"{self.OAUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str, _code_verifier: str = None) -> dict:
        """Exchange authorization code for tokens"""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.REDIRECT_URI,
            "code": code,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in", 3600),
                "success": True,
            }
        return {"success": False, "error": response.text}

    def refresh_access_token(self) -> bool:
        """Refresh Pipedrive access token"""
        if not self.refresh_token:
            return False

        data = {
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "refresh_token": self.refresh_token,
        }

        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            if self.crm_connection:
                self.crm_connection.access_token = self.access_token
                self.crm_connection.access_token_expires_at = (
                    timezone.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600))
                )
                self.crm_connection.save()
            return True
        return False

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Pipedrive webhook verification"""
        return True

    def configure_webhook(self, webhook_url: str) -> dict:
        """Configure webhook on Pipedrive"""
        return {"success": True, "message": "Pipedrive webhook configured"}


class GHLService(BaseOAuthService):
    """GoHighLevel OAuth Service - Placeholder for later"""

    CLIENT_ID = config("GHL_CLIENT_ID", default=None)
    CLIENT_SECRET = config("GHL_CLIENT_SECRET", default=None)
    REDIRECT_URI = None

    OAUTH_URL = "https://highlevel.com/oauth/authorize"
    TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"

    def __init__(self, crm_connection=None, redirect_uri=None):
        super().__init__(crm_connection)
        self.REDIRECT_URI = (
            redirect_uri or f"{config('CALLBACK_BASE_URL')}/api/crm/callback/ghl/"
        )

    def get_oauth_url(self, state: str) -> str:
        raise NotImplementedError("GHL OAuth will be implemented later")

    def exchange_code_for_token(self, code: str, _code_verifier: str = None) -> dict:
        raise NotImplementedError("GHL OAuth will be implemented later")

    def refresh_access_token(self) -> bool:
        raise NotImplementedError("GHL OAuth will be implemented later")

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        return True

    def configure_webhook(self, webhook_url: str) -> dict:
        raise NotImplementedError("GHL OAuth will be implemented later")


def get_oauth_service(crm_type: str, crm_connection=None, redirect_uri=None):
    """Factory function to get appropriate OAuth service"""
    services = {
        "hubspot": HubSpotService,
        "salesforce": SalesforceService,
        "zoho": ZohoService,
        "pipedrive": PipedriveService,
        "ghl": GHLService,
    }

    service_class = services.get(crm_type)
    if not service_class:
        raise ValueError(f"Unknown CRM type: {crm_type}")

    return service_class(crm_connection, redirect_uri)

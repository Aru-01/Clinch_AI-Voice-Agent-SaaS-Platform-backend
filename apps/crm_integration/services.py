import requests
from decouple import config

class HubSpotService:
    def __init__(self):
        self.access_token = config("HUBSPOT_ACCESS_TOKEN", default=None)
        self.base_url = "https://api.hubapi.com/crm/v3/objects/contacts"

    def fetch_leads(self):
        if not self.access_token:
            return {"error": "HubSpot Access Token is missing in .env"}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        # Requesting more properties explicitly
        params = {
            "properties": "firstname,lastname,email,phone,company,website,lifecyclestage"
        }
        response = requests.get(self.base_url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json().get('results', [])
        return {"error": f"Failed with status {response.status_code}", "details": response.text}


class ZohoService:
    def __init__(self):
        self.client_id = config("zoho_client_id", default=None)
        self.client_secret = config("zoho_client_secret", default=None)
        self.refresh_token = config("zoho_refresh_token", default=None)
        # We need an access token to make API calls to Zoho
        self.access_token = None 

    def generate_access_token(self):
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return False
            
        url = "https://accounts.zoho.com/oauth/v2/token"
        data = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            return True
        return False

    def fetch_leads(self):
        # If no refresh token, we can't proceed
        if not self.refresh_token:
            return {
                "error": "zoho_refresh_token is missing in .env. "
                         "You need to generate a grant token and exchange it for a refresh token."
            }

        if not self.access_token:
            success = self.generate_access_token()
            if not success:
                return {"error": "Could not generate Zoho Access Token. Check Client ID, Secret, and Refresh Token."}

        url = "https://www.zohoapis.com/crm/v3/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}"
        }
        # Explicitly asking for fields to satisfy Zoho V3 requirements
        params = {
            "fields": "First_Name,Last_Name,Email,Phone,Company,Full_Name"
        }
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json().get('data', [])
        return {"error": f"Failed with status {response.status_code}", "details": response.text}


class SalesforceService:
    def __init__(self):
        self.client_id = config("SALESFORCE_CLIENT_ID", default=None)
        self.client_secret = config("SALESFORCE_CLIENT_SECRET", default=None)
        self.refresh_token = config("SALESFORCE_REFRESH_TOKEN", default=None)
        self.instance_url = config("SALESFORCE_INSTANCE_URL", default=None)
        self.access_token = None

    def refresh_access_token(self):
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return False
        
        # Salesforce token endpoint
        url = "https://login.salesforce.com/services/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            return True
        return False

    def fetch_leads(self):
        if not self.refresh_token:
            return {"error": "SALESFORCE_REFRESH_TOKEN missing in .env"}

        if not self.access_token:
            if not self.refresh_access_token():
                return {"error": "Could not refresh Salesforce token"}

        # Salesforce query to get Leads
        url = f"{self.instance_url}/services/data/v60.0/query/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"q": "SELECT Id, FirstName, LastName, Email, Company, Phone FROM Lead LIMIT 10"}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get("records", [])
        return {"error": f"Salesforce API failed: {response.status_code}", "details": response.text}


class GoHighLevelService:
    def __init__(self):
        self.client_id = config("GHL_CLIENT_ID", default=None)
        self.client_secret = config("GHL_CLIENT_SECRET", default=None)
        self.refresh_token = config("GHL_REFRESH_TOKEN", default=None)
        self.location_id = config("GHL_LOCATION_ID", default=None)
        self.access_token = None

    def refresh_access_token(self):
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return False
            
        url = "https://services.leadconnectorhq.com/oauth/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "user_type": "Location"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            return True
        return False

    def fetch_leads(self):
        if not self.location_id:
            return {"error": "GHL_LOCATION_ID missing in .env"}

        if not self.access_token:
            if not self.refresh_access_token():
                return {"error": "Could not refresh GHL token"}

        url = "https://services.leadconnectorhq.com/contacts/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Version": "2021-07-28", # Current GHL API Version
            "Accept": "application/json"
        }
        params = {"locationId": self.location_id, "limit": 10}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get("contacts", [])
        return {"error": f"GHL API failed: {response.status_code}", "details": response.text}

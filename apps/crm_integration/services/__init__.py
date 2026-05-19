from .hubspot import HubSpotService
from .salesforce import SalesforceService
from .zoho import ZohoService
from .pipedrive import PipedriveService
from .ghl import GHLService

_SERVICE_MAP = {
    "hubspot": HubSpotService,
    "salesforce": SalesforceService,
    "zoho": ZohoService,
    "pipedrive": PipedriveService,
    "ghl": GHLService,
}


def get_oauth_service(crm_type: str, crm_connection=None, redirect_uri=None):
    cls = _SERVICE_MAP.get(crm_type)
    if not cls:
        raise ValueError(f"Unsupported CRM: {crm_type}")
    return cls(crm_connection, redirect_uri)

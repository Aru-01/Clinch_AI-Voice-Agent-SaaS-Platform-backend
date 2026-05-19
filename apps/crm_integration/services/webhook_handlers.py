import xml.etree.ElementTree as ET
from apps.crm_integration.models import SyncedLead


def upsert_lead(conn, crm_id, **fields):
    SyncedLead.objects.update_or_create(
        crm_connection=conn,
        crm_lead_id=str(crm_id),
        defaults={"business": conn.business, **fields},
    )


def parse_salesforce_soap(body: str) -> dict:
    try:
        root = ET.fromstring(body)
        obj = root.find(".//{http://soap.sforce.com/2005/09/outbound}sObject")
        if obj is None:
            return {}
        return {
            (child.tag.split("}")[-1] if "}" in child.tag else child.tag): child.text
            for child in obj
        }
    except Exception:
        return {}


def handle_hubspot(conn, data):
    from apps.crm_integration.services.hubspot import HubSpotService

    service = HubSpotService(conn)
    for event in (data if isinstance(data, list) else [data]):
        object_id = event.get("objectId")
        if not object_id:
            continue
        contact = service.fetch_contact_by_id(object_id)
        if contact:
            props = contact.get("properties", {})
            upsert_lead(conn, object_id, crm_object_type="contact",
                        first_name=props.get("firstname", ""), last_name=props.get("lastname", ""),
                        email=props.get("email"), phone=props.get("phone"), raw_data=contact)
        else:
            upsert_lead(conn, object_id, crm_object_type="contact", raw_data=event)


def handle_salesforce(conn, data):
    upsert_lead(conn, data.get("Id") or data.get("id"),
                crm_object_type="lead",
                first_name=data.get("FirstName", ""), last_name=data.get("LastName", ""),
                email=data.get("Email"), phone=data.get("Phone"),
                company=data.get("Company"), raw_data=data)


def handle_zoho(conn, data):
    if isinstance(data, list):
        record = data[0] if data else {}
    elif "data" in data:
        records = data["data"]
        record = records[0] if isinstance(records, list) and records else records or {}
    else:
        record = data

    lead_id = (
        record.get("id") or record.get("ID") or record.get("lead_id")
        or record.get("email") or record.get("Email")
        or record.get("phone") or record.get("Phone")
    )
    if not lead_id:
        return

    upsert_lead(conn, lead_id, crm_object_type="lead",
                first_name=record.get("First_Name") or record.get("first_name", ""),
                last_name=record.get("Last_Name") or record.get("last_name", ""),
                email=record.get("Email") or record.get("email"),
                phone=record.get("Phone") or record.get("phone"),
                raw_data=record)


def handle_pipedrive(conn, data):
    from apps.crm_integration.services.pipedrive import PipedriveService

    service = PipedriveService(conn)
    item = data.get("current") or data
    fields = service._extract_person_fields(item)
    upsert_lead(conn, item.get("id"), crm_object_type="person", raw_data=item, **fields)


_HANDLERS = {
    "hubspot": handle_hubspot,
    "salesforce": handle_salesforce,
    "zoho": handle_zoho,
    "pipedrive": handle_pipedrive,
}


def dispatch(crm_type, conn, data):
    handler = _HANDLERS.get(crm_type)
    if handler:
        handler(conn, data)

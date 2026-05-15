from drf_yasg import openapi

CRM_TAG = "CRM Integration"

crm_test_leads_schema = {
    "operation_description": "Fetch leads from all integrated CRMs (HubSpot, Zoho, Salesforce, GHL) for testing purposes.",
    "tags": [CRM_TAG],
    "responses": {
        200: openapi.Response(
            description="Leads fetched successfully from all active CRMs.",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "hubspot_leads": [],
                        "zoho_leads": [],
                        "salesforce_leads": [],
                        "ghl_leads": []
                    }
                }
            }
        ),
        400: "CRM integration error or missing credentials"
    }
}

crm_webhook_schema = {
    "operation_description": "Generic endpoint to receive real-time lead/contact updates from various CRMs via webhooks.",
    "tags": [CRM_TAG],
    "manual_parameters": [
        openapi.Parameter(
            'crm_type', 
            openapi.IN_PATH, 
            description="Type of the CRM sending the webhook (hubspot, zoho, salesforce, ghl)", 
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    "responses": {
        200: openapi.Response(
            description="Webhook received and processed successfully.",
            examples={"application/json": {"status": "success", "message": "Webhook received for salesforce"}}
        ),
        401: "Unauthorized/Invalid signature"
    }
}

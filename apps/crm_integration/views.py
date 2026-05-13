from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import HubSpotService, ZohoService


class TestCRMLeadsView(APIView):
    def get(self, request):
        try:
            # Initialize services (No credentials passed for testing mock)
            hubspot_service = HubSpotService()
            zoho_service = ZohoService()

            # Fetch leads
            hubspot_leads = hubspot_service.fetch_leads()
            zoho_leads = zoho_service.fetch_leads()

            return Response(
                {
                    "success": True,
                    "message": "Successfully fetched leads from CRMs",
                    "data": {"hubspot_leads": hubspot_leads, "zoho_leads": zoho_leads},
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CRMWebhookView(APIView):
    # In production, you should verify signatures from HubSpot/Zoho
    def post(self, request, crm_type):
        # Debugging info to see where data is coming from
        print(f"--- Webhook Received from {crm_type} ---")
        print(f"Data (request.data): {request.data}")
        print(f"POST (request.POST): {request.POST}")
        print(f"Query Params: {request.query_params}")

        data = request.data
        print(data)

        # Logic for HubSpot (Event list)
        if crm_type == "hubspot" and isinstance(data, list):
            for event in data:
                object_id = event.get("objectId")
                print(
                    f"HubSpot: New event for Object ID {object_id}. We should now fetch details for this ID."
                )

        # Logic for Zoho
        elif crm_type == "zoho":
            if not data and request.POST:
                data = request.POST
                print(f"Zoho: Found data in POST instead of JSON Body: {data}")

        return Response(
            {"status": "success", "message": f"Webhook received for {crm_type}"},
            status=status.HTTP_200_OK,
        )

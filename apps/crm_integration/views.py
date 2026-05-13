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

            return Response({
                "success": True,
                "message": "Successfully fetched leads from CRMs",
                "data": {
                    "hubspot_leads": hubspot_leads,
                    "zoho_leads": zoho_leads
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

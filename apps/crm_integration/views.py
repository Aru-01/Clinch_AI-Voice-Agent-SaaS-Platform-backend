import uuid
import json
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from apps.crm_integration.services import get_oauth_service
from apps.crm_integration.services.webhook_handlers import dispatch, parse_salesforce_soap
from apps.crm_integration.models import CRMConnection, CRMWebhookLog, SyncedLead, CRMSyncState
from apps.crm_integration.serializers import CRMConnectionSerializer, SyncedLeadSerializer
from apps.crm_integration import schemas
from core.pagination import DynamicPageNumberPagination

SUPPORTED_CRMS = ["hubspot", "salesforce", "zoho", "pipedrive", "ghl"]

SALESFORCE_ACK = (
    '<?xml version="1.0"?>'
    '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
    "<soapenv:Body>"
    '<notificationsResponse xmlns="http://soap.sforce.com/2005/09/outbound">'
    "<Ack>true</Ack>"
    "</notificationsResponse>"
    "</soapenv:Body>"
    "</soapenv:Envelope>"
)


class CRMOAuthURLView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(**schemas.crm_oauth_url_schema)
    def get(self, request, crm_type):
        if crm_type not in SUPPORTED_CRMS:
            return Response({"success": False, "error": f"Unsupported CRM: {crm_type}"}, status=400)
        try:
            state = str(uuid.uuid4())
            request.session[f"oauth_state_{crm_type}"] = state

            service = get_oauth_service(crm_type)
            result = service.get_oauth_url(state)

            if isinstance(result, tuple):
                oauth_url, code_verifier = result
                request.session[f"pkce_verifier_{crm_type}"] = code_verifier
            else:
                oauth_url = result

            return Response({"success": True, "authorization_url": oauth_url, "state": state})
        except NotImplementedError as e:
            return Response({"success": False, "error": str(e)}, status=501)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)


class CRMOAuthCallbackView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(auto_schema=None)
    @transaction.atomic
    def get(self, request, crm_type):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        if error:
            return Response({"success": False, "error": f"OAuth error: {error}"}, status=400)
        if not code or not state:
            return Response({"success": False, "error": "Missing code or state"}, status=400)

        stored_state = request.session.get(f"oauth_state_{crm_type}")
        if not stored_state or stored_state != state:
            return Response({"success": False, "error": "Invalid state"}, status=400)

        try:
            code_verifier = request.session.get(f"pkce_verifier_{crm_type}")
            service = get_oauth_service(crm_type)
            token_result = service.exchange_code_for_token(code, code_verifier=code_verifier)

            if not token_result.get("success"):
                return Response({"success": False, "error": token_result.get("error")}, status=400)

            business = request.user.business
            if not business:
                return Response({"success": False, "error": "User not associated with a business"}, status=400)

            expires_at = None
            if token_result.get("expires_in"):
                expires_at = timezone.now() + timezone.timedelta(seconds=token_result["expires_in"])

            crm_connection, created = CRMConnection.objects.update_or_create(
                user=request.user,
                crm_type=crm_type,
                defaults={
                    "business": business,
                    "access_token": token_result.get("access_token"),
                    "refresh_token": token_result.get("refresh_token"),
                    "access_token_expires_at": expires_at,
                    "is_active": True,
                    "raw_config": {"instance_url": token_result.get("instance_url")},
                },
            )
            if created:
                CRMSyncState.objects.create(crm_connection=crm_connection)

            webhook_url = f"{request.build_absolute_uri('/api/crm/webhook/')}{crm_type}/"
            webhook_result = get_oauth_service(crm_type, crm_connection).configure_webhook(webhook_url)
            if webhook_result.get("success"):
                crm_connection.webhook_url = webhook_url
                crm_connection.webhook_secret = webhook_result.get("webhook_secret")
                crm_connection.webhook_id = webhook_result.get("webhook_id")
                crm_connection.save()

            request.session.pop(f"oauth_state_{crm_type}", None)
            request.session.pop(f"pkce_verifier_{crm_type}", None)

            sync_result = get_oauth_service(crm_type, crm_connection).sync_leads_to_db()

            return Response({
                "success": True,
                "message": f"{crm_type} connected successfully",
                "connection_id": str(crm_connection.id),
                "initial_sync": sync_result,
            })
        except NotImplementedError as e:
            return Response({"success": False, "error": str(e)}, status=501)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)


class CRMConnectionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(**schemas.crm_connections_list_schema)
    def get(self, request):
        business = request.user.business
        if not business:
            return Response({"success": False, "error": "No business found"}, status=400)
        connections = CRMConnection.objects.filter(business=business, is_active=True)
        return Response({"success": True, "data": CRMConnectionSerializer(connections, many=True).data})


class CRMDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(**schemas.crm_disconnect_schema)
    def delete(self, request, connection_id):
        try:
            conn = CRMConnection.objects.get(id=connection_id, user=request.user)
            conn.is_active = False
            conn.save(update_fields=["is_active"])
            return Response({"success": True, "message": f"{conn.get_crm_type_display()} disconnected"})
        except CRMConnection.DoesNotExist:
            return Response({"success": False, "error": "Connection not found"}, status=404)


class CRMSyncView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(**schemas.crm_sync_schema)
    def post(self, request, connection_id):
        try:
            business = request.user.business
            conn = CRMConnection.objects.get(id=connection_id, business=business, is_active=True)
            result = get_oauth_service(conn.crm_type, conn).sync_leads_to_db()
            return Response(result)
        except CRMConnection.DoesNotExist:
            return Response({"success": False, "error": "Connection not found"}, status=404)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)


class CRMWebhookView(APIView):

    @swagger_auto_schema(**schemas.crm_webhook_schema)
    def post(self, request, crm_type):
        try:
            conn = CRMConnection.objects.filter(crm_type=crm_type, is_active=True).first()
            if not conn:
                return Response({"success": False, "error": "No active connection"}, status=404)

            body = request.body.decode() if isinstance(request.body, bytes) else request.body
            content_type = request.content_type or ""

            if crm_type == "salesforce" and ("xml" in content_type or body.strip().startswith("<")):
                data = parse_salesforce_soap(body)
            else:
                data = request.data if hasattr(request, "data") else json.loads(body)

            print(f"\n{'='*60}\n[WEBHOOK] CRM: {crm_type}\n[WEBHOOK] DATA: {data}\n{'='*60}\n")

            CRMWebhookLog.objects.create(
                crm_connection=conn,
                event_type="new_lead",
                raw_data=data if isinstance(data, dict) else {"events": data},
            )

            dispatch(crm_type, conn, data)

            if crm_type == "salesforce":
                return HttpResponse(SALESFORCE_ACK, content_type="text/xml")

            return Response({"success": True, "message": f"Webhook from {crm_type} processed"})
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)


class SyncedLeadsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(**schemas.crm_leads_list_schema)
    def get(self, request):
        business = request.user.business
        crm_type = request.query_params.get("crm_type")

        qs = SyncedLead.objects.filter(business=business).select_related("crm_connection").order_by("-created_at")
        if crm_type:
            qs = qs.filter(crm_connection__crm_type=crm_type)

        paginator = DynamicPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(SyncedLeadSerializer(page, many=True).data)

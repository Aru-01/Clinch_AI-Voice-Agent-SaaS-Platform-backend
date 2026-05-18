import uuid
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone
from django.db import transaction

from apps.crm_integration.services import get_oauth_service
from apps.crm_integration.models import CRMConnection, CRMWebhookLog, SyncedLead, CRMSyncState
from apps.accounts.models import Business
from core.permissions import IsBusinessAdmin


class CRMOAuthURLView(APIView):
    """Generate OAuth URL for CRM authorization"""
    permission_classes = [IsAuthenticated]

    def get(self, request, crm_type):
        try:
            if crm_type not in ['hubspot', 'salesforce', 'zoho', 'pipedrive', 'ghl']:
                return Response(
                    {"success": False, "error": f"Unsupported CRM: {crm_type}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            state = str(uuid.uuid4())
            request.session[f'oauth_state_{crm_type}'] = state

            service = get_oauth_service(crm_type)
            result = service.get_oauth_url(state)

            # HubSpot MCP returns (url, code_verifier) tuple for PKCE
            if isinstance(result, tuple):
                oauth_url, code_verifier = result
                request.session[f'pkce_verifier_{crm_type}'] = code_verifier
            else:
                oauth_url = result

            return Response({
                "success": True,
                "authorization_url": oauth_url,
                "state": state
            }, status=status.HTTP_200_OK)

        except NotImplementedError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CRMOAuthCallbackView(APIView):
    """Handle OAuth callback from CRM"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def get(self, request, crm_type):
        try:
            code = request.query_params.get('code')
            state = request.query_params.get('state')
            error = request.query_params.get('error')

            if error:
                return Response(
                    {"success": False, "error": f"OAuth error: {error}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not code or not state:
                return Response(
                    {"success": False, "error": "Missing code or state parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            stored_state = request.session.get(f'oauth_state_{crm_type}')
            if not stored_state or stored_state != state:
                return Response(
                    {"success": False, "error": "Invalid state parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = get_oauth_service(crm_type)
            code_verifier = request.session.get(f'pkce_verifier_{crm_type}')
            token_result = service.exchange_code_for_token(code, code_verifier=code_verifier)

            if not token_result.get('success'):
                return Response(
                    {"success": False, "error": token_result.get('error')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            business = request.user.business
            if not business:
                return Response(
                    {"success": False, "error": "User not associated with a business"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            expires_at = None
            if token_result.get('expires_in'):
                expires_at = timezone.now() + timezone.timedelta(seconds=token_result['expires_in'])

            crm_connection, created = CRMConnection.objects.update_or_create(
                user=request.user,
                crm_type=crm_type,
                defaults={
                    'business': business,
                    'access_token': token_result.get('access_token'),
                    'refresh_token': token_result.get('refresh_token'),
                    'access_token_expires_at': expires_at,
                    'is_active': True,
                    'raw_config': {
                        'instance_url': token_result.get('instance_url'),
                    }
                }
            )

            if created:
                CRMSyncState.objects.create(crm_connection=crm_connection)

            webhook_url = f"{request.build_absolute_uri('/api/crm/webhook/')}{crm_type}/"
            webhook_result = service.configure_webhook(webhook_url)

            if webhook_result.get('success'):
                crm_connection.webhook_url = webhook_url
                crm_connection.webhook_secret = webhook_result.get('webhook_secret')
                crm_connection.webhook_id = webhook_result.get('webhook_id')
                crm_connection.save()

            del request.session[f'oauth_state_{crm_type}']

            return Response({
                "success": True,
                "message": f"{crm_type} connected successfully",
                "connection_id": str(crm_connection.id)
            }, status=status.HTTP_200_OK)

        except NotImplementedError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CRMConnectionListView(APIView):
    """List all connected CRMs for user's business"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            business = request.user.business
            if not business:
                return Response(
                    {"success": False, "error": "User not associated with a business"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            connections = CRMConnection.objects.filter(
                business=business,
                is_active=True
            ).values(
                'id', 'crm_type', 'is_active', 'synced_leads_count', 'last_sync_at', 'created_at'
            )

            return Response({
                "success": True,
                "data": list(connections)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CRMDisconnectView(APIView):
    """Disconnect a CRM"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, connection_id):
        try:
            crm_connection = CRMConnection.objects.get(
                id=connection_id,
                user=request.user
            )

            crm_type = crm_connection.crm_type
            crm_connection.is_active = False
            crm_connection.save()

            return Response({
                "success": True,
                "message": f"{crm_type} disconnected successfully"
            }, status=status.HTTP_200_OK)

        except CRMConnection.DoesNotExist:
            return Response(
                {"success": False, "error": "Connection not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CRMWebhookView(APIView):
    """Receive and process webhook events from CRMs"""

    def post(self, request, crm_type):
        try:
            signature = request.META.get('HTTP_X_HUBSPOT_REQUEST_SIGNATURE')

            try:
                crm_connection = CRMConnection.objects.get(
                    crm_type=crm_type,
                    is_active=True
                )
            except CRMConnection.DoesNotExist:
                return Response(
                    {"success": False, "error": "CRM connection not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            service = get_oauth_service(crm_type, crm_connection)

            body = request.body if isinstance(request.body, str) else request.body.decode()

            if signature and not service.verify_webhook_signature(body, signature):
                return Response(
                    {"success": False, "error": "Invalid signature"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            data = request.data if hasattr(request, 'data') else json.loads(body)

            CRMWebhookLog.objects.create(
                crm_connection=crm_connection,
                event_type='new_lead',
                raw_data=data if isinstance(data, dict) else {"data": data}
            )

            if crm_type == 'hubspot' and isinstance(data, list):
                for event in data:
                    _process_hubspot_webhook(crm_connection, event)

            elif crm_type == 'salesforce':
                _process_salesforce_webhook(crm_connection, data)

            elif crm_type == 'zoho':
                _process_zoho_webhook(crm_connection, data)

            elif crm_type == 'pipedrive':
                _process_pipedrive_webhook(crm_connection, data)

            return Response({
                "success": True,
                "message": f"Webhook from {crm_type} processed successfully"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


def _process_hubspot_webhook(crm_connection, event):
    """Process HubSpot webhook event"""
    object_id = event.get('objectId')
    event_type = event.get('subscriptionType')

    if 'contact.creation' in event_type or 'propertyChange' in event_type:
        SyncedLead.objects.update_or_create(
            crm_connection=crm_connection,
            crm_lead_id=str(object_id),
            defaults={
                'business': crm_connection.business,
                'crm_object_type': 'contact',
                'raw_data': event
            }
        )


def _process_salesforce_webhook(crm_connection, data):
    """Process Salesforce webhook event"""
    lead_id = data.get('Id')
    SyncedLead.objects.update_or_create(
        crm_connection=crm_connection,
        crm_lead_id=lead_id,
        defaults={
            'business': crm_connection.business,
            'first_name': data.get('FirstName', ''),
            'last_name': data.get('LastName', ''),
            'email': data.get('Email'),
            'phone': data.get('Phone'),
            'company': data.get('Company'),
            'raw_data': data
        }
    )


def _process_zoho_webhook(crm_connection, data):
    """Process Zoho webhook event"""
    zoho_data = data.get('data', [{}])[0] if data.get('data') else {}
    lead_id = zoho_data.get('id')

    SyncedLead.objects.update_or_create(
        crm_connection=crm_connection,
        crm_lead_id=lead_id,
        defaults={
            'business': crm_connection.business,
            'first_name': zoho_data.get('First_Name', ''),
            'last_name': zoho_data.get('Last_Name', ''),
            'email': zoho_data.get('Email'),
            'phone': zoho_data.get('Phone'),
            'company': zoho_data.get('Company'),
            'raw_data': zoho_data
        }
    )


def _process_pipedrive_webhook(crm_connection, data):
    """Process Pipedrive webhook event"""
    lead_id = data.get('id')
    SyncedLead.objects.update_or_create(
        crm_connection=crm_connection,
        crm_lead_id=lead_id,
        defaults={
            'business': crm_connection.business,
            'raw_data': data
        }
    )


class SyncedLeadsView(APIView):
    """Get synced leads from CRMs"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            business = request.user.business
            crm_type = request.query_params.get('crm_type')
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 20))

            query = SyncedLead.objects.filter(business=business)

            if crm_type:
                query = query.filter(crm_connection__crm_type=crm_type)

            total = query.count()
            offset = (page - 1) * limit
            leads = list(query[offset:offset + limit].values())

            return Response({
                "success": True,
                "data": leads,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

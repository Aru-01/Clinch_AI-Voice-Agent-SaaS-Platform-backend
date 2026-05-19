import logging
from django.utils import timezone
from apps.crm_integration.models import CRMConnection, CRMSyncState
from apps.crm_integration.services import get_oauth_service

logger = logging.getLogger(__name__)


def process_oauth_callback(crm_type, code, state, stored_state, request_user, build_webhook_url):
    """
    Handles the full OAuth callback flow: token exchange, connection upsert,
    webhook registration, and initial lead sync.

    Returns (result_dict, error_message, http_status) where error_message is None on success.
    """
    if not stored_state or stored_state != state:
        return None, "Invalid state", 400

    service = get_oauth_service(crm_type)
    token_result = service.exchange_code_for_token(code)

    if not token_result.get("success"):
        return None, token_result.get("error"), 400

    business = getattr(request_user, "business", None)
    if not business:
        return None, "User not associated with a business", 400

    expires_at = None
    if token_result.get("expires_in"):
        expires_at = timezone.now() + timezone.timedelta(seconds=token_result["expires_in"])

    crm_connection, created = CRMConnection.objects.update_or_create(
        user=request_user,
        crm_type=crm_type,
        defaults={
            "business": business,
            "access_token": token_result.get("access_token"),
            "refresh_token": token_result.get("refresh_token"),
            "access_token_expires_at": expires_at,
            "is_active": True,
            "raw_config": {
                "instance_url": token_result.get("instance_url"),
                "api_domain": token_result.get("api_domain"),
            },
        },
    )
    if created:
        CRMSyncState.objects.create(crm_connection=crm_connection)

    webhook_url = build_webhook_url(crm_type)
    webhook_result = get_oauth_service(crm_type, crm_connection).configure_webhook(webhook_url)
    if webhook_result.get("success"):
        crm_connection.webhook_url = webhook_url
        crm_connection.webhook_secret = webhook_result.get("webhook_secret")
        crm_connection.webhook_id = webhook_result.get("webhook_id")
        crm_connection.save()

    sync_result = get_oauth_service(crm_type, crm_connection).sync_leads_to_db()

    return {
        "success": True,
        "message": f"{crm_type} connected successfully",
        "connection_id": str(crm_connection.id),
        "initial_sync": sync_result,
    }, None, 200

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# ── common response shapes ────────────────────────────────────────────────

_config_id    = openapi.Schema(type=openapi.TYPE_STRING, format="uuid", description="Config UUID")
_business_id  = openapi.Schema(type=openapi.TYPE_STRING, format="uuid", description="Business UUID")
_masked_key   = openapi.Schema(type=openapi.TYPE_STRING, description="Masked API key, e.g. sk-pr****")
_ts           = openapi.Schema(type=openapi.TYPE_STRING, format="date-time")


# ─────────────────────────────────────────────────────────────────────────
# APIConfig
# ─────────────────────────────────────────────────────────────────────────

_api_config_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id":           _config_id,
        "business":     _business_id,
        "openai_key":   _masked_key,
        "deepgram_key": _masked_key,
        "created_at":   _ts,
        "updated_at":   _ts,
    },
)

_api_config_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "openai_key":   openapi.Schema(type=openapi.TYPE_STRING, description="Full OpenAI key"),
        "deepgram_key": openapi.Schema(type=openapi.TYPE_STRING, description="Full Deepgram key"),
    },
)

api_config_get_schema = dict(
    operation_summary="Get API Config",
    operation_description="Retrieve business API keys (masked for display).",
    tags=["Configuration – API Keys"],
    responses={200: _api_config_response, 404: "Not configured yet"},
)

api_config_create_schema = dict(
    operation_summary="Create API Config",
    operation_description="Add OpenAI and Deepgram keys for the business. Keys are encrypted at rest.",
    tags=["Configuration – API Keys"],
    request_body=_api_config_body,
    responses={201: _api_config_response, 400: "Validation error"},
)

api_config_update_schema = dict(
    operation_summary="Update API Config",
    operation_description="Patch one or both API keys. Omitted keys remain unchanged.",
    tags=["Configuration – API Keys"],
    request_body=_api_config_body,
    responses={200: _api_config_response},
)


# ─────────────────────────────────────────────────────────────────────────
# CRMConfig
# ─────────────────────────────────────────────────────────────────────────

_crm_config_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id":             _config_id,
        "business":       _business_id,
        "provider":       openapi.Schema(type=openapi.TYPE_STRING, enum=["gohighlevel","hubspot","zoho","salesforce","other"]),
        "token":          _masked_key,
        "location_id":    _masked_key,
        "webhook_secret": _masked_key,
        "created_at":     _ts,
        "updated_at":     _ts,
    },
)

_crm_config_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "provider":       openapi.Schema(type=openapi.TYPE_STRING),
        "token":          openapi.Schema(type=openapi.TYPE_STRING),
        "location_id":    openapi.Schema(type=openapi.TYPE_STRING),
        "webhook_secret": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

crm_config_get_schema = dict(
    operation_summary="Get CRM Config",
    operation_description="Retrieve CRM integration credentials (masked).",
    tags=["Configuration – CRM"],
    responses={200: _crm_config_response, 404: "Not configured yet"},
)

crm_config_create_schema = dict(
    operation_summary="Create CRM Config",
    operation_description="Store CRM credentials. Sensitive fields are encrypted at rest.",
    tags=["Configuration – CRM"],
    request_body=_crm_config_body,
    responses={201: _crm_config_response},
)

crm_config_update_schema = dict(
    operation_summary="Update CRM Config",
    operation_description="Patch CRM credentials.",
    tags=["Configuration – CRM"],
    request_body=_crm_config_body,
    responses={200: _crm_config_response},
)


# ─────────────────────────────────────────────────────────────────────────
# TwilioConfig
# ─────────────────────────────────────────────────────────────────────────

_twilio_config_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id":            _config_id,
        "business":      _business_id,
        "twilio_sid":    _masked_key,
        "twilio_token":  _masked_key,
        "twilio_number": openapi.Schema(type=openapi.TYPE_STRING, description="E.164 phone number"),
        "created_at":    _ts,
        "updated_at":    _ts,
    },
)

_twilio_config_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "twilio_sid":    openapi.Schema(type=openapi.TYPE_STRING),
        "twilio_token":  openapi.Schema(type=openapi.TYPE_STRING),
        "twilio_number": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

twilio_config_get_schema = dict(
    operation_summary="Get Twilio Config",
    operation_description="Retrieve Twilio credentials (masked).",
    tags=["Configuration – Twilio"],
    responses={200: _twilio_config_response, 404: "Not configured yet"},
)

twilio_config_create_schema = dict(
    operation_summary="Create Twilio Config",
    operation_description="Store Twilio SID & token. Encrypted at rest.",
    tags=["Configuration – Twilio"],
    request_body=_twilio_config_body,
    responses={201: _twilio_config_response},
)

twilio_config_update_schema = dict(
    operation_summary="Update Twilio Config",
    operation_description="Patch Twilio credentials.",
    tags=["Configuration – Twilio"],
    request_body=_twilio_config_body,
    responses={200: _twilio_config_response},
)


# ─────────────────────────────────────────────────────────────────────────
# VoiceConfig
# ─────────────────────────────────────────────────────────────────────────

_voice_config_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id":             _config_id,
        "business":       _business_id,
        "gender":         openapi.Schema(type=openapi.TYPE_STRING, enum=["male","female","neutral"]),
        "tone":           openapi.Schema(type=openapi.TYPE_STRING, enum=["professional","friendly","formal","casual"]),
        "voice_template": openapi.Schema(type=openapi.TYPE_STRING, description="URL of uploaded audio file"),
        "created_at":     _ts,
        "updated_at":     _ts,
    },
)

_voice_config_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "gender":         openapi.Schema(type=openapi.TYPE_STRING),
        "tone":           openapi.Schema(type=openapi.TYPE_STRING),
        "voice_template": openapi.Schema(type=openapi.TYPE_STRING, format="binary"),
    },
)

voice_config_get_schema = dict(
    operation_summary="Get Voice Config",
    operation_description="Retrieve AI voice personality settings.",
    tags=["Configuration – Voice"],
    responses={200: _voice_config_response, 404: "Not configured yet"},
)

voice_config_create_schema = dict(
    operation_summary="Create Voice Config",
    operation_description="Set AI voice gender, tone and optional audio template.",
    tags=["Configuration – Voice"],
    request_body=_voice_config_body,
    responses={201: _voice_config_response},
)

voice_config_update_schema = dict(
    operation_summary="Update Voice Config",
    operation_description="Patch voice settings.",
    tags=["Configuration – Voice"],
    request_body=_voice_config_body,
    responses={200: _voice_config_response},
)


# ─────────────────────────────────────────────────────────────────────────
# KnowledgeFile
# ─────────────────────────────────────────────────────────────────────────

_knowledge_file_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id":            _config_id,
        "business":      _business_id,
        "name":          openapi.Schema(type=openapi.TYPE_STRING),
        "file":          openapi.Schema(type=openapi.TYPE_STRING, description="File URL"),
        "file_name":     openapi.Schema(type=openapi.TYPE_STRING),
        "file_type":     openapi.Schema(type=openapi.TYPE_STRING),
        "status":        openapi.Schema(type=openapi.TYPE_STRING, enum=["uploaded","processing","processed","failed"]),
        "error_message": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
        "created_at":    _ts,
        "updated_at":    _ts,
    },
)

knowledge_file_list_schema = dict(
    operation_summary="List Knowledge Files",
    operation_description="List all knowledge base files for the business.",
    tags=["Configuration – Knowledge Base"],
    responses={200: openapi.Schema(type=openapi.TYPE_ARRAY, items=_knowledge_file_response)},
)

knowledge_file_upload_schema = dict(
    operation_summary="Upload Knowledge File",
    operation_description="Upload a new knowledge file (pdf/json/csv/txt/docx/xlsx). Stored and queued for processing.",
    tags=["Configuration – Knowledge Base"],
    responses={201: _knowledge_file_response},
)

knowledge_file_delete_schema = dict(
    operation_summary="Delete Knowledge File",
    operation_description="Permanently delete a knowledge file.",
    tags=["Configuration – Knowledge Base"],
    responses={204: "Deleted"},
)

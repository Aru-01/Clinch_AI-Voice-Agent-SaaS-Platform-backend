from django.contrib import admin
from apps.crm_integration.models import (
    CRMConnection,
    CRMWebhookLog,
    SyncedLead,
    CRMSyncState,
)

# Register your models here.
admin.site.register(CRMConnection)
admin.site.register(CRMWebhookLog)
admin.site.register(SyncedLead)
admin.site.register(CRMSyncState)

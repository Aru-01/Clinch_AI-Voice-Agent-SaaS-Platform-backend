from django.contrib import admin
from apps.billing.models import Plan, PlanPrice, PlanFeature, Subscription, Invoice


class PlanPriceInline(admin.TabularInline):
    model = PlanPrice
    extra = 0
    readonly_fields = ["stripe_price_id", "created_at", "updated_at"]
    fields = ["billing_cycle", "price", "currency", "stripe_price_id", "is_active"]


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 1
    fields = ["feature_key", "feature_value"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "created_at"]
    list_editable = ["is_active"]
    search_fields = ["name"]
    inlines = [PlanPriceInline, PlanFeatureInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            instance.save()
            if isinstance(instance, PlanPrice):
                from .services.stripe_service import StripeService

                try:
                    StripeService.sync_plan_price_to_stripe(instance)
                except Exception as e:
                    from django.contrib import messages

                    messages.error(request, f"Stripe sync failed for price: {e}")
        formset.save_m2m()


@admin.register(PlanPrice)
class PlanPriceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "plan",
        "billing_cycle",
        "price",
        "currency",
        "stripe_price_id",
        "is_active",
    ]
    list_filter = ["billing_cycle", "is_active"]
    readonly_fields = ["stripe_price_id", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .services.stripe_service import StripeService

        try:
            StripeService.sync_plan_price_to_stripe(obj)
        except Exception as e:
            from django.contrib import messages

            messages.error(request, f"Stripe sync failed: {e}")


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ["id", "plan", "feature_key", "feature_value"]
    list_filter = ["plan"]
    search_fields = ["feature_key", "plan__name"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "business",
        "plan_price",
        "status",
        "current_period_start",
        "current_period_end",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["business__name", "stripe_subscription_id"]
    readonly_fields = [
        "stripe_subscription_id",
        "stripe_customer_id",
        "current_period_start",
        "current_period_end",
        "cancelled_at",
        "created_at",
        "updated_at",
    ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "business",
        "snapshot_plan_name",
        "snapshot_billing_cycle",
        "amount",
        "currency",
        "status",
        "paid_at",
        "created_at",
    ]
    list_filter = ["status", "snapshot_billing_cycle"]
    search_fields = ["business__name", "stripe_invoice_id", "snapshot_plan_name"]
    readonly_fields = [
        "stripe_invoice_id",
        "stripe_payment_intent_id",
        "snapshot_business_name",
        "snapshot_plan_name",
        "snapshot_billing_cycle",
        "snapshot_price",
        "paid_at",
        "created_at",
    ]

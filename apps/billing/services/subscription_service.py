import logging
import stripe
from apps.billing.models import Subscription, SubscriptionStatus, PlanPrice

logger = logging.getLogger(__name__)


class SubscriptionService:

    @staticmethod
    def get_active(business):
        return (
            Subscription.objects.filter(
                business=business, status=SubscriptionStatus.ACTIVE
            )
            .select_related("plan_price__plan")
            .first()
        )

    @staticmethod
    def create_checkout(business, plan_price, success_url, cancel_url):
        from apps.billing.services.stripe_service import StripeService

        existing = SubscriptionService.get_active(business)

        if existing:
            if existing.plan_price_id == plan_price.id:
                return {
                    "error": "already_subscribed",
                    "detail": "Already subscribed to this plan. Your subscription will auto-renew.",
                    "plan_end_date": existing.current_period_end,
                }
            # Different plan — cancel current first
            try:
                if existing.stripe_subscription_id:
                    StripeService.cancel_subscription(existing.stripe_subscription_id)
                existing.cancel(reason=f"Switched to {plan_price.plan.name}")
            except stripe.error.StripeError as e:
                return {"error": "stripe_error", "detail": f"Could not cancel current plan: {e}"}

        try:
            session = StripeService.create_checkout_session(
                business, plan_price, success_url, cancel_url
            )
            return {"checkout_url": session.url, "session_id": session.id}
        except stripe.error.StripeError as e:
            return {"error": "stripe_error", "detail": f"Stripe error: {e}"}

    @staticmethod
    def switch_plan(business, new_plan_price):
        from apps.billing.services.stripe_service import StripeService

        sub = SubscriptionService.get_active(business)
        if not sub:
            return {"error": "no_subscription", "detail": "No active subscription to switch from."}
        if not sub.stripe_subscription_id:
            return {"error": "not_linked", "detail": "Subscription not linked to Stripe."}
        if sub.plan_price_id == new_plan_price.id:
            return {"error": "same_plan", "detail": "Already on this plan."}

        try:
            StripeService.switch_subscription_plan(
                sub.stripe_subscription_id, new_plan_price.stripe_price_id
            )
            sub.plan_price = new_plan_price
            sub.save(update_fields=["plan_price", "updated_at"])
            return {"success": True, "subscription": sub}
        except stripe.error.StripeError as e:
            return {"error": "stripe_error", "detail": f"Stripe error: {e}"}

    @staticmethod
    def cancel(business, reason=""):
        from apps.billing.services.stripe_service import StripeService

        sub = (
            Subscription.objects.filter(
                business=business, status=SubscriptionStatus.ACTIVE
            )
            .only("id", "stripe_subscription_id", "status", "cancelled_at", "cancel_reason", "updated_at")
            .first()
        )
        if not sub:
            return {"error": "no_subscription", "detail": "No active subscription to cancel."}

        try:
            if sub.stripe_subscription_id:
                StripeService.cancel_subscription(sub.stripe_subscription_id)
        except stripe.error.StripeError as e:
            return {"error": "stripe_error", "detail": f"Stripe error: {e}"}

        sub.cancel(reason=reason)
        return {"success": True}

    @staticmethod
    def resolve_payment_success(session_id, user):
        from apps.billing.services.stripe_service import StripeService
        from apps.billing.models import Invoice

        invoice_obj = None
        stripe_invoice_url = None

        if not (session_id and session_id.startswith("cs_")):
            return invoice_obj, stripe_invoice_url

        try:
            session = stripe.checkout.Session.retrieve(
                session_id, expand=["subscription", "invoice"]
            )
            _get = StripeService._stripe_get

            stripe_sub = _get(session, "subscription")
            if stripe_sub:
                if isinstance(stripe_sub, str):
                    stripe_sub = stripe.Subscription.retrieve(stripe_sub)
                StripeService.handle_subscription_created_or_updated(stripe_sub)

            stripe_invoice = _get(session, "invoice")
            if stripe_invoice:
                if isinstance(stripe_invoice, str):
                    stripe_invoice = stripe.Invoice.retrieve(stripe_invoice)
                StripeService.handle_invoice_paid(stripe_invoice)

                invoice_obj = Invoice.objects.filter(
                    stripe_invoice_id=_get(stripe_invoice, "id")
                ).first()
                if not invoice_obj:
                    stripe_invoice_url = _get(stripe_invoice, "hosted_invoice_url")

            if not invoice_obj and user.is_authenticated and hasattr(user, "business"):
                invoice_obj = (
                    Invoice.objects.filter(business=user.business)
                    .order_by("-created_at")
                    .first()
                )
        except Exception as e:
            logger.error("resolve_payment_success error: %s", e, exc_info=True)

        return invoice_obj, stripe_invoice_url

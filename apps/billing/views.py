import stripe
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Plan, PlanPrice, PlanFeature, Subscription, Invoice, SubscriptionStatus
from .serializers import (
    PlanListSerializer,
    PlanWriteSerializer,
    PlanPriceWriteSerializer,
    PlanFeatureSerializer,
    SubscriptionSerializer,
    SubscribeSerializer,
    CancelSubscriptionSerializer,
    SwitchPlanSerializer,
    InvoiceSerializer,
)
from .services.stripe_service import StripeService
from apps.system_admin.permissions import IsSystemAdmin
from drf_yasg.utils import swagger_auto_schema
from . import schemas


class IsBusinessAdmin(BasePermission):
    """Only authenticated users that belong to a business."""

    message = "Business admin access required."

    def has_permission(self, request, view):
        if not (
            request.user and request.user.is_authenticated and request.user.is_verified
        ):
            return False
        if not hasattr(request.user, "_is_business_admin"):
            request.user._is_business_admin = request.user.user_roles.filter(
                role__name="business_admin"
            ).exists()
        return request.user._is_business_admin


class PlanListView(generics.ListAPIView):
    """
    GET /api/billing/plans/
    Public — list all active plans with prices & features.
    """

    @swagger_auto_schema(**schemas.plan_list_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    serializer_class = PlanListSerializer
    permission_classes = [AllowAny]
    queryset = Plan.objects.filter(is_active=True).prefetch_related(
        "prices", "features"
    )


class PlanDetailView(generics.RetrieveAPIView):
    """
    GET /api/billing/plans/{id}/
    Public — single plan detail.
    """

    @swagger_auto_schema(
        tags=[schemas.BILLING_PUBLIC_TAG], operation_summary="Get Plan Detail"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    serializer_class = PlanListSerializer
    permission_classes = [AllowAny]
    queryset = Plan.objects.filter(is_active=True).prefetch_related(
        "prices", "features"
    )


# ─── System Admin: Plan CRUD (Separate views, no ViewSet) ────────────────────

class AdminPlanCreateView(generics.CreateAPIView):
    """POST /api/billing/admin/plans/ — Create a new plan."""

    serializer_class = PlanWriteSerializer
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.admin_plan_create_schema)
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class AdminPlanUpdateView(generics.UpdateAPIView):
    """PUT/PATCH /api/billing/admin/plans/<id>/ — Update a plan."""

    queryset = Plan.objects.all().prefetch_related("prices", "features")
    serializer_class = PlanWriteSerializer
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.admin_plan_update_schema)
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(**schemas.admin_plan_update_schema)
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class AdminPlanDeleteView(generics.DestroyAPIView):
    """DELETE /api/billing/admin/plans/<id>/ — Delete a plan."""

    queryset = Plan.objects.all()
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.admin_plan_delete_schema)
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class SubscribeView(APIView):
    """
    POST /api/billing/subscribe/
    Business admin initiates a Stripe Checkout Session.
    Returns { checkout_url } to redirect the user.
    """

    permission_classes = [IsBusinessAdmin]

    @swagger_auto_schema(**schemas.subscribe_schema)
    def post(self, request):
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_price = PlanPrice.objects.get(
            id=serializer.validated_data["plan_price_id"]
        )
        business = request.user.business

        # Check if already subscribed to same plan
        existing_active = Subscription.objects.filter(
            business=business,
            plan_price=plan_price,
            status=SubscriptionStatus.ACTIVE
        ).exists()
        if existing_active:
            return Response(
                {"detail": "Already subscribed to this plan. Your subscription will auto-renew."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build success URL pointing to our Django view
        from django.urls import reverse

        base_url = request.build_absolute_uri("/")[:-1]
        success_url = (
            base_url
            + reverse("billing-payment-success")
            + "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = serializer.validated_data["cancel_url"]

        try:
            session = StripeService.create_checkout_session(
                business, plan_price, success_url, cancel_url
            )
        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"checkout_url": session.url, "session_id": session.id},
            status=status.HTTP_200_OK,
        )


# ─── Success & Invoice Views (HTML) ───────────────────────────────────────────


class PaymentSuccessView(APIView):
    """
    Renders the beautiful success page after payment.
    URL: /api/billing/success/
    """

    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.GET.get("session_id")
        invoice_obj = None

        if session_id:
            try:
                # 1. Try to find the local invoice first
                # Check if we have an invoice linked to a subscription that has this business
                if request.user.is_authenticated and hasattr(request.user, "business"):
                    invoice_obj = (
                        Invoice.objects.filter(business=request.user.business)
                        .order_by("-created_at")
                        .first()
                    )

                # 2. If local invoice not found (webhook might be slow),
                # fetch the Stripe Invoice ID from the session directly
                if not invoice_obj and session_id.startswith("cs_"):
                    session = stripe.checkout.Session.retrieve(
                        session_id, expand=["subscription", "invoice"]
                    )

                    # SAFETY NET: If subscription hasn't been created yet, do it now
                    stripe_sub = getattr(session, "subscription", None)
                    if stripe_sub:
                        # If it's just an ID, retrieve the full object
                        if isinstance(stripe_sub, str):
                            stripe_sub = stripe.Subscription.retrieve(stripe_sub)
                        StripeService.handle_subscription_created_or_updated(stripe_sub)

                    stripe_invoice = getattr(session, "invoice", None)
                    if stripe_invoice:
                        # If it's just an ID, retrieve the full object
                        if isinstance(stripe_invoice, str):
                            stripe_invoice = stripe.Invoice.retrieve(stripe_invoice)
                        StripeService.handle_invoice_paid(stripe_invoice)

                    # Try to find the local invoice again after manual sync
                    if stripe_invoice:
                        invoice_obj = Invoice.objects.filter(
                            stripe_invoice_id=getattr(stripe_invoice, "id", None)
                        ).first()

                    # If STILL not found locally, show the hosted URL as fallback
                    if not invoice_obj and stripe_invoice:
                        return render(
                            request,
                            "billing/success.html",
                            {
                                "session_id": session_id,
                                "stripe_invoice_url": stripe_invoice.hosted_invoice_url,
                                "is_processing": True,
                            },
                        )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in success view: {e}")

        return render(
            request,
            "billing/success.html",
            {
                "session_id": session_id,
                "invoice_id": invoice_obj.id if invoice_obj else None,
            },
        )


class InvoiceDownloadView(APIView):
    """
    Renders/Downloads a premium invoice.
    URL: /api/billing/invoices/<id>/download/
    """

    permission_classes = [IsBusinessAdmin]

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, business=request.user.business)
        return render(request, "billing/invoice.html", {"invoice": invoice})


class SwitchPlanView(APIView):
    """
    POST /api/billing/subscription/switch/
    Business admin switches to a different plan (mid-cycle with proration).
    """

    permission_classes = [IsBusinessAdmin]

    @swagger_auto_schema(**schemas.switch_plan_schema)
    def post(self, request):
        serializer = SwitchPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_plan_price = PlanPrice.objects.select_related("plan").get(
            id=serializer.validated_data["plan_price_id"]
        )
        business = request.user.business

        # Get active subscription
        sub = Subscription.objects.filter(
            business=business, status=SubscriptionStatus.ACTIVE
        ).select_related("plan_price__plan").first()

        if not sub:
            return Response(
                {"detail": "No active subscription to switch from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not sub.stripe_subscription_id:
            return Response(
                {"detail": "Subscription not linked to Stripe."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Same plan? Don't allow
        if sub.plan_price_id == new_plan_price.id:
            return Response(
                {"detail": "Already on this plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Call Stripe to switch with proration
            StripeService.switch_subscription_plan(
                sub.stripe_subscription_id,
                new_plan_price.stripe_price_id
            )
            # Update local subscription
            sub.plan_price = new_plan_price
            sub.save(update_fields=["plan_price", "updated_at"])

            return Response(
                {
                    "detail": "Plan switched successfully. Changes will be reflected in your next invoice.",
                    "subscription": SubscriptionSerializer(sub).data,
                },
                status=status.HTTP_200_OK,
            )
        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class MySubscriptionView(generics.RetrieveAPIView):
    """
    GET /api/billing/subscription/
    Returns the active subscription of the logged-in business admin.
    """

    @swagger_auto_schema(**schemas.my_subscription_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    serializer_class = SubscriptionSerializer
    permission_classes = [IsBusinessAdmin]

    def get_object(self):
        sub = (
            Subscription.objects.filter(
                business=self.request.user.business, status="active"
            )
            .select_related("plan_price__plan")
            .first()
        )
        if not sub:
            from rest_framework.exceptions import NotFound

            raise NotFound("No active subscription found.")
        return sub


class CancelSubscriptionView(APIView):
    """
    POST /api/billing/subscription/cancel/
    Business admin cancels their current subscription.
    """

    permission_classes = [IsBusinessAdmin]

    @swagger_auto_schema(**schemas.cancel_sub_schema)
    def post(self, request):
        serializer = CancelSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sub = Subscription.objects.filter(
            business=request.user.business, status="active"
        ).first()
        if not sub:
            return Response(
                {"detail": "No active subscription to cancel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if sub.stripe_subscription_id:
                StripeService.cancel_subscription(sub.stripe_subscription_id)
        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        sub.cancel(reason=serializer.validated_data.get("reason", ""))
        return Response(
            {"detail": "Subscription cancelled successfully."},
            status=status.HTTP_200_OK,
        )


class MyInvoiceListView(generics.ListAPIView):
    """
    GET /api/billing/invoices/
    Returns all invoices for the logged-in business.
    """

    @swagger_auto_schema(**schemas.invoice_list_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    serializer_class = InvoiceSerializer
    permission_classes = [IsBusinessAdmin]

    def get_queryset(self):
        return Invoice.objects.filter(business=self.request.user.business)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    POST /api/billing/stripe/webhook/
    Receives Stripe webhook events. No authentication — uses signature verification.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(**schemas.stripe_webhook_schema)
    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = StripeService.construct_webhook_event(payload, sig_header)
        except stripe.error.SignatureVerificationError:
            return Response(
                {"detail": "Invalid webhook signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_type = event["type"]
        data_obj = event["data"]["object"]

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Received Stripe Webhook: {event_type}")

        if event_type == "customer.subscription.created":
            StripeService.handle_subscription_created_or_updated(data_obj)
            logger.info(f"Subscription Created: {data_obj.get('id')}")

        elif event_type == "customer.subscription.updated":
            StripeService.handle_subscription_created_or_updated(data_obj)
            logger.info(f"Subscription Updated: {data_obj.get('id')}")

        elif event_type == "customer.subscription.deleted":
            StripeService.handle_subscription_deleted(data_obj)
            logger.info(f"Subscription Deleted: {data_obj.get('id')}")

        elif event_type == "invoice.paid":
            StripeService.handle_invoice_paid(data_obj)
            logger.info(f"Invoice Paid: {data_obj.get('id')}")

        elif event_type == "invoice.payment_failed":
            StripeService.handle_invoice_payment_failed(data_obj)
            logger.info(f"Invoice Payment Failed: {data_obj.get('id')}")

        return Response({"status": "ok"}, status=status.HTTP_200_OK)

from django.urls import path
from .views import (
    # Public
    PlanListView,
    PlanDetailView,
    # System Admin (CRUD)
    AdminPlanCreateView,
    AdminPlanUpdateView,
    AdminPlanDeleteView,
    # Business Admin
    SubscribeView,
    SwitchPlanView,
    MySubscriptionView,
    CancelSubscriptionView,
    MyInvoiceListView,
    # HTML Views
    PaymentSuccessView,
    InvoiceDownloadView,
    # Stripe Webhook
    StripeWebhookView,
)

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────
    path("plans/", PlanListView.as_view(), name="billing-plan-list"),
    path("plans/<int:pk>/", PlanDetailView.as_view(), name="billing-plan-detail"),

    # ── System Admin (CRUD) ──────────────────────────────────────────────
    path("admin/plans/", AdminPlanCreateView.as_view(), name="billing-admin-plan-create"),
    path("admin/plans/<int:pk>/", AdminPlanUpdateView.as_view(), name="billing-admin-plan-update"),
    path("admin/plans/<int:pk>/delete/", AdminPlanDeleteView.as_view(), name="billing-admin-plan-delete"),

    # ── Business Admin ────────────────────────────────────────────────────
    path("subscribe/", SubscribeView.as_view(), name="billing-subscribe"),
    path("subscription/", MySubscriptionView.as_view(), name="billing-subscription"),
    path("subscription/cancel/", CancelSubscriptionView.as_view(), name="billing-subscription-cancel"),
    path("subscription/switch/", SwitchPlanView.as_view(), name="billing-subscription-switch"),
    path("invoices/", MyInvoiceListView.as_view(), name="billing-invoice-list"),

    # ── HTML Views (Success & Invoice) ────────────────────────────────────
    path("success/", PaymentSuccessView.as_view(), name="billing-payment-success"),
    path("invoices/<int:pk>/download/", InvoiceDownloadView.as_view(), name="billing-invoice-download"),

    # ── Stripe Webhook ─────────────────────────────────────────────────────
    path("stripe/webhook/", StripeWebhookView.as_view(), name="billing-stripe-webhook"),
]

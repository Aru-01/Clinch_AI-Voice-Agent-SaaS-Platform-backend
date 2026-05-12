from drf_yasg import openapi

# Tags
BILLING_PUBLIC_TAG = "Billing - Public Plans"
BILLING_ADMIN_TAG = "Billing - System Admin Management"
BILLING_BUSINESS_TAG = "Billing - Business Subscription"
BILLING_WEBHOOK_TAG = "Billing - Webhooks"

# Common Responses
error_response = openapi.Response(
    description="Error response",
    examples={
        "application/json": {"detail": "Detailed error message"}
    },
)

# ─── Public Plans ────────────────────────────────────────────────────────────

plan_list_schema = {
    "operation_summary": "List Active Plans",
    "operation_description": "Retrieves a list of all active subscription plans with their prices and features. System admins see all plans including inactive.",
    "tags": [BILLING_PUBLIC_TAG],
    "responses": {
        200: openapi.Response(
            description="List of active plans",
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "name": "Starter",
                        "description": "Perfect for small teams",
                        "is_active": True,
                        "prices": [
                            {
                                "id": 1,
                                "billing_cycle": "monthly",
                                "price": "29.00",
                                "currency": "usd",
                                "stripe_price_id": "price_1O0afE...",
                                "is_active": True
                            },
                            {
                                "id": 2,
                                "billing_cycle": "yearly",
                                "price": "290.00",
                                "currency": "usd",
                                "stripe_price_id": "price_1O0afF...",
                                "is_active": True
                            }
                        ],
                        "features": [
                            {"id": 1, "feature_key": "max_calls_per_month", "feature_value": "500"},
                            {"id": 2, "feature_key": "crm_integration", "feature_value": "true"}
                        ]
                    }
                ]
            },
        ),
    },
}

plan_detail_schema = {
    "operation_summary": "Get Plan Detail",
    "operation_description": "Retrieves details for a single subscription plan.",
    "tags": [BILLING_PUBLIC_TAG],
    "responses": {
        200: openapi.Response(
            description="Plan detail",
            examples={
                "application/json": {
                    "id": 1,
                    "name": "Starter",
                    "description": "Perfect for small teams",
                    "is_active": True,
                    "prices": [
                        {
                            "id": 1,
                            "billing_cycle": "monthly",
                            "price": "29.00",
                            "currency": "usd",
                            "stripe_price_id": "price_1O0afE...",
                            "is_active": True
                        }
                    ],
                    "features": [
                        {"id": 1, "feature_key": "max_calls_per_month", "feature_value": "500"}
                    ]
                }
            },
        ),
        404: error_response,
    },
}

# ─── System Admin ────────────────────────────────────────────────────────────

admin_plan_create_schema = {
    "operation_summary": "Create New Plan",
    "operation_description": "Creates a new subscription plan and syncs prices to Stripe (System Admin only).",
    "tags": [BILLING_ADMIN_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["name"],
        properties={
            "name": openapi.Schema(type=openapi.TYPE_STRING, example="Professional"),
            "description": openapi.Schema(type=openapi.TYPE_STRING, example="For growing teams"),
            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
            "prices": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "billing_cycle": openapi.Schema(type=openapi.TYPE_STRING, example="monthly"),
                        "price": openapi.Schema(type=openapi.TYPE_STRING, example="99.00"),
                        "currency": openapi.Schema(type=openapi.TYPE_STRING, example="usd"),
                    }
                ),
            ),
            "features": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "feature_key": openapi.Schema(type=openapi.TYPE_STRING, example="max_calls_per_month"),
                        "feature_value": openapi.Schema(type=openapi.TYPE_STRING, example="5000"),
                    }
                ),
            ),
        },
    ),
    "responses": {
        201: openapi.Response(description="Plan created and synced to Stripe"),
        400: error_response,
        403: error_response,
    },
}

admin_plan_update_schema = {
    "operation_summary": "Update Plan",
    "operation_description": "Updates a plan (name changes sync to Stripe product). System Admin only.",
    "tags": [BILLING_ADMIN_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "name": openapi.Schema(type=openapi.TYPE_STRING, example="Professional Plus"),
            "description": openapi.Schema(type=openapi.TYPE_STRING, example="For enterprise teams"),
            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
        },
    ),
    "responses": {
        200: openapi.Response(description="Plan updated"),
        400: error_response,
        403: error_response,
        404: error_response,
    },
}

admin_plan_delete_schema = {
    "operation_summary": "Delete Plan",
    "operation_description": "Deletes a plan from the system. System Admin only.",
    "tags": [BILLING_ADMIN_TAG],
    "responses": {
        204: openapi.Response(description="Plan deleted"),
        403: error_response,
        404: error_response,
    },
}

# ─── Business Admin ──────────────────────────────────────────────────────────

subscribe_schema = {
    "operation_summary": "Initiate Subscription",
    "operation_description": "Creates a Stripe Checkout Session for the selected plan price. Returns checkout URL to redirect user for payment.",
    "tags": [BILLING_BUSINESS_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["plan_price_id"],
        properties={
            "plan_price_id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1, description="ID of the PlanPrice to subscribe to"),
            "success_url": openapi.Schema(type=openapi.TYPE_STRING, format="url", example="https://example.com/dashboard/billing?success=true"),
            "cancel_url": openapi.Schema(type=openapi.TYPE_STRING, format="url", example="https://example.com/dashboard/billing?cancelled=true"),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Checkout session created",
            examples={
                "application/json": {
                    "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
                    "session_id": "cs_test_..."
                }
            },
        ),
        400: openapi.Response(description="Invalid plan or already subscribed", examples={"application/json": {"detail": "Already subscribed to this plan"}}),
        403: error_response,
    },
}

my_subscription_schema = {
    "operation_summary": "Get Active Subscription",
    "operation_description": "Retrieves the current active subscription for the logged-in business.",
    "tags": [BILLING_BUSINESS_TAG],
    "responses": {
        200: openapi.Response(
            description="Active subscription details",
            examples={
                "application/json": {
                    "id": 1,
                    "plan_name": "Professional",
                    "billing_cycle": "monthly",
                    "price": "99.00",
                    "status": "active",
                    "current_period_start": "2026-05-12T10:00:00Z",
                    "current_period_end": "2026-06-12T10:00:00Z",
                    "cancelled_at": None,
                    "cancel_reason": "",
                    "created_at": "2026-05-12T10:00:00Z"
                }
            },
        ),
        404: openapi.Response(description="No active subscription"),
    },
}

switch_plan_schema = {
    "operation_summary": "Switch Plan",
    "operation_description": "Switches active subscription to a different plan with Stripe proration (immediate change).",
    "tags": [BILLING_BUSINESS_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["plan_price_id"],
        properties={
            "plan_price_id": openapi.Schema(type=openapi.TYPE_INTEGER, example=3, description="ID of the new PlanPrice"),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Plan switched successfully",
            examples={
                "application/json": {
                    "detail": "Plan switched successfully. Changes will be reflected in your next invoice.",
                    "subscription": {
                        "id": 1,
                        "plan_name": "Enterprise",
                        "billing_cycle": "monthly",
                        "price": "299.00",
                        "status": "active",
                        "current_period_end": "2026-06-12T10:00:00Z",
                    }
                }
            },
        ),
        400: openapi.Response(description="Invalid switch", examples={"application/json": {"detail": "Already on this plan"}}),
        403: error_response,
    },
}

cancel_sub_schema = {
    "operation_summary": "Cancel Subscription",
    "operation_description": "Cancels the active subscription.",
    "tags": [BILLING_BUSINESS_TAG],
    "request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "reason": openapi.Schema(type=openapi.TYPE_STRING, example="Scaling down for now", description="Optional cancellation reason"),
        },
    ),
    "responses": {
        200: openapi.Response(
            description="Subscription cancelled",
            examples={"application/json": {"detail": "Subscription cancelled successfully."}},
        ),
        400: error_response,
        403: error_response,
    },
}

invoice_list_schema = {
    "operation_summary": "List Invoices",
    "operation_description": "Retrieves all billing invoices for the business.",
    "tags": [BILLING_BUSINESS_TAG],
    "responses": {
        200: openapi.Response(
            description="List of invoices",
            examples={
                "application/json": [
                    {
                        "id": 1,
                        "stripe_invoice_id": "in_1O0afE...",
                        "amount": "99.00",
                        "currency": "usd",
                        "status": "paid",
                        "paid_at": "2026-05-12T10:00:00Z",
                        "snapshot_business_name": "Acme Corp",
                        "snapshot_plan_name": "Professional",
                        "snapshot_billing_cycle": "monthly",
                        "snapshot_price": "99.00",
                        "created_at": "2026-05-12T10:00:00Z"
                    }
                ]
            },
        ),
        403: error_response,
    },
}

invoice_download_schema = {
    "operation_summary": "Download Invoice",
    "operation_description": "Renders/downloads a PDF invoice.",
    "tags": [BILLING_BUSINESS_TAG],
    "responses": {
        200: openapi.Response(description="Invoice PDF"),
        403: error_response,
        404: error_response,
    },
}

# ─── Webhooks ────────────────────────────────────────────────────────────────

stripe_webhook_schema = {
    "operation_summary": "Stripe Webhook Receiver",
    "operation_description": "Endpoint for Stripe to send async notifications (subscriptions, invoices). No authentication required (uses signature verification).",
    "tags": [BILLING_WEBHOOK_TAG],
    "responses": {
        200: openapi.Response(description="Webhook processed"),
        400: openapi.Response(description="Invalid signature"),
    },
}

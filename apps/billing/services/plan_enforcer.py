"""
plan_enforcer.py
Checks subscription plan limits before allowing actions.
Usage: PlanEnforcer.check_call_limit(business)
"""
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone


class PlanEnforcer:
    """Enforce feature limits defined in PlanFeature."""

    @staticmethod
    def _get_active_subscription(business):
        sub = business.subscriptions.filter(status="active").select_related(
            "plan_price__plan"
        ).first()
        if not sub:
            raise PermissionDenied("No active subscription. Please subscribe to a plan.")
        return sub

    @staticmethod
    def _get_feature_value(sub, feature_key):
        feature = sub.plan_price.plan.features.filter(feature_key=feature_key).first()
        return feature.feature_value if feature else None

    @staticmethod
    def check_call_limit(business):
        sub = PlanEnforcer._get_active_subscription(business)
        val = PlanEnforcer._get_feature_value(sub, "max_calls_per_month")
        if val is None or val == "unlimited":
            return True
        max_calls = int(val)
        current_month = timezone.now().month
        current_year = timezone.now().year
        calls_this_month = business.calls.filter(
            created_at__month=current_month,
            created_at__year=current_year,
        ).count()
        if calls_this_month >= max_calls:
            raise PermissionDenied(f"Monthly call limit reached ({max_calls} calls).")
        return True

    @staticmethod
    def check_lead_limit(business):
        sub = PlanEnforcer._get_active_subscription(business)
        val = PlanEnforcer._get_feature_value(sub, "max_leads")
        if val is None or val == "unlimited":
            return True
        max_leads = int(val)
        total_leads = business.leads.count()
        if total_leads >= max_leads:
            raise PermissionDenied(f"Lead limit reached ({max_leads} leads).")
        return True

    @staticmethod
    def check_feature_enabled(business, feature_key):
        """
        For boolean features like 'call_transfer', 'crm_integration', etc.
        Raises PermissionDenied if feature_value is 'false'.
        """
        sub = PlanEnforcer._get_active_subscription(business)
        val = PlanEnforcer._get_feature_value(sub, feature_key)
        if val is None or val.lower() == "false":
            raise PermissionDenied(f"Feature '{feature_key}' is not available on your plan.")
        return True

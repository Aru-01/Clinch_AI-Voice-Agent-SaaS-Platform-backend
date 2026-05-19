from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from apps.system_admin.permissions import IsSystemAdmin
from apps.system_admin.serializers import (
    SystemAdminCreateSerializer,
    BusinessAdminListSerializer,
    BusinessAdminDetailSerializer,
)
from apps.system_admin import schemas
from apps.accounts.serializers import UserSerializer
from apps.accounts.models import OTPCode
from apps.accounts.services import utils
from apps.billing.models import Invoice, Subscription, SubscriptionStatus
from apps.billing.serializers import InvoiceSerializer, SubscriptionSerializer
from apps.system_admin.services.stats_service import StatsService

User = get_user_model()


class SystemUserListView(generics.ListAPIView):
    """
    List all system admins. Optimized with prefetch_related.
    """

    @swagger_auto_schema(**schemas.system_user_list_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    queryset = (
        User.objects.filter(user_roles__role__name="system_admin")
        .select_related("business")
        .prefetch_related("user_roles__role")
        .order_by("-created_at")
    )
    serializer_class = UserSerializer
    permission_classes = [IsSystemAdmin]


class BusinessAdminListView(generics.ListAPIView):
    """
    List all business admins with minimal data. Recent joiners first.
    Optimized to use prefetch_related for subscription data.
    """

    @swagger_auto_schema(**schemas.business_admin_list_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    queryset = (
        User.objects.filter(user_roles__role__name="business_admin")
        .select_related("business")
        .prefetch_related(
            "user_roles__role",
            "business__subscriptions__plan_price__plan",
        )
        .order_by("-created_at")
    )
    serializer_class = BusinessAdminListSerializer
    permission_classes = [IsSystemAdmin]


class SystemAdminCreateView(generics.CreateAPIView):
    """
    Create a new System Admin. Triggers OTP verification flow.
    """

    serializer_class = SystemAdminCreateSerializer
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.system_admin_create_schema)
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        OTPCode.clean_expired()
        otp = utils.generate_otp(user, OTPCode.OTPType.EMAIL_VERIFY)
        utils.send_otp_email(user, otp, OTPCode.OTPType.EMAIL_VERIFY)
        utils.update_otp_rate_limit(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "New System Admin created. A verification OTP has been sent to their email.",
            },
            status=status.HTTP_201_CREATED,
        )


class SystemAdminDeleteView(generics.DestroyAPIView):
    """
    Delete a system admin. Constraints: Cannot delete self or superusers.
    """

    queryset = User.objects.filter(user_roles__role__name="system_admin")
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.system_admin_delete_schema)
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "System Admin successfully removed."}, status=status.HTTP_200_OK
        )

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise serializers.ValidationError("You cannot remove yourself.")

        if instance.is_superuser:
            raise serializers.ValidationError(
                "You cannot remove a superuser/root admin."
            )

        instance.delete()


class SystemAdminStatsView(APIView):
    """
    Statistics and Dashboard data for System Admins.
    Uses StatsService for optimized data retrieval.
    """

    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.stats_schema)
    def get(self, request):
        stats_data = StatsService.get_dashboard_stats()
        return Response(stats_data)


class AdminAllInvoicesView(generics.ListAPIView):
    """
    GET /api/system-admin/invoices/
    System admin sees all invoices across all businesses.
    """

    serializer_class = InvoiceSerializer
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.admin_invoices_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Invoice.objects.select_related(
            "business", "subscription__plan_price__plan"
        ).order_by("-created_at")


class AdminAllSubscriptionsView(generics.ListAPIView):
    """
    GET /api/system-admin/subscriptions/
    System admin sees all subscriptions across all businesses.
    """

    serializer_class = SubscriptionSerializer
    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.admin_subscriptions_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Subscription.objects.select_related(
            "business", "plan_price__plan"
        ).order_by("-created_at")


class BusinessAdminDetailView(APIView):
    """
    GET /api/system-admin/business-admins/{user_id}/
    System admin views detailed data for a specific business admin.
    Includes full business profile, stats, and metrics.
    """

    permission_classes = [IsSystemAdmin]

    @swagger_auto_schema(**schemas.business_admin_detail_schema)
    def get(self, request, user_id):
        try:
            from django.db.models import Prefetch

            user = User.objects.select_related("business").prefetch_related(
                Prefetch(
                    "business__subscriptions",
                    queryset=Subscription.objects.select_related("plan_price__plan")
                )
            ).get(
                id=user_id,
                user_roles__role__name="business_admin"
            )

            if not user.business:
                return Response({
                    "success": False,
                    "error": "User has no business assigned"
                }, status=404)

            serializer = BusinessAdminDetailSerializer(user)
            return Response({
                "success": True,
                "data": serializer.data
            })
        except User.DoesNotExist:
            return Response({
                "success": False,
                "error": "Business admin not found"
            }, status=404)
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=400)

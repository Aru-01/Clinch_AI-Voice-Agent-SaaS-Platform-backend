from rest_framework import generics, status, serializers
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from apps.system_admin.permissions import IsSystemAdmin
from apps.system_admin.serializers import (
    SystemAdminCreateSerializer, BusinessAdminListSerializer
)
from apps.accounts.serializers import UserSerializer
from apps.accounts.models import OTPCode
from apps.accounts.services import utils

User = get_user_model()


class SystemUserListView(generics.ListAPIView):
    """
    List all system admins. Optimized with prefetch_related.
    """
    queryset = User.objects.filter(user_roles__role__name="system_admin").prefetch_related(
        "user_roles__role", "business"
    ).order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [IsSystemAdmin]


class BusinessAdminListView(generics.ListAPIView):
    """
    List all business admins. Recent joiners first.
    """
    queryset = User.objects.filter(user_roles__role__name="business_admin").prefetch_related(
        "user_roles__role", "business"
    ).order_by("-created_at")
    serializer_class = BusinessAdminListSerializer
    permission_classes = [IsSystemAdmin]


class SystemAdminCreateView(generics.CreateAPIView):
    """
    Create a new System Admin. Triggers OTP verification flow.
    """

    serializer_class = SystemAdminCreateSerializer
    permission_classes = [IsSystemAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send Verification OTP (similar to registration)
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

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise serializers.ValidationError("You cannot remove yourself.")

        if instance.is_superuser:
            raise serializers.ValidationError(
                "You cannot remove a superuser/root admin."
            )

        instance.delete()

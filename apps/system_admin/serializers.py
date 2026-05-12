from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, UserRole
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class SystemAdminCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            phone=validated_data["phone"],
        )
        user.is_staff = True
        user.is_verified = False
        user.save()

        role, _ = Role.objects.get_or_create(name="system_admin")
        UserRole.objects.create(user=user, role=role)

        return user


class BusinessAdminListSerializer(serializers.ModelSerializer):
    join_date = serializers.DateTimeField(source="created_at", format="%Y-%m-%d")
    plan = serializers.SerializerMethodField()
    plan_start_date = serializers.SerializerMethodField()
    plan_end_date = serializers.SerializerMethodField()
    total_leads = serializers.IntegerField(default=0, read_only=True)
    total_call = serializers.IntegerField(default=0, read_only=True)
    conversation_rate = serializers.FloatField(default=0.0, read_only=True)
    book_appointment = serializers.IntegerField(default=0, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "profile_image",
            "join_date",
            "plan",
            "plan_start_date",
            "plan_end_date",
            "total_leads",
            "total_call",
            "conversation_rate",
            "book_appointment",
        ]

    def _active_sub(self, obj):
        if not obj.business:
            return None
        from apps.billing.models import Subscription, SubscriptionStatus
        return (
            obj.business.subscriptions
            .filter(status=SubscriptionStatus.ACTIVE)
            .select_related("plan_price__plan")
            .first()
        )

    def get_plan(self, obj):
        sub = self._active_sub(obj)
        if sub:
            return f"{sub.plan_price.plan.name} ({sub.plan_price.billing_cycle})"
        return "Free"

    def get_plan_start_date(self, obj):
        sub = self._active_sub(obj)
        if sub and sub.current_period_start:
            return sub.current_period_start.strftime("%Y-%m-%d")
        return None

    def get_plan_end_date(self, obj):
        sub = self._active_sub(obj)
        if sub and sub.current_period_end:
            return sub.current_period_end.strftime("%Y-%m-%d")
        return None

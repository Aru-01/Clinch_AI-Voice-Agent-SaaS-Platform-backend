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

    plan = serializers.CharField(default="Free", read_only=True)
    plan_start_date = serializers.CharField(default=None, read_only=True)
    plan_end_date = serializers.CharField(default=None, read_only=True)
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

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.models import Business, Role, UserRole

User = get_user_model()


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ["id", "name", "description", "address"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "profile_image",
            "business",
            "is_verified",
        ]
        read_only_fields = ["id", "business", "is_verified"]


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)
    business_name = serializers.CharField(max_length=255)

    def create(self, validated_data):
        business = Business.objects.create(name=validated_data["business_name"])

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            phone=validated_data["phone"],
            business=business,
        )

        business.owner_id = user.id
        business.save()

        role, _ = Role.objects.get_or_create(name="business_admin")
        UserRole.objects.create(user=user, role=role)

        return user

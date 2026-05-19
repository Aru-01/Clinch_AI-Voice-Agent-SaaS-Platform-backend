from rest_framework import serializers
from apps.support.models import SupportTicket
from apps.accounts.models import CustomUser


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "name", "phone", "profile_image"]


class BusinessSupportTicketListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_number",
            "subject",
            "message",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "ticket_number",
            "subject",
            "message",
            "status",
            "notes",
            "created_at",
        ]


class SupportTicketListSerializer(serializers.ModelSerializer):
    creator = UserLiteSerializer(read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_number",
            "business",
            "business_name",
            "creator",
            "subject",
            "message",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ticket_number",
            "business",
            "business_name",
            "creator",
            "subject",
            "message",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]


class SupportTicketSerializer(serializers.ModelSerializer):
    creator = UserLiteSerializer(read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_number",
            "business",
            "business_name",
            "creator",
            "subject",
            "message",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ticket_number",
            "business",
            "business_name",
            "creator",
            "created_at",
            "updated_at",
        ]

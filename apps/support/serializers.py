from rest_framework import serializers
from apps.support.models import SupportTicket, TicketMessage
from apps.accounts.models import CustomUser


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "name", "phone", "profile_image"]


class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = ["id", "message"]
        read_only_fields = ["id"]


class SupportTicketSerializer(serializers.ModelSerializer):
    creator = UserLiteSerializer(read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    message = serializers.CharField(
        write_only=True, required=False, help_text="Initial message for the ticket"
    )

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_number",
            "business",
            "business_name",
            "creator",
            "subject",
            "status",
            "notes",
            "message",
            "messages",
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

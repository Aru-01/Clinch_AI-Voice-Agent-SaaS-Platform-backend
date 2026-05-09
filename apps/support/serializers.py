from rest_framework import serializers
from .models import SupportTicket, TicketMessage, TicketNote
from apps.accounts.models import CustomUser


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "name", "phone", "profile_image"]


class TicketMessageSerializer(serializers.ModelSerializer):
    sender = UserLiteSerializer(read_only=True)

    class Meta:
        model = TicketMessage
        fields = ["id", "ticket", "sender", "message", "created_at"]
        read_only_fields = ["id", "ticket", "sender", "created_at"]


class TicketNoteSerializer(serializers.ModelSerializer):
    sender = UserLiteSerializer(read_only=True)

    class Meta:
        model = TicketNote
        fields = ["id", "ticket", "sender", "note", "created_at"]
        read_only_fields = ["id", "ticket", "sender", "created_at"]


class SupportTicketSerializer(serializers.ModelSerializer):
    creator = UserLiteSerializer(read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    notes = serializers.SerializerMethodField()
    message = serializers.CharField(
        write_only=True, required=True, help_text="Initial message for the ticket"
    )

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "business",
            "business_name",
            "creator",
            "subject",
            "status",
            "message",
            "messages",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "business",
            "business_name",
            "creator",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_notes(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            if request.user.business_id is None:
                notes = obj.notes.all()
                return TicketNoteSerializer(notes, many=True).data
        return []

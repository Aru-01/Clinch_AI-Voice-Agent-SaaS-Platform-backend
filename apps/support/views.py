from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import SupportTicket, TicketMessage, TicketNote
from .serializers import (
    SupportTicketSerializer,
    TicketMessageSerializer,
    TicketNoteSerializer,
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Support Tickets.
    - Business admins can create tickets and view their own tickets.
    - System admins can view all tickets, patch status, and add notes.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SupportTicketSerializer
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["subject"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return SupportTicket.objects.none()

        if user.business_id is None:
            # System admin
            queryset = SupportTicket.objects.all().select_related("business", "creator")
        else:
            # Business admin
            queryset = SupportTicket.objects.filter(
                business_id=user.business_id
            ).select_related("business", "creator")

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.business_id is None:
            raise serializers.ValidationError({"detail": "System admins cannot create tickets."})
        
        message_text = serializer.validated_data.pop("message", None)
        ticket = serializer.save(creator=user, business_id=user.business_id)
        
        if message_text:
            TicketMessage.objects.create(
                ticket=ticket,
                sender=user,
                message=message_text
            )

    def update(self, request, *args, **kwargs):
        # Business admins cannot update tickets. System admins can update status.
        user = request.user
        if user.business_id is not None:
            return Response(
                {"detail": "Business admins cannot update tickets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # Only allow updating 'status'
        allowed_fields = {"status"}
        update_fields = set(request.data.keys())
        if not update_fields.issubset(allowed_fields):
            return Response(
                {"detail": "You can only update the status field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Tickets cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["message"],
            properties={
                "message": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={201: TicketMessageSerializer()},
    )
    @action(detail=True, methods=["post"], url_path="messages")
    def add_message(self, request, pk=None):
        """Add a message to a ticket (visible to both System and Business admins)."""
        ticket = self.get_object()
        message_text = request.data.get("message")
        if not message_text:
            return Response(
                {"detail": "Message text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = TicketMessage.objects.create(
            ticket=ticket, sender=request.user, message=message_text
        )
        return Response(
            TicketMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        method="post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["note"],
            properties={
                "note": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={201: TicketNoteSerializer()},
    )
    @action(detail=True, methods=["post"], url_path="notes")
    def add_note(self, request, pk=None):
        """Add an internal note to a ticket (System Admins only)."""
        user = request.user
        if user.business_id is not None:
            return Response(
                {"detail": "Only system admins can add internal notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ticket = self.get_object()
        note_text = request.data.get("note")
        if not note_text:
            return Response(
                {"detail": "Note text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        note = TicketNote.objects.create(ticket=ticket, sender=user, note=note_text)
        return Response(TicketNoteSerializer(note).data, status=status.HTTP_201_CREATED)

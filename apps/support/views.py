from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.support.models import SupportTicket, TicketMessage
from apps.support.serializers import (
    SupportTicketSerializer,
    TicketMessageSerializer,
)
from apps.support import schemas


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Support Tickets.
    - Business admins can create tickets and view their own tickets.
    - System admins can view all tickets, patch status, and update notes.
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

    @swagger_auto_schema(**schemas.ticket_list_schema)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(**schemas.ticket_create_schema)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(**schemas.ticket_retrieve_schema)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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

        queryset = queryset.prefetch_related("messages__sender")

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.business_id is None:
            raise serializers.ValidationError(
                {"detail": "System admins cannot create tickets."}
            )

        message_text = serializer.validated_data.pop("message", None)
        ticket = serializer.save(creator=user, business_id=user.business_id)

        if message_text:
            TicketMessage.objects.create(
                ticket=ticket, sender=user, message=message_text
            )

    @swagger_auto_schema(**schemas.ticket_update_schema)
    def update(self, request, *args, **kwargs):
        user = request.user
        if user.business_id is not None:
            return Response(
                {"detail": "Business admins cannot update tickets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        data = {}
        if "status" in request.data:
            data["status"] = request.data["status"]

        notes_input = request.data.get("notes") or request.data.get("note")
        if notes_input is not None:
            if isinstance(notes_input, list):
                data["notes"] = "\n".join(str(n) for n in notes_input if n)
            else:
                data["notes"] = str(notes_input)

        if not data:
            return Response(
                {"detail": "You must provide either status or notes to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Tickets cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @swagger_auto_schema(**schemas.add_message_schema)
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

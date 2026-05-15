from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from apps.call_logs.models import CallLog
from apps.call_logs.serializers import CallLogListSerializer, CallLogDetailSerializer
from apps.call_logs.pagination import CallLogPagination
from apps.call_logs import schemas


class CallLogListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CallLogPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    # Filtering fields
    filterset_fields = {
        "location": ["exact", "icontains"],
        "status": ["exact", "icontains"],
        "call_date_time": ["exact", "date", "gte", "lte"],  # Support date filtering
    }

    # Searching fields
    search_fields = ["name", "phone_number", "location", "status"]

    # Default ordering
    ordering_fields = ["call_date_time", "duration"]
    ordering = ["-call_date_time"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CallLogDetailSerializer
        return CallLogListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.business:
            return CallLog.objects.select_related("business").filter(
                business=user.business
            )
        return CallLog.objects.none()

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)

    @swagger_auto_schema(**schemas.call_log_list_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(**schemas.call_log_create_schema)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CallLogDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = CallLogDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.business:
            return CallLog.objects.select_related("business").filter(
                business=user.business
            )
        return CallLog.objects.none()

    @swagger_auto_schema(**schemas.call_log_detail_schema)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(**schemas.call_log_delete_schema)
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

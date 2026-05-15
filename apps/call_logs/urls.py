from django.urls import path
from apps.call_logs.views import CallLogListCreateView, CallLogDetailView

urlpatterns = [
    path("", CallLogListCreateView.as_view(), name="call-log-list"),
    path("<int:pk>/", CallLogDetailView.as_view(), name="call-log-detail"),
]

from rest_framework import serializers
from .models import CallLog

class CallLogListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = ['id', 'name', 'phone_number', 'location', 'duration', 'status', 'call_date_time']

class CallLogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = '__all__'

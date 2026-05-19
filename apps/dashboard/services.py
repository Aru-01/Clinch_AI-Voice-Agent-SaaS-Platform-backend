from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from apps.crm_integration.models import SyncedLead
from apps.call_logs.models import CallLog
from apps.bookings.models import Booking
from apps.notifications.models import Notification


def get_date_range_stats(model, business=None, date_field='created_at', start_date=None, end_date=None):
    """Get count of records within a date range"""
    filters = Q()
    if business:
        filters &= Q(business=business)
    if start_date:
        filters &= Q(**{f"{date_field}__gte": start_date})
    if end_date:
        filters &= Q(**{f"{date_field}__lte": end_date})
    return model.objects.filter(filters).count()


def get_month_over_month_percentage(current, previous):
    """Calculate percentage change from previous to current"""
    if previous == 0:
        return 0 if current == 0 else 100
    return round(((current - previous) / previous) * 100, 1)


def get_leads_stats(business=None):
    """Get total leads and month-over-month change"""
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_end = current_month_start - timedelta(seconds=1)
    previous_month_start = previous_month_end.replace(day=1)

    current_count = get_date_range_stats(
        SyncedLead, business, 'created_at', current_month_start, now
    )
    previous_count = get_date_range_stats(
        SyncedLead, business, 'created_at', previous_month_start, previous_month_end
    )

    percentage = get_month_over_month_percentage(current_count, previous_count)

    return {
        "total": current_count,
        "percentage_change": percentage,
        "trend": "up" if percentage >= 0 else "down"
    }


def get_calls_stats(business=None):
    """Get total calls and month-over-month change"""
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_end = current_month_start - timedelta(seconds=1)
    previous_month_start = previous_month_end.replace(day=1)

    current_count = get_date_range_stats(
        CallLog, business, 'call_date_time', current_month_start, now
    )
    previous_count = get_date_range_stats(
        CallLog, business, 'call_date_time', previous_month_start, previous_month_end
    )

    percentage = get_month_over_month_percentage(current_count, previous_count)

    return {
        "total": current_count,
        "percentage_change": percentage,
        "trend": "up" if percentage >= 0 else "down"
    }


def get_conversion_rate(business=None):
    """Calculate conversion rate: (bookings / leads) * 100"""
    leads_qs = SyncedLead.objects.all()
    bookings_qs = Booking.objects.all()

    if business:
        leads_qs = leads_qs.filter(business=business)
        bookings_qs = bookings_qs.filter(business=business)

    total_leads = leads_qs.count()
    total_bookings = bookings_qs.count()

    # Current month
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_end = current_month_start - timedelta(seconds=1)
    previous_month_start = previous_month_end.replace(day=1)

    current_leads = get_date_range_stats(SyncedLead, business, 'created_at', current_month_start, now)
    current_bookings = get_date_range_stats(Booking, business, 'created_at', current_month_start, now)
    previous_leads = get_date_range_stats(SyncedLead, business, 'created_at', previous_month_start, previous_month_end)
    previous_bookings = get_date_range_stats(Booking, business, 'created_at', previous_month_start, previous_month_end)

    current_rate = (current_bookings / current_leads * 100) if current_leads > 0 else 0
    previous_rate = (previous_bookings / previous_leads * 100) if previous_leads > 0 else 0

    percentage = get_month_over_month_percentage(current_rate, previous_rate)

    return {
        "rate": round(current_rate, 1),
        "percentage_change": percentage,
        "trend": "up" if percentage >= 0 else "down"
    }


def get_appointments_stats(business=None):
    """Get total appointments/bookings and month-over-month change"""
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_end = current_month_start - timedelta(seconds=1)
    previous_month_start = previous_month_end.replace(day=1)

    current_count = get_date_range_stats(
        Booking, business, 'created_at', current_month_start, now
    )
    previous_count = get_date_range_stats(
        Booking, business, 'created_at', previous_month_start, previous_month_end
    )

    percentage = get_month_over_month_percentage(current_count, previous_count)

    return {
        "total": current_count,
        "percentage_change": percentage,
        "trend": "up" if percentage >= 0 else "down"
    }


def get_call_logs_graph(business=None):
    """Get call logs grouped by day for this week and last week"""
    now = timezone.now()

    # This week (Monday to now)
    days_since_monday = now.weekday()
    this_week_start = now - timedelta(days=days_since_monday, hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)

    # Last week (Monday to Sunday)
    last_week_end = this_week_start - timedelta(seconds=1)
    last_week_start = last_week_end - timedelta(days=6)

    this_week_data = []
    last_week_data = []

    # Get this week data
    for i in range(days_since_monday + 1):
        day_start = this_week_start + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_name = day_start.strftime("%a")  # Mon, Tue, etc.

        qs = CallLog.objects.filter(call_date_time__gte=day_start, call_date_time__lt=day_end)
        if business:
            qs = qs.filter(business=business)

        count = qs.count()
        this_week_data.append({
            "day": day_name,
            "date": day_start.date().isoformat(),
            "calls": count
        })

    # Get last week data
    for i in range(7):
        day_start = last_week_start + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_name = day_start.strftime("%a")

        qs = CallLog.objects.filter(call_date_time__gte=day_start, call_date_time__lt=day_end)
        if business:
            qs = qs.filter(business=business)

        count = qs.count()
        last_week_data.append({
            "day": day_name,
            "date": day_start.date().isoformat(),
            "calls": count
        })

    return {
        "this_week": this_week_data,
        "last_week": last_week_data
    }


def get_recent_calls(business=None, limit=6):
    """Get recent call logs"""
    qs = CallLog.objects.all()
    if business:
        qs = qs.filter(business=business)

    calls = qs[:limit]

    return [
        {
            "id": str(call.id) if hasattr(call, 'id') else None,
            "name": call.name,
            "phone": call.phone_number,
            "status": call.status,
            "duration": call.duration,
            "date": call.call_date_time.isoformat()
        }
        for call in calls
    ]


def get_recent_notifications(user=None, limit=6):
    """Get recent notifications"""
    qs = Notification.objects.all()
    if user:
        qs = qs.filter(recipient=user)

    notifications = qs[:limit]

    return [
        {
            "id": str(notif.id),
            "type": notif.notification_type,
            "title": notif.title,
            "message": notif.message,
            "is_read": notif.is_read,
            "created_at": notif.created_at.isoformat()
        }
        for notif in notifications
    ]

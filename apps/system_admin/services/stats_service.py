from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.system_admin.serializers import BusinessAdminListSerializer

User = get_user_model()


class StatsService:
    @staticmethod
    def get_dashboard_stats():
        now = timezone.now()
        first_day_this_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        last_month_end = first_day_this_month - timedelta(seconds=1)
        first_day_last_month = last_month_end.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        business_admins = User.objects.filter(user_roles__role__name="business_admin")

        total_biz = business_admins.count()
        this_month_biz = business_admins.filter(
            created_at__gte=first_day_this_month
        ).count()
        last_month_biz = business_admins.filter(
            created_at__gte=first_day_last_month, created_at__lte=last_month_end
        ).count()

        total_purchased = business_admins.filter(business__isnull=False).count()
        this_month_purchased = business_admins.filter(
            business__isnull=False, created_at__gte=first_day_this_month
        ).count()
        last_month_purchased = business_admins.filter(
            business__isnull=False,
            created_at__gte=first_day_last_month,
            created_at__lte=last_month_end,
        ).count()

        graph_data = StatsService._get_comparison_graph_data(
            first_day_this_month, now, first_day_last_month, last_month_end
        )

        recent_users = business_admins.prefetch_related(
            "user_roles__role", "business"
        ).order_by("-created_at")[:6]

        return {
            "overview": {
                "total_business_admin": {
                    "count": total_biz,
                    "growth_percentage": StatsService._calculate_growth(
                        this_month_biz, last_month_biz
                    ),
                },
                "total_plan_purchase_user": {
                    "count": total_purchased,
                    "growth_percentage": StatsService._calculate_growth(
                        this_month_purchased, last_month_purchased
                    ),
                },
            },
            "graph": graph_data,
            "recent_users": BusinessAdminListSerializer(recent_users, many=True).data,
        }

    @staticmethod
    def _calculate_growth(current, previous):
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    @staticmethod
    def _get_comparison_graph_data(this_start, this_end, last_start, last_end):
        this_month_counts = StatsService._get_daily_counts(this_start, this_end)
        last_month_counts = StatsService._get_daily_counts(last_start, last_end)

        return {"this_month": this_month_counts, "prev_month": last_month_counts}

    @staticmethod
    def _get_daily_counts(start_date, end_date):
        counts = (
            User.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
            .extra(select={"day": "EXTRACT(DAY FROM created_at)"})
            .values("day")
            .annotate(count=Count("id"))
        )

        result = {int(item["day"]): item["count"] for item in counts}

        max_day = end_date.day
        return {day: result.get(day, 0) for day in range(1, max_day + 1)}

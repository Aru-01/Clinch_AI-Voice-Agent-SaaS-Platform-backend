from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncDay
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

        agg = User.objects.filter(user_roles__role__name="business_admin").aggregate(
            total_biz=Count("id"),
            this_month_biz=Count(
                "id",
                filter=Q(created_at__gte=first_day_this_month),
            ),
            last_month_biz=Count(
                "id",
                filter=Q(
                    created_at__gte=first_day_last_month, created_at__lte=last_month_end
                ),
            ),
            total_purchased=Count(
                "id",
                filter=Q(business__subscriptions__status="active"),
                distinct=True,
            ),
            this_month_purchased=Count(
                "id",
                filter=Q(
                    business__subscriptions__status="active",
                    created_at__gte=first_day_this_month,
                ),
                distinct=True,
            ),
            last_month_purchased=Count(
                "id",
                filter=Q(
                    business__subscriptions__status="active",
                    created_at__gte=first_day_last_month,
                    created_at__lte=last_month_end,
                ),
                distinct=True,
            ),
        )

        graph_data = StatsService._get_comparison_graph_data(
            first_day_this_month, now, first_day_last_month, last_month_end
        )

        recent_users = (
            User.objects.filter(user_roles__role__name="business_admin")
            .select_related("business")
            .prefetch_related(
                "user_roles__role",
                "business__subscriptions__plan_price__plan",
            )
            .order_by("-created_at")[:6]
        )

        return {
            "overview": {
                "total_business_admin": {
                    "count": agg["total_biz"],
                    "growth_percentage": StatsService._calculate_growth(
                        agg["this_month_biz"], agg["last_month_biz"]
                    ),
                },
                "total_plan_purchase_user": {
                    "count": agg["total_purchased"],
                    "growth_percentage": StatsService._calculate_growth(
                        agg["this_month_purchased"], agg["last_month_purchased"]
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
        rows = (
            User.objects.filter(
                Q(created_at__gte=this_start, created_at__lte=this_end)
                | Q(created_at__gte=last_start, created_at__lte=last_end)
            )
            .annotate(day=TruncDay("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )

        this_map, last_map = {}, {}
        for r in rows:
            d = r["day"]
            if this_start <= d <= this_end:
                this_map[d.day] = r["count"]
            elif last_start <= d <= last_end:
                last_map[d.day] = r["count"]

        return {
            "this_month": {
                day: this_map.get(day, 0) for day in range(1, this_end.day + 1)
            },
            "prev_month": {
                day: last_map.get(day, 0) for day in range(1, last_end.day + 1)
            },
        }

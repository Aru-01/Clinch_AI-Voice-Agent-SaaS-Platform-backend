from drf_yasg import openapi

TAG = "Dashboard"


business_admin_dashboard_schema = dict(
    operation_summary="Business Admin Dashboard",
    operation_description="Get business-specific statistics for business admins",
    tags=[TAG],
    responses={
        200: openapi.Response(
            "Dashboard data",
            examples={
                "application/json": {
                    "success": True,
                    "stats": {
                        "total_leads": {
                            "total": 245,
                            "percentage_change": 20.2,
                            "trend": "up",
                        },
                        "total_calls": {
                            "total": 189,
                            "percentage_change": 15.5,
                            "trend": "up",
                        },
                        "conversion_rate": {
                            "rate": 12.5,
                            "percentage_change": 8.3,
                            "trend": "up",
                        },
                        "total_appointments": {
                            "total": 31,
                            "percentage_change": -5.2,
                            "trend": "down",
                        },
                    },
                    "graphs": {
                        "call_logs": {
                            "this_week": [
                                {"day": "Mon", "date": "2026-05-18", "calls": 15},
                                {"day": "Tue", "date": "2026-05-19", "calls": 22},
                            ],
                            "last_week": [
                                {"day": "Mon", "date": "2026-05-11", "calls": 18},
                                {"day": "Tue", "date": "2026-05-12", "calls": 20},
                            ],
                        }
                    },
                    "recent": {
                        "calls": [
                            {
                                "id": "call-1",
                                "name": "John Doe",
                                "phone": "+1-555-0100",
                                "status": "completed",
                                "duration": "02:30",
                                "date": "2026-05-20T10:30:00Z",
                            }
                        ],
                        "notifications": [
                            {
                                "id": "notif-1",
                                "type": "new_business_registered",
                                "title": "New Business",
                                "message": "ABC Corp registered",
                                "is_read": False,
                                "created_at": "2026-05-20T10:30:00Z",
                            }
                        ],
                    },
                }
            },
        )
    },
)

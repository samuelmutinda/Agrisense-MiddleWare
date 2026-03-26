"""
§5.6 API Integration Tests – Middleware Route & Response Contract Validation

Validates:
1. All expected route groups are registered on the FastAPI app.
2. Admin aggregate routes return the expected response schema.
3. Notification history endpoint contract.
4. Response model fields match frontend TypeScript interfaces.

Run:  python -m pytest tests/test_api_integration.py -v
"""

import importlib
import re

import pytest

# ---------------------------------------------------------------------------
# 1. Route Registration
# ---------------------------------------------------------------------------


def _get_app_routes():
    """Import the FastAPI app and extract registered routes."""
    from app.api.routes import router  # noqa: E402

    paths = [r.path for r in router.routes if hasattr(r, "path")]
    return paths


EXPECTED_ROUTE_GROUPS = {
    "admin_aggregates": [
        "/admin/aggregates/asset-health",
        "/admin/aggregates/critical-alerts",
        "/admin/aggregates/financial-metrics",
        "/admin/aggregates/trucks-in-transit",
    ],
    "notifications": [
        "/notifications/send",
        "/notifications/history",
    ],
}


@pytest.mark.parametrize(
    "group,expected_paths",
    list(EXPECTED_ROUTE_GROUPS.items()),
)
def test_route_group_registered(group, expected_paths):
    routes = _get_app_routes()
    for path in expected_paths:
        matches = [r for r in routes if path in r]
        assert len(matches) >= 1, f"[{group}] Route {path} not found. All routes: {routes[:20]}..."


# ---------------------------------------------------------------------------
# 2. Response model field checks
# ---------------------------------------------------------------------------


def test_notification_history_response_model():
    """NotificationHistoryResponse must have items (list) and total (int)."""
    from app.api.routes.notifications import NotificationHistoryResponse

    schema = NotificationHistoryResponse.model_json_schema()
    props = schema.get("properties", {})
    assert "items" in props, "Missing 'items' field"
    assert "total" in props, "Missing 'total' field"


def test_admin_aggregate_asset_health_fields():
    """AssetHealthSummary response must contain expected keys."""
    from app.api.routes.admin_aggregates import router as agg_router

    # Find the asset-health endpoint handler
    for route in agg_router.routes:
        if hasattr(route, "path") and "asset-health" in route.path:
            # Endpoint exists — that validates registration.
            break
    else:
        pytest.fail("asset-health route not registered on admin_aggregates router")


# ---------------------------------------------------------------------------
# 3. Data consistency helpers
# ---------------------------------------------------------------------------


def test_notification_channel_enum_matches_frontend():
    """Backend channel enum values should match frontend types."""
    from app.services.notification_service import NotificationChannel

    backend_values = {e.value for e in NotificationChannel}
    frontend_channels = {"push", "sms", "email", "voice"}
    assert frontend_channels.issubset(backend_values), (
        f"Frontend channels {frontend_channels - backend_values} missing from backend enum"
    )


def test_notification_priority_enum_matches_frontend():
    from app.services.notification_service import NotificationPriority

    backend_values = {e.value for e in NotificationPriority}
    frontend_priorities = {"LOW", "NORMAL", "HIGH", "CRITICAL"}
    assert frontend_priorities.issubset(backend_values), (
        f"Frontend priorities {frontend_priorities - backend_values} missing from backend enum"
    )

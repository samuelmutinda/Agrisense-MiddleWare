"""Admin aggregate endpoints for dashboard metrics.

These compose multiple service calls into single responses,
replacing the client-side Firebase aggregate functions:
- getAssetHealthSummary
- getCriticalAlerts
- getFinancialMetrics
- getTrucksInTransit
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services import (
    cold_storage_unit_service,
    reefer_truck_service,
    produce_batch_service,
    manifest_service,
)

router = APIRouter(
    prefix="/admin/aggregates",
    tags=["admin-aggregates"],
    dependencies=[Depends(deps.require_admin)],
)


@router.get("/asset-health")
async def asset_health_summary(
    session: AsyncSession = Depends(deps.get_system_db),
) -> dict[str, Any]:
    """Aggregate health status across cold-storage units and reefer trucks."""
    units = await cold_storage_unit_service.list_cold_storage_units(session)
    trucks = await reefer_truck_service.list_reefer_trucks(session)

    all_assets: list[dict[str, Any]] = []
    for u in units:
        row = u if isinstance(u, dict) else (u.__dict__ if hasattr(u, "__dict__") else {})
        all_assets.append(row)
    for t in trucks:
        row = t if isinstance(t, dict) else (t.__dict__ if hasattr(t, "__dict__") else {})
        all_assets.append(row)

    total = len(all_assets)
    healthy = sum(
        1
        for a in all_assets
        if a.get("is_active", a.get("isActive", False))
        and not a.get("maintenance_required", a.get("maintenanceRequired", False))
    )
    warning = sum(
        1
        for a in all_assets
        if a.get("is_active", a.get("isActive", False))
        and a.get("maintenance_required", a.get("maintenanceRequired", False))
    )
    offline = total - healthy - warning

    return {
        "total": total,
        "healthy": healthy,
        "warning": warning,
        "offline": offline,
        "healthPercentage": round((healthy / total) * 100, 1) if total else 100.0,
    }


@router.get("/critical-alerts")
async def critical_alerts(
    session: AsyncSession = Depends(deps.get_system_db),
) -> list[dict[str, Any]]:
    """Derive critical alerts from asset status flags."""
    units = await cold_storage_unit_service.list_cold_storage_units(session)
    trucks = await reefer_truck_service.list_reefer_trucks(session)
    alerts: list[dict[str, Any]] = []

    for u in units:
        row = u if isinstance(u, dict) else (u.__dict__ if hasattr(u, "__dict__") else {})
        uid = str(row.get("id", ""))
        name = row.get("name", uid)
        if not row.get("is_active", row.get("isActive", True)):
            alerts.append({
                "id": f"unit-offline-{uid}",
                "type": "Unit Offline",
                "severity": "critical",
                "assetId": uid,
                "assetName": name,
                "message": f"Cold storage unit {name} is offline",
            })
        if row.get("maintenance_required", row.get("maintenanceRequired", False)):
            alerts.append({
                "id": f"unit-maintenance-{uid}",
                "type": "Maintenance Required",
                "severity": "warning",
                "assetId": uid,
                "assetName": name,
                "message": f"{name} requires maintenance",
            })

    for t in trucks:
        row = t if isinstance(t, dict) else (t.__dict__ if hasattr(t, "__dict__") else {})
        tid = str(row.get("id", ""))
        plate = row.get("license_plate", row.get("licensePlate", tid))
        if not row.get("is_active", row.get("isActive", True)):
            alerts.append({
                "id": f"truck-offline-{tid}",
                "type": "Truck Offline",
                "severity": "critical",
                "assetId": tid,
                "assetName": plate,
                "message": f"Reefer truck {plate} is offline",
            })

    return alerts


@router.get("/financial-metrics")
async def financial_metrics(
    session: AsyncSession = Depends(deps.get_system_db),
) -> dict[str, Any]:
    """Compute financial metrics from produce batches."""
    batches = await produce_batch_service.list_produce_batches(session)

    total_value = 0.0
    total_weight = 0.0
    spoiled_weight = 0.0

    for b in batches:
        row = b if isinstance(b, dict) else (b.__dict__ if hasattr(b, "__dict__") else {})
        initial = float(row.get("initial_weight_kg", row.get("initialWeightKg", 0)) or 0)
        current = float(row.get("current_weight_kg", row.get("currentWeightKg", initial)) or initial)
        price = float(row.get("price_per_kg", row.get("pricePerKg", 0)) or 0)
        total_weight += initial
        total_value += current * price
        spoiled_weight += max(0.0, initial - current)

    spoilage_rate = (spoiled_weight / total_weight * 100) if total_weight > 0 else 0.0
    spoilage_cost = total_value * (spoilage_rate / 100)

    return {
        "totalInventoryValue": round(total_value, 2),
        "spoilageRate": round(spoilage_rate, 2),
        "spoilageCost": round(spoilage_cost, 2),
        "netValue": round(total_value - spoilage_cost, 2),
    }


_TRANSIT_STATUSES = frozenset([
    "in_transit", "driver_in_transit", "dispatch_in_progress",
    "in_progress", "dispatched", "en_route", "transit",
])


def _is_transit(value: Any) -> bool:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_") in _TRANSIT_STATUSES


@router.get("/trucks-in-transit")
async def trucks_in_transit(
    session: AsyncSession = Depends(deps.get_system_db),
) -> list[dict[str, Any]]:
    """Return trucks currently in transit (by truck status or manifest status)."""
    trucks = await reefer_truck_service.list_reefer_trucks(session)
    manifests = await manifest_service.list_manifests(session)

    truck_map: dict[str, dict] = {}
    for t in trucks:
        row = t if isinstance(t, dict) else (t.__dict__ if hasattr(t, "__dict__") else {})
        tid = str(row.get("id", ""))
        truck_map[tid] = row
        if any(
            _is_transit(row.get(f))
            for f in ("status", "current_status", "operational_status")
        ):
            truck_map.setdefault(f"__transit__{tid}", row)

    transit_ids: set[str] = set()
    for t in trucks:
        row = t if isinstance(t, dict) else (t.__dict__ if hasattr(t, "__dict__") else {})
        tid = str(row.get("id", ""))
        if any(_is_transit(row.get(f)) for f in ("status", "current_status", "operational_status")):
            transit_ids.add(tid)

    for m in manifests:
        mrow = m if isinstance(m, dict) else (m.__dict__ if hasattr(m, "__dict__") else {})
        if any(_is_transit(mrow.get(f)) for f in ("status", "dispatch_status")):
            vehicle_id = str(
                mrow.get("vehicle_id")
                or mrow.get("assigned_truck_id")
                or mrow.get("truck_id")
                or ""
            )
            if vehicle_id and vehicle_id in truck_map:
                transit_ids.add(vehicle_id)

    return [truck_map[tid] for tid in transit_ids if tid in truck_map]

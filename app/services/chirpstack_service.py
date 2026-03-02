"""
ChirpStack event ingestion service.

This service handles incoming ChirpStack webhook events. It:
- Normalizes ChirpStack payloads
- Resolves tenant and device identifiers from the database
- Emits filtered events to WebSocket subscribers

This service does NOT:
- Create business events (arrivals, transfers, etc.)
- Modify inventory or ledger
- Expose ChirpStack schemas to business APIs
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.ws.manager import manager


async def resolve_tenant_by_name(
    session: AsyncSession, tenant_name: str
) -> Optional[str]:
    """Resolve tenant name to tenant UUID."""
    if not tenant_name:
        return None
    stmt = select(models.Tenant).where(models.Tenant.name == tenant_name)
    result = await session.execute(stmt)
    tenant = result.scalar_one_or_none()
    return str(tenant.id) if tenant else None


async def resolve_device_by_external_id(
    session: AsyncSession, tenant_id: str, dev_eui: str
) -> Optional[str]:
    """Resolve external device ID (devEUI) to device UUID."""
    if not dev_eui:
        return None
    stmt = (
        select(models.Device)
        .where(models.Device.external_device_id == dev_eui)
        .where(models.Device.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    device = result.scalar_one_or_none()
    return str(device.id) if device else None


async def process_uplink_event(
    session: AsyncSession, raw_payload: dict, event_type: str = "unknown"
) -> dict:
    """
    Process a ChirpStack uplink event.

    This function:
    1. Extracts tenant/device identifiers from the payload
    2. Resolves them to database UUIDs
    3. Normalizes the payload into our internal event schema
    4. Emits the event to WebSocket subscribers (filtered by tenant/device)

    This function does NOT:
    - Create business records
    - Modify inventory
    - Require authentication (it's a webhook from external system)
    """
    # Extract ChirpStack-specific fields
    device_info = raw_payload.get("deviceInfo", {})
    tenant_name = device_info.get("tenantName")
    dev_eui = device_info.get("devEui")

    # Resolve tenant UUID from name
    tenant_id: Optional[str] = None
    if tenant_name:
        tenant_id = await resolve_tenant_by_name(session, tenant_name)

    # Resolve device UUID from external ID (if tenant is known)
    device_id: Optional[str] = None
    if tenant_id and dev_eui:
        device_id = await resolve_device_by_external_id(session, tenant_id, dev_eui)

    # Build normalized event payload
    event_payload = {
        "type": "sensor_uplink",
        "event": event_type,
        "timestamp": raw_payload.get("time"),
        "tenant_id": tenant_id,
        "device_id": device_id,
        "device_name": device_info.get("deviceName"),
        "dev_eui": dev_eui,
        "dev_addr": raw_payload.get("devAddr"),
        "f_cnt": raw_payload.get("fCnt"),
        "confirmed": raw_payload.get("confirmed"),
        "f_port": raw_payload.get("fPort"),
        "data_base64": raw_payload.get("data"),
        "decoded_object": raw_payload.get("object"),
        "rx_info": raw_payload.get("rxInfo", []),
        "tx_info": raw_payload.get("txInfo"),
        "region": raw_payload.get("regionConfigId"),
    }

    # Emit to WebSocket subscribers (filtered by tenant and device)
    # NOTE: manager.broadcast() automatically filters by tenant_id - only connections
    # with matching tenant_id (from their AuthContext) will receive this event.
    # ChirpStack has unlimited access to send events, but WebSocket filtering ensures
    # tenant isolation on the receiving side.
    if tenant_id:
        await manager.broadcast(
            tenant_id=tenant_id,
            payload=event_payload,
            device_id=device_id,
        )

    return {"status": "ok"}

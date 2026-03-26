"""
ChirpStack event ingestion service.

This service handles incoming ChirpStack webhook events. It:
- Normalizes ChirpStack payloads
- Resolves tenant and device identifiers from the database
- Persists telemetry data to InfluxDB
- Emits filtered events to WebSocket subscribers

This service does NOT:
- Create business events (arrivals, transfers, etc.)
- Modify inventory or ledger
- Expose ChirpStack schemas to business APIs
"""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.ws.manager import manager
from app.services import influxdb_service

logger = logging.getLogger(__name__)


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


async def resolve_asset_for_device(
    session: AsyncSession, device_id: str
) -> Optional[str]:
    """
    Resolve which asset (cold storage unit or reefer truck) a device is assigned to.
    
    Returns the asset UUID if the device is assigned to an asset, None otherwise.
    """
    if not device_id:
        return None
    
    # Check ColdStorageUnit (has sensor_device_id field)
    stmt = select(models.ColdStorageUnit).where(
        models.ColdStorageUnit.sensor_device_id == device_id
    )
    result = await session.execute(stmt)
    unit = result.scalar_one_or_none()
    if unit:
        return str(unit.id)
    
    # Check ReeferTruck (has sensor_device_id field)
    stmt = select(models.ReeferTruck).where(
        models.ReeferTruck.sensor_device_id == device_id
    )
    result = await session.execute(stmt)
    truck = result.scalar_one_or_none()
    if truck:
        return str(truck.id)
    
    return None


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

    # =========================================================================
    # PERSIST TELEMETRY TO INFLUXDB
    # =========================================================================
    decoded_object = raw_payload.get("object", {})
    if decoded_object and device_id:
        # Extract telemetry from decoded payload
        temperature = decoded_object.get("temperature")
        humidity = decoded_object.get("humidity")
        door_open = decoded_object.get("doorOpen") or decoded_object.get("door_open")
        battery = decoded_object.get("batteryLevel") or decoded_object.get("battery")
        
        # Get asset_id from device assignment (if available)
        asset_id = await resolve_asset_for_device(session, device_id)
        
        # Determine asset type
        asset_type = "cold_storage_unit"  # Default
        if asset_id:
            # Check if it's a reefer truck
            stmt = select(models.ReeferTruck).where(models.ReeferTruck.id == asset_id)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                asset_type = "reefer_truck"
        
        # Parse timestamp
        timestamp = None
        time_str = raw_payload.get("time")
        if time_str:
            try:
                timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp = None
        
        # Get signal strength from rxInfo
        signal_strength = None
        rx_info_list = raw_payload.get("rxInfo", [])
        if rx_info_list and len(rx_info_list) > 0:
            signal_strength = rx_info_list[0].get("rssi")
        
        # Write to InfluxDB
        if temperature is not None or humidity is not None or door_open is not None:
            await influxdb_service.write_telemetry_point(
                device_id=dev_eui or device_id,
                asset_id=asset_id or device_id,
                asset_type=asset_type,
                temperature=temperature,
                humidity=humidity,
                door_open=door_open,
                battery_level=battery,
                signal_strength=signal_strength,
                timestamp=timestamp,
                tenant_id=tenant_id,
                extra_fields={
                    "f_cnt": raw_payload.get("fCnt"),
                    "f_port": raw_payload.get("fPort"),
                }
            )
            logger.info(
                f"Persisted telemetry for device {dev_eui}: "
                f"temp={temperature}°C, humidity={humidity}%, door_open={door_open}"
            )

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

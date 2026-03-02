from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas import device as device_schema
from app.services import chirpstack_client
from app.services.helpers import get_or_404


async def _cold_storage_unit_for_device(
        session: AsyncSession, device_id: uuid.UUID
) -> uuid.UUID | None:
    stmt = (
        select(models.DeviceAssignment.cs_id)
        .where(
            models.DeviceAssignment.dev_id == device_id,
            models.DeviceAssignment.unassigned_at.is_(None),
        )
        .order_by(models.DeviceAssignment.assigned_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _to_response(
        device: models.Device,
        cold_storage_unit_id: uuid.UUID | None,
) -> device_schema.DeviceResponse:
    return device_schema.DeviceResponse(
        id=device.id,
        dev_eui=device.dev_eui,
        name=device.name,
        is_active=device.is_active,
        created_at=device.created_at,
        cold_storage_unit_id=cold_storage_unit_id,
        app_key=device.app_key,
    )


async def get_devices(
        session: AsyncSession,
        tenant_id: uuid.UUID,
) -> list[device_schema.DeviceResponse]:
    stmt = (
        select(models.Device)
        .where(models.Device.tenant_id == tenant_id)
        .order_by(models.Device.name.asc())
    )
    result = await session.execute(stmt)
    devices = result.scalars().all()
    out = []
    for d in devices:
        cs_id = await _cold_storage_unit_for_device(session, d.id)
        out.append(_to_response(d, cs_id))
    return out


async def get_device_by_id(
        session: AsyncSession,
        device_id: uuid.UUID,
        tenant_id: uuid.UUID,
) -> device_schema.DeviceResponse:
    device = await get_or_404(session, models.Device, device_id, tenant_id)
    cs_id = await _cold_storage_unit_for_device(session, device.id)
    return _to_response(device, cs_id)


async def create_device(
        session: AsyncSession,
        data: device_schema.DeviceCreate,
        tenant_id: uuid.UUID,
) -> device_schema.DeviceResponse:
    tenant = await get_or_404(session, models.Tenant, tenant_id)
    app_id = tenant.chirpstack_application_id
    profile_id = tenant.chirpstack_device_profile_id

    if not app_id or not profile_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant not provisioned. ChirpStack application or profile missing.",
        )

    dev_eui, app_key = chirpstack_client.generate_lorawan_keys()

    if data.cold_storage_unit_id is not None:
        await get_or_404(
            session, models.ColdStorageUnit, data.cold_storage_unit_id, tenant_id
        )

    await chirpstack_client.create_device(
        application_id=str(app_id),
        device_profile_id=str(profile_id),
        dev_eui=dev_eui,
        name=data.name,
        tags={},
    )

    await chirpstack_client.set_device_keys(dev_eui, app_key)

    try:
        now = datetime.utcnow()
        device = models.Device(
            dev_eui=dev_eui,
            app_key=app_key,
            tenant_id=tenant_id,
            name=data.name,
            is_active=True,
            created_at=now,
        )
        session.add(device)
        await session.flush()

        if data.cold_storage_unit_id is not None:
            assignment = models.DeviceAssignment(
                dev_id=device.id,
                cs_id=data.cold_storage_unit_id,
                assigned_at=now,
            )
            session.add(assignment)

        await session.commit()
        await session.refresh(device)
    except Exception:
        try:
            await chirpstack_client.delete_device(dev_eui)
        except Exception:
            pass
        raise

    cs_id = await _cold_storage_unit_for_device(session, device.id)
    return _to_response(device, cs_id)


async def update_device(
        session: AsyncSession,
        device_id: uuid.UUID,
        data: device_schema.DeviceUpdate,
        tenant_id: uuid.UUID,
) -> device_schema.DeviceResponse:
    device = await get_or_404(session, models.Device, device_id, tenant_id)
    prev_name = device.name

    if data.name is not None and data.name != prev_name:
        await chirpstack_client.update_device(device.dev_eui, data.name)

    try:
        if data.name is not None:
            device.name = data.name
        if data.is_active is not None:
            device.is_active = data.is_active

        if data.cold_storage_unit_id is not None:
            await get_or_404(
                session, models.ColdStorageUnit, data.cold_storage_unit_id, tenant_id
            )
            now = datetime.utcnow()

            stmt = select(models.DeviceAssignment).where(
                models.DeviceAssignment.dev_id == device_id,
                models.DeviceAssignment.unassigned_at.is_(None),
            )
            res = await session.execute(stmt)
            for a in res.scalars().all():
                a.unassigned_at = now

            new_assignment = models.DeviceAssignment(
                dev_id=device.id,
                cs_id=data.cold_storage_unit_id,
                assigned_at=now,
            )
            session.add(new_assignment)

        await session.commit()
        await session.refresh(device)
    except Exception:
        if data.name is not None and data.name != prev_name:
            try:
                await chirpstack_client.update_device(device.dev_eui, prev_name)
            except Exception:
                pass
        raise

    cs_id = await _cold_storage_unit_for_device(session, device.id)
    return _to_response(device, cs_id)


async def delete_device(
        session: AsyncSession,
        device_id: uuid.UUID,
        tenant_id: uuid.UUID,
) -> None:
    device = await get_or_404(session, models.Device, device_id, tenant_id)
    dev_eui = device.dev_eui

    await chirpstack_client.delete_device(dev_eui)

    stmt = select(models.DeviceAssignment).where(
        models.DeviceAssignment.dev_id == device.id
    )
    res = await session.execute(stmt)
    for a in res.scalars().all():
        await session.delete(a)

    await session.delete(device)
    await session.commit()
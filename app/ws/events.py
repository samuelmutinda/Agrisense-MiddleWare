from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from app.db import models
from app.ws.schemas import ArrivalEvent, CollectionEvent, TransferEvent, SpoilageEvent, LossEvent


def build_arrival_event(
    arrival: models.HarvestArrival,
    quantity: float,
    volume: float,
    cold_storage_unit_id: uuid.UUID,
) -> Dict[str, Any]:
    event = ArrivalEvent(
        intake_id=str(arrival.id),
        customer_id=str(arrival.customer_id),
        crop_id=str(arrival.crop_id),
        quantity=quantity,
        volume=volume,
        cold_storage_unit_id=str(cold_storage_unit_id),
        arrived_at=arrival.arrived_at,
    )
    return event.model_dump()

def build_spoilage_event(
    spoilage: models.HarvestSpoilage,
    quantity: float,
    volume: float,
    cold_storage_unit_id: uuid.UUID,
) -> Dict[str, Any]:
    event = SpoilageEvent(
        spoilage_id=str(spoilage.id),
        intake_id=str(spoilage.intake_id),
        detected_at=str(spoilage.detected_at),
        quantity=quantity,
        volume=volume,
        cold_storage_unit_id=str(cold_storage_unit_id)
    )
    return event.model_dump()

def build_collection_event(
    collection: models.HarvestCollection,
    quantity: float,
    volume: float,
    cold_storage_unit_id: uuid.UUID,
) -> Dict[str, Any]:
    event = CollectionEvent(
        collection_id=str(collection.id),
        intake_id=str(collection.intake_id),
        collected_at=collection.collected_at,
        quantity=quantity,
        volume=volume,
        cold_storage_unit_id=str(cold_storage_unit_id),
    )
    return event.model_dump()


def build_transfer_event(
    transfer: models.HarvestTransfer,
    quantity: float,
    volume: float,
) -> Dict[str, Any]:
    event = TransferEvent(
        transfer_id=str(transfer.id),
        intake_id=str(transfer.intake_id),
        from_cold_storage_unit_id=str(transfer.from_cs_id),
        to_cold_storage_unit_id=str(transfer.to_cs_id),
        transfer_status=str(transfer.status),
        quantity=quantity,
        volume=volume
    )
    return event.model_dump()

def build_loss_event(
    loss: models.HarvestLoss,
    quantity: float,
    volume: float
) -> Dict[str, Any]:
    event = LossEvent(
        loss_id=str(loss.id),
        intake_id=str(loss.intake_id),
        occurred_during=str(loss.occurred_during),
        loss_reason=str(loss.loss_reason),
        quantity=quantity,
        volume=volume
    )

    return event.model_dump()


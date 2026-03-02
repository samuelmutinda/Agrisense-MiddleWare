from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SensorUplinkEvent(BaseModel):
    event_type: str = Field(..., alias="type")
    timestamp: Optional[datetime] = None
    tenant_id: Optional[str] = None
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    dev_eui: Optional[str] = None
    dev_addr: Optional[str] = None
    f_cnt: Optional[int] = None
    confirmed: Optional[bool] = None
    f_port: Optional[int] = None
    data_base64: Optional[str] = None
    decoded_object: Optional[Dict[str, Any]] = None
    rx_info: list[Dict[str, Any]] = Field(default_factory=list)
    tx_info: Optional[Dict[str, Any]] = None
    region: Optional[str] = None

    class Config:
        populate_by_name = True


class BusinessEvent(BaseModel):
    event_type: str
    quantity: float
    volume: float
    intake_id: str

class ArrivalEvent(BusinessEvent):
    event_type: str = "arrival"
    customer_id: str
    crop_id: str
    cold_storage_unit_id: str
    arrived_at: datetime

class SpoilageEvent(BusinessEvent):
    event_type: str = "spoilage"
    spoilage_id: str
    detected_at: str
    cold_storage_unit_id: str

class CollectionEvent(BusinessEvent):
    event_type: str = "collection"
    collection_id: str
    collected_at: datetime
    cold_storage_unit_id: str

class TransferEvent(BusinessEvent):
    event_type: str = "transfer"
    transfer_id: str
    from_cold_storage_unit_id: str
    to_cold_storage_unit_id: str
    transfer_status: str

class LossEvent(BusinessEvent):
    event_type: str = "loss"
    loss_id: str
    occurred_during: str
    loss_reason: str
from app.db.models.tenant import Tenant
from app.db.models.customer import Customer
from app.db.models.user import User
from app.db.models.user_role import UserRole
from app.db.models.device import Device
from app.db.models.device_assignment import DeviceAssignment
from app.db.models.sensor_type import SensorType
from app.db.models.device_sensor_capability import DeviceSensorCapability
from app.db.models.cold_storage_unit import ColdStorageUnit
from app.db.models.crop import Crop
from app.db.models.harvest_arrival import HarvestArrival
from app.db.models.harvest_transfer import HarvestTransfer
from app.db.models.harvest_spoilage import HarvestSpoilage
from app.db.models.harvest_loss import HarvestLoss
from app.db.models.harvest_collection import HarvestCollection
from app.db.models.harvest_inventory_ledger import HarvestInventoryLedger

# New models for AgriSenseApp integration
from app.db.models.organization import Organization
from app.db.models.reefer_truck import ReeferTruck
from app.db.models.manifest import Manifest, ManifestItem
from app.db.models.produce_batch import ProduceBatch
from app.db.models.inventory_movement import InventoryMovement
from app.db.models.inspection import Inspection
from app.db.models.certification import Certification
from app.db.models.regulatory_compliance import RegulatoryCompliance
from app.db.models.financial_transaction import FinancialTransaction
from app.db.models.invoice import Invoice
from app.db.models.kpi_metric import KpiMetric
from app.db.models.gcp_profile import GcpProfile
from app.db.models.asset_performance import AssetPerformance
from app.db.models.energy_consumption import EnergyConsumption
from app.db.models.operating_cost import OperatingCost
from app.db.models.maintenance_record import MaintenanceRecord
from app.db.models.staff_operation import StaffOperation
from app.db.models.audit_trail import AuditTrail

__all__ = [
    "Tenant",
    "Customer",
    "User",
    "UserRole",
    "Device",
    "DeviceAssignment",
    "SensorType",
    "DeviceSensorCapability",
    "ColdStorageUnit",
    "Crop",
    "HarvestArrival",
    "HarvestTransfer",
    "HarvestSpoilage",
    "HarvestLoss",
    "HarvestCollection",
    "HarvestInventoryLedger",
    # New models
    "Organization",
    "ReeferTruck",
    "Manifest",
    "ManifestItem",
    "ProduceBatch",
    "InventoryMovement",
    "Inspection",
    "Certification",
    "RegulatoryCompliance",
    "FinancialTransaction",
    "Invoice",
    "KpiMetric",
    "GcpProfile",
    "AssetPerformance",
    "EnergyConsumption",
    "OperatingCost",
    "MaintenanceRecord",
    "StaffOperation",
    "AuditTrail",
]


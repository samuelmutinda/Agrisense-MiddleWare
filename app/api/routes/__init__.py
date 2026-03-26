from fastapi import APIRouter

from app.api.routes import (
    admin,
    admin_aggregates,
    arrivals,
    auth,
    chirpstack,
    cold_storage_units,
    collections,
    crops,
    customers,
    inventory,
    losses,
    spoilages,
    transfers,
    # New routes for AgriSenseApp integration
    organizations,
    users,
    reefer_trucks,
    manifests,
    produce_batches,
    inventory_movements,
    inspections,
    certifications,
    regulatory_compliance,
    financial_transactions,
    invoices,
    kpi_metrics,
    gcp_profiles,
    asset_performance,
    energy_consumption,
    operating_costs,
    maintenance_records,
    staff_operations,
    audit_trail,
    notifications,
    # RSL and prediction services
    predictions,
    # Telemetry ingestion and query (Roadmap §3.2)
    telemetry,
    # Digital twin analytics (InfluxDB digital_twin bucket)
    digital_twin,
)


def get_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth.router)
    router.include_router(admin.router)
    router.include_router(admin_aggregates.router)
    router.include_router(arrivals.router)
    router.include_router(cold_storage_units.router)
    router.include_router(customers.router)
    router.include_router(crops.router)
    router.include_router(transfers.router)
    router.include_router(collections.router)
    router.include_router(inventory.router)
    router.include_router(losses.router)
    router.include_router(spoilages.router)
    router.include_router(chirpstack.router)
    # New routers for AgriSenseApp integration
    router.include_router(organizations.router)
    router.include_router(users.router)
    router.include_router(reefer_trucks.router)
    router.include_router(manifests.router)
    router.include_router(produce_batches.router)
    router.include_router(inventory_movements.router)
    router.include_router(inspections.router)
    router.include_router(certifications.router)
    router.include_router(regulatory_compliance.router)
    router.include_router(financial_transactions.router)
    router.include_router(invoices.router)
    router.include_router(kpi_metrics.router)
    router.include_router(gcp_profiles.router)
    router.include_router(asset_performance.router)
    router.include_router(energy_consumption.router)
    router.include_router(operating_costs.router)
    router.include_router(maintenance_records.router)
    router.include_router(staff_operations.router)
    router.include_router(audit_trail.router)
    router.include_router(notifications.router)
    # RSL and prediction services
    router.include_router(predictions.router)
    # Telemetry ingestion and query (Roadmap §3.2)
    router.include_router(telemetry.router)
    # Digital twin analytics (InfluxDB digital_twin bucket)
    router.include_router(digital_twin.router)
    return router


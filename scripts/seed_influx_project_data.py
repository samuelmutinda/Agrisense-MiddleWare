from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.domain.bucket_retention_rules import BucketRetentionRules


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
APP_SEED_ROOT = WORKSPACE_ROOT / "AgriSenseApp" / "src" / "data" / "seedData"

load_dotenv(ROOT / ".env")

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "agrisense")
BUCKET_RAW = os.getenv("INFLUXDB_BUCKET_RAW", "telemetry-raw")
BUCKET_DOWNSAMPLED = os.getenv("INFLUXDB_BUCKET_DOWNSAMPLED", "telemetry-downsampled-1h")
BUCKET_KPI = os.getenv("INFLUXDB_BUCKET_KPI", "kpi-metrics")


def read_json(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00").replace(" ", "T")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def ensure_bucket(client: InfluxDBClient, bucket_name: str) -> None:
    buckets_api = client.buckets_api()
    if buckets_api.find_bucket_by_name(bucket_name) is not None:
        return

    orgs = client.organizations_api().find_organizations(org=INFLUXDB_ORG)
    if not orgs:
        raise RuntimeError(f"InfluxDB org not found: {INFLUXDB_ORG}")

    retention = BucketRetentionRules(type="expire", every_seconds=365 * 86400)
    buckets_api.create_bucket(bucket_name=bucket_name, retention_rules=retention, org_id=orgs[0].id)
    print(f"[agrisense] Created bucket {bucket_name}")


def build_asset_type_lookup() -> Dict[str, str]:
    cold_rooms = read_json(APP_SEED_ROOT / "coldStorageUnits.json")
    reefer_trucks = read_json(APP_SEED_ROOT / "reeferTrucks.json")

    lookup: Dict[str, str] = {}
    for item in cold_rooms:
        asset_type = item.get("type") or "cold_storage_unit"
        lookup[item["id"]] = "reefer_truck" if asset_type == "reefer_truck" else "cold_storage_unit"
    for item in reefer_trucks:
        lookup[item["id"]] = "reefer_truck"
    return lookup


def build_device_lookup() -> Dict[str, str]:
    sensor_devices = read_json(APP_SEED_ROOT / "sensorDevices.json")
    lookup: Dict[str, str] = {}
    for device in sensor_devices:
        if device.get("isActive") and device.get("assetId") and device["assetId"] not in lookup:
            lookup[device["assetId"]] = device["id"]
    return lookup


def build_raw_points(records: Iterable[Dict[str, Any]]) -> List[Point]:
    device_lookup = build_device_lookup()
    asset_type_lookup = build_asset_type_lookup()
    points: List[Point] = []

    for record in records:
        asset_id = record["assetId"]
        device_id = device_lookup.get(asset_id, f"derived-{asset_id}")
        point = (
            Point("sensor_reading")
            .tag("device_id", device_id)
            .tag("asset_id", asset_id)
            .tag("asset_type", asset_type_lookup.get(asset_id, "cold_storage_unit"))
            .tag("tenant_id", record["organizationId"])
            .field("temperature", float(record["averageTempC"]))
            .field("humidity", float(record["humidityPct"]))
            .field("door_open", bool(record["doorOpenings"] > 0))
            .field("door_openings", int(record["doorOpenings"]))
            .field("energy_consumed_kwh", float(record["totalKwh"]))
            .field("peak_kwh", float(record["peakKwh"]))
            .field("off_peak_kwh", float(record["offPeakKwh"]))
            .field("total_cost_kes", float(record["totalCostKes"]))
            .field("efficiency_score", float(record["efficiencyScore"]))
            .field("outside_temp_c", float(record["outsideTempC"]))
            .time(parse_timestamp(record["readingTimestamp"]))
        )
        points.append(point)

    return points


def build_downsampled_points(records: Iterable[Dict[str, Any]]) -> List[Point]:
    points: List[Point] = []
    for record in records:
        point = (
            Point("sensor_reading_hourly")
            .tag("asset_id", record["assetId"])
            .tag("tenant_id", record["organizationId"])
            .field("temperature_mean", float(record["averageTempC"]))
            .field("humidity_mean", float(record["humidityPct"]))
            .field("energy_consumed_kwh", float(record["totalKwh"]))
            .field("door_openings", int(record["doorOpenings"]))
            .field("efficiency_score", float(record["efficiencyScore"]))
            .time(parse_timestamp(record["readingTimestamp"]))
        )
        points.append(point)
    return points


def build_kpi_points(records: Iterable[Dict[str, Any]]) -> List[Point]:
    points: List[Point] = []
    for record in records:
        point = (
            Point("organization_kpi")
            .tag("organization_id", record["organizationId"])
            .tag("metric_period", record["metricPeriod"])
            .field("spoilage_rate_pct", float(record["spoilageRatePct"]))
            .field("quality_compliance_rate_pct", float(record["qualityComplianceRatePct"]))
            .field("on_time_delivery_rate_pct", float(record["onTimeDeliveryRatePct"]))
            .field("asset_utilization_rate_pct", float(record["assetUtilizationRatePct"]))
            .field("inventory_turnover_ratio", float(record["inventoryTurnoverRatio"]))
            .field("revenue_kes", float(record["revenueKes"]))
            .field("operating_costs_kes", float(record["operatingCostsKes"]))
            .field("gross_profit_margin_pct", float(record["grossProfitMarginPct"]))
            .field("cost_per_kg_kes", float(record["costPerKgKes"]))
            .field("revenue_per_kg_kes", float(record["revenuePerKgKes"]))
            .field("energy_efficiency_score", float(record["energyEfficiencyScore"]))
            .field("labor_productivity_score", float(record["laborProductivityScore"]))
            .field("equipment_uptime_pct", float(record["equipmentUptimePct"]))
            .field("average_response_time_minutes", float(record["averageResponseTimeMinutes"]))
            .field("customer_satisfaction_score", float(record["customerSatisfactionScore"]))
            .field("compliance_score", float(record["complianceScore"]))
            .field("safety_incident_count", int(record["safetyIncidentCount"]))
            .field("audit_pass_rate_pct", float(record["auditPassRatePct"]))
            .time(parse_timestamp(record["metricDate"]))
        )
        points.append(point)

    return points


def main() -> None:
    if not INFLUXDB_TOKEN:
        raise RuntimeError("INFLUXDB_TOKEN is not set")

    energy_records = read_json(APP_SEED_ROOT / "energyConsumption.json")
    kpi_records = read_json(APP_SEED_ROOT / "kpiMetrics.json")

    with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
        ensure_bucket(client, BUCKET_RAW)
        ensure_bucket(client, BUCKET_DOWNSAMPLED)
        ensure_bucket(client, BUCKET_KPI)

        write_api = client.write_api(write_options=SYNCHRONOUS)
        raw_points = build_raw_points(energy_records)
        downsampled_points = build_downsampled_points(energy_records)
        kpi_points = build_kpi_points(kpi_records)

        write_api.write(bucket=BUCKET_RAW, org=INFLUXDB_ORG, record=raw_points)
        write_api.write(bucket=BUCKET_DOWNSAMPLED, org=INFLUXDB_ORG, record=downsampled_points)
        write_api.write(bucket=BUCKET_KPI, org=INFLUXDB_ORG, record=kpi_points)

        print(f"[agrisense] Seeded {len(raw_points):,} telemetry-raw points")
        print(f"[agrisense] Seeded {len(downsampled_points):,} telemetry-downsampled-1h points")
        print(f"[agrisense] Seeded {len(kpi_points):,} kpi-metrics points")


if __name__ == "__main__":
    main()
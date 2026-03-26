"""
Digital Twin CSV → InfluxDB ingest script (middleware-integrated).

Adapted from the standalone Agrisense-Project-default/ingest.py to work
inside the middleware repo, reading InfluxDB credentials from the
middleware's .env file.

Usage:
  cd Agrisense-MiddleWare-main
  python scripts/ingest_digital_twin.py                           # default CSV path from .env
  python scripts/ingest_digital_twin.py --csv /path/to/data.csv   # explicit CSV
  python scripts/ingest_digital_twin.py --dry-run                 # parse only
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

# ── Load middleware .env ──────────────────────────────────────────────────────
load_dotenv()

INFLUXDB_URL    = os.getenv("INFLUXDB_URL",    "http://localhost:8086")
INFLUXDB_TOKEN  = os.getenv("INFLUXDB_TOKEN",  "")
INFLUXDB_ORG    = os.getenv("INFLUXDB_ORG",    "agrisense")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET_DIGITAL_TWIN", "digital_twin")
CSV_PATH        = os.getenv("CSV_PATH", "digital_twin_balanced_20000_seed42.csv")

# ── Schema (mirrors Agrisense-Project-default/ingest.py) ─────────────────────
MEASUREMENT = "cold_chain"

TAG_COLUMNS = [
    "crop_type",
    "quality_status",
    "temp_profile",
    "humidity_profile",
    "initial_condition",
    "scenario_id",
]

FLAG_TAG_COLUMNS = [
    "compressor_on",
    "door_open",
    "is_good",
    "is_spoiled",
]

INT_FIELD_COLUMNS = [
    "hour",
    "door_cycles_today",
    "door_cycles_cumulative",
    "compressor_duty_cycle",
    "condensation_risk_zones",
    "quality_class",
]

FLOAT_FIELD_COLUMNS = [
    "temperature", "humidity", "co2_ppm", "light_lux", "ethylene_ppm",
    "temperature_floor", "temperature_mid", "temperature_ceiling",
    "humidity_point_1", "humidity_point_2", "humidity_point_3",
    "humidity_gradient_variance",
    "compressor_power_kw", "energy_consumed_kwh", "energy_anomaly_score",
    "room_pressure_pa", "pressure_stability",
    "quality_index", "rsl_hours", "rsl_percent",
    "decay_temperature", "decay_humidity", "decay_co2",
    "decay_microbial", "decay_infrastructure", "flu_total",
    "water_loss_percent", "microbial_load", "mold_risk_score",
]


def minutes_to_ns(minutes: int, base_ns: int) -> int:
    max_minutes = 20160   # 14 days
    offset_ns = (max_minutes - int(minutes)) * 60 * 1_000_000_000
    return base_ns - offset_ns


def row_to_point(row: pd.Series, base_ns: int) -> dict:
    tags = {}
    for col in TAG_COLUMNS:
        val = row.get(col)
        if pd.notna(val):
            tags[col] = str(val)

    for col in FLAG_TAG_COLUMNS:
        val = row.get(col)
        if pd.notna(val):
            tags[col] = "true" if int(val) == 1 else "false"

    fields = {}
    for col in FLOAT_FIELD_COLUMNS:
        val = row.get(col)
        if pd.notna(val):
            fields[col] = float(val)

    for col in INT_FIELD_COLUMNS:
        val = row.get(col)
        if pd.notna(val):
            fields[col] = int(val)

    return {
        "measurement": MEASUREMENT,
        "tags": tags,
        "fields": fields,
        "time": minutes_to_ns(row["timestamp_minutes"], base_ns),
    }


def ensure_bucket(client: InfluxDBClient, bucket_name: str, org: str) -> None:
    """Create the target bucket if it doesn't already exist."""
    buckets_api = client.buckets_api()
    existing = buckets_api.find_bucket_by_name(bucket_name)
    if existing is None:
        from influxdb_client.domain.bucket_retention_rules import BucketRetentionRules
        org_obj = client.organizations_api().find_organizations(org=org)
        if not org_obj:
            print(f"[agrisense] WARNING: Org '{org}' not found — skipping bucket creation")
            return
        retention = BucketRetentionRules(type="expire", every_seconds=365 * 86400)
        buckets_api.create_bucket(
            bucket_name=bucket_name,
            retention_rules=retention,
            org_id=org_obj[0].id,
        )
        print(f"[agrisense] Created bucket '{bucket_name}'")
    else:
        print(f"[agrisense] Bucket '{bucket_name}' already exists")


def main():
    parser = argparse.ArgumentParser(description="Ingest digital twin CSV → InfluxDB")
    parser.add_argument("--csv",     default=CSV_PATH, help="Path to CSV file")
    parser.add_argument("--batch",   type=int, default=1000, help="Write batch size")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no writes")
    args = parser.parse_args()

    print(f"[agrisense] Loading {args.csv} …")
    df = pd.read_csv(args.csv)
    print(f"[agrisense] Loaded {len(df):,} rows × {len(df.columns)} columns")

    print("[agrisense] Building line-protocol points …")
    base_ns = int(time.time() * 1_000_000_000)
    points = [row_to_point(row, base_ns) for _, row in df.iterrows()]
    print(f"[agrisense] {len(points):,} points ready")

    if args.dry_run:
        print("[agrisense] --dry-run: showing first 2 points, then exiting")
        for p in points[:2]:
            print(p)
        return

    if not INFLUXDB_TOKEN:
        sys.exit("[agrisense] ERROR: INFLUXDB_TOKEN is not set. Check your .env file.")

    print(f"[agrisense] Connecting → {INFLUXDB_URL} | org={INFLUXDB_ORG} | bucket={INFLUXDB_BUCKET}")

    with InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
        ensure_bucket(client, INFLUXDB_BUCKET, INFLUXDB_ORG)

        write_api = client.write_api(write_options=SYNCHRONOUS)

        total   = len(points)
        written = 0
        t0      = time.time()

        for i in range(0, total, args.batch):
            batch = points[i : i + args.batch]
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=batch)
            written += len(batch)
            pct = written / total * 100
            print(f"  [{pct:5.1f}%] {written:,}/{total:,} points written …", end="\r")

        elapsed = time.time() - t0
        print(f"\n[agrisense] Done — {written:,} points in {elapsed:.1f}s "
              f"({written/elapsed:,.0f} pts/sec)")


if __name__ == "__main__":
    main()

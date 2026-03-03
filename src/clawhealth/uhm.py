"""Minimal UHM (Universal Health Metrics) mapping for Phase 1.

This module defines helpers to map Garmin daily stats into a simple
`uhm_daily` table stored in SQLite.

Schema (first pass):

    CREATE TABLE IF NOT EXISTS uhm_daily (
        date_local TEXT PRIMARY KEY,
        timezone TEXT,
        offset_to_utc_min INTEGER,
        sleep_total_min INTEGER,
        rhr_bpm REAL,
        steps INTEGER,
        distance_m REAL,
        calories_total REAL,
        weight_kg REAL,
        extra_metrics TEXT,
        source_vendor TEXT NOT NULL DEFAULT 'garmin',
        driver_version TEXT,
        mapping_version TEXT,
        raw_ref TEXT,
        ingested_at TEXT NOT NULL
    );

This is intentionally minimal and can be extended later.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


UHM_MAPPING_VERSION = "uhm_v1"
DRIVER_VERSION = "garminconnect_v1"


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uhm_daily (
                date_local TEXT PRIMARY KEY,
                timezone TEXT,
                offset_to_utc_min INTEGER,
                sleep_total_min INTEGER,
                rhr_bpm REAL,
                steps INTEGER,
                distance_m REAL,
                calories_total REAL,
                weight_kg REAL,
                extra_metrics TEXT,
                source_vendor TEXT NOT NULL DEFAULT 'garmin',
                driver_version TEXT,
                mapping_version TEXT,
                raw_ref TEXT,
                ingested_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def map_garmin_daily(date_str: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    """Map Garmin daily stats into UHM fields.

    Phase 1 uses a very small subset and parks the rest into extra_metrics.
    """

    # The exact keys depend on python-garminconnect; we keep this loose
    # for now and refine via real data.
    steps = stats.get("totalSteps") or stats.get("steps")
    distance_m = stats.get("totalDistanceMeters") or stats.get("distance")
    calories_total = stats.get("totalCalories") or stats.get("calories")
    rhr = stats.get("restingHeartRate") or stats.get("resting_hr")

    # Sleep duration in minutes, if available.
    sleep_total_min = None
    sleep = stats.get("sleep") or stats.get("sleepData")
    if isinstance(sleep, dict):
        # Many APIs report sleep duration in seconds.
        dur_sec = sleep.get("duration") or sleep.get("durationInSeconds")
        if isinstance(dur_sec, (int, float)):
            sleep_total_min = int(dur_sec // 60)

    weight_kg = stats.get("weightKilograms") or stats.get("weight_kg")

    extra_metrics = {
        k: v
        for k, v in stats.items()
        if k
        not in {
            "totalSteps",
            "steps",
            "totalDistanceMeters",
            "distance",
            "totalCalories",
            "calories",
            "restingHeartRate",
            "resting_hr",
            "sleep",
            "sleepData",
            "weightKilograms",
            "weight_kg",
        }
    }

    return {
        "date_local": date_str,
        "timezone": None,
        "offset_to_utc_min": None,
        "sleep_total_min": sleep_total_min,
        "rhr_bpm": float(rhr) if isinstance(rhr, (int, float)) else None,
        "steps": int(steps) if isinstance(steps, (int, float)) else None,
        "distance_m": float(distance_m) if isinstance(distance_m, (int, float)) else None,
        "calories_total": float(calories_total)
        if isinstance(calories_total, (int, float))
        else None,
        "weight_kg": float(weight_kg) if isinstance(weight_kg, (int, float)) else None,
        "extra_metrics": json.dumps(extra_metrics, ensure_ascii=False),
        "source_vendor": "garmin",
        "driver_version": DRIVER_VERSION,
        "mapping_version": UHM_MAPPING_VERSION,
        "raw_ref": None,
        "ingested_at": _now_iso(),
    }


def upsert_uhm_daily(db_path: Path, row: Dict[str, Any]) -> None:
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cols = list(row.keys())
        placeholders = ", ".join([":" + c for c in cols])
        assignments = ", ".join([f"{c}=excluded.{c}" for c in cols if c != "date_local"])
        sql = (
            "INSERT INTO uhm_daily (" + ", ".join(cols) + ") VALUES (" + placeholders + ") "
            "ON CONFLICT(date_local) DO UPDATE SET " + assignments
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()

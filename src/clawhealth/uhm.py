"""Minimal UHM (Universal Health Metrics) mapping for Phase 1.

This module defines helpers to map Garmin daily stats into a simple
`uhm_daily` table stored in SQLite, plus basic sync run logging and
raw payload storage.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

UHM_MAPPING_VERSION = "uhm_v1"
DRIVER_VERSION = "garminconnect_v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # uhm_daily
        cur.execute(
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
                -- Stress metrics
                stress_avg INTEGER,
                stress_max INTEGER,
                stress_qualifier TEXT,
                stress_total_min INTEGER,
                stress_low_min INTEGER,
                stress_medium_min INTEGER,
                stress_high_min INTEGER,
                -- Body Battery (estimated start/end of day)
                body_battery_start REAL,
                body_battery_end REAL,
                -- SpO2 summary
                spo2_avg REAL,
                spo2_lowest REAL,
                -- Respiration summary
                respiration_avg REAL,
                respiration_lowest REAL,
                respiration_highest REAL,
                -- HRV metrics (ms) and status
                hrv_last_night_avg REAL,
                hrv_weekly_avg REAL,
                hrv_status TEXT,
                hrv_feedback TEXT,
                extra_metrics TEXT,
                source_vendor TEXT NOT NULL DEFAULT 'garmin',
                driver_version TEXT,
                mapping_version TEXT,
                raw_ref TEXT,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw daily payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_daily_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw HRV payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_hrv_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # sync runs
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                range_start TEXT,
                range_end TEXT,
                error_code TEXT,
                error_message TEXT,
                driver_version TEXT,
                mapping_version TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def map_garmin_daily(date_str: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    """Map Garmin daily stats into UHM fields.

    Phase 1 uses a very small subset and parks the rest into extra_metrics.
    """

    steps = stats.get("totalSteps") or stats.get("steps")
    distance_m = stats.get("totalDistanceMeters") or stats.get("distance")
    # 优先使用千卡相关字段，兼容不同 key 命名
    calories_total = (
        stats.get("totalKilocalories")
        or stats.get("wellnessKilocalories")
        or stats.get("totalCalories")
        or stats.get("calories")
    )
    rhr = stats.get("restingHeartRate") or stats.get("resting_hr")

    # 睡眠：优先用顶层 sleepingSeconds；否则退回 sleep/sleepData 字段
    sleep_total_min: Optional[int] = None
    sleeping_sec = stats.get("sleepingSeconds")
    if isinstance(sleeping_sec, (int, float)):
        sleep_total_min = int(sleeping_sec // 60)
    else:
        sleep = stats.get("sleep") or stats.get("sleepData")
        if isinstance(sleep, dict):
            dur_sec = sleep.get("duration") or sleep.get("durationInSeconds")
            if isinstance(dur_sec, (int, float)):
                sleep_total_min = int(dur_sec // 60)

    # 体重：优先用 weight（通常为 kg），否则退回 weightKilograms/weight_kg
    weight_kg = stats.get("weight") or stats.get("weightKilograms") or stats.get("weight_kg")

    # Stress & Body Battery (日级)
    stress_avg = stats.get("averageStressLevel")
    stress_max = stats.get("maxStressLevel")
    stress_qualifier = stats.get("stressQualifier")

    body_battery_start = stats.get("bodyBatteryAtWakeTime")
    body_battery_end = stats.get("bodyBatteryMostRecentValue")

    # Stress durations (seconds → minutes)
    stress_total_min = None
    stress_low_min = None
    stress_medium_min = None
    stress_high_min = None
    total_stress = stats.get("totalStressDuration")
    low_stress = stats.get("lowStressDuration")
    med_stress = stats.get("mediumStressDuration")
    high_stress = stats.get("highStressDuration")
    if isinstance(total_stress, (int, float)):
        stress_total_min = int(total_stress // 60)
    if isinstance(low_stress, (int, float)):
        stress_low_min = int(low_stress // 60)
    if isinstance(med_stress, (int, float)):
        stress_medium_min = int(med_stress // 60)
    if isinstance(high_stress, (int, float)):
        stress_high_min = int(high_stress // 60)

    # SpO2 summary
    spo2_avg = stats.get("averageSpo2")
    spo2_lowest = stats.get("lowestSpo2")

    # Respiration summary
    respiration_avg = stats.get("avgWakingRespirationValue")
    respiration_lowest = stats.get("lowestRespirationValue")
    respiration_highest = stats.get("highestRespirationValue")

    extra_metrics = {
        k: v
        for k, v in stats.items()
        if k
        not in {
            "totalSteps",
            "steps",
            "totalDistanceMeters",
            "distance",
            "totalKilocalories",
            "wellnessKilocalories",
            "totalCalories",
            "calories",
            "restingHeartRate",
            "resting_hr",
            "sleep",
            "sleepData",
            "sleepingSeconds",
            "weight",
            "weightKilograms",
            "weight_kg",
            "averageStressLevel",
            "maxStressLevel",
            "stressQualifier",
            "bodyBatteryAtWakeTime",
            "bodyBatteryMostRecentValue",
            "totalStressDuration",
            "lowStressDuration",
            "mediumStressDuration",
            "highStressDuration",
            "averageSpo2",
            "lowestSpo2",
            "avgWakingRespirationValue",
            "highestRespirationValue",
            "lowestRespirationValue",
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
        # Stress & Body Battery
        "stress_avg": int(stress_avg) if isinstance(stress_avg, (int, float)) else None,
        "stress_max": int(stress_max) if isinstance(stress_max, (int, float)) else None,
        "stress_qualifier": str(stress_qualifier) if stress_qualifier is not None else None,
        "stress_total_min": stress_total_min,
        "stress_low_min": stress_low_min,
        "stress_medium_min": stress_medium_min,
        "stress_high_min": stress_high_min,
        "body_battery_start": float(body_battery_start)
        if isinstance(body_battery_start, (int, float))
        else None,
        "body_battery_end": float(body_battery_end)
        if isinstance(body_battery_end, (int, float))
        else None,
        "spo2_avg": float(spo2_avg) if isinstance(spo2_avg, (int, float)) else None,
        "spo2_lowest": float(spo2_lowest) if isinstance(spo2_lowest, (int, float)) else None,
        "respiration_avg": float(respiration_avg)
        if isinstance(respiration_avg, (int, float))
        else None,
        "respiration_lowest": float(respiration_lowest)
        if isinstance(respiration_lowest, (int, float))
        else None,
        "respiration_highest": float(respiration_highest)
        if isinstance(respiration_highest, (int, float))
        else None,
        # HRV fields are populated separately from garmin_hrv_raw
        "hrv_last_night_avg": None,
        "hrv_weekly_avg": None,
        "hrv_status": None,
        "hrv_feedback": None,
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


def upsert_daily_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = {
            "date_local": date_str,
            "payload": json.dumps(payload, ensure_ascii=False),
            "ingested_at": _now_iso(),
        }
        sql = (
            "INSERT INTO garmin_daily_raw (date_local, payload, ingested_at) "
            "VALUES (:date_local, :payload, :ingested_at) "
            "ON CONFLICT(date_local) DO UPDATE SET payload=excluded.payload, ingested_at=excluded.ingested_at"
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


def upsert_hrv_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    """Upsert raw HRV payload for a given local date.

    We store the exact JSON returned by get_hrv_data so that mapping can
    evolve over time without losing information.
    """

    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = {
            "date_local": date_str,
            "payload": json.dumps(payload, ensure_ascii=False),
            "ingested_at": _now_iso(),
        }
        sql = (
            "INSERT INTO garmin_hrv_raw (date_local, payload, ingested_at) "
            "VALUES (:date_local, :payload, :ingested_at) "
            "ON CONFLICT(date_local) DO UPDATE SET payload=excluded.payload, ingested_at=excluded.ingested_at"
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


def map_hrv_into_uhm(db_path: Path, date_str: str) -> None:
    """Map HRV raw payload for date_str into uhm_daily HRV fields.

    This reads garmin_hrv_raw.payload, extracts summary metrics, and updates
    the corresponding uhm_daily row if present.
    """

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT payload FROM garmin_hrv_raw WHERE date_local = ?",
            (date_str,),
        )
        row = cur.fetchone()
        if not row:
            return
        payload = json.loads(row[0])
        summary = payload.get("hrvSummary") or {}
        baseline = summary.get("baseline") or {}

        hrv_last_night_avg = summary.get("lastNightAvg")
        hrv_weekly_avg = summary.get("weeklyAvg")
        hrv_status = summary.get("status")
        hrv_feedback = summary.get("feedbackPhrase")

        # 目前先只写 summary 指标，如后续需要 baseline 范围可扩展。
        cur.execute(
            """
            UPDATE uhm_daily
               SET hrv_last_night_avg = :hrv_last_night_avg,
                   hrv_weekly_avg = :hrv_weekly_avg,
                   hrv_status = :hrv_status,
                   hrv_feedback = :hrv_feedback
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "hrv_last_night_avg": hrv_last_night_avg,
                "hrv_weekly_avg": hrv_weekly_avg,
                "hrv_status": hrv_status,
                "hrv_feedback": hrv_feedback,
            },
        )
        conn.commit()
    finally:
        conn.close()


def log_sync_run(
    db_path: Path,
    *,
    run_id: Optional[str] = None,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    status: str,
    range_start: Optional[str] = None,
    range_end: Optional[str] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> str:
    """Insert or update a sync_runs row.

    - If run_id is None, a new row is inserted with a generated UUID.
    - Otherwise, the existing row is updated.
    """

    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        if run_id is None:
            run_id = uuid.uuid4().hex
            started_at = started_at or _now_iso()
            cur.execute(
                """
                INSERT INTO sync_runs (
                    run_id, started_at, ended_at, status,
                    range_start, range_end, error_code, error_message,
                    driver_version, mapping_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    started_at,
                    ended_at,
                    status,
                    range_start,
                    range_end,
                    error_code,
                    error_message,
                    DRIVER_VERSION,
                    UHM_MAPPING_VERSION,
                ),
            )
        else:
            cur.execute(
                """
                UPDATE sync_runs
                   SET started_at = COALESCE(?, started_at),
                       ended_at = COALESCE(?, ended_at),
                       status = ?,
                       range_start = COALESCE(?, range_start),
                       range_end = COALESCE(?, range_end),
                       error_code = ?,
                       error_message = ?,
                       driver_version = ?,
                       mapping_version = ?
                 WHERE run_id = ?
                """,
                (
                    started_at,
                    ended_at,
                    status,
                    range_start,
                    range_end,
                    error_code,
                    error_message,
                    DRIVER_VERSION,
                    UHM_MAPPING_VERSION,
                    run_id,
                ),
            )
        conn.commit()
        return run_id
    finally:
        conn.close()

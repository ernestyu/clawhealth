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
                -- Training readiness (morning)
                training_readiness_score REAL,
                training_readiness_level TEXT,
                training_readiness_feedback TEXT,
                training_readiness_recovery_min INTEGER,
                training_readiness_acute_load REAL,
                training_readiness_hrv_factor REAL,
                training_readiness_sleep_factor REAL,
                training_readiness_stress_factor REAL,
                -- Training status & load
                training_status_code INTEGER,
                training_status_feedback TEXT,
                training_acwr_percent REAL,
                training_acwr_status TEXT,
                training_load_acute REAL,
                training_load_chronic REAL,
                training_load_acwr_ratio REAL,
                -- Endurance & fitness age
                endurance_overall_score REAL,
                endurance_classification INTEGER,
                endurance_feedback TEXT,
                fitness_age REAL,
                fitness_age_chronological REAL,
                fitness_age_achievable REAL,
                -- Sleep stages + score
                sleep_deep_min INTEGER,
                sleep_light_min INTEGER,
                sleep_rem_min INTEGER,
                sleep_awake_min INTEGER,
                sleep_score REAL,
                -- Body composition (units as provided by Garmin)
                body_fat_percent REAL,
                body_water_percent REAL,
                muscle_mass REAL,
                bone_mass REAL,
                bmi REAL,
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
        # raw sleep payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_sleep_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw body composition payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_body_composition_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw training readiness payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_training_readiness_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw training status payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_training_status_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw endurance score payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_endurance_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw fitness age payloads (single global record keyed by lastUpdated date)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_fitness_age_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw activity list payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_activities_raw (
                activity_id TEXT PRIMARY KEY,
                start_time_local TEXT,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw activity details payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_activity_details_raw (
                activity_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw menstrual dayview payloads
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_menstrual_raw (
                date_local TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            );
            """
        )
        # raw menstrual calendar payloads (range-level)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS garmin_menstrual_calendar_raw (
                range_start TEXT NOT NULL,
                range_end TEXT NOT NULL,
                payload TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                PRIMARY KEY (range_start, range_end)
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
        _ensure_columns(
            cur,
            "uhm_daily",
            {
                "sleep_deep_min": "INTEGER",
                "sleep_light_min": "INTEGER",
                "sleep_rem_min": "INTEGER",
                "sleep_awake_min": "INTEGER",
                "sleep_score": "REAL",
                "body_fat_percent": "REAL",
                "body_water_percent": "REAL",
                "muscle_mass": "REAL",
                "bone_mass": "REAL",
                "bmi": "REAL",
            },
        )
        conn.commit()
    finally:
        conn.close()


def _ensure_columns(cur: sqlite3.Cursor, table: str, columns: Dict[str, str]) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    for name, col_type in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")


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

    # Sleep stage breakdown (seconds -> minutes)
    def _sec_to_min(val: Any) -> Optional[int]:
        if isinstance(val, (int, float)):
            return int(val // 60)
        return None

    sleep_deep_min = _sec_to_min(stats.get("deepSleepSeconds"))
    sleep_light_min = _sec_to_min(stats.get("lightSleepSeconds"))
    sleep_rem_min = _sec_to_min(stats.get("remSleepSeconds"))
    sleep_awake_min = _sec_to_min(stats.get("awakeSleepSeconds"))
    sleep_score = stats.get("sleepScore")
    if isinstance(sleep_score, dict):
        sleep_score = sleep_score.get("overall") or sleep_score.get("value")

    # Body composition (units as provided by Garmin)
    body_fat_percent = stats.get("bodyFatPercentage") or stats.get("bodyFat")
    body_water_percent = stats.get("bodyWaterPercentage") or stats.get("bodyWater")
    muscle_mass = stats.get("muscleMass") or stats.get("skeletalMuscleMass")
    bone_mass = stats.get("boneMass")
    bmi = stats.get("bmi")

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
            "deepSleepSeconds",
            "lightSleepSeconds",
            "remSleepSeconds",
            "awakeSleepSeconds",
            "sleepScore",
            "sleepTimeSeconds",
            "bodyFatPercentage",
            "bodyFat",
            "bodyWaterPercentage",
            "bodyWater",
            "muscleMass",
            "skeletalMuscleMass",
            "boneMass",
            "bmi",
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
        # Sleep stages + score
        "sleep_deep_min": sleep_deep_min,
        "sleep_light_min": sleep_light_min,
        "sleep_rem_min": sleep_rem_min,
        "sleep_awake_min": sleep_awake_min,
        "sleep_score": float(sleep_score) if isinstance(sleep_score, (int, float)) else None,
        # Body composition
        "body_fat_percent": float(body_fat_percent)
        if isinstance(body_fat_percent, (int, float))
        else None,
        "body_water_percent": float(body_water_percent)
        if isinstance(body_water_percent, (int, float))
        else None,
        "muscle_mass": float(muscle_mass) if isinstance(muscle_mass, (int, float)) else None,
        "bone_mass": float(bone_mass) if isinstance(bone_mass, (int, float)) else None,
        "bmi": float(bmi) if isinstance(bmi, (int, float)) else None,
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


def _upsert_raw_generic(db_path: Path, table: str, date_str: str, payload: Dict[str, Any]) -> None:
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = {
            "date_local": date_str,
            "payload": json.dumps(payload, ensure_ascii=False),
            "ingested_at": _now_iso(),
        }
        sql = (
            f"INSERT INTO {table} (date_local, payload, ingested_at) "
            "VALUES (:date_local, :payload, :ingested_at) "
            "ON CONFLICT(date_local) DO UPDATE SET payload=excluded.payload, ingested_at=excluded.ingested_at"
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


def upsert_training_readiness_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_training_readiness_raw", date_str, payload)


def upsert_training_status_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_training_status_raw", date_str, payload)


def upsert_endurance_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_endurance_raw", date_str, payload)


def upsert_fitness_age_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_fitness_age_raw", date_str, payload)


def upsert_hrv_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    """Upsert raw HRV payload for a given local date.

    We store the exact JSON returned by get_hrv_data so that mapping can
    evolve over time without losing information.
    """

    _upsert_raw_generic(db_path, "garmin_hrv_raw", date_str, payload)


def upsert_sleep_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_sleep_raw", date_str, payload)


def upsert_body_composition_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_body_composition_raw", date_str, payload)


def upsert_menstrual_raw(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    _upsert_raw_generic(db_path, "garmin_menstrual_raw", date_str, payload)


def upsert_menstrual_calendar_raw(db_path: Path, start: str, end: str, payload: Dict[str, Any]) -> None:
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = {
            "range_start": start,
            "range_end": end,
            "payload": json.dumps(payload, ensure_ascii=False),
            "ingested_at": _now_iso(),
        }
        sql = (
            "INSERT INTO garmin_menstrual_calendar_raw (range_start, range_end, payload, ingested_at) "
            "VALUES (:range_start, :range_end, :payload, :ingested_at) "
            "ON CONFLICT(range_start, range_end) DO UPDATE SET payload=excluded.payload, ingested_at=excluded.ingested_at"
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


def ensure_daily_stub(db_path: Path, date_str: str) -> None:
    """Ensure a minimal uhm_daily row exists for date_str."""

    row = {
        "date_local": date_str,
        "ingested_at": _now_iso(),
        "source_vendor": "garmin",
        "driver_version": DRIVER_VERSION,
        "mapping_version": UHM_MAPPING_VERSION,
    }
    upsert_uhm_daily(db_path, row)


def upsert_activity_raw(db_path: Path, activity_id: str, start_time_local: str | None, payload: Dict[str, Any]) -> None:
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = {
            "activity_id": str(activity_id),
            "start_time_local": start_time_local,
            "payload": json.dumps(payload, ensure_ascii=False),
            "ingested_at": _now_iso(),
        }
        sql = (
            "INSERT INTO garmin_activities_raw (activity_id, start_time_local, payload, ingested_at) "
            "VALUES (:activity_id, :start_time_local, :payload, :ingested_at) "
            "ON CONFLICT(activity_id) DO UPDATE SET "
            "start_time_local=excluded.start_time_local, payload=excluded.payload, ingested_at=excluded.ingested_at"
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


def upsert_activity_details_raw(db_path: Path, activity_id: str, payload: Dict[str, Any]) -> None:
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        row = {
            "activity_id": str(activity_id),
            "payload": json.dumps(payload, ensure_ascii=False),
            "ingested_at": _now_iso(),
        }
        sql = (
            "INSERT INTO garmin_activity_details_raw (activity_id, payload, ingested_at) "
            "VALUES (:activity_id, :payload, :ingested_at) "
            "ON CONFLICT(activity_id) DO UPDATE SET payload=excluded.payload, ingested_at=excluded.ingested_at"
        )
        conn.execute(sql, row)
        conn.commit()
    finally:
        conn.close()


def map_sleep_into_uhm(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    """Map sleep stage breakdown into uhm_daily for date_str."""

    dto = payload.get("dailySleepDTO") or payload.get("sleepData") or payload.get("sleep") or payload
    if not isinstance(dto, dict):
        return

    def _sec_to_min(val: Any) -> Optional[int]:
        if isinstance(val, (int, float)):
            return int(val // 60)
        return None

    sleep_score = dto.get("sleepScore")
    if isinstance(sleep_score, dict):
        sleep_score = sleep_score.get("overall") or sleep_score.get("value")

    sleep_total_min = _sec_to_min(
        dto.get("sleepTimeSeconds") or dto.get("duration") or dto.get("durationInSeconds")
    )
    deep_min = _sec_to_min(dto.get("deepSleepSeconds"))
    light_min = _sec_to_min(dto.get("lightSleepSeconds"))
    rem_min = _sec_to_min(dto.get("remSleepSeconds"))
    awake_min = _sec_to_min(dto.get("awakeSleepSeconds"))

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE uhm_daily
               SET sleep_total_min = COALESCE(:sleep_total_min, sleep_total_min),
                   sleep_deep_min = :deep_min,
                   sleep_light_min = :light_min,
                   sleep_rem_min = :rem_min,
                   sleep_awake_min = :awake_min,
                   sleep_score = :sleep_score
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "sleep_total_min": sleep_total_min,
                "deep_min": deep_min,
                "light_min": light_min,
                "rem_min": rem_min,
                "awake_min": awake_min,
                "sleep_score": float(sleep_score) if isinstance(sleep_score, (int, float)) else None,
            },
        )
        conn.commit()
    finally:
        conn.close()


def _coerce_body_comp_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(entry.get("bodyComposition"), dict):
        merged = dict(entry["bodyComposition"])
        for key in (
            "weight",
            "weightKilograms",
            "bodyFatPercentage",
            "bodyWaterPercentage",
            "muscleMass",
            "skeletalMuscleMass",
            "boneMass",
            "bmi",
        ):
            if key in entry and key not in merged:
                merged[key] = entry[key]
        return merged
    return entry


def _extract_body_comp(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Try common layouts
    if "totalAverage" in payload and isinstance(payload.get("totalAverage"), dict):
        return payload["totalAverage"]
    if "dateWeightList" in payload and isinstance(payload.get("dateWeightList"), list):
        items = payload.get("dateWeightList") or []
        if len(items) == 1 and isinstance(items[0], dict):
            return _coerce_body_comp_entry(items[0])
        return {}
    if "bodyCompositions" in payload and isinstance(payload.get("bodyCompositions"), list):
        items = payload.get("bodyCompositions") or []
        if len(items) == 1 and isinstance(items[0], dict):
            return _coerce_body_comp_entry(items[0])
        return {}
    return payload


def map_body_composition_into_uhm(db_path: Path, date_str: str, payload: Dict[str, Any]) -> None:
    """Map body composition summary into uhm_daily for date_str."""

    dto = _extract_body_comp(payload)
    if not isinstance(dto, dict) or not dto:
        return

    body_fat_percent = dto.get("bodyFatPercentage") or dto.get("bodyFat")
    body_water_percent = dto.get("bodyWaterPercentage") or dto.get("bodyWater")
    muscle_mass = dto.get("muscleMass") or dto.get("skeletalMuscleMass")
    bone_mass = dto.get("boneMass")
    bmi = dto.get("bmi")
    weight_kg = dto.get("weight") or dto.get("weightKilograms") or dto.get("weight_kg")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE uhm_daily
               SET body_fat_percent = :body_fat_percent,
                   body_water_percent = :body_water_percent,
                   muscle_mass = :muscle_mass,
                   bone_mass = :bone_mass,
                   bmi = :bmi,
                   weight_kg = COALESCE(:weight_kg, weight_kg)
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "body_fat_percent": float(body_fat_percent)
                if isinstance(body_fat_percent, (int, float))
                else None,
                "body_water_percent": float(body_water_percent)
                if isinstance(body_water_percent, (int, float))
                else None,
                "muscle_mass": float(muscle_mass) if isinstance(muscle_mass, (int, float)) else None,
                "bone_mass": float(bone_mass) if isinstance(bone_mass, (int, float)) else None,
                "bmi": float(bmi) if isinstance(bmi, (int, float)) else None,
                "weight_kg": float(weight_kg) if isinstance(weight_kg, (int, float)) else None,
            },
        )
        conn.commit()
    finally:
        conn.close()


def map_training_readiness_into_uhm(db_path: Path, payload: Dict[str, Any]) -> None:
    """Map morning training readiness payload into uhm_daily.

    Expects a single dict from get_morning_training_readiness().
    """

    date_str = payload.get("calendarDate")
    if not date_str:
        return

    score = payload.get("score")
    level = payload.get("level")
    feedback_short = payload.get("feedbackShort")
    recovery_time = payload.get("recoveryTime")  # minutes
    acute_load = payload.get("acuteLoad")
    hrv_factor = payload.get("hrvFactorPercent")
    sleep_factor = payload.get("sleepHistoryFactorPercent") or payload.get("sleepScoreFactorPercent")
    stress_factor = payload.get("stressHistoryFactorPercent")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE uhm_daily
               SET training_readiness_score = :score,
                   training_readiness_level = :level,
                   training_readiness_feedback = :feedback,
                   training_readiness_recovery_min = :recovery_min,
                   training_readiness_acute_load = :acute_load,
                   training_readiness_hrv_factor = :hrv_factor,
                   training_readiness_sleep_factor = :sleep_factor,
                   training_readiness_stress_factor = :stress_factor
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "score": score,
                "level": level,
                "feedback": feedback_short,
                "recovery_min": int(recovery_time) if isinstance(recovery_time, (int, float)) else None,
                "acute_load": float(acute_load) if isinstance(acute_load, (int, float)) else None,
                "hrv_factor": float(hrv_factor) if isinstance(hrv_factor, (int, float)) else None,
                "sleep_factor": float(sleep_factor) if isinstance(sleep_factor, (int, float)) else None,
                "stress_factor": float(stress_factor) if isinstance(stress_factor, (int, float)) else None,
            },
        )
        conn.commit()
    finally:
        conn.close()


def map_training_status_into_uhm(db_path: Path, payload: Dict[str, Any]) -> None:
    """Map most recent training status into uhm_daily.

    Uses latestTrainingStatusData for the primary device.
    """

    most = payload.get("mostRecentTrainingStatus") or {}
    latest_map = most.get("latestTrainingStatusData") or {}
    if not latest_map:
        return
    device_id, dto = next(iter(latest_map.items()))
    date_str = dto.get("calendarDate")
    if not date_str:
        return

    status_code = dto.get("trainingStatus")
    feedback = dto.get("trainingStatusFeedbackPhrase")
    acute = dto.get("acuteTrainingLoadDTO") or {}
    acwr_percent = acute.get("acwrPercent")
    acwr_status = acute.get("acwrStatus")
    load_acute = acute.get("dailyTrainingLoadAcute")
    load_chronic = acute.get("dailyTrainingLoadChronic")
    load_ratio = acute.get("dailyAcuteChronicWorkloadRatio")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE uhm_daily
               SET training_status_code = :status_code,
                   training_status_feedback = :feedback,
                   training_acwr_percent = :acwr_percent,
                   training_acwr_status = :acwr_status,
                   training_load_acute = :load_acute,
                   training_load_chronic = :load_chronic,
                   training_load_acwr_ratio = :load_ratio
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "status_code": status_code,
                "feedback": feedback,
                "acwr_percent": float(acwr_percent) if isinstance(acwr_percent, (int, float)) else None,
                "acwr_status": acwr_status,
                "load_acute": float(load_acute) if isinstance(load_acute, (int, float)) else None,
                "load_chronic": float(load_chronic) if isinstance(load_chronic, (int, float)) else None,
                "load_ratio": float(load_ratio) if isinstance(load_ratio, (int, float)) else None,
            },
        )
        conn.commit()
    finally:
        conn.close()


def map_endurance_into_uhm(db_path: Path, payload: Dict[str, Any]) -> None:
    dto = (payload.get("enduranceScoreDTO") or {}).copy()
    date_str = dto.get("calendarDate") or payload.get("endDate") or payload.get("startDate")
    if not date_str:
        return

    overall = dto.get("overallScore")
    classification = dto.get("classification")
    feedback = dto.get("feedbackPhrase")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE uhm_daily
               SET endurance_overall_score = :overall,
                   endurance_classification = :classification,
                   endurance_feedback = :feedback
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "overall": float(overall) if isinstance(overall, (int, float)) else None,
                "classification": classification,
                "feedback": str(feedback) if feedback is not None else None,
            },
        )
        conn.commit()
    finally:
        conn.close()


def map_fitness_age_into_uhm(db_path: Path, payload: Dict[str, Any]) -> None:
    date_str = None
    last_updated = payload.get("lastUpdated")
    if isinstance(last_updated, str) and last_updated:
        date_str = last_updated.split("T", 1)[0]
    if not date_str:
        return

    chronological = payload.get("chronologicalAge")
    fitness_age = payload.get("fitnessAge")
    achievable = payload.get("achievableFitnessAge")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE uhm_daily
               SET fitness_age_chronological = :chronological,
                   fitness_age = :fitness_age,
                   fitness_age_achievable = :achievable
             WHERE date_local = :date_local
            """,
            {
                "date_local": date_str,
                "chronological": float(chronological) if isinstance(chronological, (int, float)) else None,
                "fitness_age": float(fitness_age) if isinstance(fitness_age, (int, float)) else None,
                "achievable": float(achievable) if isinstance(achievable, (int, float)) else None,
            },
        )
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

"""Command implementations for clawhealth CLI.

This module keeps the top-level cli.py thin by moving the command
implementations into dedicated helpers.

Phase 1: Garmin login/sync/status + daily-summary.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .uhm import (
    DRIVER_VERSION as UHM_DRIVER_VERSION,
    UHM_MAPPING_VERSION,
    _now_iso,
    ensure_schema,
    log_sync_run,
    map_garmin_daily,
    upsert_uhm_daily,
    upsert_daily_raw,
    upsert_hrv_raw,
    upsert_training_readiness_raw,
    upsert_training_status_raw,
    upsert_endurance_raw,
    upsert_fitness_age_raw,
)


def _print_json(obj: Any) -> int:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0 if obj.get("ok", True) else 1


def cmd_garmin_login(args) -> int:
    import os
    try:
        from .driver_garmin import login as garmin_login
    except Exception as exc:  # noqa: BLE001
        msg = f"Missing dependency for Garmin login: {exc}"
        if args.json:
            return _print_json({"ok": False, "error_code": "MISSING_DEP", "message": msg})
        print(f"ERROR: {msg}")
        return 2

    username = args.username or os.getenv("CLAWHEALTH_GARMIN_USERNAME")
    password_file = args.password_file or os.getenv("CLAWHEALTH_GARMIN_PASSWORD_FILE")
    config_dir_val = os.getenv("CLAWHEALTH_CONFIG_DIR", args.config_dir)
    config_dir = Path(config_dir_val).expanduser().resolve()

    if not username and not password_file:
        msg = "username and --password-file (or CLAWHEALTH_GARMIN_*) are required"
        if args.json:
            return _print_json({"ok": False, "error_code": "MISSING_CREDENTIALS", "message": msg})
        print(f"ERROR: {msg}")
        return 2

    if password_file:
        try:
            password = Path(password_file).read_text(encoding="utf-8").splitlines()[0]
        except Exception as exc:  # noqa: BLE001
            msg = f"Failed to read password file: {exc}"
            if args.json:
                return _print_json({"ok": False, "error_code": "PASSWORD_FILE_ERROR", "message": msg})
            print(f"ERROR: {msg}")
            return 2
    else:
        import os

        password = os.getenv("CLAWHEALTH_GARMIN_PASSWORD") or ""
        if not password:
            msg = "No password source found (CLAWHEALTH_GARMIN_PASSWORD_FILE or CLAWHEALTH_GARMIN_PASSWORD)"
            if args.json:
                return _print_json({"ok": False, "error_code": "MISSING_PASSWORD", "message": msg})
            print(f"ERROR: {msg}")
            return 2

    result = garmin_login(username=username, password=password, config_dir=config_dir, mfa_code=args.mfa_code)
    if not result.ok:
        payload = {"ok": False, "error_code": result.error_code or "LOGIN_FAILED", "message": result.message or "login failed"}
        if args.json:
            return _print_json(payload)
        print(f"ERROR: {payload['message']}")
        return 1

    payload = {"ok": True, "auth_state": "AUTH_OK"}
    if args.json:
        return _print_json(payload)
    print("Login successful; session saved under", config_dir)
    return 0


def cmd_garmin_sync(args) -> int:
    import os
    try:
        from .driver_garmin import fetch_daily_summary, make_client, resume_session
    except Exception as exc:  # noqa: BLE001
        msg = f"Missing dependency for Garmin sync: {exc}"
        if args.json:
            return _print_json({"ok": False, "error_code": "MISSING_DEP", "message": msg})
        print(f"ERROR: {msg}")
        return 2

    since = args.since
    until = args.until or args.since
    config_dir = Path(os.getenv("CLAWHEALTH_CONFIG_DIR", args.config_dir)).expanduser().resolve()
    db_path = Path(os.getenv("CLAWHEALTH_DB", args.db)).expanduser().resolve()

    ensure_schema(db_path)

    if not since:
        msg = "--since is required for sync"
        if args.json:
            return _print_json({"ok": False, "error_code": "MISSING_SINCE", "message": msg})
        print(f"ERROR: {msg}")
        return 2

    if not resume_session(config_dir):
        payload = {
            "ok": False,
            "error_code": "AUTH_CHALLENGE_REQUIRED",
            "message": "Session missing or expired; please run 'clawhealth garmin login' first.",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    client = make_client(config_dir)

    # Simple inclusive date loop [since, until]
    from datetime import date, timedelta

    try:
        d_start = date.fromisoformat(since)
        d_end = date.fromisoformat(until)
    except Exception:  # noqa: BLE001
        payload = {
            "ok": False,
            "error_code": "INVALID_DATE",
            "message": "Invalid date format; expected YYYY-MM-DD",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 2

    if d_end < d_start:
        payload = {
            "ok": False,
            "error_code": "INVALID_RANGE",
            "message": "--until must be >= --since",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 2

    current = d_start
    ok = True
    days_synced = []
    errors: list[dict[str, Any]] = []

    # Record sync run start
    run_id = log_sync_run(
        db_path,
        status="running",
        range_start=d_start.isoformat(),
        range_end=d_end.isoformat(),
    )

    while current <= d_end:
        d_str = current.isoformat()
        try:
            stats = fetch_daily_summary(client, d_str)
            # Store raw payload for full-fidelity access.
            upsert_daily_raw(db_path, d_str, stats)
            row = map_garmin_daily(d_str, stats)
            upsert_uhm_daily(db_path, row)
            days_synced.append(d_str)
        except Exception as exc:  # noqa: BLE001
            ok = False
            errors.append({"date": d_str, "message": str(exc)})
        current += timedelta(days=1)

    # Finish sync run
    log_sync_run(
        db_path,
        run_id=run_id,
        ended_at=_now_iso(),
        status="success" if ok else "error",
        range_start=d_start.isoformat(),
        range_end=d_end.isoformat(),
        error_code=None if ok else "SYNC_PARTIAL_ERROR",
        error_message=None if ok else json.dumps(errors, ensure_ascii=False)[:2000],
    )

    payload: dict[str, Any] = {
        "ok": ok,
        "synced_dates": days_synced,
        "errors": errors,
        "db": str(db_path),
        "driver_version": UHM_DRIVER_VERSION,
        "mapping_version": UHM_MAPPING_VERSION,
    }

    if args.json:
        return _print_json(payload)

    if ok:
        print("Sync completed.")
        print("Synced dates:", ", ".join(days_synced) or "(none)")
    else:
        print("Sync completed with errors.")
        print("Synced dates:", ", ".join(days_synced) or "(none)")
        for err in errors:
            print(f"- {err['date']}: {err['message']}")
    return 0 if ok else 1


def cmd_garmin_status(args) -> int:
    import os

    db_path = Path(os.getenv("CLAWHEALTH_DB", args.db)).expanduser().resolve()
    if not db_path.exists():
        payload = {
            "ok": False,
            "error_code": "DB_NOT_FOUND",
            "message": f"SQLite DB not found at {db_path}",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # 覆盖范围来自 uhm_daily
        cur.execute("SELECT MIN(date_local), MAX(date_local) FROM uhm_daily")
        row = cur.fetchone()
        covered_from, covered_to = row if row else (None, None)
        # 最近一次成功 sync_run
        cur.execute(
            "SELECT ended_at FROM sync_runs WHERE status = 'success' ORDER BY ended_at DESC LIMIT 1"
        )
        row2 = cur.fetchone()
        last_success_at = row2[0] if row2 else None
        # 最近一次错误
        cur.execute(
            "SELECT ended_at, error_code, error_message FROM sync_runs WHERE status = 'error' ORDER BY ended_at DESC LIMIT 1"
        )
        row3 = cur.fetchone()
        last_error = None
        if row3:
            last_error = {
                "ended_at": row3[0],
                "error_code": row3[1],
                "error_message": row3[2],
            }
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error_code": "DB_QUERY_ERROR", "message": str(exc)}
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1
    finally:
        conn.close()

    data_freshness_hours = None
    if last_success_at:
        try:
            dt = datetime.fromisoformat(last_success_at.replace("Z", "+00:00"))
            data_freshness_hours = round((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 3)
        except Exception:
            data_freshness_hours = None

    payload = {
        "ok": True,
        "covered_from": covered_from,
        "covered_to": covered_to,
        "last_success_at": last_success_at,
        "data_freshness_hours": data_freshness_hours,
        "last_error": last_error,
        "source_vendor": "garmin",
        "driver_version": UHM_DRIVER_VERSION,
        "mapping_version": UHM_MAPPING_VERSION,
    }

    if args.json:
        return _print_json(payload)

    print("Garmin health DB status:")
    print("  DB:", db_path)
    print("  Covered from:", covered_from)
    print("  Covered to  :", covered_to)
    print("  Freshness   :", f"{data_freshness_hours} h" if data_freshness_hours is not None else "unknown")
    return 0


def cmd_garmin_training_metrics(args) -> int:
    """Fetch training readiness/status/endurance/fitness-age and map into UHM.

    This reuses the existing Garmin session and updates both raw tables and
    uhm_daily fields for the relevant dates.
    """

    import os
    from garminconnect import Garmin

    config_dir = Path(os.getenv("CLAWHEALTH_CONFIG_DIR", args.config_dir)).expanduser().resolve()
    db_path = Path(os.getenv("CLAWHEALTH_DB", args.db)).expanduser().resolve()

    if not resume_session(config_dir):
        payload = {
            "ok": False,
            "error_code": "AUTH_CHALLENGE_REQUIRED",
            "message": "Session missing or expired; please run 'clawhealth garmin login' first.",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    os.environ.setdefault("GARMINTOKENS", str(config_dir))
    try:
        client = Garmin()
        client.login(tokenstore=str(config_dir))
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error_code": "AUTH_FAILED", "message": str(exc)}
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    from .uhm import (
        map_training_readiness_into_uhm,
        map_training_status_into_uhm,
        map_endurance_into_uhm,
        map_fitness_age_into_uhm,
    )

    ok = True
    details: dict[str, Any] = {}

    # Use today as default target date for training-related metrics.
    from datetime import date as _date

    today_str = _date.today().isoformat()

    # Morning training readiness
    try:
        tr = client.get_morning_training_readiness(today_str)
        calendar_date = tr.get("calendarDate") if isinstance(tr, dict) else today_str
        if calendar_date:
            upsert_training_readiness_raw(db_path, calendar_date, tr)
            map_training_readiness_into_uhm(db_path, tr)
        details["training_readiness"] = {"ok": True, "date": calendar_date}
    except Exception as exc:  # noqa: BLE001
        ok = False
        details["training_readiness"] = {"ok": False, "error": str(exc)}

    # Training status
    try:
        ts = client.get_training_status(today_str)
        # training status payload may cover multiple devices; mapping helper handles date
        upsert_training_status_raw(db_path, "most_recent", ts)
        map_training_status_into_uhm(db_path, ts)
        details["training_status"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        ok = False
        details["training_status"] = {"ok": False, "error": str(exc)}

    # Endurance score (single-day precision for today)
    try:
        es = client.get_endurance_score(today_str)
        # Use calendarDate inside DTO as key
        dto = es.get("enduranceScoreDTO") or {}
        date_key = dto.get("calendarDate") or today_str
        if date_key:
            upsert_endurance_raw(db_path, date_key, es)
            map_endurance_into_uhm(db_path, es)
        details["endurance_score"] = {"ok": True, "date": date_key}
    except Exception as exc:  # noqa: BLE001
        ok = False
        details["endurance_score"] = {"ok": False, "error": str(exc)}

    # Fitness age
    try:
        fa = client.get_fitnessage_data(today_str)
        # lastUpdated ISO date-time
        last_updated = fa.get("lastUpdated")
        date_key = last_updated.split("T", 1)[0] if isinstance(last_updated, str) else None
        if date_key:
            upsert_fitness_age_raw(db_path, date_key, fa)
            map_fitness_age_into_uhm(db_path, fa)
        details["fitness_age"] = {"ok": True, "date": date_key}
    except Exception as exc:  # noqa: BLE001
        ok = False
        details["fitness_age"] = {"ok": False, "error": str(exc)}

    payload = {
        "ok": ok,
        "db": str(db_path),
        "details": details,
    }

    if args.json:
        return _print_json(payload)

    print("Training metrics update:")
    for key, info in details.items():
        status = "OK" if info.get("ok") else "ERROR"
        extra = f"date={info.get('date')}" if info.get("date") else info.get("error", "")
        print(f"- {key}: {status} {extra}")
    return 0 if ok else 1


def cmd_garmin_hrv_dump(args) -> int:
    """Dump raw HRV JSON for a given date.

    This is intended for testers/auditors to capture real HRV payloads so
    that UHM mapping can be designed against actual data instead of guesses.
    """

    from datetime import date as _date
    import os
    from garminconnect import Garmin

    # Validate date format early
    target_date = args.date
    try:
        _date.fromisoformat(target_date)
    except Exception:  # noqa: BLE001
        payload = {"ok": False, "error_code": "INVALID_DATE", "message": f"Invalid date: {target_date}"}
        if getattr(args, "json", False):
            return _print_json(payload)
        print(f"ERROR: {payload['message']}")
        return 1

    config_dir = Path(os.getenv("CLAWHEALTH_CONFIG_DIR", args.config_dir)).expanduser().resolve()

    if not resume_session(config_dir):
        payload = {
            "ok": False,
            "error_code": "AUTH_CHALLENGE_REQUIRED",
            "message": "Session missing or expired; please run 'clawhealth garmin login' first.",
        }
        if getattr(args, "json", False):
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    # Use the same tokenstore-based login as sync
    os.environ.setdefault("GARMINTOKENS", str(config_dir))
    try:
        client = Garmin()
        client.login(tokenstore=str(config_dir))
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error_code": "AUTH_FAILED", "message": str(exc)}
        if getattr(args, "json", False):
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    try:
        raw = client.get_hrv_data(target_date)
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error_code": "HRV_FETCH_ERROR", "message": str(exc)}
        if getattr(args, "json", False):
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    # Persist raw HRV payload so that mapping can be refined over time.
    db_path = Path(os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db")).expanduser().resolve()
    upsert_hrv_raw(db_path, target_date, raw or {})

    # Also map HRV summary into UHM if a daily row already exists.
    from .uhm import map_hrv_into_uhm

    try:
        map_hrv_into_uhm(db_path, target_date)
    except Exception:
        # HRV mapping should not break the dump command; raw payload is persisted.
        pass

    out_path = getattr(args, "out", None)
    if out_path:
        out = Path(out_path).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        payload = {"ok": True, "date": target_date, "written": str(out)}
        if getattr(args, "json", False):
            return _print_json(payload)
        print(f"HRV JSON for {target_date} written to {out}")
        return 0

    # No --out: either dump raw payload or status JSON
    if getattr(args, "json", False):
        payload = {"ok": True, "date": target_date, "payload": raw}
        return _print_json(payload)

    print(json.dumps(raw, ensure_ascii=False, indent=2))
    return 0


def _load_window_rows(db_path: Path, days: int) -> list[dict[str, Any]]:
    """Load recent `days` rows from uhm_daily ordered by date_local ascending.

    This helper is used by trend-summary and flags commands.
    """

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Trend/flags 目前只用到部分字段，这里只取必要列，避免解包错位
        cur.execute(
            "SELECT date_local, sleep_total_min, rhr_bpm, steps, distance_m, calories_total, weight_kg, "
            "stress_avg, stress_max, stress_qualifier, body_battery_start, body_battery_end, "
            "hrv_last_night_avg, hrv_weekly_avg, hrv_status, hrv_feedback "
            "FROM uhm_daily ORDER BY date_local DESC LIMIT ?",
            (days,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    # Reverse to ascending date order
    result: list[dict[str, Any]] = []
    for row in reversed(rows):
        (
            date_local,
            sleep_total_min,
            rhr_bpm,
            steps,
            distance_m,
            calories_total,
            weight_kg,
            stress_avg,
            stress_max,
            stress_qualifier,
            body_battery_start,
            body_battery_end,
            hrv_last_night_avg,
            hrv_weekly_avg,
            hrv_status,
            hrv_feedback,
        ) = row
        result.append(
            {
                "date_local": date_local,
                "sleep_total_min": sleep_total_min,
                "rhr_bpm": rhr_bpm,
                "steps": steps,
                "distance_m": distance_m,
                "calories_total": calories_total,
                "weight_kg": weight_kg,
                "stress_avg": stress_avg,
                "stress_max": stress_max,
                "stress_qualifier": stress_qualifier,
                "body_battery_start": body_battery_start,
                "body_battery_end": body_battery_end,
                "hrv_last_night_avg": hrv_last_night_avg,
                "hrv_weekly_avg": hrv_weekly_avg,
                "hrv_status": hrv_status,
                "hrv_feedback": hrv_feedback,
            }
        )
    return result


def cmd_garmin_trend_summary(args) -> int:
    import os

    db_path = Path(os.getenv("CLAWHEALTH_DB", args.db)).expanduser().resolve()
    days = max(1, int(args.days or 7))

    if not db_path.exists():
        payload = {
            "ok": False,
            "error_code": "DB_NOT_FOUND",
            "message": f"SQLite DB not found at {db_path}",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    rows = _load_window_rows(db_path, days)
    if not rows:
        payload = {"ok": True, "days": days, "message": "No UHM daily data", "data": None}
        if args.json:
            return _print_json(payload)
        print("No UHM daily data in DB; run 'clawhealth garmin sync' first.")
        return 0

    # Compute simple averages over window
    def _avg(key: str) -> float | None:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not vals:
            return None
        return sum(vals) / len(vals)

    trend = {
        "window_days": len(rows),
        "from": rows[0]["date_local"],
        "to": rows[-1]["date_local"],
        "sleep_total_min_avg": _avg("sleep_total_min"),
        "rhr_bpm_avg": _avg("rhr_bpm"),
        "steps_avg": _avg("steps"),
        "distance_m_avg": _avg("distance_m"),
        "calories_total_avg": _avg("calories_total"),
        "stress_avg": _avg("stress_avg"),
        "hrv_last_night_avg": _avg("hrv_last_night_avg"),
    }

    if args.json:
        payload = {"ok": True, "days": len(rows), "trend": trend}
        return _print_json(payload)

    print(f"最近 {len(rows)} 天趋势（{rows[0]['date_local']} - {rows[-1]['date_local']}）")
    if trend["sleep_total_min_avg"] is not None:
        print(f"- 平均睡眠：{trend['sleep_total_min_avg'] / 60:.1f} 小时")
    if trend["rhr_bpm_avg"] is not None:
        print(f"- 平均静息心率：{trend['rhr_bpm_avg']:.0f} bpm")
    if trend["steps_avg"] is not None:
        print(f"- 平均步数：{trend['steps_avg']:.0f} 步")
    if trend["calories_total_avg"] is not None:
        print(f"- 平均总能量消耗：{trend['calories_total_avg']:.0f} kcal")
    if trend["stress_avg"] is not None:
        print(f"- 平均压力得分：{trend['stress_avg']:.0f}")
    if trend["hrv_last_night_avg"] is not None:
        print(f"- HRV 昨夜平均：{trend['hrv_last_night_avg']:.0f} ms")

    return 0


def cmd_garmin_flags(args) -> int:
    import os

    db_path = Path(os.getenv("CLAWHEALTH_DB", args.db)).expanduser().resolve()
    days = max(1, int(args.days or 7))

    if not db_path.exists():
        payload = {
            "ok": False,
            "error_code": "DB_NOT_FOUND",
            "message": f"SQLite DB not found at {db_path}",
        }
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

    rows = _load_window_rows(db_path, days)
    if not rows:
        payload = {"ok": True, "days": days, "message": "No UHM daily data", "flags": []}
        if args.json:
            return _print_json(payload)
        print("No UHM daily data in DB; run 'clawhealth garmin sync' first.")
        return 0

    # Helpers
    def _avg(key: str) -> float | None:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not vals:
            return None
        return sum(vals) / len(vals)

    flags: list[dict[str, Any]] = []

    # 1) Sleep low: 平均睡眠 < 6.5 小时
    sleep_avg_min = _avg("sleep_total_min")
    if sleep_avg_min is not None and sleep_avg_min < 6.5 * 60:
        flags.append(
            {
                "code": "SLEEP_LOW",
                "severity": "warning",
                "message": f"最近 {len(rows)} 天平均睡眠约 {sleep_avg_min/60:.1f} 小时（低于 6.5h）",
            }
        )

    # 2) HRV low: HRV 昨夜平均 <  baseline-ish 阈值（简单用绝对值 30ms 作为示例）
    hrv_avg = _avg("hrv_last_night_avg")
    if hrv_avg is not None and hrv_avg < 30:
        flags.append(
            {
                "code": "HRV_LOW",
                "severity": "warning",
                "message": f"最近 {len(rows)} 天 HRV 昨夜平均约 {hrv_avg:.0f} ms，略偏低",
            }
        )

    # 3) Stress high: 平均压力 > 60
    stress_avg = _avg("stress_avg")
    if stress_avg is not None and stress_avg > 60:
        flags.append(
            {
                "code": "STRESS_HIGH",
                "severity": "warning",
                "message": f"最近 {len(rows)} 天平均压力得分约 {stress_avg:.0f}，偏高",
            }
        )

    # 4) Steps low: 平均步数 < 5000
    steps_avg = _avg("steps")
    if steps_avg is not None and steps_avg < 5000:
        flags.append(
            {
                "code": "STEPS_LOW",
                "severity": "info",
                "message": f"最近 {len(rows)} 天平均步数约 {steps_avg:.0f}，偏少",
            }
        )

    payload = {
        "ok": True,
        "days": len(rows),
        "from": rows[0]["date_local"],
        "to": rows[-1]["date_local"],
        "flags": flags,
    }

    if args.json:
        return _print_json(payload)

    print(f"最近 {len(rows)} 天健康 flags（{rows[0]['date_local']} - {rows[-1]['date_local']}）：")
    if not flags:
        print("- 未检测到明显异常（基于当前简单阈值）")
        return 0
    for f in flags:
        print(f"- [{f['severity']}] {f['code']}: {f['message']}")
    return 0


def cmd_daily_summary(args) -> int:
    from datetime import date
    import os

    target_date = args.date or date.today().isoformat()
    db_default = os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db")
    db_val = getattr(args, "db", None) or db_default
    db_path = Path(db_val).expanduser().resolve()

    if not db_path.exists():
        payload = {
            "ok": False,
            "error_code": "DB_NOT_FOUND",
            "message": f"SQLite DB not found at {db_path}",
        }
        if getattr(args, "json", False):
            return _print_json(payload)
        print(f"ERROR: {payload['message']}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        # Row factory for name-based access; avoids unpacking issues as schema evolves
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT sleep_total_min, rhr_bpm, steps, distance_m, calories_total, weight_kg, "
            "stress_avg, stress_max, stress_qualifier, body_battery_start, body_battery_end, "
            "spo2_avg, spo2_lowest, respiration_avg, respiration_lowest, respiration_highest, "
            "hrv_last_night_avg, hrv_weekly_avg, hrv_status, hrv_feedback, "
            "training_readiness_score, training_readiness_level, training_readiness_feedback, "
            "training_readiness_recovery_min, training_readiness_acute_load, training_readiness_hrv_factor, "
            "training_readiness_sleep_factor, training_readiness_stress_factor, "
            "training_status_code, training_status_feedback, training_acwr_percent, training_acwr_status, "
            "training_load_acute, training_load_chronic, training_load_acwr_ratio, "
            "endurance_overall_score, endurance_classification, endurance_feedback, "
            "fitness_age, fitness_age_chronological, fitness_age_achievable, extra_metrics "
            "FROM uhm_daily WHERE date_local = ?",
            (target_date,),
        )
        row = cur.fetchone()
        if not row:
            if getattr(args, "json", False):
                return _print_json(
                    {"ok": True, "date": target_date, "message": "No UHM daily data", "data": None}
                )
            print(f"No UHM daily data for {target_date} in {db_path}")
            return 0
        r = {k: row[k] for k in row.keys()}

        sleep_total_min = r.get("sleep_total_min")
        rhr_bpm = r.get("rhr_bpm")
        steps = r.get("steps")
        distance_m = r.get("distance_m")
        calories_total = r.get("calories_total")
        weight_kg = r.get("weight_kg")
        stress_avg = r.get("stress_avg")
        stress_max = r.get("stress_max")
        stress_qualifier = r.get("stress_qualifier")
        body_battery_start = r.get("body_battery_start")
        body_battery_end = r.get("body_battery_end")
        spo2_avg = r.get("spo2_avg")
        spo2_lowest = r.get("spo2_lowest")
        respiration_avg = r.get("respiration_avg")
        respiration_lowest = r.get("respiration_lowest")
        respiration_highest = r.get("respiration_highest")
        hrv_last_night_avg = r.get("hrv_last_night_avg")
        hrv_weekly_avg = r.get("hrv_weekly_avg")
        hrv_status = r.get("hrv_status")
        hrv_feedback = r.get("hrv_feedback")
        training_readiness_score = r.get("training_readiness_score")
        training_readiness_level = r.get("training_readiness_level")
        training_readiness_feedback = r.get("training_readiness_feedback")
        training_readiness_recovery_min = r.get("training_readiness_recovery_min")
        training_readiness_acute_load = r.get("training_readiness_acute_load")
        training_readiness_hrv_factor = r.get("training_readiness_hrv_factor")
        training_readiness_sleep_factor = r.get("training_readiness_sleep_factor")
        training_readiness_stress_factor = r.get("training_readiness_stress_factor")
        training_status_code = r.get("training_status_code")
        training_status_feedback = r.get("training_status_feedback")
        training_acwr_percent = r.get("training_acwr_percent")
        training_acwr_status = r.get("training_acwr_status")
        training_load_acute = r.get("training_load_acute")
        training_load_chronic = r.get("training_load_chronic")
        training_load_acwr_ratio = r.get("training_load_acwr_ratio")
        endurance_overall_score = r.get("endurance_overall_score")
        endurance_classification = r.get("endurance_classification")
        endurance_feedback = r.get("endurance_feedback")
        fitness_age = r.get("fitness_age")
        fitness_age_chronological = r.get("fitness_age_chronological")
        fitness_age_achievable = r.get("fitness_age_achievable")
        extra_metrics_json = r.get("extra_metrics")
    finally:
        conn.close()

    if getattr(args, "json", False):
        payload = {
            "ok": True,
            "date": target_date,
            "sleep_total_min": sleep_total_min,
            "rhr_bpm": rhr_bpm,
            "steps": steps,
            "distance_m": distance_m,
            "calories_total": calories_total,
            "weight_kg": weight_kg,
            "stress_avg": stress_avg,
            "stress_max": stress_max,
            "stress_qualifier": stress_qualifier,
            "body_battery_start": body_battery_start,
            "body_battery_end": body_battery_end,
            "spo2_avg": spo2_avg,
            "spo2_lowest": spo2_lowest,
            "respiration_avg": respiration_avg,
            "respiration_lowest": respiration_lowest,
            "respiration_highest": respiration_highest,
            "hrv_last_night_avg": hrv_last_night_avg,
            "hrv_weekly_avg": hrv_weekly_avg,
            "hrv_status": hrv_status,
            "hrv_feedback": hrv_feedback,
            "training_readiness_score": training_readiness_score,
            "training_readiness_level": training_readiness_level,
            "training_readiness_feedback": training_readiness_feedback,
            "training_readiness_recovery_min": training_readiness_recovery_min,
            "training_readiness_acute_load": training_readiness_acute_load,
            "training_readiness_hrv_factor": training_readiness_hrv_factor,
            "training_readiness_sleep_factor": training_readiness_sleep_factor,
            "training_readiness_stress_factor": training_readiness_stress_factor,
            "training_status_code": training_status_code,
            "training_status_feedback": training_status_feedback,
            "training_acwr_percent": training_acwr_percent,
            "training_acwr_status": training_acwr_status,
            "training_load_acute": training_load_acute,
            "training_load_chronic": training_load_chronic,
            "training_load_acwr_ratio": training_load_acwr_ratio,
            "endurance_overall_score": endurance_overall_score,
            "endurance_classification": endurance_classification,
            "endurance_feedback": endurance_feedback,
            "fitness_age": fitness_age,
            "fitness_age_chronological": fitness_age_chronological,
            "fitness_age_achievable": fitness_age_achievable,
            "mapping_version": UHM_MAPPING_VERSION,
        }
        return _print_json(payload)

    print(f"{target_date} 健康概要（来源：Garmin，本地 {UHM_MAPPING_VERSION}）")
    if sleep_total_min is not None:
        print(f"- 睡眠：{sleep_total_min/60:.1f} 小时")
    if rhr_bpm is not None:
        print(f"- 静息心率：{rhr_bpm:.0f} bpm")
    if steps is not None:
        print(f"- 步数：{int(steps)} 步")
    if distance_m is not None:
        print(f"- 距离：{distance_m/1000:.1f} km")
    if calories_total is not None:
        print(f"- 总能量消耗：{calories_total:.0f} kcal")
    if weight_kg is not None:
        print(f"- 体重：{weight_kg:.1f} kg")
    if stress_avg is not None or stress_max is not None or stress_qualifier:
        parts = []
        if stress_avg is not None:
            parts.append(f"平均 {stress_avg}")
        if stress_max is not None:
            parts.append(f"峰值 {stress_max}")
        if stress_qualifier:
            parts.append(str(stress_qualifier))
        print("- 压力：" + "，".join(parts))
    if body_battery_start is not None or body_battery_end is not None:
        print(f"- 身体电量：起床 {body_battery_start or '?'} → 当前 {body_battery_end or '?'}")
    if spo2_avg is not None or spo2_lowest is not None:
        parts = []
        if spo2_avg is not None:
            parts.append(f"平均 {spo2_avg:.0f}%")
        if spo2_lowest is not None:
            parts.append(f"最低 {spo2_lowest:.0f}%")
        print("- 血氧：" + "，".join(parts))
    if respiration_avg is not None:
        print(f"- 呼吸频率（清醒）：{respiration_avg:.0f} 次/分钟")
    if training_readiness_score is not None or training_readiness_level:
        parts = []
        if training_readiness_score is not None:
            parts.append(f"评分 {training_readiness_score:.0f}")
        if training_readiness_level:
            parts.append(str(training_readiness_level))
        print("- 训练准备度：" + "，".join(parts))
    if training_status_code is not None or training_status_feedback:
        print(f"- 训练状态：code={training_status_code}, {training_status_feedback or ''}")
    if fitness_age is not None:
        ca = f"生理 {fitness_age_chronological:.0f} 岁" if fitness_age_chronological is not None else ""
        aa = f"可达 {fitness_age_achievable:.0f} 岁" if fitness_age_achievable is not None else ""
        print(f"- 体能年龄：当前 {fitness_age:.1f} 岁 {ca} {aa}")
    if hrv_last_night_avg is not None or hrv_status is not None:
        # HRV 以“昨夜平均 + 状态”形式展示
        parts = []
        if hrv_last_night_avg is not None:
            parts.append(f"昨夜平均 {hrv_last_night_avg:.0f} ms")
        if hrv_status:
            parts.append(f"状态：{hrv_status}")
        print("- HRV：" + "，".join(parts))

    return 0

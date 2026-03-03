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

from .driver_garmin import LoginResult, fetch_daily_summary, login as garmin_login, make_client, resume_session
from .uhm import DRIVER_VERSION as UHM_DRIVER_VERSION, UHM_MAPPING_VERSION, map_garmin_daily, upsert_uhm_daily


def _print_json(obj: Any) -> int:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0 if obj.get("ok", True) else 1


def cmd_garmin_login(args) -> int:
    import os

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

    result: LoginResult = garmin_login(username=username, password=password, config_dir=config_dir, mfa_code=args.mfa_code)
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

    since = args.since
    until = args.until or args.since
    config_dir = Path(os.getenv("CLAWHEALTH_CONFIG_DIR", args.config_dir)).expanduser().resolve()
    db_path = Path(os.getenv("CLAWHEALTH_DB", args.db)).expanduser().resolve()

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

    d_start = date.fromisoformat(since)
    d_end = date.fromisoformat(until)

    current = d_start
    ok = True
    days_synced = []
    errors: list[dict[str, Any]] = []

    while current <= d_end:
        d_str = current.isoformat()
        try:
            stats = fetch_daily_summary(client, d_str)
            row = map_garmin_daily(d_str, stats)
            upsert_uhm_daily(db_path, row)
            days_synced.append(d_str)
        except Exception as exc:  # noqa: BLE001
            ok = False
            errors.append({"date": d_str, "message": str(exc)})
        current += timedelta(days=1)

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
        cur.execute("SELECT MIN(date_local), MAX(date_local) FROM uhm_daily")
        row = cur.fetchone()
        covered_from, covered_to = row if row else (None, None)
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error_code": "DB_QUERY_ERROR", "message": str(exc)}
        if args.json:
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1
    finally:
        conn.close()

    data_freshness_hours = None
    if covered_to:
        try:
            dt = datetime.fromisoformat(covered_to + "T00:00:00+00:00")
            data_freshness_hours = round((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 3)
        except Exception:
            data_freshness_hours = None

    payload = {
        "ok": True,
        "covered_from": covered_from,
        "covered_to": covered_to,
        "data_freshness_hours": data_freshness_hours,
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


def cmd_daily_summary(args) -> int:
    from datetime import date
    import os

    target_date = args.date or date.today().isoformat()
    db_default = os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db")
    db_path = Path(getattr(args, "db", db_default)).expanduser().resolve()

    if not db_path.exists():
        print(f"ERROR: SQLite DB not found at {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sleep_total_min, rhr_bpm, steps, distance_m, calories_total, weight_kg, extra_metrics "
            "FROM uhm_daily WHERE date_local = ?",
            (target_date,),
        )
        row = cur.fetchone()
        if not row:
            print(f"No UHM daily data for {target_date} in {db_path}")
            return 0
        (
            sleep_total_min,
            rhr_bpm,
            steps,
            distance_m,
            calories_total,
            weight_kg,
            extra_metrics_json,
        ) = row
    finally:
        conn.close()

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

    return 0

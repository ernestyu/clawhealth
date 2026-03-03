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

from .driver_garmin import (
    LoginResult,
    fetch_daily_summary,
    login as garmin_login,
    make_client,
    resume_session,
)
from .uhm import (
    DRIVER_VERSION as UHM_DRIVER_VERSION,
    UHM_MAPPING_VERSION,
    _now_iso,
    ensure_schema,
    log_sync_run,
    map_garmin_daily,
    upsert_uhm_daily,
    upsert_daily_raw,
)


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

    d_start = date.fromisoformat(since)
    d_end = date.fromisoformat(until)

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
    client = Garmin()
    client.login(tokenstore=str(config_dir))

    try:
        raw = client.get_hrv_data(target_date)
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "error_code": "HRV_FETCH_ERROR", "message": str(exc)}
        if getattr(args, "json", False):
            return _print_json(payload)
        print("ERROR:", payload["message"])
        return 1

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
        cur = conn.cursor()
        cur.execute(
            "SELECT sleep_total_min, rhr_bpm, steps, distance_m, calories_total, weight_kg, extra_metrics "
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

    return 0

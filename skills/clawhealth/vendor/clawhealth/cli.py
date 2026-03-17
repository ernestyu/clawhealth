"""CLI entrypoint for clawhealth.

CLI-first design:

    clawhealth garmin login --username ... --password-file ... [--mfa-code ...]
    clawhealth garmin sync --since 2026-03-01 --until 2026-03-03
    clawhealth garmin status --json
    clawhealth garmin sleep-dump --date 2026-03-02
    clawhealth garmin body-composition --since 2026-03-01 --until 2026-03-03
    clawhealth garmin activities --since 2026-03-01 --until 2026-03-03
    clawhealth garmin activity-details --activity-id 123456789
    clawhealth daily-summary --date 2026-03-02

Garmin Phase 1 implementation will be built on top of python-garminconnect
and garth. For now, the commands are stubs and will print a clear
"not implemented" message.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import os

from .commands import (
    cmd_daily_summary as _cmd_daily_summary,
    cmd_garmin_login as _cmd_garmin_login,
    cmd_garmin_status as _cmd_garmin_status,
    cmd_garmin_sync as _cmd_garmin_sync,
)


def main(argv: list[str] | None = None) -> int:
    # Load project-level .env (if present) before parsing args, without
    # overriding existing environment variables.
    try:
        from .utils import load_project_env

        load_project_env()
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="clawhealth",
        description="Health data bridge for OpenClaw (CLI-first Garmin hub)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Provider-specific commands (starting with Garmin)
    sp_garmin = sub.add_parser("garmin", help="Garmin-related commands")
    sp_garmin_sub = sp_garmin.add_subparsers(dest="garmin_cmd", required=True)

    # garmin login
    sp_garmin_login = sp_garmin_sub.add_parser(
        "login",
        help="Perform Garmin login (username/password/MFA) and persist session (stub)",
    )
    sp_garmin_login.add_argument("--username", help="Garmin account username/email")
    sp_garmin_login.add_argument(
        "--password-file",
        help="Path to file containing password (one line)",
    )
    sp_garmin_login.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory to store Garmin session/config (default: %(default)s)",
    )
    sp_garmin_login.add_argument(
        "--mfa-code",
        help="MFA/OTP code when a challenge is required",
    )
    sp_garmin_login.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # garmin sync
    sp_garmin_sync = sp_garmin_sub.add_parser(
        "sync",
        help="Sync Garmin data into a local SQLite UHM DB (stub)",
    )
    sp_garmin_sync.add_argument("--since", help="Start date YYYY-MM-DD for sync")
    sp_garmin_sync.add_argument("--until", help="End date YYYY-MM-DD for sync")
    sp_garmin_sync.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_sync.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_sync.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # garmin status
    sp_garmin_status = sp_garmin_sub.add_parser(
        "status",
        help="Show sync status and data freshness",
    )

    # garmin trend-summary (recent days window)
    sp_garmin_trend = sp_garmin_sub.add_parser(
        "trend-summary",
        help="Show recent trend summary over a sliding window of days",
    )
    sp_garmin_trend.add_argument(
        "--days",
        type=int,
        default=7,
        help="Window size in days (default: 7)",
    )
    sp_garmin_trend.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_trend.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # garmin flags (simple health flags based on recent days)
    sp_garmin_flags = sp_garmin_sub.add_parser(
        "flags",
        help="Compute simple health flags over recent days",
    )

    # garmin training-metrics (readiness/status/endurance/fitness-age)
    sp_garmin_train = sp_garmin_sub.add_parser(
        "training-metrics",
        help="Fetch training readiness/status/endurance/fitness-age and map into UHM",
    )
    sp_garmin_train.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_train.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_train.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of human-readable text",
    )
    sp_garmin_flags.add_argument(
        "--days",
        type=int,
        default=7,
        help="Window size in days (default: 7)",
    )
    sp_garmin_flags.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_flags.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # garmin hrv-dump (internal / debugging endpoint for HRV mapping)
    sp_garmin_hrv = sp_garmin_sub.add_parser(
        "hrv-dump",
        help="Dump raw HRV JSON for a given date (for debugging/mapping)",
    )
    sp_garmin_hrv.add_argument(
        "--date",
        required=True,
        help="Target date (YYYY-MM-DD) for HRV data",
    )
    sp_garmin_hrv.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_hrv.add_argument(
        "--out",
        help="Optional path to write raw HRV JSON (default: print to stdout)",
    )
    sp_garmin_hrv.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of raw payload",
    )

    # garmin sleep-dump (sleep stages/score)
    sp_garmin_sleep = sp_garmin_sub.add_parser(
        "sleep-dump",
        help="Fetch sleep stages/score for a date and persist into DB",
    )
    sp_garmin_sleep.add_argument(
        "--date",
        required=True,
        help="Target date (YYYY-MM-DD) for sleep data",
    )
    sp_garmin_sleep.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_sleep.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_sleep.add_argument(
        "--out",
        help="Optional path to write raw sleep JSON (default: no file)",
    )
    sp_garmin_sleep.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of raw payload",
    )

    # garmin body-composition (range)
    sp_garmin_body = sp_garmin_sub.add_parser(
        "body-composition",
        help="Fetch body composition metrics for a date or range",
    )
    sp_garmin_body.add_argument(
        "--date",
        help="Target date (YYYY-MM-DD). If set, overrides --since/--until.",
    )
    sp_garmin_body.add_argument(
        "--since",
        help="Start date (YYYY-MM-DD) for body composition range",
    )
    sp_garmin_body.add_argument(
        "--until",
        help="End date (YYYY-MM-DD) for body composition range",
    )
    sp_garmin_body.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_body.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_body.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of human-readable text",
    )

    # garmin activities (list)
    sp_garmin_acts = sp_garmin_sub.add_parser(
        "activities",
        help="Fetch activity list for a date range and persist raw payloads",
    )
    sp_garmin_acts.add_argument(
        "--since",
        required=True,
        help="Start date (YYYY-MM-DD) for activities",
    )
    sp_garmin_acts.add_argument(
        "--until",
        help="End date (YYYY-MM-DD) for activities",
    )
    sp_garmin_acts.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max activities to return (default: 20)",
    )
    sp_garmin_acts.add_argument(
        "--activity-type",
        dest="activity_type",
        help="Optional activity type filter (e.g., running, cycling)",
    )
    sp_garmin_acts.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_acts.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_acts.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of human-readable text",
    )

    # garmin activity-details
    sp_garmin_act_detail = sp_garmin_sub.add_parser(
        "activity-details",
        help="Fetch full activity details by activity ID",
    )
    sp_garmin_act_detail.add_argument(
        "--activity-id",
        required=True,
        help="Garmin activityId (from activities list)",
    )
    sp_garmin_act_detail.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_act_detail.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_act_detail.add_argument(
        "--out",
        help="Optional path to write raw activity details JSON",
    )
    sp_garmin_act_detail.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of human-readable text",
    )

    # garmin menstrual (day)
    sp_garmin_mens = sp_garmin_sub.add_parser(
        "menstrual",
        help="Fetch menstrual day view for a date (if available)",
    )
    sp_garmin_mens.add_argument(
        "--date",
        required=True,
        help="Target date (YYYY-MM-DD) for menstrual data",
    )
    sp_garmin_mens.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_mens.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_mens.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of human-readable text",
    )

    # garmin menstrual-calendar (range)
    sp_garmin_mens_cal = sp_garmin_sub.add_parser(
        "menstrual-calendar",
        help="Fetch menstrual calendar range (if available)",
    )
    sp_garmin_mens_cal.add_argument(
        "--since",
        required=True,
        help="Start date (YYYY-MM-DD) for menstrual calendar",
    )
    sp_garmin_mens_cal.add_argument(
        "--until",
        help="End date (YYYY-MM-DD) for menstrual calendar",
    )
    sp_garmin_mens_cal.add_argument(
        "--config-dir",
        default=os.getenv("CLAWHEALTH_CONFIG_DIR", "/opt/clawhealth/config"),
        help="Directory with Garmin session/config (default: %(default)s)",
    )
    sp_garmin_mens_cal.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_mens_cal.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON status instead of human-readable text",
    )
    sp_garmin_status.add_argument(
        "--db",
        default=os.getenv("CLAWHEALTH_DB", "/opt/clawhealth/data/health.db"),
        help="Path to SQLite DB for UHM data (default: %(default)s)",
    )
    sp_garmin_status.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # Aggregated summaries for agents/humans
    sp_summary = sub.add_parser(
        "daily-summary",
        help="Show a summarized view of health metrics for a given date",
    )
    sp_summary.add_argument(
        "--date",
        help="Target date (YYYY-MM-DD). If omitted, implementation will choose a default",
    )
    sp_summary.add_argument(
        "--db",
        help="Path to SQLite DB for UHM data (default: CLAWHEALTH_DB or /opt/clawhealth/data/health.db)",
    )
    sp_summary.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    args = parser.parse_args(argv)

    if args.command == "garmin":
        if args.garmin_cmd == "login":
            return _cmd_garmin_login(args)
        if args.garmin_cmd == "sync":
            return _cmd_garmin_sync(args)
        if args.garmin_cmd == "status":
            return _cmd_garmin_status(args)
        if args.garmin_cmd == "trend-summary":
            from .commands import cmd_garmin_trend_summary as _cmd_garmin_trend_summary

            return _cmd_garmin_trend_summary(args)
        if args.garmin_cmd == "flags":
            from .commands import cmd_garmin_flags as _cmd_garmin_flags

            return _cmd_garmin_flags(args)
        if args.garmin_cmd == "training-metrics":
            from .commands import cmd_garmin_training_metrics as _cmd_garmin_training_metrics

            return _cmd_garmin_training_metrics(args)
        if args.garmin_cmd == "hrv-dump":
            from .commands import cmd_garmin_hrv_dump as _cmd_garmin_hrv_dump

            return _cmd_garmin_hrv_dump(args)
        if args.garmin_cmd == "sleep-dump":
            from .commands import cmd_garmin_sleep_dump as _cmd_garmin_sleep_dump

            return _cmd_garmin_sleep_dump(args)
        if args.garmin_cmd == "body-composition":
            from .commands import cmd_garmin_body_composition as _cmd_garmin_body_composition

            return _cmd_garmin_body_composition(args)
        if args.garmin_cmd == "activities":
            from .commands import cmd_garmin_activities as _cmd_garmin_activities

            return _cmd_garmin_activities(args)
        if args.garmin_cmd == "activity-details":
            from .commands import cmd_garmin_activity_details as _cmd_garmin_activity_details

            return _cmd_garmin_activity_details(args)
        if args.garmin_cmd == "menstrual":
            from .commands import cmd_garmin_menstrual as _cmd_garmin_menstrual

            return _cmd_garmin_menstrual(args)
        if args.garmin_cmd == "menstrual-calendar":
            from .commands import cmd_garmin_menstrual_calendar as _cmd_garmin_menstrual_calendar

            return _cmd_garmin_menstrual_calendar(args)

    if args.command == "daily-summary":
        return _cmd_daily_summary(args)

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

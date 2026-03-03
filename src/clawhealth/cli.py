"""CLI entrypoint for clawhealth.

CLI-first design:

    clawhealth garmin login --username ... --password-file ... [--mfa-code ...]
    clawhealth garmin sync --since 2026-03-01 --until 2026-03-03
    clawhealth garmin status --json
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

from .commands import (
    cmd_daily_summary as _cmd_daily_summary,
    cmd_garmin_login as _cmd_garmin_login,
    cmd_garmin_status as _cmd_garmin_status,
    cmd_garmin_sync as _cmd_garmin_sync,
)


def main(argv: list[str] | None = None) -> int:
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
        default="/opt/clawhealth/config",
        help="Directory to store Garmin session/config (default: /opt/clawhealth/config)",
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
        default="/opt/clawhealth/config",
        help="Directory with Garmin session/config (default: /opt/clawhealth/config)",
    )
    sp_garmin_sync.add_argument(
        "--db",
        default="/opt/clawhealth/data/health.db",
        help="Path to SQLite DB for UHM data (default: /opt/clawhealth/data/health.db)",
    )
    sp_garmin_sync.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # garmin status
    sp_garmin_status = sp_garmin_sub.add_parser(
        "status",
        help="Show sync status and data freshness (stub)",
    )
    sp_garmin_status.add_argument(
        "--db",
        default="/opt/clawhealth/data/health.db",
        help="Path to SQLite DB for UHM data (default: /opt/clawhealth/data/health.db)",
    )
    sp_garmin_status.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON instead of human-readable text",
    )

    # Aggregated summaries for agents/humans
    sp_summary = sub.add_parser(
        "daily-summary",
        help="Show a summarized view of health metrics for a given date (stub)",
    )
    sp_summary.add_argument(
        "--date",
        help="Target date (YYYY-MM-DD). If omitted, implementation will choose a default",
    )

    args = parser.parse_args(argv)

    if args.command == "garmin":
        if args.garmin_cmd == "login":
            return _cmd_garmin_login(args)
        if args.garmin_cmd == "sync":
            return _cmd_garmin_sync(args)
        if args.garmin_cmd == "status":
            return _cmd_garmin_status(args)

    if args.command == "daily-summary":
        return _cmd_daily_summary(args)

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

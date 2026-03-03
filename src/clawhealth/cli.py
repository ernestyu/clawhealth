"""CLI entrypoint for clawhealth.

Bootstrap structure only. Planned shape:

    clawhealth garmin sync --since 2026-03-01
    clawhealth daily-summary --date 2026-03-02

For now, the commands are stubs and will print a clear "not implemented"
message.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="clawhealth",
        description="Health data bridge for OpenClaw",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Provider-specific commands (starting with Garmin)
    sp_garmin = sub.add_parser("garmin", help="Garmin-related commands")
    sp_garmin_sub = sp_garmin.add_subparsers(dest="garmin_cmd", required=True)

    sp_garmin_sync = sp_garmin_sub.add_parser(
        "sync",
        help="Sync Garmin data into a local cache (stub)",
    )
    sp_garmin_sync.add_argument(
        "--since",
        help="Sync data since this date (YYYY-MM-DD). Optional; semantics TBD",
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

    if args.command == "garmin" and args.garmin_cmd == "sync":
        sys.stderr.write(
            "ERROR: 'clawhealth garmin sync' is not implemented yet. "
            "This is a bootstrap CLI; provider integration will be added later.\n"
        )
        return 2

    if args.command == "daily-summary":
        sys.stderr.write(
            "ERROR: 'clawhealth daily-summary' is not implemented yet. "
            "This will eventually summarize daily health metrics for agents.\n"
        )
        return 2

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    if os.getenv("CLAWHEALTH_RUN_INTEGRATION_TESTS") != "1":
        print("SKIP: set CLAWHEALTH_RUN_INTEGRATION_TESTS=1 to run")
        return 0

    base_dir = Path(__file__).resolve().parent
    runner = base_dir / "run_clawhealth.py"

    if not runner.exists():
        print("FAIL: run_clawhealth.py not found")
        return 2

    # Ensure required env vars exist
    if not os.getenv("CLAWHEALTH_GARMIN_USERNAME"):
        print("FAIL: CLAWHEALTH_GARMIN_USERNAME is required")
        return 2
    if not (os.getenv("CLAWHEALTH_GARMIN_PASSWORD_FILE") or os.getenv("CLAWHEALTH_GARMIN_PASSWORD")):
        print("FAIL: CLAWHEALTH_GARMIN_PASSWORD_FILE or CLAWHEALTH_GARMIN_PASSWORD is required")
        return 2

    # 1) Login (may require MFA; if NEED_MFA, exit with message)
    code, out, err = _run([sys.executable, str(runner), "garmin", "login", "--json"])
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        payload = {}

    if payload.get("error_code") == "NEED_MFA":
        print("STOP: MFA required. Run login with --mfa-code, then re-run the test.")
        return 2

    if code != 0 or not payload.get("ok", False):
        print("FAIL: login failed")
        print("stdout:", out)
        print("stderr:", err)
        return 2

    # 2) Sync last 2 days
    d_end = date.today()
    d_start = d_end - timedelta(days=1)
    code, out, err = _run(
        [
            sys.executable,
            str(runner),
            "garmin",
            "sync",
            "--since",
            d_start.isoformat(),
            "--until",
            d_end.isoformat(),
            "--json",
        ]
    )
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        payload = {}
    if code != 0 or not payload.get("ok", False):
        print("FAIL: sync failed")
        print("stdout:", out)
        print("stderr:", err)
        return 2

    # 3) Status should report coverage
    code, out, err = _run([sys.executable, str(runner), "garmin", "status", "--json"])
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        payload = {}
    if code != 0 or not payload.get("ok", False):
        print("FAIL: status failed")
        print("stdout:", out)
        print("stderr:", err)
        return 2

    print("OK: integration test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

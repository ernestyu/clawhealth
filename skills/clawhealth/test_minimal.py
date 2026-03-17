from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    runner = base_dir / "run_clawhealth.py"
    test_db = base_dir / "_test_empty.db"
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass

    if not runner.exists():
        print("FAIL: run_clawhealth.py not found")
        return 2

    # 1) CLI help should work
    env = dict(os.environ)
    env["CLAWHEALTH_DB"] = str(test_db)
    env["CLAWHEALTH_USE_VENV"] = env.get("CLAWHEALTH_USE_VENV", "1")

    proc = subprocess.run([sys.executable, str(runner), "--help"], capture_output=True, text=True, env=env)
    code, out, err = proc.returncode, proc.stdout, proc.stderr
    if code != 0:
        print("FAIL: CLI --help failed")
        print(err)
        return 2

    # 2) daily-summary should return DB_NOT_FOUND if DB missing (expected)
    proc = subprocess.run(
        [
            sys.executable,
            str(runner),
            "daily-summary",
            "--date",
            "2000-01-01",
            "--json",
        ]
        ,
        capture_output=True,
        text=True,
        env=env,
    )
    code, out, err = proc.returncode, proc.stdout, proc.stderr
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        payload = {}
    if payload.get("error_code") != "DB_NOT_FOUND":
        print("FAIL: expected DB_NOT_FOUND from daily-summary")
        print("stdout:", out)
        print("stderr:", err)
        return 2

    if code not in (0, 1):
        print("FAIL: unexpected exit code from daily-summary:", code)
        return 2

    print("OK: minimal tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

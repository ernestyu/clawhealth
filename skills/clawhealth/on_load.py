from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _in_docker() -> bool:
    try:
        if Path("/.dockerenv").exists():
            return True
        cgroup = Path("/proc/1/cgroup")
        if cgroup.exists():
            txt = cgroup.read_text(encoding="utf-8", errors="ignore")
            return any(x in txt for x in ("docker", "kubepods", "containerd"))
    except Exception:
        return False
    return False


def _missing() -> list[str]:
    missing: list[str] = []
    for mod in ("garminconnect", "garth"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return missing


def main() -> int:
    missing = _missing()
    if not missing:
        print(json.dumps({"ok": True, "status": "OK"}, ensure_ascii=False))
        return 0

    in_docker = _in_docker()
    msg_lines = [
        "Skill environment is missing Python dependencies: " + ", ".join(missing),
        "Fix:",
        f"- Run: {sys.executable} {Path(__file__).resolve().parent / 'bootstrap_deps.py'}",
    ]
    if in_docker:
        msg_lines.append("- If you are using the official OpenClaw Docker image, consider switching to 'ernestyu/openclaw-patched'.")

    payload = {
        "ok": False,
        "error_code": "ENV_MISSING_DEP",
        "missing": missing,
        "likely_docker": in_docker,
        "message": "\n".join(msg_lines),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


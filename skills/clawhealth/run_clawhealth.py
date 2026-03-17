from __future__ import annotations

import os
import sys
from pathlib import Path
import json


def _venv_python(base_dir: Path) -> Path:
    venv = base_dir / ".venv"
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _reexec_into_venv_if_present(base_dir: Path) -> None:
    if os.environ.get("CLAWHEALTH_USE_VENV", "1") not in ("1", "true", "True", "yes", "YES"):
        return
    vpy = _venv_python(base_dir)
    if not vpy.exists():
        return
    # If we're already running inside the venv, no-op.
    try:
        if Path(sys.executable).resolve() == vpy.resolve():
            return
    except Exception:
        pass
    os.execv(str(vpy), [str(vpy), str(Path(__file__).resolve()), *sys.argv[1:]])


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except Exception:
        # Best-effort only; do not block execution.
        return


def _set_skill_defaults(base_dir: Path) -> None:
    config_dir = base_dir / "config"
    db_path = base_dir / "data" / "health.db"
    os.environ.setdefault("CLAWHEALTH_CONFIG_DIR", str(config_dir))
    os.environ.setdefault("CLAWHEALTH_DB", str(db_path))


def _resolve_env_paths_relative_to_skill(base_dir: Path) -> None:
    # OpenClaw may invoke this script with a CWD that is not the skill folder.
    # Treat relative paths in env vars as relative to the skill directory.
    for key in ("CLAWHEALTH_GARMIN_PASSWORD_FILE", "CLAWHEALTH_CONFIG_DIR", "CLAWHEALTH_DB"):
        raw = os.environ.get(key)
        if not raw:
            continue
        try:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = base_dir / p
            os.environ[key] = str(p.resolve())
        except Exception:
            # Best-effort: keep raw value if resolution fails.
            continue


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


def _missing_deps() -> list[str]:
    missing: list[str] = []
    for mod in ("garminconnect", "garth"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return missing


def _truthy(v: str | None) -> bool:
    return (v or "").strip() in ("1", "true", "True", "yes", "YES", "on", "ON")


def _bootstrap_deps(base_dir: Path) -> bool:
    """Best-effort dependency bootstrap into {baseDir}/.venv."""
    import subprocess

    script = base_dir / "bootstrap_deps.py"
    if not script.exists():
        return False
    proc = subprocess.run([sys.executable, str(script)])
    return proc.returncode == 0


def _exec_into_venv(base_dir: Path) -> None:
    vpy = _venv_python(base_dir)
    if not vpy.exists():
        return
    os.execv(str(vpy), [str(vpy), str(Path(__file__).resolve()), *sys.argv[1:]])


def _audit_env_or_exit(base_dir: Path, argv: list[str]) -> None:
    # Only audit for commands that actually require third-party deps.
    if not argv:
        return
    if argv[0] != "garmin":
        return
    garmin_cmd = argv[1] if len(argv) >= 2 else ""
    if garmin_cmd in ("status", "trend-summary", "flags"):
        return

    missing = _missing_deps()
    if not missing:
        return

    likely_docker = _in_docker()
    allow_auto = _truthy(os.environ.get("CLAWHEALTH_AUTO_BOOTSTRAP", "1"))
    allow_in_docker = _truthy(os.environ.get("CLAWHEALTH_AUTO_BOOTSTRAP_IN_DOCKER", "0"))

    # Auto bootstrap: enabled by default for non-Docker installs. For Docker,
    # default is to print guidance and recommend a patched image.
    if allow_auto and (not likely_docker or allow_in_docker):
        if _bootstrap_deps(base_dir):
            _exec_into_venv(base_dir)

    msg_lines = [
        "Missing Python dependencies: " + ", ".join(missing),
        "Fix:",
        f"- Run: {sys.executable} {base_dir / 'bootstrap_deps.py'}",
    ]
    if likely_docker:
        msg_lines.append("- If you are using the official OpenClaw Docker image, consider switching to 'ernestyu/openclaw-patched'.")
        msg_lines.append("- To auto-bootstrap inside Docker (not recommended), set CLAWHEALTH_AUTO_BOOTSTRAP_IN_DOCKER=1.")

    payload = {
        "ok": False,
        "error_code": "ENV_MISSING_DEP",
        "missing": missing,
        "likely_docker": likely_docker,
        "auto_bootstrap_enabled": bool(allow_auto),
        "message": "\n".join(msg_lines),
    }

    if "--json" in argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        sys.stderr.write(payload["message"] + "\n")
    raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    base_dir = Path(__file__).resolve().parent
    _reexec_into_venv_if_present(base_dir)
    _load_env(base_dir / ".env")
    _set_skill_defaults(base_dir)
    _resolve_env_paths_relative_to_skill(base_dir)

    # Prefer vendored clawhealth module shipped with the skill (no pip install
    # needed for clawhealth itself). Third-party deps are handled via .venv.
    vendor_dir = base_dir / "vendor"
    if vendor_dir.exists():
        sys.path.insert(0, str(vendor_dir))

    try:
        _audit_env_or_exit(base_dir, argv or sys.argv[1:])
        from clawhealth.cli import main as clawhealth_main
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "clawhealth dependencies are missing.\n"
            "Run bootstrap once:\n"
            f"  {sys.executable} {base_dir / 'bootstrap_deps.py'}\n"
        )
        sys.stderr.write(f"Import error: {exc}\n")
        return 2

    return clawhealth_main(argv or sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
import sys
from pathlib import Path


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


def main(argv: list[str] | None = None) -> int:
    base_dir = Path(__file__).resolve().parent
    _reexec_into_venv_if_present(base_dir)
    _load_env(base_dir / ".env")
    _set_skill_defaults(base_dir)

    # Prefer vendored clawhealth module shipped with the skill (no pip install
    # needed for clawhealth itself). Third-party deps are handled via .venv.
    vendor_dir = base_dir / "vendor"
    if vendor_dir.exists():
        sys.path.insert(0, str(vendor_dir))

    try:
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

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


REQS = [
    "garminconnect>=0.2.1,<0.3.0",
    "garth>=0.5.0,<0.6.0",
]


def _venv_python(base_dir: Path) -> Path:
    venv_dir = base_dir / ".venv"
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    venv_dir = base_dir / ".venv"
    vpy = _venv_python(base_dir)

    if not vpy.exists():
        print("Creating venv at", venv_dir)
        venv.EnvBuilder(with_pip=True).create(venv_dir)

    print("Upgrading pip/setuptools/wheel")
    _run([str(vpy), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"])

    print("Installing dependencies:", ", ".join(REQS))
    _run([str(vpy), "-m", "pip", "install", *REQS])

    print("OK: dependencies installed. Run the skill with:")
    print(f"  {sys.executable} {base_dir / 'run_clawhealth.py'} --help")
    print("Tip: run_clawhealth.py will re-exec into .venv automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path


def main() -> int:
    base = Path(__file__).resolve().parent
    src = (base / ".." / ".." / "src" / "clawhealth").resolve()
    dst = base / "vendor" / "clawhealth"

    if not src.exists():
        print("SKIP: src/clawhealth not found; nothing to sync.")
        return 0

    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in src.glob("*.py"):
        (dst / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        copied += 1

    print(f"OK: synced {copied} files from {src} to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _read_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter start '---'")
    try:
        end_idx = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md missing frontmatter end '---'") from exc
    fm_lines = lines[1:end_idx]
    frontmatter: dict[str, str] = {}
    for line in fm_lines:
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    repo_src = (base_dir / ".." / ".." / "src" / "clawhealth").resolve()
    skill_md = base_dir / "SKILL.md"
    env_example = base_dir / "ENV.example"
    runner = base_dir / "run_clawhealth.py"
    publish_doc = base_dir / "PUBLISH.md"
    bootstrap = base_dir / "bootstrap_deps.py"
    vendor_pkg = base_dir / "vendor" / "clawhealth" / "cli.py"
    readme = base_dir / "README.md"

    _require(skill_md.exists(), "SKILL.md not found")
    _require(env_example.exists(), "ENV.example not found")
    _require(runner.exists(), "run_clawhealth.py not found")
    _require(publish_doc.exists(), "PUBLISH.md not found")
    _require(bootstrap.exists(), "bootstrap_deps.py not found")
    _require(vendor_pkg.exists(), "vendored clawhealth package not found (vendor/clawhealth/...)")
    _require(readme.exists(), "README.md not found (used for listing)")

    text = skill_md.read_text(encoding="utf-8")
    fm = _read_frontmatter(text)

    _require("name" in fm, "frontmatter missing 'name'")
    _require("description" in fm, "frontmatter missing 'description'")
    _require("metadata" in fm, "frontmatter missing 'metadata'")

    metadata_raw = fm["metadata"]
    try:
        metadata = json.loads(metadata_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("frontmatter 'metadata' must be valid single-line JSON") from exc

    requires = metadata.get("openclaw", {}).get("requires", {})
    bins = requires.get("bins", [])
    _require(isinstance(bins, list) and "python" in bins, "metadata requires bins must include 'python'")

    # Note: OpenClaw official skill metadata does not currently standardize an
    # "on_load" hook; validation is limited to required bins and packaging.

    # Validate that the vendored clawhealth module is importable.
    vendor_dir = base_dir / "vendor"
    sys.path.insert(0, str(vendor_dir))
    try:
        import clawhealth.cli  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise ValueError("vendored clawhealth module is not importable") from exc

    # If this skill lives inside the repo (src/ is present), verify vendor sync.
    if repo_src.exists():
        src_files = sorted(p for p in repo_src.glob("*.py"))
        for src_file in src_files:
            vend_file = vendor_dir / "clawhealth" / src_file.name
            _require(vend_file.exists(), f"vendored file missing: {src_file.name}")
            src_text = src_file.read_text(encoding="utf-8")
            vend_text = vend_file.read_text(encoding="utf-8")
            _require(
                src_text == vend_text,
                f"vendored file out of date: {src_file.name} (run sync_vendor.py)",
            )

    # Guard against stale vendored code: driver_garmin must support legacy
    # garminconnect signatures (tokenstore may not be accepted).
    driver_path = vendor_dir / "clawhealth" / "driver_garmin.py"
    _require(driver_path.exists(), "vendored driver_garmin.py not found")
    driver_text = driver_path.read_text(encoding="utf-8")
    _require(
        "def _supports_param" in driver_text,
        "vendored driver_garmin.py is stale (missing signature detection for login/ctor)",
    )
    _require(
        "TypeError" in driver_text and "client.login()" in driver_text,
        "vendored driver_garmin.py is stale (missing login fallback for legacy garminconnect)",
    )

    proc = subprocess.run(
        [sys.executable, str(runner), "--help"],
        capture_output=True,
        text=True,
    )
    _require(proc.returncode == 0, "CLI help failed to run via run_clawhealth.py")

    print("OK: Skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

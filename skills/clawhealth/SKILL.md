---
name: clawhealth-garmin
description: Sync Garmin Connect health summaries into local SQLite and return JSON-friendly outputs for OpenClaw.
metadata: {"openclaw":{"requires":{"bins":["python"]},"homepage":"https://github.com/ernestyu/clawhealth","tags":["health","garmin","sqlite","cli"],"on_load":"{baseDir}/on_load.py"}}
---

# clawhealth-garmin (OpenClaw Skill)

This skill connects to Garmin Connect, syncs daily health summaries into a
local SQLite database, and exposes small commands with JSON output that
OpenClaw agents can consume.

If OpenClaw reports an "audit failed" / "environment missing" error while
loading this skill, run the dependency bootstrap step in the Setup section.

## What It Does

- Login with username/password (MFA supported)
- Sync daily summary signals into SQLite
- Provide `--json` outputs for agent workflows

## Prerequisites

- Python 3.10+
- Network access to Garmin Connect
- Garmin account (may require MFA)

If you run OpenClaw in Docker, you may prefer a prepatched image that already
includes the required Python dependencies:

- `ernestyu/openclaw-patched`

## Setup

1) Create `{baseDir}/.env` (see `{baseDir}/ENV.example`).

Recommended: use `CLAWHEALTH_GARMIN_PASSWORD_FILE` (password file) rather than
`CLAWHEALTH_GARMIN_PASSWORD` (plaintext env var). If your environment supports
an MFA-only flow, password may be optional; if login fails, provide a password
file or env var.

2) Install Python dependencies (if needed):

```bash
python {baseDir}/bootstrap_deps.py
```

Notes:

- The skill ships a vendored copy of `clawhealth` under `{baseDir}/vendor/`.
- Bootstrap installs third-party deps only (`garth`, `garminconnect`) into `{baseDir}/.venv`.
- `{baseDir}/run_clawhealth.py` will automatically re-exec into the venv if present.

## Commands

Login (may return `NEED_MFA`):

```bash
python {baseDir}/run_clawhealth.py garmin login --username you@example.com --json
```

Complete MFA:

```bash
python {baseDir}/run_clawhealth.py garmin login --mfa-code 123456 --json
```

Sync:

```bash
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

Status:

```bash
python {baseDir}/run_clawhealth.py garmin status --json
```

Daily summary:

```bash
python {baseDir}/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

## Data Locations

- Tokens/config: `{baseDir}/config`
- SQLite DB: `{baseDir}/data/health.db`

Override with `CLAWHEALTH_CONFIG_DIR` and `CLAWHEALTH_DB`.

## Publish Validation

```bash
python {baseDir}/validate_skill.py
python {baseDir}/test_minimal.py
```

Optional real-account integration test:

```bash
CLAWHEALTH_RUN_INTEGRATION_TESTS=1 python {baseDir}/test_integration_optional.py
```

## Security

- Do not print or log credentials.
- Prefer a password file over plaintext env vars.
- Data stays local (SQLite + local token files).

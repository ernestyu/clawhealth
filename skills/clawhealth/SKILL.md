---
name: clawhealth-garmin
description: Sync Garmin Connect health data into local SQLite and return JSON-friendly outputs for OpenClaw.
metadata: {"openclaw":{"requires":{"bins":["python"],"env":["CLAWHEALTH_GARMIN_USERNAME","CLAWHEALTH_GARMIN_PASSWORD_FILE"]},"primaryEnv":["CLAWHEALTH_GARMIN_PASSWORD_FILE","CLAWHEALTH_GARMIN_PASSWORD"],"homepage":"https://github.com/ernestyu/clawhealth","tags":["health","garmin","sqlite","cli"]}}
---

# clawhealth-garmin (OpenClaw Skill)

This skill connects to Garmin Connect, syncs health data into a local SQLite
DB, and exposes JSON-friendly commands that OpenClaw agents can call.

## What It Does

- Login with username/password (MFA supported)
- Sync daily health summaries into SQLite (stage 1)
- Fetch HRV + training metrics via separate commands (stage 2)
- Fetch sleep stages + sleep score (stage 2)
- Fetch body composition (stage 2)
- Fetch activity lists and full activity details (stage 2)
- Fetch menstrual day view and calendar range if supported by garminconnect (experimental)
- Provide `--json` outputs for agent workflows
- Persist raw JSON payloads for later analysis

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
`CLAWHEALTH_GARMIN_PASSWORD` (plaintext env var).

Note: relative paths in env vars (like `./garmin_pass.txt`) are resolved relative
to the skill directory by `run_clawhealth.py`.

Login step 1 typically requires a password source (password file or plaintext env var).

2) Install Python dependencies (if needed):

```bash
python {baseDir}/bootstrap_deps.py
```

Notes:

- The skill ships a vendored copy of `clawhealth` under `{baseDir}/vendor/`.
- Bootstrap installs third-party deps only (`garth`, `garminconnect`) into `{baseDir}/.venv`.
- `{baseDir}/run_clawhealth.py` will automatically re-exec into the venv if present.

## Commands (Basic)

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

## Advanced Data Endpoints (Stage 2)

Garmin exposes some metrics via separate endpoints. In `clawhealth`, these are
intentionally modeled as separate commands so you can control cost, latency,
and failure modes.

### HRV (per date)

Fetch and persist raw HRV JSON, then map HRV summary fields into `uhm_daily`:

```bash
python {baseDir}/run_clawhealth.py garmin hrv-dump --date 2026-03-03 --json
```

Important:

- Run `garmin sync` for the same date first. HRV mapping updates an existing
  `uhm_daily` row; without it, HRV will remain `null` in `daily-summary`.

### Training Readiness / Status / Endurance / Fitness Age (today)

Fetch training-related metrics and map them into `uhm_daily`:

```bash
python {baseDir}/run_clawhealth.py garmin training-metrics --json
```

Important:

- This command targets "today" in the current environment.
- Run `garmin sync --since TODAY --until TODAY` first so the daily row exists.

### Sleep Stages + Sleep Score

```bash
python {baseDir}/run_clawhealth.py garmin sleep-dump --date 2026-03-03 --json
```

### Body Composition

```bash
python {baseDir}/run_clawhealth.py garmin body-composition --date 2026-03-03 --json
```

### Activities (list + details)

```bash
python {baseDir}/run_clawhealth.py garmin activities --since 2026-03-01 --until 2026-03-03 --json
python {baseDir}/run_clawhealth.py garmin activity-details --activity-id 123456789 --json
```

### Menstrual Data (experimental, requires garminconnect support)

```bash
python {baseDir}/run_clawhealth.py garmin menstrual --date 2026-03-03 --json
python {baseDir}/run_clawhealth.py garmin menstrual-calendar --since 2026-03-01 --until 2026-03-31 --json
```

## Diagnostics & Analysis

### Trend summary (window averages)

```bash
python {baseDir}/run_clawhealth.py garmin trend-summary --days 7 --json
```

### Health flags (simple warnings)

```bash
python {baseDir}/run_clawhealth.py garmin flags --days 7 --json
```

Note:

- Trend/flags are computed from `uhm_daily`. If you want HRV to be included,
  backfill HRV using `garmin hrv-dump` for the relevant dates.

## Suggested Daily Routine

Example for "today" and "yesterday":

```bash
# Stage 1: daily summaries
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-16 --until 2026-03-17 --json

# Stage 2: HRV for yesterday (per-date)
python {baseDir}/run_clawhealth.py garmin hrv-dump --date 2026-03-16 --json

# Stage 2: training metrics (today)
python {baseDir}/run_clawhealth.py garmin training-metrics --json

# Stage 2: sleep stages + body composition (yesterday)
python {baseDir}/run_clawhealth.py garmin sleep-dump --date 2026-03-16 --json
python {baseDir}/run_clawhealth.py garmin body-composition --date 2026-03-16 --json

# Diagnostics
python {baseDir}/run_clawhealth.py garmin flags --days 7 --json
python {baseDir}/run_clawhealth.py garmin trend-summary --days 7 --json
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

## Limitations (Current)

- Activity, menstrual, and body composition data are stored as raw JSON only; no
  normalized per-activity schema yet.
- Menstrual endpoints require garminconnect support; otherwise commands return `UNSUPPORTED_ENDPOINT`.
- Some metrics are only available on specific Garmin devices or account settings.
- HRV backfill is per-date (`hrv-dump`); training metrics target "today".

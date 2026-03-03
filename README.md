# clawhealth

**Languages:** English | [中文说明](README_zh.md)

`clawhealth` is a **CLI toolbox for personal health data**. It pulls
health and fitness signals from Garmin Connect into a local SQLite
database, and gives you small, composable commands that are easy for
both humans and OpenClaw agents to use.

You can think of it as a "daily health journal" backend:

- Sleep time and resting heart rate
- Steps, distance, calories
- Stress and body battery
- HRV (nightly)
- Training readiness / training status / endurance score
- Fitness age

All of this is available via simple commands like
`clawhealth daily-summary` and JSON outputs that agents can consume.

> Status: Garmin Phase 1 implemented and physically tested
> (login/sync/status/hrv-dump/daily-summary + trends/flags/training metrics).

---

## What clawhealth does (today)

For a single Garmin account, clawhealth:

- Logs in with username/password + MFA and stores a reusable session
- Syncs your daily stats into a local SQLite file
- Keeps track of when data was last synced
- Produces **one-line-per-day health summaries** for you and your agents
- Exposes simple trend and flag commands over the last N days

It does **not**:

- Send your health data anywhere else
- Run a long‑lived HTTP server by default
- Replace Garmin Connect for detailed per-activity analysis

---

## Quick start

### 1. Install (dev mode)

```bash
cd clawhealth
python -m pip install -e .
```

This will install a `clawhealth` CLI into your current Python
environment.

### 2. Configure Garmin credentials

Create a `.env` file in the repo root (or set env vars directly):

```env
CLAWHEALTH_GARMIN_USERNAME=you@example.com
CLAWHEALTH_GARMIN_PASSWORD_FILE=/path/to/garmin.pass
CLAWHEALTH_CONFIG_DIR=/opt/clawhealth/config
CLAWHEALTH_DB=/opt/clawhealth/data/health.db
```

- `CLAWHEALTH_GARMIN_PASSWORD_FILE` should point to a file whose first
  line is your Garmin password.
- The CLI will create `CLAWHEALTH_CONFIG_DIR` and `CLAWHEALTH_DB`
  directories/files as needed.

### 3. Log in with MFA

```bash
# Step 1: start login, may return NEED_MFA
clawhealth garmin login --json

# Step 2: when you see NEED_MFA, run again with the code from your app
clawhealth garmin login --mfa-code 123456 --json
```

On success you should see:

```json
{
  "ok": true,
  "auth_state": "AUTH_OK"
}
```

The session tokens are stored under `CLAWHEALTH_CONFIG_DIR` and reused
by other commands until they expire.

### 4. Sync a few days of data

```bash
clawhealth garmin sync \
  --since 2026-03-01 \
  --until 2026-03-03 \
  --json
```

This will:

- Fetch daily summaries from Garmin for each date
- Store the raw payloads in `garmin_daily_raw`
- Map them into a per‑day `uhm_daily` table
- Record the run in a `sync_runs` table for status reporting

### 5. Check sync status

```bash
clawhealth garmin status --json
```

Example output:

```json
{
  "ok": true,
  "covered_from": "2026-03-01",
  "covered_to": "2026-03-03",
  "last_success_at": "2026-03-03T20:15:00+00:00",
  "data_freshness_hours": 0.3,
  "source_vendor": "garmin",
  "driver_version": "garminconnect_v1",
  "mapping_version": "uhm_v1"
}
```

### 6. Get your daily summary

```bash
# Human-friendly summary
clawhealth daily-summary --date 2026-03-03

# JSON for agents
clawhealth daily-summary --date 2026-03-03 --json
```

Example text summary:

```text
2026-03-03 Health summary (source: Garmin, local uhm_v1)
- Sleep: 6.5 h
- Resting HR: 60 bpm
- Steps: 5030 (4.2 km)
- Total energy: 2482 kcal
- Stress: avg 47, max 97, VERY_STRESSFUL
- Body battery: wake 33 → now 5
- HRV: last night avg 40 ms, status: BALANCED
- Training readiness: score 68, MODERATE
- Fitness age: 48.7 y (chronological 50 y, achievable 43 y)
```

Example JSON (truncated):

```json
{
  "ok": true,
  "date": "2026-03-03",
  "sleep_total_min": 391,
  "rhr_bpm": 60,
  "steps": 5030,
  "distance_m": 4156.0,
  "calories_total": 2482.0,
  "stress_avg": 47,
  "body_battery_start": 33,
  "body_battery_end": 5,
  "hrv_last_night_avg": 40,
  "hrv_status": "BALANCED",
  "training_readiness_score": 68,
  "training_status_code": 5,
  "endurance_overall_score": 3464,
  "fitness_age": 48.69,
  "fitness_age_chronological": 50.0,
  "fitness_age_achievable": 43.4,
  "mapping_version": "uhm_v1"
}
```

---

## Command cheat sheet

### Garmin

```bash
# Login + MFA
clawhealth garmin login [--username ...] [--password-file ...] [--mfa-code ...] [--json]

# Sync daily data into SQLite
clawhealth garmin sync --since YYYY-MM-DD [--until YYYY-MM-DD] [--db ...] [--json]

# Check coverage and freshness
clawhealth garmin status [--db ...] [--json]

# Dump HRV JSON and map HRV summary into DB
clawhealth garmin hrv-dump --date YYYY-MM-DD [--config-dir ...] [--out ...] [--json]

# Show recent trends (last N days)
clawhealth garmin trend-summary [--days 7] [--db ...] [--json]

# Compute simple health flags over recent days
clawhealth garmin flags [--days 7] [--db ...] [--json]

# Fetch training metrics (readiness/status/endurance/fitness-age) for today
clawhealth garmin training-metrics [--config-dir ...] [--db ...] [--json]
```

### Daily summary

```bash
# Today (default)
clawhealth daily-summary [--db ...]

# Specific date
clawhealth daily-summary --date YYYY-MM-DD [--db ...] [--json]
```

For detailed CLI options, see [`CLI_HELP_SPEC.md`](CLI_HELP_SPEC.md).

---

## Configuration

The following environment variables control most behavior (all are
optional; CLI flags override them):

- `CLAWHEALTH_GARMIN_USERNAME` – Garmin username/email
- `CLAWHEALTH_GARMIN_PASSWORD_FILE` – path to a file containing the
  password on the first line
- `CLAWHEALTH_GARMIN_PASSWORD` – plain password (less recommended)
- `CLAWHEALTH_CONFIG_DIR` – where session tokens and cache live
  (default: `/opt/clawhealth/config`)
- `CLAWHEALTH_DB` – path to the SQLite DB (default:
  `/opt/clawhealth/data/health.db`)

A `.env` file in the project root will be read automatically at startup,
using `setdefault` semantics so that OS env vars always win.

---

## Where the data goes

By default clawhealth creates a SQLite database at
`/opt/clawhealth/data/health.db` with these key tables:

- `uhm_daily` – one row per local date with normalized metrics
- `garmin_daily_raw` – the raw JSON returned by `get_stats_and_body`
- `garmin_hrv_raw` – raw HRV payloads
- `garmin_training_readiness_raw` / `garmin_training_status_raw` /
  `garmin_endurance_raw` / `garmin_fitness_age_raw`
- `sync_runs` – a log of sync executions

You normally dont need to touch these tables directly; `daily-summary`,
`trend-summary`, and `flags` sit on top of them.

If you are experimenting and the schema changes, its safe to delete a
purely test `health.db` and let clawhealth recreate it on the next sync.

---

## More details

If you want to understand the internal schema and mapping logic:

- [`DESIGN.md`](DESIGN.md) – technical overview of the SQLite schema,
  mapping functions, and auth flow (garth + garminconnect).
- [`PLAN_CN.md`](PLAN_CN.md) – Chinese design/plan document with
  background, tradeoffs, and future ideas.

---

## License

MIT © Ernest Yu

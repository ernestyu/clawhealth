# clawhealth DESIGN.md – Garmin Phase 1

Status: **implemented**. This document summarizes the effective design of
clawhealth as of the Garmin Phase 1 implementation (login/sync/status/
hrv-dump/daily-summary).

---

## 1. Scope & Positioning

- **Project:** `clawhealth` – health data CLI toolbox for OpenClaw.
- **Phase 1 provider:** Garmin Connect for a single personal account.
- **Interaction style:** CLI-first, JSON-first. No long-running HTTP
  service inside clawhealth.
- **Storage:** independent SQLite DB (e.g. `/opt/clawhealth/data/health.db`),
  not mixed with Clawkb/OpenClaw internal databases.

clawhealth is responsible for:

- Authenticating against Garmin (username/password + MFA) via garth.
- Pulling daily health summaries from Garmin via `garminconnect`.
- Normalizing metrics into a simple UHM (Universal Health Metrics) schema.
- Exposing CLI commands for login, sync, status, HRV debug, and
  daily summaries (both human-readable and JSON).

Everything else (MCP tools, REST wrappers, dashboards) can be built
on top by other components.

---

## 2. Tech Stack & Dependencies

- **Language:** Python
- **Packaging:** `pyproject.toml` (project name `clawhealth`)
- **CLI entrypoint:** `clawhealth = "clawhealth.cli:main"`
- **Auth / session:** `garth>=0.5.0`
- **Data access:** `garminconnect>=0.1.53`
- **DB:** `sqlite3` (standard library)

### 2.1 Authentication flow (garth)

- We use `garth.sso.login` with `return_on_mfa=True` and
  `garth.sso.resume_login` for a **two-step, non-interactive MFA** flow.
- Intermediate MFA state is serialized to `garth_mfa_state.pkl` inside
  `CLAWHEALTH_CONFIG_DIR` using `pickle` because the client state is not
  JSON-serializable.
- On success, garth persists tokens into the tokenstore directory
  (under `config_dir`) using its own filenames (e.g. `oauth1_token.json`,
  `oauth2_token.json`).
- `garminconnect.Garmin().login(tokenstore=config_dir)` reuses these
  tokens to establish an authenticated session.

### 2.2 Data access (garminconnect)

We rely on the following methods in the installed `garminconnect`:

- `Garmin.get_stats_and_body(date_str)` – daily summary (steps, distance,
  calories, sleep, stress, body battery, etc.).
- `Garmin.get_hrv_data(date_str)` – daily HRV summary + readings for a
  given date.

No HTTP endpoints are hardcoded in clawhealth; we only use the public
methods exposed by the installed `garminconnect` version.

---

## 3. SQLite Schema (health.db)

clawhealth uses a single SQLite database file (path configurable via
`CLAWHEALTH_DB` or `--db`). Phase 1 defines three tables:

### 3.1 `uhm_daily`

Canonical per-day health summary in a simplified UHM form:

```sql
CREATE TABLE IF NOT EXISTS uhm_daily (
    date_local TEXT PRIMARY KEY,
    timezone TEXT,
    offset_to_utc_min INTEGER,
    sleep_total_min INTEGER,
    rhr_bpm REAL,
    steps INTEGER,
    distance_m REAL,
    calories_total REAL,
    weight_kg REAL,
    -- Stress metrics
    stress_avg INTEGER,
    stress_max INTEGER,
    stress_qualifier TEXT,
    -- Body Battery (estimated start/end of day)
    body_battery_start REAL,
    body_battery_end REAL,
    -- HRV metrics (ms) and status
    hrv_last_night_avg REAL,
    hrv_weekly_avg REAL,
    hrv_status TEXT,
    hrv_feedback TEXT,
    extra_metrics TEXT,
    source_vendor TEXT NOT NULL DEFAULT 'garmin',
    driver_version TEXT,
    mapping_version TEXT,
    raw_ref TEXT,
    ingested_at TEXT NOT NULL
);
```

Notes:

- `date_local` is the primary key and uses the local date semantics as
  provided by Garmin (typically the calendar date in the user's timezone).
- `extra_metrics` stores a JSON string with all non-core fields from the
  Garmin daily payload.
- `source_vendor` is currently always `'garmin'`.
- `driver_version` is set to `garminconnect_v1`; `mapping_version` is
  set to `uhm_v1` for the current mapping logic.

### 3.2 `garmin_daily_raw`

Raw daily payloads from `get_stats_and_body`:

```sql
CREATE TABLE IF NOT EXISTS garmin_daily_raw (
    date_local TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
```

Used to:

- Preserve all fields from `get_stats_and_body` for later analysis.
- Allow future UHM mapping changes without needing to re-fetch from
  Garmin.

### 3.3 `garmin_hrv_raw`

Raw HRV payloads from `get_hrv_data`:

```sql
CREATE TABLE IF NOT EXISTS garmin_hrv_raw (
    date_local TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
```

Contains:

- `hrvSummary` (with `lastNightAvg`, `weeklyAvg`, `status`, `baseline`,
  etc.).
- `hrvReadings[]` – 5-minute HRV readings across the sleep period.

### 3.4 `sync_runs`

Tracks sync executions:

```sql
CREATE TABLE IF NOT EXISTS sync_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    range_start TEXT,
    range_end TEXT,
    error_code TEXT,
    error_message TEXT,
    driver_version TEXT,
    mapping_version TEXT
);
```

- `status`: `running` | `success` | `error`.
- `range_start` / `range_end`: inclusive date range for the sync.
- `error_code` / `error_message`: summary of failures (e.g.
  `SYNC_PARTIAL_ERROR`).

---

## 4. Mapping Logic

The mapping logic lives in `clawhealth/uhm.py`.

### 4.1 Daily summary mapping (`map_garmin_daily`)

Input: `stats` dict from `Garmin.get_stats_and_body(date_str)`.

Core mappings:

- **Steps**: `steps = stats["totalSteps"] or stats["steps"]` → `steps`.
- **Distance (m)**: `distance_m = stats["totalDistanceMeters"] or stats["distance"]`.
- **Calories (kcal)**:
  - Prefer `totalKilocalories` or `wellnessKilocalories`.
  - Fallback to `totalCalories` or `calories`.
- **Resting HR (bpm)**: `restingHeartRate` or `resting_hr` → `rhr_bpm`.
- **Sleep total (min)**:
  - Prefer top-level `sleepingSeconds` (seconds → minutes).
  - Fallback to `sleep.duration` / `sleep.durationInSeconds` or
    `sleepData.*`.
- **Weight (kg)**: `weight` or `weightKilograms` or `weight_kg`.

Stress & body battery:

- `stress_avg` ← `averageStressLevel`.
- `stress_max` ← `maxStressLevel`.
- `stress_qualifier` ← `stressQualifier` (e.g. `"VERY_STRESSFUL"`).
- `body_battery_start` ← `bodyBatteryAtWakeTime`.
- `body_battery_end` ← `bodyBatteryMostRecentValue`.

All other fields are stored in `extra_metrics`.

### 4.2 HRV mapping (`map_hrv_into_uhm`)

- Reads JSON from `garmin_hrv_raw.payload` for the given `date_local`.
- Extracts `hrvSummary`:
  - `hrv_last_night_avg` ← `hrvSummary.lastNightAvg`.
  - `hrv_weekly_avg` ← `hrvSummary.weeklyAvg`.
  - `hrv_status` ← `hrvSummary.status` (e.g. `"BALANCED"`).
  - `hrv_feedback` ← `hrvSummary.feedbackPhrase`.
- Updates the corresponding row in `uhm_daily` if it exists.
- The full `hrvReadings` array remains in `garmin_hrv_raw` for future
  high-resolution analysis.

---

## 5. CLI Commands (Effective Behavior)

### 5.1 `clawhealth garmin login`

```bash
clawhealth garmin login \
  --username YOUR_EMAIL \
  --password-file /path/to/pass.txt \
  --config-dir /opt/clawhealth/config \
  [--mfa-code 123456] \
  [--json]
```

- Uses `CLAWHEALTH_GARMIN_USERNAME`, `CLAWHEALTH_GARMIN_PASSWORD_FILE`,
  `CLAWHEALTH_GARMIN_PASSWORD`, `CLAWHEALTH_CONFIG_DIR` as defaults.
- First run without `--mfa-code` may return `NEED_MFA`.
- Second run with `--mfa-code` completes login and saves tokens.

Error codes:

- `MISSING_CREDENTIALS`, `PASSWORD_FILE_ERROR`, `MISSING_PASSWORD`,
  `NEED_MFA`, `MFA_STATE_MISSING`, `LOGIN_FAILED`.

### 5.2 `clawhealth garmin sync`

```bash
clawhealth garmin sync \
  --since 2026-03-01 \
  --until 2026-03-03 \
  --config-dir /opt/clawhealth/config \
  --db /opt/clawhealth/data/health.db \
  [--json]
```

- Requires `--since` (inclusive start date); `--until` defaults to
  `--since`.
- Validates session via `resume_session(config_dir)`; if missing/expired
  returns `AUTH_CHALLENGE_REQUIRED`.
- For each day in `[since, until]`:
  - Calls `get_stats_and_body(date_str)`.
  - Writes raw payload into `garmin_daily_raw`.
  - Maps into `uhm_daily` via `map_garmin_daily`.
- Records the sync in `sync_runs` with `status="running"` then
  `"success"` or `"error"`.

### 5.3 `clawhealth garmin status`

```bash
clawhealth garmin status --db /opt/clawhealth/data/health.db --json
```

JSON output includes:

- `covered_from` / `covered_to` from `uhm_daily` date range.
- `last_success_at` from the latest `sync_runs` row with
  `status='success'`.
- `data_freshness_hours` calculated as time since `last_success_at`.
- `last_error` from the latest `sync_runs` row with `status='error'`.

### 5.4 `clawhealth garmin hrv-dump`

```bash
clawhealth garmin hrv-dump \
  --date 2026-03-02 \
  --config-dir /opt/clawhealth/config \
  [--out /tmp/garmin_hrv_2026-03-02.json] \
  [--json]
```

- Validates session and calls `Garmin.get_hrv_data(date)`.
- Persists the raw payload into `garmin_hrv_raw` and immediately calls
  `map_hrv_into_uhm` to update HRV fields in `uhm_daily` for that date.
- If `--out` is provided, writes raw JSON to the given path.
- `--json` controls whether to print raw payload vs a status envelope.

### 5.5 `clawhealth daily-summary`

```bash
clawhealth daily-summary \
  --date 2026-03-02 \
  --db /opt/clawhealth/data/health.db \
  [--json]
```

- Reads `uhm_daily` for the given `date_local`.
- If `--json`:
  - Returns a JSON object with all core metrics:

    ```json
    {
      "ok": true,
      "date": "2026-03-02",
      "sleep_total_min": 391,
      "rhr_bpm": 60,
      "steps": 5030,
      "distance_m": 4156.0,
      "calories_total": 2482.0,
      "weight_kg": null,
      "stress_avg": 47,
      "stress_max": 97,
      "stress_qualifier": "VERY_STRESSFUL",
      "body_battery_start": 33,
      "body_battery_end": 5,
      "hrv_last_night_avg": 40,
      "hrv_weekly_avg": 35,
      "hrv_status": "BALANCED",
      "hrv_feedback": "HRV_BALANCED_7",
      "mapping_version": "uhm_v1"
    }
    ```

- If no `--json`:
  - Prints a concise Chinese summary suitable for daily logs, e.g.:

    ```text
    2026-03-02 健康概要（来源：Garmin，本地 uhm_v1）
    - 睡眠：6.5 小时
    - 静息心率：60 bpm
    - 步数：5030 步
    - 距离：4.2 km
    - 总能量消耗：2482 kcal
    - 体重：--（暂无称重数据）
    - 压力：平均 47，峰值 97，VERY_STRESSFUL
    - 身体电量：起床 33 → 当前 5
    - HRV：昨夜平均 40 ms，状态：BALANCED
    ```

---

## 6. Environment & Configuration

Key environment variables (also documented in `ENV.example`):

- `CLAWHEALTH_GARMIN_USERNAME`
- `CLAWHEALTH_GARMIN_PASSWORD_FILE`
- `CLAWHEALTH_GARMIN_PASSWORD` (optional, less recommended)
- `CLAWHEALTH_CONFIG_DIR` (defaults to `/opt/clawhealth/config`)
- `CLAWHEALTH_DB` (defaults to `/opt/clawhealth/data/health.db`)

The project-level `.env` (loaded via `load_project_env()`) can set
defaults, but **OS environment variables always win** (we use
`os.environ.setdefault`).

---

## 7. Migration & Compatibility Notes

- Phase 1 is still in early adoption; the schema may evolve.
- For now, the recommended approach when upgrading early versions is:
  - If `health.db` is small and purely experimental, consider deleting
    it and letting clawhealth recreate it with the latest schema.
  - If you have valuable historical data, dump tables to CSV/JSON before
    upgrading and plan a manual migration.
- Future versions may include explicit migration helpers that
  auto-detect missing columns and apply `ALTER TABLE` statements.

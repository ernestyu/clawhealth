# clawhealth

**Languages:** English | [Chinese](README_zh.md)

`clawhealth` is a Python package and CLI that bridges health data (starting
with Garmin Connect) into a local **SQLite** database and exposes
**JSON‑friendly commands**. It is designed to be:

- A **CLI‑first** health hub: `clawhealth garmin ...` / `clawhealth daily-summary ...`
- A stable **data layer** for OpenClaw agents and other automation
- A foundation for future vendors (`garmin`, `huami`, `xiaomi`, ...)

The same core is also used by the OpenClaw skill
`skills/clawhealth-garmin/`, but the Python package itself is the primary
entrypoint.

---

## Installation (Python package / CLI)

Requirements:

- Python 3.10+

Install from PyPI:

```bash
python -m pip install --upgrade pip  # optional but recommended
python -m pip install clawhealth
```

After installation, you should have a `clawhealth` command:

```bash
clawhealth --help
```

Typical help output:

```text
usage: clawhealth [-h] {garmin,daily-summary} ...

Health data bridge for OpenClaw (CLI-first Garmin hub)

positional arguments:
  {garmin,daily-summary}
    garmin          Garmin-related commands
    daily-summary   Show a summarized view of health metrics for a given date

options:
  -h, --help        show this help message and exit
```

---

## Quickstart: Garmin → SQLite → JSON

### 1. Configure credentials

`clawhealth` uses the official Garmin Connect login flow via
[`garminconnect`](https://github.com/cyberjunky/python-garminconnect).

The CLI expects your Garmin email + password. Two common patterns:

1. **Environment variables / .env** (when running under a process manager)
2. **Password file** (when embedding into a skill environment)

Example (environment variables + password file):

```bash
export CLAWHEALTH_GARMIN_USERNAME="you@example.com"
export CLAWHEALTH_GARMIN_PASSWORD_FILE="/secure/path/garmin_pass.txt"

# Or pass explicitly on the CLI
clawhealth garmin login \
  --username you@example.com \
  --password-file /secure/path/garmin_pass.txt \
  --json
```

> Do **not** commit password files to git. Protect them with file
> permissions (e.g. `chmod 600`).

### 2. Login (with MFA)

Login is usually a two‑step process:

```bash
# Step 1: trigger login + MFA challenge
clawhealth garmin login --json

# Step 2: submit the MFA code you received
clawhealth garmin login --mfa-code 123456 --json
```

On success, `clawhealth` caches a Garmin session token under a local
config directory (the path is included in the JSON response). Subsequent
commands do not need the password again.

### 3. Sync data into SQLite

`clawhealth` maintains a local health SQLite database using a UHM schema.

For example, sync three days of data:

```bash
clawhealth garmin sync --since 2026-03-17 --until 2026-03-19 --json
```

The JSON response includes:

- `ok`: whether the sync succeeded
- `synced_dates`: list of dates actually synced
- `db`: path to the SQLite DB (e.g. `.../data/health.db`)

### 4. Query a daily summary (for agents/automation)

After syncing, you can request a summarized view of health metrics for a
specific date:

```bash
clawhealth daily-summary --date 2026-03-19 --json
```

Example output (simplified):

```json
{
  "ok": true,
  "date": "2026-03-19",
  "sleep_total_min": 403,
  "rhr_bpm": 58,
  "steps": 4237,
  "distance_m": 3299.0,
  "calories_total": 1746.0,
  "stress_avg": 42,
  "stress_max": 96,
  "body_battery_start": 43.0,
  "body_battery_end": 5.0,
  "spo2_avg": 98.0,
  "mapping_version": "uhm_v1"
}
```

This JSON structure is designed for agents and automation: stable
fields, ready to feed into an LLM or an external data warehouse.

---

## Command overview

Core commands (CLI + agent):

- `clawhealth daily-summary --date YYYY-MM-DD --json`
- `clawhealth garmin sync --since YYYY-MM-DD --until YYYY-MM-DD --json`

Advanced commands (on demand):

- `clawhealth garmin training-metrics --json`
- `clawhealth garmin sleep-dump --date YYYY-MM-DD --json`
- `clawhealth garmin body-composition --date YYYY-MM-DD --json`
- `clawhealth garmin activities --since ... --until ... --json`
- `clawhealth garmin activity-details --activity-id 123456789 --json`
- `clawhealth garmin hrv-dump --date YYYY-MM-DD --json`
- `clawhealth garmin menstrual --date YYYY-MM-DD --json`
- `clawhealth garmin menstrual-calendar --since ... --until ... --json`

> Some metrics depend on your device model and Garmin account settings
> (e.g. sleep stages, body composition, menstrual tracking).

---

## Security model

- All logic runs locally.
- Garmin credentials and tokens stay on your machine.
- The SQLite DB is local (its path is included in JSON responses).
- Strongly recommend using a password manager or `.env` files for
  secrets; avoid hard‑coding passwords in scripts.

---

## Using `clawhealth` as an OpenClaw skill

If you use OpenClaw and want to interact with Garmin health data via
Telegram or other chat surfaces, you can use the bundled skill:

- Directory: `skills/clawhealth-garmin/`
- Docs: `skills/clawhealth-garmin/SKILL.md` / `SKILL_zh.md`
- ClawHub slug: `clawhealth-garmin`

Typical installation via ClawHub:

```bash
npx clawhub@latest install clawhealth-garmin --force
```

After installation, OpenClaw will load the skill from
`<workspace>/skills/clawhealth-garmin`. Detailed `.env`/password/MFA
configuration lives in the SKILL docs under that directory.

> In short: **root README = Python package / CLI docs.**
> Skill README/SKILL = OpenClaw integration details.

---

## Roadmap

See `ROADMAP.md` for planned vendors (e.g. Huami/Xiaomi) and schema
extensions.

---

## License

Apache-2.0

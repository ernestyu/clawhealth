# clawhealth

**Languages:** English | [Chinese](README_zh.md)

`clawhealth` is the Garmin-to-SQLite health sync engine used by the OpenClaw
skill `clawhealth-garmin`.

It logs into Garmin Connect (supports MFA), syncs daily health summaries
into a local SQLite database, and exposes small JSON-friendly commands
that OpenClaw agents can call.

## OpenClaw Quick Start

### 1) Install the skill

After publishing to ClawHub:

```bash
openclaw skill install clawhealth-garmin
```

Local development from this repo:

```bash
openclaw skill install --path skills/clawhealth
```

Manual install from GitHub (clone + path install):

```bash
cd ~/.openclaw/workspace
git clone https://github.com/ernestyu/clawhealth.git
cd clawhealth
openclaw skill install --path skills/clawhealth
```

### 2) Configure credentials

Create `skills/clawhealth/.env` based on `skills/clawhealth/ENV.example`.

Recommended: use a password file (`CLAWHEALTH_GARMIN_PASSWORD_FILE`) rather
than putting the password directly into an environment variable. Some setups
can complete login via an MFA-only flow; if login fails, provide a password
file/env var.

### 3) Install Python dependencies (if needed)

If your OpenClaw environment does not already include `garminconnect` and
`garth`, run:

```bash
python skills/clawhealth/bootstrap_deps.py
```

This creates `skills/clawhealth/.venv` and installs the required Python
packages. `run_clawhealth.py` will automatically re-exec into that venv.

Note: the skill ships a vendored copy of `clawhealth` itself under
`skills/clawhealth/vendor/`, so you do not need to `pip install clawhealth`
just to use the skill.

### 4) Login, sync, and query

Login (may return `NEED_MFA`):

```bash
python skills/clawhealth/run_clawhealth.py garmin login --username you@example.com --json
```

Complete MFA:

```bash
python skills/clawhealth/run_clawhealth.py garmin login --mfa-code 123456 --json
```

Sync a date range:

```bash
python skills/clawhealth/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

Daily summary:

```bash
python skills/clawhealth/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

## Docker (Patched Image)

If you run OpenClaw via Docker, you may prefer a prepatched image that
already includes the Python dependencies used by this skill:

- Docker image: `ernestyu/openclaw-patched`
- One-click installer/launcher: `https://github.com/ernestyu/openclaw-launcher`

## Data & Security Notes

- The SQLite DB path is controlled by `CLAWHEALTH_DB` (default in the skill:
  `skills/clawhealth/data/health.db`).
- Garmin session tokens are stored under `CLAWHEALTH_CONFIG_DIR` (default in the
  skill: `skills/clawhealth/config`).
- `clawhealth` does not upload your health data to any third-party service; it
  stores data locally.

## Standalone CLI (Developer Mode)

If you want to run outside OpenClaw:

```bash
python -m pip install -e .
clawhealth --help
```

## License

MIT

## Roadmap

See `ROADMAP.md`.

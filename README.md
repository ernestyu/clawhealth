# clawhealth

**Languages:** English | [Chinese](README_zh.md)

`clawhealth` is an OpenClaw-first Garmin Connect sync tool. It logs in (MFA
supported), syncs health data into a local SQLite DB, and provides JSON-friendly
commands that OpenClaw agents can call.

The primary deliverable of this repo is the OpenClaw skill at `skills/clawhealth/`.

## What It Can Do

- Login with Garmin username/password (MFA supported)
- Sync daily health summaries into SQLite (steps, sleep total, stress, body battery, SpO2, respiration, weight)
- Fetch sleep stages + sleep score (`garmin sleep-dump`)
- Fetch HRV (`garmin hrv-dump`) and training readiness/status/endurance/fitness age (`garmin training-metrics`)
- Fetch body composition metrics (`garmin body-composition`)
- Fetch activity lists and full activity details (`garmin activities`, `garmin activity-details`)
- Fetch menstrual day view and calendar range if supported by garminconnect and enabled on the account (experimental)
- Produce JSON outputs for agent workflows
- Store raw JSON payloads in SQLite for full-fidelity access

Notes:

- Some metrics depend on your Garmin device and account settings (e.g., sleep stages, body composition, menstrual data).
- Menstrual endpoints require garminconnect support; if missing, the command returns `UNSUPPORTED_ENDPOINT`.

## OpenClaw (Primary)

### Step 1: Install the skill

OpenClaw loads skills from `<workspace>/skills` (highest precedence) and
`~/.openclaw/skills` (shared/local). You can install this skill in two ways.

Scenario A: Install via ClawHub CLI (recommended, once published):

```bash
npm i -g clawhub
clawhub install clawhealth-garmin
```

Scenario B: Install from GitHub source (physical placement under your workspace):

```bash
git clone https://github.com/ernestyu/clawhealth.git /home/node/.openclaw/workspace/clawhealth_temp
mv /home/node/.openclaw/workspace/clawhealth_temp/skills/clawhealth /home/node/.openclaw/workspace/skills/
rm -rf /home/node/.openclaw/workspace/clawhealth_temp
```

### Step 2: Dependencies on first run

Native OpenClaw (non-Docker):
- `run_clawhealth.py` tries to auto-bootstrap Python deps into `skills/clawhealth/.venv` on the first Garmin command.
- Disable auto-bootstrap with `CLAWHEALTH_AUTO_BOOTSTRAP=0`.

Docker OpenClaw:
- Recommended: use `ernestyu/openclaw-patched` (deps preinstalled).
- If you stay on the official image, run `python skills/clawhealth/bootstrap_deps.py` inside the container
  (or set `CLAWHEALTH_AUTO_BOOTSTRAP_IN_DOCKER=1` to allow auto-bootstrap).

### Step 3: Configure username + password

You have two ways to configure credentials:

- Let OpenClaw write the files for you:
  Create `skills/clawhealth/.env` and a password file under `skills/clawhealth/` (see `skills/clawhealth/ENV.example`).
- Configure from a terminal (example for a running container):

```bash
docker exec -it openclaw sh -c '
cd ~/.openclaw/workspace/skills/clawhealth &&
printf "CLAWHEALTH_GARMIN_USERNAME=you@example.com\nCLAWHEALTH_GARMIN_PASSWORD_FILE=./garmin_pass.txt\n" > .env &&
printf "YOUR_GARMIN_PASSWORD" > garmin_pass.txt &&
chmod 600 .env garmin_pass.txt &&
echo "Configuration completed. Return to your chat UI and trigger login."
'
```

Notes:

- Relative paths in env vars (like `./garmin_pass.txt`) are resolved relative to the skill directory by `run_clawhealth.py`.
- Keep `.env` and password files out of git and protect file permissions.

### Step 4: Login (MFA) and sync

Login step 1 (triggers MFA, requires username + password source):

```bash
python skills/clawhealth/run_clawhealth.py garmin login --username you@example.com --json
```

Login step 2 (submit MFA code):

```bash
python skills/clawhealth/run_clawhealth.py garmin login --mfa-code 123456 --json
```

Sync and query:

```bash
python skills/clawhealth/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

### Optional: Advanced endpoints

Menstrual endpoints are experimental and require garminconnect support.

```bash
python skills/clawhealth/run_clawhealth.py garmin sleep-dump --date 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin body-composition --date 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin activities --since 2026-03-01 --until 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin activity-details --activity-id 123456789 --json
python skills/clawhealth/run_clawhealth.py garmin menstrual --date 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin menstrual-calendar --since 2026-03-01 --until 2026-03-31 --json
```

## Not Using OpenClaw (Secondary)

If you want to run the CLI directly:

```bash
python -m pip install -e .
clawhealth --help
```

## Roadmap

See `ROADMAP.md`.

## License

MIT

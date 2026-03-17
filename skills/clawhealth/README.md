# clawhealth-garmin (OpenClaw Skill)

This skill syncs Garmin Connect daily health summaries into a local SQLite
database and exposes JSON-friendly commands for OpenClaw agents.

## Quick Start

1) Configure `CLAWHEALTH_GARMIN_USERNAME` and password file in `.env`.

Use `ENV.example` in this folder as a template.

2) Install Python dependencies (if needed):

```bash
python {baseDir}/bootstrap_deps.py
```

The skill includes a vendored copy of `clawhealth` under `{baseDir}/vendor/`.
Bootstrap only installs third-party dependencies (`garth`, `garminconnect`).

3) Login (MFA supported):

```bash
python {baseDir}/run_clawhealth.py garmin login --json
python {baseDir}/run_clawhealth.py garmin login --mfa-code 123456 --json
```

4) Sync:

```bash
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

## Data Paths

- Tokens/config: `{baseDir}/config`
- SQLite DB: `{baseDir}/data/health.db`

## Docs

- Skill instructions: `SKILL.md`
- Publish checklist: `PUBLISH.md`

## Docker

If you run OpenClaw in Docker, you may prefer a prepatched image that already
includes the Python dependencies:

- `ernestyu/openclaw-patched`
- `https://github.com/ernestyu/openclaw-launcher`

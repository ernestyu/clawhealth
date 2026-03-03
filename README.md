# clawhealth

**Languages:** English | [中文说明](README_zh.md)

Health data CLI toolbox for OpenClaw.

`clawhealth` pulls health and fitness data from external providers
(starting with Garmin) into a local SQLite database and exposes
**CLI-first workflows** that are easy for both humans and agents to use.
The primary goal is to let your OpenClaw agents understand your daily
sleep, training load, and recovery trends based on real signals rather
than guesswork.

> Status: design-in-progress. CLI shape and technical route are defined;
> Garmin Phase 1 implementation is next.

---

## Vision

- **Single health hub (CLI-first)**: aggregate data from multiple
  providers (Garmin first) behind a single, scriptable command-line
  interface.
- **Local-first, privacy-aware**: raw data and SQLite live on your
  machine; agents primarily consume derived summaries (e.g. daily stats),
  not full raw timeseries, unless you explicitly ask for them.
- **OpenClaw-native**: outputs are designed to drop directly into
  OpenClaw prompts, daily logs, and long-term planning workflows.

For a detailed technical plan (in Chinese), see
[`PLAN_CN.md`](PLAN_CN.md).

---

## CLI overview (planned Garmin Phase 1)

```bash
# 1) Login (username/password/MFA), persist session tokens
clawhealth garmin login \
  --username YOUR_EMAIL \
  --password-file /path/to/pass.txt \
  --config-dir /opt/clawhealth/config \
  [--mfa-code 123456] \
  [--json]

# 2) Sync Garmin data into a local SQLite UHM database
clawhealth garmin sync \
  --since 2026-03-01 \
  --until 2026-03-03 \
  --config-dir /opt/clawhealth/config \
  --db /opt/clawhealth/data/health.db \
  [--json]

# 3) Check sync status and data freshness
clawhealth garmin status \
  --db /opt/clawhealth/data/health.db \
  [--json]

# 4) Get a human/agent-friendly daily summary
clawhealth daily-summary \
  --date 2026-03-02 \
  --db /opt/clawhealth/data/health.db
```

All commands are designed to be:

- **Script-friendly**: machine-readable JSON under `--json`.
- **Agent-friendly**: clear error codes (e.g. `NEED_MFA`,
  `AUTH_CHALLENGE_REQUIRED`) instead of free-form error messages.

---

## Packaging & CLI

This project uses `pyproject.toml` as its packaging configuration:

- Project name: `clawhealth`.
- Version: kept in `pyproject.toml` and `clawhealth/__init__.py`.
- CLI entrypoint: defined via `[project.scripts]` as
  `clawhealth = "clawhealth.cli:main"`.

For development installs:

```bash
cd clawhealth
python -m pip install -e .

# After that
clawhealth garmin login --help
clawhealth garmin sync --help
clawhealth daily-summary --help
```

---

## License

MIT © Ernest Yu

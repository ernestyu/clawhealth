# Roadmap

This roadmap describes likely next steps for `clawhealth` (Garmin + OpenClaw
skill) and is intentionally lightweight. Priorities may change as upstream
APIs and OpenClaw skill requirements evolve.

## Near Term

- Document the local OpenClaw install flow (no ClawHub).
- Add basic CI checks (run skill validation + minimal tests).
- Improve dependency/bootstrap UX for non-Docker (better error messages and retries).
- Expand docs for OpenClaw sandbox/Docker setups.

## Medium Term

- Schema migrations for SQLite (`ALTER TABLE` helpers, versioned migrations).
- Better date/timezone handling (explicit timezone fields and conversions).
- More metrics coverage (SpO2, respiration, stress breakdown, training load details).
- Export helpers (CSV/JSON export per date range).

## Longer Term

- Split providers into separate skills (e.g. `skills/clawhealth-garmin/`, `skills/clawhealth-huami/`).
- Additional providers (TBD): Fitbit/Apple Health/Google Fit/Oura/Whoop.
- Per-activity ingestion and summaries (beyond daily rollups).
- Optional MCP or REST wrapper on top of the SQLite DB (kept out of the core by default).

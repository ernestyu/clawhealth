# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to
Semantic Versioning.

## [Unreleased]

### Added
- OpenClaw Skill packaging (`skills/clawhealth/`).
- Skill validation and minimal test scripts.
- Publish checklist and release template.

### Changed
- Python dependencies now include upper bounds for stability.

### Fixed
- Removed duplicate `upsert_hrv_raw` definition.
- Added date range validation in `garmin sync`.

## [0.0.1] - 2026-03-03

### Added
- Garmin Phase 1 CLI (login/sync/status/hrv-dump/daily-summary).
- SQLite UHM schema and mapping helpers.

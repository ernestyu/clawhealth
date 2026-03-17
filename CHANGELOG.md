# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to
Semantic Versioning.

## [Unreleased]

- Renamed the OpenClaw skill folder to `skills/clawhealth-garmin/` for consistency with the skill name.
- Removed ClawHub publish/install references from docs (local GitHub install is the supported path).
- Updated `garminconnect` dependency to `>=0.2.1,<0.3.0` to align with garth/token-based auth.

## [0.1.0] - 2026-03-17

### Added
- OpenClaw skill packaging (`skills/clawhealth-garmin/`).
- Skill validation and minimal test scripts.
- Release checklist and release template.
- Stage 2 endpoints: sleep-dump, body-composition, activities, activity-details, menstrual, menstrual-calendar.
- Raw tables for sleep/body composition/activity/menstrual payloads.
- Daily summary now includes sleep stages/score and body composition fields.
- A `.clawhubignore` file to help avoid accidentally packaging local secrets/caches.

### Changed
- Python dependencies now include upper bounds for stability.
- Documentation updated with advanced endpoints and OpenClaw-first feature list.

### Fixed
- Removed duplicate `upsert_hrv_raw` definition.
- Added date range validation in `garmin sync`.

## [0.0.1] - 2026-03-03

### Added
- Garmin Phase 1 CLI (login/sync/status/hrv-dump/daily-summary).
- SQLite UHM schema and mapping helpers.

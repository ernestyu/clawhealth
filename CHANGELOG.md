# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to
Semantic Versioning.

## [Unreleased]

- (empty)

## [0.1.0] - 2026-03-17

### Added
- OpenClaw skill packaging (`skills/clawhealth/`).
- Skill validation and minimal test scripts.
- Publish checklist and release template.
- Stage 2 endpoints: sleep-dump, body-composition, activities, activity-details, menstrual, menstrual-calendar.
- Raw tables for sleep/body composition/activity/menstrual payloads.
- Daily summary now includes sleep stages/score and body composition fields.
- Skill metadata env requirements and a `.clawhubignore` publish filter.

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

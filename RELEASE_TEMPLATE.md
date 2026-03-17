# Release Template (ClawHub)

## Version
`vX.Y.Z`

## Summary
One or two sentences describing the release.

## Changes
- Added:
- Changed:
- Fixed:

## Compatibility
- Python:
- garminconnect:
- garth:

## Migration Notes
- None (or describe changes)

## Verification
- `python skills/clawhealth/validate_skill.py`
- `python skills/clawhealth/bootstrap_deps.py` (if needed)
- `python skills/clawhealth/test_minimal.py`
- (Optional) `python skills/clawhealth/test_integration_optional.py`

## Publish
- `openclaw clawhub login`
- `openclaw skill publish skills/clawhealth`

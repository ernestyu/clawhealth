# Release Template

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
- `python skills/clawhealth-garmin/validate_skill.py`
- `python skills/clawhealth-garmin/bootstrap_deps.py` (if needed)
- `python skills/clawhealth-garmin/test_minimal.py`
- (Optional) `python skills/clawhealth-garmin/test_integration_optional.py`

## Release
- Create a git tag `vX.Y.Z` and push it.
- Create a GitHub Release using this template.

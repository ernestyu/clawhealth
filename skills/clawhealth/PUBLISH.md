# ClawHub Publish Checklist

## 0. Sync vendored code (recommended)

If you are publishing from the repo, refresh the vendored package:

```bash
python {baseDir}/sync_vendor.py
```

## 1. Prerequisites
- OpenClaw installed
- Python 3.10+
- Optional: network access to install Python deps (unless using a prepatched image)
- `clawhub` CLI installed (`npm i -g clawhub`)

## 2. Validate
```bash
python {baseDir}/validate_skill.py
```

## 3. Minimal Tests
```bash
python {baseDir}/test_minimal.py
```

## 4. Optional Integration Test (real account)
```bash
python {baseDir}/test_integration_optional.py
```

## 5. Bootstrap Dependencies (if needed)
```bash
python {baseDir}/bootstrap_deps.py
```

## 6. Publish
```bash
clawhub login
clawhub publish {baseDir} --slug clawhealth-garmin --name "clawhealth-garmin" --version 0.1.0
```

## 7. Release Notes
Use `RELEASE_TEMPLATE.md` at repo root.

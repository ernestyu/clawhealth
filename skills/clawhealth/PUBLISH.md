# ClawHub Publish Checklist

## 1. Prerequisites
- `openclaw` CLI installed
- Python 3.10+
- Optional: network access to install Python deps (unless using a prepatched image)

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
openclaw clawhub login
openclaw skill publish {baseDir}
```

## 7. Release Notes
Use `RELEASE_TEMPLATE.md` at repo root.

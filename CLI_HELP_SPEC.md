# CLI Help Spec (from argparse)

## clawhealth --help
usage: clawhealth [-h] {garmin,daily-summary} ...

Health data bridge for OpenClaw

positional arguments:
  {garmin,daily-summary}
    garmin              Garmin-related commands
    daily-summary       Show a summarized view of health metrics for a given
                        date (stub)

options:
  -h, --help            show this help message and exit


## clawhealth garmin --help
usage: clawhealth garmin [-h] {login,sync,status,hrv-dump} ...

positional arguments:
  {login,sync,status,hrv-dump}
    login               Perform Garmin login (username/password/MFA) and
                        persist session
    sync                Sync Garmin data into a local SQLite UHM DB
    status              Show sync status and data freshness
    hrv-dump            Dump raw HRV JSON for a given date (and persist to DB)

options:
  -h, --help            show this help message and exit


## clawhealth garmin login --help
usage: clawhealth garmin login [-h] [--username USERNAME]
                               [--password-file PASSWORD_FILE]
                               [--config-dir CONFIG_DIR] [--mfa-code MFA_CODE]
                               [--json]

options:
  -h, --help            show this help message and exit
  --username USERNAME   Garmin account username/email
  --password-file PASSWORD_FILE
                        Path to file containing password (one line)
  --config-dir CONFIG_DIR
                        Directory to store Garmin session/config (default:
                        /opt/clawhealth/config)
  --mfa-code MFA_CODE   MFA/OTP code when a challenge is required
  --json                Output structured JSON instead of human-readable
                        text


## clawhealth garmin sync --help
usage: clawhealth garmin sync [-h] [--since SINCE] [--until UNTIL]
                              [--config-dir CONFIG_DIR] [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --since SINCE         Start date YYYY-MM-DD for sync
  --until UNTIL         End date YYYY-MM-DD for sync
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON instead of human-readable
                        text


## clawhealth garmin status --help
usage: clawhealth garmin status [-h] [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON instead of human-readable
                        text


## clawhealth garmin hrv-dump --help
usage: clawhealth garmin hrv-dump [-h] --date DATE [--config-dir CONFIG_DIR]
                                  [--out OUT] [--json]

options:
  -h, --help            show this help message and exit
  --date DATE           Target date (YYYY-MM-DD) for HRV data
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --out OUT             Optional path to write raw HRV JSON (default: print to
                        stdout)
  --json                Output structured JSON status instead of raw payload


## clawhealth daily-summary --help
usage: clawhealth daily-summary [-h] [--date DATE] [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --date DATE           Target date (YYYY-MM-DD). If omitted, implementation
                        will choose a default
  --db DB               Path to SQLite DB for UHM data (default:
                        CLAWHEALTH_DB or /opt/clawhealth/data/health.db)
  --json                Output structured JSON instead of human-readable
                        text

# CLI Help Spec (from argparse)

## clawhealth --help
usage: clawhealth [-h] {garmin,daily-summary} ...

Health data bridge for OpenClaw

positional arguments:
  {garmin,daily-summary}
    garmin              Garmin-related commands
    daily-summary       Show a summarized view of health metrics for a given
                        date

options:
  -h, --help            show this help message and exit


## clawhealth garmin --help
usage: clawhealth garmin [-h]
                         {login,sync,status,trend-summary,flags,training-metrics,hrv-dump,sleep-dump,body-composition,activities,activity-details,menstrual,menstrual-calendar} ...

positional arguments:
  {login,sync,status,trend-summary,flags,training-metrics,hrv-dump,sleep-dump,body-composition,activities,activity-details,menstrual,menstrual-calendar}
    login               Perform Garmin login (username/password/MFA) and
                        persist session
    sync                Sync Garmin data into a local SQLite UHM DB
    status              Show sync status and data freshness
    trend-summary       Show recent trend summary over a sliding window of days
    flags               Compute simple health flags over recent days
    training-metrics    Fetch training readiness/status/endurance/fitness-age
                        and map into UHM
    hrv-dump            Dump raw HRV JSON for a given date (and persist to DB)
    sleep-dump          Fetch sleep stages/score for a date and persist into DB
    body-composition    Fetch body composition metrics for a date or range
    activities          Fetch activity list for a date range and persist raw
                        payloads
    activity-details    Fetch full activity details by activity ID
    menstrual           Fetch menstrual day view for a date (if available)
    menstrual-calendar  Fetch menstrual calendar range (if available)

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
usage: clawhealth garmin sync [-h] --since SINCE [--until UNTIL]
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


## clawhealth garmin sleep-dump --help
usage: clawhealth garmin sleep-dump [-h] --date DATE [--config-dir CONFIG_DIR]
                                    [--db DB] [--out OUT] [--json]

options:
  -h, --help            show this help message and exit
  --date DATE           Target date (YYYY-MM-DD) for sleep data
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --out OUT             Optional path to write raw sleep JSON (default: no file)
  --json                Output structured JSON status instead of raw payload


## clawhealth garmin body-composition --help
usage: clawhealth garmin body-composition [-h] [--date DATE] [--since SINCE]
                                          [--until UNTIL]
                                          [--config-dir CONFIG_DIR] [--db DB]
                                          [--json]

options:
  -h, --help            show this help message and exit
  --date DATE           Target date (YYYY-MM-DD). If set, overrides --since/--until.
  --since SINCE         Start date (YYYY-MM-DD) for body composition range
  --until UNTIL         End date (YYYY-MM-DD) for body composition range
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON status instead of human-readable text


## clawhealth garmin activities --help
usage: clawhealth garmin activities [-h] --since SINCE [--until UNTIL]
                                    [--limit LIMIT] [--activity-type ACTIVITY_TYPE]
                                    [--config-dir CONFIG_DIR] [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --since SINCE         Start date (YYYY-MM-DD) for activities
  --until UNTIL         End date (YYYY-MM-DD) for activities
  --limit LIMIT         Max activities to return (default: 20)
  --activity-type ACTIVITY_TYPE
                        Optional activity type filter (e.g., running, cycling)
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON status instead of human-readable text


## clawhealth garmin activity-details --help
usage: clawhealth garmin activity-details [-h] --activity-id ACTIVITY_ID
                                          [--config-dir CONFIG_DIR] [--db DB]
                                          [--out OUT] [--json]

options:
  -h, --help            show this help message and exit
  --activity-id ACTIVITY_ID
                        Garmin activityId (from activities list)
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --out OUT             Optional path to write raw activity details JSON
  --json                Output structured JSON status instead of human-readable text


## clawhealth garmin menstrual --help
usage: clawhealth garmin menstrual [-h] --date DATE [--config-dir CONFIG_DIR]
                                   [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --date DATE           Target date (YYYY-MM-DD) for menstrual data
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON status instead of human-readable text


## clawhealth garmin menstrual-calendar --help
usage: clawhealth garmin menstrual-calendar [-h] --since SINCE [--until UNTIL]
                                            [--config-dir CONFIG_DIR] [--db DB]
                                            [--json]

options:
  -h, --help            show this help message and exit
  --since SINCE         Start date (YYYY-MM-DD) for menstrual calendar
  --until UNTIL         End date (YYYY-MM-DD) for menstrual calendar
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON status instead of human-readable text


## clawhealth garmin trend-summary --help
usage: clawhealth garmin trend-summary [-h] [--days DAYS] [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --days DAYS           Window size in days (default: 7)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON instead of human-readable
                        text


## clawhealth garmin flags --help
usage: clawhealth garmin flags [-h] [--days DAYS] [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --days DAYS           Window size in days (default: 7)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON instead of human-readable
                        text


## clawhealth garmin training-metrics --help
usage: clawhealth garmin training-metrics [-h] [--config-dir CONFIG_DIR]
                                          [--db DB] [--json]

options:
  -h, --help            show this help message and exit
  --config-dir CONFIG_DIR
                        Directory with Garmin session/config (default:
                        /opt/clawhealth/config)
  --db DB               Path to SQLite DB for UHM data (default:
                        /opt/clawhealth/data/health.db)
  --json                Output structured JSON instead of human-readable
                        text


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

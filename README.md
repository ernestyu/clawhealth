# clawhealth

**Languages:** English | [Chinese](README_zh.md)

`clawhealth` is a Python package and CLI that bridges health data (starting with
Garmin Connect) into a local **SQLite** database and exposes **JSON‑friendly
commands**. It is designed to be:

- A **CLI‑first** health hub: `clawhealth garmin ...` / `clawhealth daily-summary ...`
- A stable **data layer** for OpenClaw agents and other automation
- A foundation for future vendors (`garmin`, `huami`, `xiaomi`, ...)

The same core is also used by the OpenClaw skill
`skills/clawhealth-garmin/`, but the Python package本身是第一等公民。

---

## Installation (Python package / CLI)

Requirements:

- Python 3.10+

Install from PyPI:

```bash
python -m pip install --upgrade pip  # optional but recommended
python -m pip install clawhealth
```

After installation, you should have a `clawhealth` command:

```bash
clawhealth --help
```

Typical help output:

```text
usage: clawhealth [-h] {garmin,daily-summary} ...

Health data bridge for OpenClaw (CLI-first Garmin hub)

positional arguments:
  {garmin,daily-summary}
    garmin          Garmin-related commands
    daily-summary   Show a summarized view of health metrics for a given date

options:
  -h, --help        show this help message and exit
```

---

## Quickstart: Garmin + SQLite

### 1. Configure credentials

`clawhealth` uses the official Garmin Connect login flow via
[`garminconnect`](https://github.com/cyberjunky/python-garminconnect).

The CLI expects your Garmin email + password. There are two common patterns:

1. **Environment variables / .env** (recommended when running under a process manager)
2. **Password file** (recommended when embedding into a skill环境)

For a pure CLI session，你可以直接在命令行指定用户名和密码文件，例如：

```bash
export CLAWHEALTH_GARMIN_USERNAME="you@example.com"
export CLAWHEALTH_GARMIN_PASSWORD_FILE="/secure/path/garmin_pass.txt"

# 或者在命令行参数中显式传入
clawhealth garmin login --username you@example.com --password-file /secure/path/garmin_pass.txt --json
```

> 提示：不要把密码文件放进 git 仓库，注意文件权限（例如 `chmod 600`）。

### 2. Login (MFA)

登录通常分两步完成：

```bash
# 第一步：触发登录与 MFA 挑战
clawhealth garmin login --json

# 第二步：在收到验证码后提交 MFA
clawhealth garmin login --mfa-code 123456 --json
```

成功后，clawhealth 会在本地 config 目录中缓存 Garmin 会话信息（具体位置会在 JSON 输出中给出），后续命令无需重新输入密码。

### 3. 同步数据到 SQLite

`clawhealth` 默认会在一个本地 SQLite 数据库中维护健康数据（UHM schema）。

同步最近几天的数据，例如：

```bash
# 同步 2026-03-17 ~ 2026-03-19 的健康数据
clawhealth garmin sync --since 2026-03-17 --until 2026-03-19 --json
```

返回的 JSON 会包含：

- `ok`: 是否成功
- `synced_dates`: 实际同步的日期列表
- `db`: SQLite 数据库路径（例如 `.../data/health.db`）

### 4. 查询 daily-summary（给 Agent / 自动化用）

一旦完成同步，你可以按日期查询汇总指标：

```bash
clawhealth daily-summary --date 2026-03-19 --json
```

示例输出（简化）：

```json
{
  "ok": true,
  "date": "2026-03-19",
  "sleep_total_min": 403,
  "rhr_bpm": 58,
  "steps": 4237,
  "distance_m": 3299.0,
  "calories_total": 1746.0,
  "stress_avg": 42,
  "stress_max": 96,
  "body_battery_start": 43.0,
  "body_battery_end": 5.0,
  "spo2_avg": 98.0,
  "mapping_version": "uhm_v1"
}
```

这个 JSON 结构是为 Agent/自动化设计的：字段稳定，可直接喂给 LLM 或存入你自己的数据仓库。

---

## Command Overview

核心命令（CLI / Agent 都可用）：

- `clawhealth daily-summary --date YYYY-MM-DD --json`
- `clawhealth garmin sync --since YYYY-MM-DD --until YYYY-MM-DD --json`

高级命令（按需调用）：

- `clawhealth garmin training-metrics --json`
- `clawhealth garmin sleep-dump --date YYYY-MM-DD --json`
- `clawhealth garmin body-composition --date YYYY-MM-DD --json`
- `clawhealth garmin activities --since ... --until ... --json`
- `clawhealth garmin activity-details --activity-id 123456789 --json`
- `clawhealth garmin hrv-dump --date YYYY-MM-DD --json`
- `clawhealth garmin menstrual --date YYYY-MM-DD --json`
- `clawhealth garmin menstrual-calendar --since ... --until ... --json`

> 注意：部分指标依赖你的设备型号和 Garmin 账号设置（例如睡眠分期、体脂、女性健康）。

---

## Security model

- 所有操作都在你的本地环境执行。
- Garmin 凭据和会话 token 不会发送给第三方服务。
- SQLite DB 存在本地（默认路径会在 JSON 输出中给出）。
- 强烈建议使用密码文件或安全的环境变量管理方式（如 1Password/Bitwarden），不要把密码硬编码在脚本里。

---

## Using clawhealth as an OpenClaw skill

如果你在使用 OpenClaw，并希望通过 Telegram 等界面与 Garmin 健康数据交互，可以使用随仓库提供的技能包：

- 目录：`skills/clawhealth-garmin/`
- 主要说明：`skills/clawhealth-garmin/SKILL.md`
- ClawHub 条目：`clawhealth-garmin`

典型安装路径（ClawHub）：

```bash
npx clawhub@latest install clawhealth-garmin --force
```

安装完成后，OpenClaw 会从 `<workspace>/skills/clawhealth-garmin` 加载这个技能，具体的 `.env` / 密码文件配置、MFA 登录流程，请参考 `skills/clawhealth-garmin/SKILL.md`。

> 总结：**包级 README = 讲 Python 包和 CLI，技能级 README/SKILL = 讲 OpenClaw 集成。**

---

## Roadmap

See `ROADMAP.md` for planned vendors (e.g. Huami/Xiaomi) and schema evolution.

---

## License

Apache-2.0

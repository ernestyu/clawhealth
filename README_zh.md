# clawhealth

**语言:** 中文 | [English](README.md)

`clawhealth` 是一个基于 Python 的健康数据桥接工具，它目前以
**Garmin Connect → SQLite → JSON** 为主线：

- 作为一个 **CLI 优先** 的健康数据 hub：`clawhealth garmin ...` / `clawhealth daily-summary ...`
- 为 OpenClaw Agent 和其他自动化提供稳定的 **数据层**（UHM schema）
- 为将来接入更多厂商打基础（`garmin` / `huami` / `xiaomi` 等）

本仓库的核心是 Python 包 + CLI；`skills/clawhealth-garmin/` 目录下的 OpenClaw
技能包是对这个包的一层集成。

---

## 安装（Python 包 / CLI）

前置要求：

- Python 3.10+

通过 PyPI 安装：

```bash
python -m pip install --upgrade pip  # 可选但推荐
python -m pip install clawhealth
```

安装完成后，你应该能看到 `clawhealth` 命令：

```bash
clawhealth --help
```

示例输出：

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

## 快速上手：Garmin + SQLite

### 1. 配置账号信息

`clawhealth` 使用 [`garminconnect`](https://github.com/cyberjunky/python-garminconnect)
登录 Garmin Connect（支持 MFA）。

CLI 支持从环境变量、密码文件或命令行参数获取账号信息。纯 CLI 场景下，你可以：

```bash
export CLAWHEALTH_GARMIN_USERNAME="you@example.com"
export CLAWHEALTH_GARMIN_PASSWORD_FILE="/secure/path/garmin_pass.txt"

# 或者：
clawhealth garmin login \
  --username you@example.com \
  --password-file /secure/path/garmin_pass.txt \
  --json
```

> 建议：不要把密码文件提交到 git；在本地用 `chmod 600` 保护好权限。

### 2. 登录（含 MFA）

登录一般分两步：

```bash
# 第一步：触发登录和 MFA 挑战
clawhealth garmin login --json

# 第二步：在收到验证码后提交 MFA
clawhealth garmin login --mfa-code 123456 --json
```

成功后，会话 token 会缓存到本地配置目录（具体路径会在 JSON 输出里给出），后续命令
不需要重复输入密码。

### 3. 同步数据到本地 SQLite

`clawhealth` 默认在本地维护一个健康数据 SQLite 数据库（采用 UHM schema）。

例如同步最近三天：

```bash
clawhealth garmin sync --since 2026-03-17 --until 2026-03-19 --json
```

返回 JSON 中会包含：

- `ok`: 是否成功
- `synced_dates`: 实际同步的日期列表
- `db`: SQLite DB 路径（如 `.../data/health.db`）

### 4. 查询 daily-summary（给 Agent / 自动化用）

同步完成后，可以按日期查询汇总指标：

```bash
clawhealth daily-summary --date 2026-03-19 --json
```

输出示例（简化）：

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

这个 JSON 结构对 Agent 友好，字段稳定，可以直接作为 LLM 上下文或写入你自己的数据仓库。

---

## 命令总览

核心命令：

- `clawhealth daily-summary --date YYYY-MM-DD --json`
- `clawhealth garmin sync --since YYYY-MM-DD --until YYYY-MM-DD --json`

高级命令（按需使用）：

- `clawhealth garmin training-metrics --json`
- `clawhealth garmin sleep-dump --date YYYY-MM-DD --json`
- `clawhealth garmin body-composition --date YYYY-MM-DD --json`
- `clawhealth garmin activities --since ... --until ... --json`
- `clawhealth garmin activity-details --activity-id 123456789 --json`
- `clawhealth garmin hrv-dump --date YYYY-MM-DD --json`
- `clawhealth garmin menstrual --date YYYY-MM-DD --json`
- `clawhealth garmin menstrual-calendar --since ... --until ... --json`

> 说明：部分指标依赖设备型号与账号开关，例如睡眠分期、身体成分、女性健康。

---

## 安全模型

- 所有逻辑在本地执行，不向第三方服务上报健康数据。
- Garmin 凭据与会话 token 存在本机（默认路径在 JSON 输出中可见）。
- 建议搭配密码管理器或 `.env` 管理敏感信息，不要把密码硬编码到脚本中。

---

## 与 OpenClaw 的集成

如果你在使用 OpenClaw，并希望通过 Telegram 等界面来查看 Garmin 健康数据，
可以使用随仓库提供的技能包：

- 目录：`skills/clawhealth-garmin/`
- 说明文档：`skills/clawhealth-garmin/SKILL_zh.md` / `SKILL.md`

在 ClawHub 上，这个技能的 slug 是：`clawhealth-garmin`。

安装示意：

```bash
npx clawhub@latest install clawhealth-garmin --force
```

之后，OpenClaw 会从 `<workspace>/skills/clawhealth-garmin` 加载技能，具体 `.env`、
密码文件、MFA 登录等配置请参考技能目录下的 SKILL 文档。

> 总结：根目录 README 主要面向 **Python 包 / CLI 用户**；技能目录下的 SKILL/README
> 则面向 **OpenClaw 集成**。

---

## Roadmap

后续会逐步支持更多厂商（如 Huami/Xiaomi），并扩展 UHM schema 以支撑更丰富的
健康/训练指标。详情参见 `ROADMAP.md`。

---

## 许可证

Apache-2.0

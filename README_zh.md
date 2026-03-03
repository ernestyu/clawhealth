# clawhealth

**语言：** [English](README.md) | 中文说明

`clawhealth` 是一个 **面向个人的健康数据命令行工具箱**。

它从 Garmin Connect 拉取你的睡眠、步数、心率、压力、HRV、训练准备度等信息，
存到本地 SQLite，然后用一组小而清晰的命令帮你和 Agent 看懂每天的状态和趋势。

可以把它当成：**“自己的运动 / 恢复日报引擎”**。

> 当前状态：Garmin 第一阶段功能已实现并通过多轮物理测试
> （登录 / 同步 / 状态 / HRV / 日摘要 + 趋势 / flags / 训练指标）。

---

## 它现在能做什么？

针对一个 Garmin 账号，clawhealth 会：

- 通过用户名/密码 + MFA 登录，并在本地保存可复用的会话；
- 按天同步你的健康数据到本地 `health.db`；
- 提供“今天/某天”的健康概要（文本 + JSON）；
- 按最近 N 天计算趋势（平均睡眠、步数、HRV、压力等）；
- 给出一些简单的健康 flags（比如睡眠偏低、HRV 偏低、步数偏少等）。

它**不会**：

- 把你的健康数据上传到任何地方；
- 自己跑一个常驻的 HTTP 服务；
- 取代 Garmin Connect 做所有细粒度分析。

clawhealth 更像是“本地健康数据中枢”，上层可以是 OpenClaw Agent、命令行脚本，或者你自己的日报工作流。

---

## 快速上手

### 1. 安装（开发模式）

```bash
cd clawhealth
python -m pip install -e .
```

安装完成后，会多出一个 `clawhealth` 命令。

### 2. 配置 Garmin 账号

在仓库根目录创建 `.env`（或直接设置环境变量）：

```env
CLAWHEALTH_GARMIN_USERNAME=you@example.com
CLAWHEALTH_GARMIN_PASSWORD_FILE=/path/to/garmin.pass
CLAWHEALTH_CONFIG_DIR=/opt/clawhealth/config
CLAWHEALTH_DB=/opt/clawhealth/data/health.db
```

- `CLAWHEALTH_GARMIN_PASSWORD_FILE` 指向一个文件，第一行是你的 Garmin 密码。
- CLI 会在需要时自动创建 `CLAWHEALTH_CONFIG_DIR` 和 `CLAWHEALTH_DB` 所在目录。

### 3. 登录（含两步 MFA）

```bash
# 第一步：尝试登录，可能返回 NEED_MFA
clawhealth garmin login --json

# 第二步：看到 NEED_MFA 后，输入手机/Authenticator 上的验证码
clawhealth garmin login --mfa-code 123456 --json
```

成功时会返回：

```json
{
  "ok": true,
  "auth_state": "AUTH_OK"
}
```

会话 token 会写入 `CLAWHEALTH_CONFIG_DIR`，后续 sync/status 会自动复用，直到失效。

### 4. 同步几天的数据

```bash
clawhealth garmin sync \
  --since 2026-03-01 \
  --until 2026-03-03 \
  --json
```

它会：

- 对每一天调用 Garmin 接口拿日汇总数据；
- 把原始 JSON 存到 `garmin_daily_raw`；
- 把核心指标映射到 `uhm_daily`（一行一天）；
- 在 `sync_runs` 记录这次同步的时间范围和状态。

### 5. 查看同步状态

```bash
clawhealth garmin status --json
```

典型输出：

```json
{
  "ok": true,
  "covered_from": "2026-03-01",
  "covered_to": "2026-03-03",
  "last_success_at": "2026-03-03T20:15:00+00:00",
  "data_freshness_hours": 0.3,
  "source_vendor": "garmin",
  "driver_version": "garminconnect_v1",
  "mapping_version": "uhm_v1"
}
```

Agent 可以用它判断“数据是不是过期了”、“要不要提醒你再同步一次”。

### 6. 看日度健康摘要

```bash
# 人类可读版本
clawhealth daily-summary --date 2026-03-03

# JSON 版本（给 Agent 用）
clawhealth daily-summary --date 2026-03-03 --json
```

示例文本输出：

```text
2026-03-03 健康概要（来源：Garmin，本地 uhm_v1）
- 睡眠：6.5 小时
- 静息心率：60 bpm
- 步数：5030 步（约 4.2 km）
- 总能量消耗：2482 kcal
- 压力：平均 47，峰值 97，VERY_STRESSFUL
- 身体电量：起床 33 → 当前 5
- HRV：昨夜平均 40 ms，状态：BALANCED
- 训练准备度：评分 68，MODERATE
- 体能年龄：当前 48.7 岁，生理 50 岁，可达 43 岁
```

JSON 版本（截断示例）：

```json
{
  "ok": true,
  "date": "2026-03-03",
  "sleep_total_min": 391,
  "rhr_bpm": 60,
  "steps": 5030,
  "distance_m": 4156.0,
  "calories_total": 2482.0,
  "stress_avg": 47,
  "body_battery_start": 33,
  "body_battery_end": 5,
  "hrv_last_night_avg": 40,
  "hrv_status": "BALANCED",
  "training_readiness_score": 68,
  "training_status_code": 5,
  "endurance_overall_score": 3464,
  "fitness_age": 48.69,
  "fitness_age_chronological": 50.0,
  "fitness_age_achievable": 43.4,
  "mapping_version": "uhm_v1"
}
```

---

## 常用命令速查

### Garmin 相关

```bash
# 登录 + MFA
clawhealth garmin login [--username ...] [--password-file ...] [--mfa-code ...] [--json]

# 将 Garmin 日数据同步到本地 SQLite
clawhealth garmin sync --since YYYY-MM-DD [--until YYYY-MM-DD] [--db ...] [--json]

# 查看覆盖范围和数据新鲜度
clawhealth garmin status [--db ...] [--json]

# 导出某天 HRV 原始 JSON，并把 HRV 摘要写入 DB
clawhealth garmin hrv-dump --date YYYY-MM-DD [--config-dir ...] [--out ...] [--json]

# 最近 N 天趋势（均值）
clawhealth garmin trend-summary [--days 7] [--db ...] [--json]

# 最近 N 天 flags（睡眠低 / HRV 低 / 压力高 / 步数少）
clawhealth garmin flags [--days 7] [--db ...] [--json]

# 拉取“今天”的训练类指标（训练准备度/训练状态/耐力/体能年龄），写入 UHM
clawhealth garmin training-metrics [--config-dir ...] [--db ...] [--json]
```

### 日度摘要

```bash
# 今天（默认）
clawhealth daily-summary [--db ...]

# 指定日期
clawhealth daily-summary --date YYYY-MM-DD [--db ...] [--json]
```

详细参数和选项见 [`CLI_HELP_SPEC.md`](CLI_HELP_SPEC.md)。

---

## 配置要点

常用环境变量（可选，CLI 参数优先）：

- `CLAWHEALTH_GARMIN_USERNAME` – Garmin 用户名/邮箱；
- `CLAWHEALTH_GARMIN_PASSWORD_FILE` – 存放密码的文件路径（第一行是密码）；
- `CLAWHEALTH_GARMIN_PASSWORD` – 明文密码（不推荐，除非你确定环境安全）；
- `CLAWHEALTH_CONFIG_DIR` – 会话 token 与缓存目录（默认 `/opt/clawhealth/config`）；
- `CLAWHEALTH_DB` – SQLite DB 路径（默认 `/opt/clawhealth/data/health.db`）。

项目根目录下的 `.env` 会在启动时自动加载，使用 `setdefault` 语义：
**环境变量优先于 `.env`**。

---

## 数据会落在哪里？

默认会生成一个 SQLite 文件：`/opt/clawhealth/data/health.db`，包含主要几张表：

- `uhm_daily` – 一行一天的标准化指标；
- `garmin_daily_raw` – `get_stats_and_body` 的原始 JSON；
- `garmin_hrv_raw` – HRV 原始数据；
- `garmin_training_readiness_raw` / `garmin_training_status_raw` /
  `garmin_endurance_raw` / `garmin_fitness_age_raw`；
- `sync_runs` – 每次同步的执行记录。

一般情况下你无需直接操作这些表：

- 日常使用：`daily-summary` / `trend-summary` / `flags` 已经足够；
- 需要更深入分析时，再用 sqlite3 / Python 自己去读 raw 表会更灵活。

如果你只是试用，发现 schema 有调整，
可以直接删掉旧的 `health.db`，重新跑 `sync` 让 clawhealth 重建。

---

## 想了解内部细节？

- [`DESIGN.md`](DESIGN.md)：英文技术设计，描述了 SQLite schema、
  映射函数和登录流程（garth + garminconnect）。
- [`PLAN_CN.md`](PLAN_CN.md)：中文设计与规划文档，记录了整个项目的背景、取舍和后续思路。

这些文档更偏工程视角，一般使用时可以不用看；
只有在需要扩展字段或增加 provider 时再参考即可。

---

## 协议

MIT © Ernest Yu

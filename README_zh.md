# clawhealth

**语言：** [English](README.md) | 中文说明

`clawhealth` 是一个面向 OpenClaw / Agent 的 **健康数据命令行工具箱**。

第一阶段聚焦 **Garmin Connect 个人账号**：

- 通过 CLI 完成登录（用户名/密码/MFA）并持久化会话；
- 从 Garmin 拉取睡眠、步数、静息心率等数据，写入本地 SQLite；
- 提供适合人类和 Agent 使用的 CLI（JSON 输出），用于查看同步状态和日度摘要。

不强制跑 REST API 服务，所有与 Agent 的集成都可以通过 CLI 完成。

---

## 核心设计原则

- **CLI-first**：所有关键操作（登录、同步、查询）都以命令行为主入口；
- **本地优先**：数据落在本机 SQLite（例如 `/opt/clawhealth/data/health.db`），不会自动上传到第三方云端；
- **易于 Agent 集成**：
  - 命令支持 `--json` 输出，返回结构化的状态和数据；
  - 错误使用稳定的 `error_code`（例如 `NEED_MFA`、`AUTH_CHALLENGE_REQUIRED`），而不是随意的错误文案；
- **分层清晰**：clawhealth 只负责本地拉取 + SQLite + CLI，MCP/REST 如有需要可以在外层再包一层。

更详细的技术规划见 [`PLAN_CN.md`](PLAN_CN.md)。

---

## Garmin 第一阶段（已实现）：CLI 形状概览

### 1. 登录（含 MFA）

```bash
clawhealth garmin login \
  --username YOUR_EMAIL \
  --password-file /path/to/pass.txt \
  --config-dir /opt/clawhealth/config \
  [--mfa-code 123456] \
  [--json]
```

- 第一次调用：
  - 使用 `python-garminconnect` + `garth` 尝试登录；
  - 如果需要 MFA，则返回 `error_code=NEED_MFA` 而不是卡在交互输入上；
- 第二次调用：
  - 携带 `--mfa-code`，完成验证码验证；
  - 登录成功后在 `config-dir` 下写入会话/Token 文件，后续 `sync` 不再需要验证码，直到 token 失效。

### 2. 同步数据到本地 SQLite（UHM）

```bash
clawhealth garmin sync \
  --since 2026-03-01 \
  --until 2026-03-03 \
  --config-dir /opt/clawhealth/config \
  --db /opt/clawhealth/data/health.db \
  [--json]
```

- 从 `config-dir` 读取会话，如果会话失效返回 `AUTH_CHALLENGE_REQUIRED`；
- 对每个日期拉取健康数据（睡眠/步数/RHR/体重等），映射到 UHM 日表 `uhm_daily`；
- 在 `sync_runs` 表记录本次同步的时间范围、状态、错误信息等；
- `--json` 模式下返回结构化的结果，方便 Agent 判断是否需要提示用户。

### 3. 查看同步状态与数据新鲜度

```bash
clawhealth garmin status \
  --db /opt/clawhealth/data/health.db \
  [--json]
```

典型 JSON 输出：

```json
{
  "ok": true,
  "last_success_at": "2026-03-02T20:15:00Z",
  "data_freshness_hours": 5.3,
  "covered_from": "2025-12-01",
  "covered_to": "2026-03-02",
  "source_vendor": "garmin",
  "driver_version": "garminconnect_v1",
  "mapping_version": "uhm_v1"
}
```

Agent 可以用它判断：

- 最近是否跑过同步；
- 数据是否过期（例如超过 24 小时未更新）。

### 4. 日度摘要（给人 / Agent 看）

```bash
clawhealth daily-summary \
  --date 2026-03-02 \
  --db /opt/clawhealth/data/health.db \
  [--json]
```

输出示例（人类友好）：

```text
2026-03-02 健康概要（来源：Garmin，本地 uhm_v1）
- 睡眠：6.5 小时
- 静息心率：60 bpm
- 步数：5030 步（约 4.2 km）
- 总能量消耗：2482 kcal
- 体重：--（暂无称重数据）
- 压力：平均 47，峰值 97，VERY_STRESSFUL
- 身体电量：起床 33 → 当前 5
- HRV：昨夜平均 40 ms，状态：BALANCED
```

`--json` 模式下会返回结构化 JSON，包括 `sleep_total_min`、`rhr_bpm`、`steps`、`distance_m`、`calories_total`、`weight_kg`、`stress_*`、`body_battery_*`、`hrv_*` 等字段，便于 Agent 进行二次加工。

---

## 安装与开发

clawhealth 使用 `pyproject.toml` 管理包和 CLI 入口：

- 包名：`clawhealth`；
- CLI 入口：`clawhealth = "clawhealth.cli:main"`。

开发模式安装：

```bash
cd clawhealth
python -m pip install -e .

# 然后直接使用：
clawhealth garmin login --help
clawhealth garmin sync --help
clawhealth daily-summary --help
```

---

## 后续规划（简要）

- 完成 Garmin 第一阶段实现：
  - login/sync/status/daily-summary；
  - 健康 SQLite schema（`uhm_daily` + `sync_runs`）；
  - 文档与 CLI 帮助对齐。
- 按使用体验迭代 UHM 字段和 CLI：
  - 增加活动级别查询（`export-series` / `activity-summary`）；
  - 根据 Agent 的反馈优化 daily-summary 文案和 JSON 结构。
- 是否需要 MCP / Web UI：
  - 完全可以在 clawhealth 之外再包一层（例如 OpenClaw skills 或轻量 Flask 服务）；
  - 不强制把这些组件塞进 clawhealth 本体。

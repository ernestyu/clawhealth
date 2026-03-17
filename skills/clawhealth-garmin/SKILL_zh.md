# clawhealth-garmin（OpenClaw 技能）

中文说明为辅，发布与审核以英文版 `SKILL.md` 为准。

## 能做什么

- Garmin 用户名/密码登录（支持 MFA）
- 同步每日健康汇总到本地 SQLite（阶段 1）
- 获取 HRV 与训练指标（阶段 2）
- 获取睡眠分期与睡眠评分（阶段 2）
- 获取身体成分（阶段 2）
- 获取活动列表与完整活动详情（阶段 2）
- 获取女性健康日视图与日历范围（实验性，需 garminconnect 支持）
- 输出 OpenClaw 可调用的 JSON 结果
- 保存原始 JSON 以便后续分析

## 前置条件

- Python 3.10+
- 可访问 Garmin Connect 的网络
- Garmin 账号（可能需要 MFA）

如果你在 Docker 中运行 OpenClaw，推荐使用已打好依赖的镜像：

- `ernestyu/openclaw-patched`

## 安装与配置

1) 创建 `{baseDir}/.env`（参考 `{baseDir}/ENV.example`）。

建议使用 `CLAWHEALTH_GARMIN_PASSWORD_FILE`（密码文件）而非
`CLAWHEALTH_GARMIN_PASSWORD`（明文环境变量）。

注意：像 `./garmin_pass.txt` 这样的相对路径会由 `run_clawhealth.py`
自动解析为技能目录下的路径。

2) 安装 Python 依赖（如需要）：

```bash
python {baseDir}/bootstrap_deps.py
```

说明：

- 技能内置了 `vendor/` 下的 `clawhealth`。
- Bootstrap 只安装第三方依赖（`garth`、`garminconnect`）到 `{baseDir}/.venv`。
- `{baseDir}/run_clawhealth.py` 会在检测到 venv 时自动 re-exec。

## 基础命令

登录（可能返回 `NEED_MFA`）：

```bash
python {baseDir}/run_clawhealth.py garmin login --username you@example.com --json
```

完成 MFA：

```bash
python {baseDir}/run_clawhealth.py garmin login --mfa-code 123456 --json
```

同步：

```bash
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

状态：

```bash
python {baseDir}/run_clawhealth.py garmin status --json
```

每日摘要：

```bash
python {baseDir}/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

## 高级接口（阶段 2）

### HRV（按日期）

```bash
python {baseDir}/run_clawhealth.py garmin hrv-dump --date 2026-03-03 --json
```

说明：先对同一天执行 `garmin sync`，否则 `daily-summary` 中 HRV 可能为 `null`。

### 训练准备度 / 训练状态 / 耐力 / 体能年龄

```bash
python {baseDir}/run_clawhealth.py garmin training-metrics --json
```

说明：该命令默认拉取“今天”的指标；建议先执行
`garmin sync --since TODAY --until TODAY`。

### 睡眠分期 + 睡眠评分

```bash
python {baseDir}/run_clawhealth.py garmin sleep-dump --date 2026-03-03 --json
```

### 身体成分

```bash
python {baseDir}/run_clawhealth.py garmin body-composition --date 2026-03-03 --json
```

### 活动（列表 + 详情）

```bash
python {baseDir}/run_clawhealth.py garmin activities --since 2026-03-01 --until 2026-03-03 --json
python {baseDir}/run_clawhealth.py garmin activity-details --activity-id 123456789 --json
```

### 女性健康（实验性，需 garminconnect 支持）

```bash
python {baseDir}/run_clawhealth.py garmin menstrual --date 2026-03-03 --json
python {baseDir}/run_clawhealth.py garmin menstrual-calendar --since 2026-03-01 --until 2026-03-31 --json
```

## 诊断与分析

### 趋势摘要

```bash
python {baseDir}/run_clawhealth.py garmin trend-summary --days 7 --json
```

### 健康告警

```bash
python {baseDir}/run_clawhealth.py garmin flags --days 7 --json
```

说明：趋势/告警基于 `uhm_daily`，若需要 HRV 纳入分析，请先回填
`garmin hrv-dump`。

## 建议的日常流程

```bash
# 阶段 1：每日摘要
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-16 --until 2026-03-17 --json

# 阶段 2：HRV（昨天）
python {baseDir}/run_clawhealth.py garmin hrv-dump --date 2026-03-16 --json

# 阶段 2：训练指标（今天）
python {baseDir}/run_clawhealth.py garmin training-metrics --json

# 阶段 2：睡眠分期 + 身体成分（昨天）
python {baseDir}/run_clawhealth.py garmin sleep-dump --date 2026-03-16 --json
python {baseDir}/run_clawhealth.py garmin body-composition --date 2026-03-16 --json

# 诊断
python {baseDir}/run_clawhealth.py garmin flags --days 7 --json
python {baseDir}/run_clawhealth.py garmin trend-summary --days 7 --json
```

## 数据位置

- Tokens/config: `{baseDir}/config`
- SQLite DB: `{baseDir}/data/health.db`

可通过 `CLAWHEALTH_CONFIG_DIR` 和 `CLAWHEALTH_DB` 覆盖。

## 发布校验

```bash
python {baseDir}/validate_skill.py
python {baseDir}/test_minimal.py
```

可选的真实账号集成测试：

```bash
CLAWHEALTH_RUN_INTEGRATION_TESTS=1 python {baseDir}/test_integration_optional.py
```

## 安全说明

- 不要打印或记录账号密码。
- 优先使用密码文件。
- 数据仅保存在本地（SQLite + token 文件）。

## 当前限制

- 活动、女性健康、身体成分暂以原始 JSON 形式存储，尚未统一归一化。
- 女性健康接口依赖 garminconnect 版本支持，否则会返回 `UNSUPPORTED_ENDPOINT`。
- 部分指标依赖设备型号与账号设置。
- HRV 需要按日期回填（`hrv-dump`），训练指标默认针对“今天”。

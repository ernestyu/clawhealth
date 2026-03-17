---
name: clawhealth-garmin
description: Garmin Connect 数据同步与健康摘要（SQLite/JSON），通过 clawhealth CLI。
metadata: {"openclaw":{"requires":{"bins":["python"]},"homepage":"https://github.com/ernestyu/clawhealth","tags":["health","garmin","sqlite","cli"]}}
---

# Clawhealth Garmin Skill / Garmin 健康数据技能

本技能通过 `clawhealth` CLI 连接 Garmin Connect，将每日健康摘要同步到本地
SQLite 数据库，并提供 JSON 输出，便于 Agent 或脚本消费。

This skill uses the `clawhealth` CLI to connect to Garmin Connect, sync
daily summaries into a local SQLite DB, and produce JSON outputs for
automation and agent workflows.

## 适用场景 / When To Use

- 已有 Garmin 账号，希望本地保存健康摘要数据。
- 需要结构化 JSON 输出用于自动化或分析。

## 前置条件 / Prerequisites

- Python 3.10+
- 可访问 Garmin Connect 的网络环境
- Garmin 账号（可能需要 MFA）
- Docker 用户可选：使用预装依赖的镜像 `ernestyu/openclaw-patched`

## 安装 / Install

1.（可选）安装 `clawhealth`（二选一）:

```bash
python -m pip install git+https://github.com/ernestyu/clawhealth
```

```bash
python -m pip install -e /path/to/clawhealth
```

2. 配置凭证（推荐密码文件）:

使用本目录下的 `ENV.example`，在同目录创建 `.env`。脚本会自动加载。

## 登录 / Login (MFA)

```bash
python {baseDir}/run_clawhealth.py garmin login --json
```

若返回 `NEED_MFA`，请输入验证码:

```bash
python {baseDir}/run_clawhealth.py garmin login --mfa-code 123456 --json
```

## 常用命令 / Common Commands

同步一段日期:

```bash
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

查看同步状态:

```bash
python {baseDir}/run_clawhealth.py garmin status --json
```

获取日摘要（JSON）:

```bash
python {baseDir}/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

## 输出与数据位置 / Output & Data Locations

默认数据位置位于技能目录内：

- `{baseDir}/config`
- `{baseDir}/data/health.db`

可通过 `CLAWHEALTH_CONFIG_DIR` 和 `CLAWHEALTH_DB` 覆盖。

JSON 输出适合 Agent 解析；原始与映射后的数据均存入 SQLite。

## 发布自检 / Publish Validation

安装依赖（如需）：

```bash
python {baseDir}/bootstrap_deps.py
```

说明：技能目录下自带 `clawhealth` 代码（`{baseDir}/vendor/`），一般不需要额外安装
`clawhealth`；只需要补齐第三方依赖即可。

运行发布自检：

```bash
python {baseDir}/validate_skill.py
```

运行最小化测试：

```bash
python {baseDir}/test_minimal.py
```

运行联网集成测试（可跳过）：

```bash
CLAWHEALTH_RUN_INTEGRATION_TESTS=1 python {baseDir}/test_integration_optional.py
```

## 安全与隐私 / Security & Privacy

- 不要打印或记录任何凭证信息。
- 优先使用密码文件而不是明文环境变量。
- 本技能仅本地存储数据，不上传到第三方服务。

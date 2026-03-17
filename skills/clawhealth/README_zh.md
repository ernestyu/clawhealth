# clawhealth-garmin（OpenClaw 技能）

该技能把 Garmin Connect 的每日健康摘要同步到本地 SQLite，并提供适合 OpenClaw agent
消费的 JSON 输出。

## 快速开始

1) 在本目录创建 `.env`，参考 `ENV.example` 填写 Garmin 凭证（推荐密码文件）。

2) 如需安装 Python 依赖：

```bash
python {baseDir}/bootstrap_deps.py
```

技能目录中已自带 `clawhealth` 代码（`{baseDir}/vendor/`）；该脚本只会安装第三方依赖
（`garth`、`garminconnect`）。

3) 登录（支持 MFA）：

```bash
python {baseDir}/run_clawhealth.py garmin login --username you@example.com --json
python {baseDir}/run_clawhealth.py garmin login --mfa-code 123456 --json
```

4) 同步：

```bash
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

## 数据目录

- Token/配置：`{baseDir}/config`
- SQLite 数据库：`{baseDir}/data/health.db`

## 文档

- 技能说明：`SKILL.md`
- 发布检查：`PUBLISH.md`

## Docker

如果用 Docker 跑 OpenClaw，可以使用包含依赖的补丁镜像：

- `ernestyu/openclaw-patched`
- `https://github.com/ernestyu/openclaw-launcher`

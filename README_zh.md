# clawhealth

**语言：** 中文 | [English](README.md)

`clawhealth` 是给 OpenClaw 使用的 Garmin → SQLite 健康数据同步引擎（对应技能：
`clawhealth-garmin`）。

它支持 Garmin Connect 登录（含 MFA），把每日健康摘要同步到本地 SQLite 数据库，
并以小而稳定的命令输出 JSON，方便 OpenClaw agent 直接调用。

## OpenClaw 快速开始

### 1) 安装技能

发布到 ClawHub 后：

```bash
openclaw skill install clawhealth-garmin
```

本仓库本地开发安装：

```bash
openclaw skill install --path skills/clawhealth
```

### 2) 配置凭证

参考 `skills/clawhealth/ENV.example` 在 `skills/clawhealth/.env` 写入配置。

建议用密码文件（`CLAWHEALTH_GARMIN_PASSWORD_FILE`），不要把明文密码直接写到环境变量。

### 3) 安装 Python 依赖（如需要）

如果你的 OpenClaw 环境里还没有 `garminconnect` 与 `garth`，执行：

```bash
python skills/clawhealth/bootstrap_deps.py
```

该脚本会创建 `skills/clawhealth/.venv` 并安装依赖；`run_clawhealth.py` 会自动切换到
这个 venv 运行。

说明：技能目录下自带了 `clawhealth` 代码（`skills/clawhealth/vendor/`），因此使用技能时
不需要额外 `pip install clawhealth`；只需要补齐第三方依赖即可。

### 4) 登录、同步、查询

登录（可能返回 `NEED_MFA`）：

```bash
python skills/clawhealth/run_clawhealth.py garmin login --json
```

输入 MFA：

```bash
python skills/clawhealth/run_clawhealth.py garmin login --mfa-code 123456 --json
```

同步一段日期：

```bash
python skills/clawhealth/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
```

查询日摘要：

```bash
python skills/clawhealth/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

## Docker（补丁镜像）

如果你用 Docker 跑 OpenClaw，可以使用我提供的补丁镜像（已包含本技能需要的 Python 依赖）：

- 镜像：`ernestyu/openclaw-patched`
- 一键安装/启动脚本：`https://github.com/ernestyu/openclaw-launcher`

## 数据与安全说明

- SQLite 数据库路径由 `CLAWHEALTH_DB` 控制（技能内默认：`skills/clawhealth/data/health.db`）。
- Garmin session token 存放在 `CLAWHEALTH_CONFIG_DIR`（技能内默认：`skills/clawhealth/config`）。
- `clawhealth` 不会把健康数据上传到第三方服务；数据只保存在本地文件中。

## 独立 CLI（开发者）

如果你不在 OpenClaw 环境中使用：

```bash
python -m pip install -e .
clawhealth --help
```

## 许可证

MIT

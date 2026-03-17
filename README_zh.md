# clawhealth

**语言:** 中文 | [English](README.md)

`clawhealth` 是一个以 OpenClaw 为第一目标的 Garmin Connect 同步工具。它支持
MFA 登录，将健康数据同步到本地 SQLite，并提供 OpenClaw 可调用的 JSON 命令。

本仓库的主要产物是 `skills/clawhealth/` 下的 OpenClaw 技能包。

## 能做什么

- Garmin 用户名/密码登录（支持 MFA）
- 同步每日健康汇总到 SQLite（步数、总睡眠、压力、Body Battery、SpO2、呼吸、体重等）
- 获取睡眠分期与睡眠评分（`garmin sleep-dump`）
- 获取 HRV（`garmin hrv-dump`）与训练指标（`garmin training-metrics`）
- 获取身体成分（`garmin body-composition`）
- 获取活动列表与完整活动详情（`garmin activities`、`garmin activity-details`）
- 获取女性健康日视图与日历范围（实验性，需 garminconnect 支持且账号启用）
- 输出适合 OpenClaw Agent 的 JSON 结果
- 在 SQLite 中保存原始 JSON 以便后续精细分析

说明：部分数据依赖设备与账号设置（例如睡眠分期、身体成分、女性健康）。
说明：女性健康接口需要 garminconnect 提供支持，否则会返回 `UNSUPPORTED_ENDPOINT`。

## OpenClaw（主要）

### 第一步：安装技能

OpenClaw 会从 `<workspace>/skills`（优先）和 `~/.openclaw/skills`（共享/本地）加载技能。
你可以使用以下两种方式安装。

方案 A：通过 ClawHub CLI 安装（发布后推荐）：

```bash
npm i -g clawhub
clawhub install clawhealth-garmin
```

方案 B：从 GitHub 源码安装（物理放置到 workspace/skills）：

```bash
git clone https://github.com/ernestyu/clawhealth.git /home/node/.openclaw/workspace/clawhealth_temp
mv /home/node/.openclaw/workspace/clawhealth_temp/skills/clawhealth /home/node/.openclaw/workspace/skills/
rm -rf /home/node/.openclaw/workspace/clawhealth_temp
```

### 第二步：首次运行的依赖

原生 OpenClaw（非 Docker）：
- 首次执行 Garmin 相关命令时，`run_clawhealth.py` 会尝试自动安装依赖到 `skills/clawhealth/.venv`。
- 可通过 `CLAWHEALTH_AUTO_BOOTSTRAP=0` 关闭自动安装。

Docker OpenClaw：
- 推荐使用 `ernestyu/openclaw-patched`（已打好依赖补丁）。
- 若仍使用官方镜像，可在容器内执行 `python skills/clawhealth/bootstrap_deps.py`
  （或设置 `CLAWHEALTH_AUTO_BOOTSTRAP_IN_DOCKER=1` 允许自动安装）。

### 第三步：配置用户名与密码

两种方式任选其一：

- 让 OpenClaw 写入配置文件：
  在 `skills/clawhealth/` 下创建 `.env` 与密码文件（参考 `skills/clawhealth/ENV.example`）。
- 在终端中手工配置（容器示例）：

```bash
docker exec -it openclaw sh -c '
cd ~/.openclaw/workspace/skills/clawhealth &&
printf "CLAWHEALTH_GARMIN_USERNAME=you@example.com\nCLAWHEALTH_GARMIN_PASSWORD_FILE=./garmin_pass.txt\n" > .env &&
printf "YOUR_GARMIN_PASSWORD" > garmin_pass.txt &&
chmod 600 .env garmin_pass.txt &&
echo "配置完成，请回到聊天界面触发登录。"
'
```

说明：

- 像 `./garmin_pass.txt` 这样的相对路径会由 `run_clawhealth.py` 解析为技能目录下的路径。
- 请不要把 `.env` 与密码文件提交到 git，并注意文件权限。

### 第四步：登录（MFA）与同步

登录步骤 1（触发 MFA，需要用户名 + 密码来源）：

```bash
python skills/clawhealth/run_clawhealth.py garmin login --username you@example.com --json
```

登录步骤 2（提交 MFA 验证码）：

```bash
python skills/clawhealth/run_clawhealth.py garmin login --mfa-code 123456 --json
```

同步与查询：

```bash
python skills/clawhealth/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py daily-summary --date 2026-03-03 --json
```

### 可选：高级接口

女性健康接口为实验性功能，需 garminconnect 版本支持。

```bash
python skills/clawhealth/run_clawhealth.py garmin sleep-dump --date 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin body-composition --date 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin activities --since 2026-03-01 --until 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin activity-details --activity-id 123456789 --json
python skills/clawhealth/run_clawhealth.py garmin menstrual --date 2026-03-03 --json
python skills/clawhealth/run_clawhealth.py garmin menstrual-calendar --since 2026-03-01 --until 2026-03-31 --json
```

## 不使用 OpenClaw（次要）

如需直接使用 CLI：

```bash
python -m pip install -e .
clawhealth --help
```

## Roadmap

参见 `ROADMAP.md`。

## 许可证

MIT

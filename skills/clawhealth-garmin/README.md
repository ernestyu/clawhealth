# clawhealth-garmin (Skill Package)

This folder contains the publishable **OpenClaw skill** that wraps the
`clawhealth` Python package/CLI for Garmin health data.

If you are looking for the Python package / CLI documentation (PyPI users),
please read the root `README.md` instead.

For OpenClaw skill users/operators, the key docs are:

- `SKILL.md` / `SKILL_zh.md` — skill behavior, callbacks, and install flows
- `PUBLISH.md` — release checklist for updating the skill on ClawHub
- The root `README.md` — high‑level overview of what `clawhealth` can do

Below is a **skill‑oriented** quickstart，迁移自仓库根目录旧版 README，方便在
只浏览 `skills/` 时仍能看到安装说明。

---

## What It Can Do (via skill)

- Login with Garmin username/password (MFA supported)
- Sync daily health summaries into SQLite (steps, sleep total, stress, body battery, SpO2, respiration, weight)
- Fetch sleep stages + sleep score (`garmin sleep-dump`)
- Fetch HRV (`garmin hrv-dump`) and training readiness/status/endurance/fitness age (`garmin training-metrics`)
- Fetch body composition metrics (`garmin body-composition`)
- Fetch activity lists and full activity details (`garmin activities`, `garmin activity-details`)
- Fetch menstrual day view and calendar range if supported by garminconnect and enabled on the account (experimental)
- Produce JSON outputs for agent workflows
- Store raw JSON payloads in SQLite for full-fidelity access

Notes:

- Some metrics depend on your Garmin device and account settings (e.g., sleep stages, body composition, menstrual data).
- Menstrual endpoints require garminconnect support; if missing, the command returns `UNSUPPORTED_ENDPOINT`.

---

## OpenClaw Install (Skill‑level)

### Step 1: Place the skill directory

OpenClaw loads skills from `<workspace>/skills` (highest precedence) and
`~/.openclaw/skills` (shared/local). If you are installing from GitHub
直接拷贝，可以用类似指令：

```bash
git clone https://github.com/ernestyu/clawhealth.git /home/node/.openclaw/workspace/clawhealth_temp
mv /home/node/.openclaw/workspace/clawhealth_temp/skills/clawhealth-garmin /home/node/.openclaw/workspace/skills/
rm -rf /home/node/.openclaw/workspace/clawhealth_temp
```

After install, the skill directory is typically：

- `<skillDir>` = `/home/node/.openclaw/workspace/skills/clawhealth-garmin`

如果从 ClawHub 安装，则路径由 ClawHub 决定（通常也是 workspace 下的
`skills/clawhealth-garmin`）。

### Step 2: Dependencies on first run

> 注意：最新版本推荐在安装阶段由 ClawHub/运维脚本跑完依赖安装；下面是手工模式的补充说明。

Native OpenClaw (non‑Docker):

- 你可以在 skill 目录下创建一个虚拟环境并安装依赖：

  ```bash
  cd "$skillDir"
  python -m venv .venv
  . .venv/bin/activate
  pip install garminconnect>=0.2.1,<0.3.0 garth>=0.5.0,<0.6.0
  ```

Docker OpenClaw:

- 推荐：使用 `ernestyu/openclaw-patched` 镜像（已预装依赖）
- 若仍使用官方镜像，可在容器内运行 `bootstrap_deps.py`：

  ```bash
  docker exec -it openclaw sh -lc '
    cd /home/node/.openclaw/workspace/skills/clawhealth-garmin && \
    python bootstrap_deps.py
  '
  ```

### Step 3: Configure username + password

你有两种方式配置 Garmin 凭据：

- **方式 A：手工创建 .env + 密码文件**

  ```bash
  cd "$skillDir"
  printf "CLAWHEALTH_GARMIN_USERNAME=you@example.com\nCLAWHEALTH_GARMIN_PASSWORD_FILE=./garmin_pass.txt\n" > .env
  printf "YOUR_GARMIN_PASSWORD" > garmin_pass.txt
  chmod 600 .env garmin_pass.txt
  ```

- **方式 B：通过 docker exec 在容器里执行一段脚本**

  ```bash
  docker exec -it openclaw sh -lc '
    cd /home/node/.openclaw/workspace/skills/clawhealth-garmin && \
    printf "CLAWHEALTH_GARMIN_USERNAME=you@example.com\nCLAWHEALTH_GARMIN_PASSWORD_FILE=./garmin_pass.txt\n" > .env && \
    printf "YOUR_GARMIN_PASSWORD" > garmin_pass.txt && \
    chmod 600 .env garmin_pass.txt && \
    echo "Configuration completed. Return to your chat UI and trigger login."
  '
  ```

Notes:

- 相对路径（例如 `./garmin_pass.txt`）会由 `run_clawhealth.py` 解释为以 skill 目录为 base 的路径。
- 不要把 `.env` 和密码文件提交到 git，并注意权限控制。

### Step 4: Login (MFA) and sync

在 skill context 下，通常会由 OpenClaw/Agent 触发登录流程，但你也可以直接在容器里测试：

```bash
cd "$skillDir"
python run_clawhealth.py garmin login --username you@example.com --json
# 获取 MFA 验证码后：
python run_clawhealth.py garmin login --mfa-code 123456 --json

# 同步与查询
python run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
python run_clawhealth.py daily-summary --date 2026-03-03 --json
```

### Optional: Advanced endpoints

女性健康、活动详情等高级接口可以按需调用：

```bash
python run_clawhealth.py garmin sleep-dump --date 2026-03-03 --json
python run_clawhealth.py garmin body-composition --date 2026-03-03 --json
python run_clawhealth.py garmin activities --since 2026-03-01 --until 2026-03-03 --json
python run_clawhealth.py garmin activity-details --activity-id 123456789 --json
python run_clawhealth.py garmin menstrual --date 2026-03-03 --json
python run_clawhealth.py garmin menstrual-calendar --since 2026-03-01 --until 2026-03-31 --json
```

---

## Quick smoke checks

本目录下提供了一些简单的检查脚本：

```bash
python {baseDir}/validate_skill.py
python {baseDir}/test_minimal.py
```

建议在修改 SKILL 后跑一遍，确保基本行为和 ClawHub 规范符合预期。

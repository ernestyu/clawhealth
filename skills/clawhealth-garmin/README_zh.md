# clawhealth-garmin（技能包）

该目录是可发布的 **OpenClaw 技能包**，对外包装了 `clawhealth`
Python 包 / CLI，用于访问 Garmin 健康数据。

如果你是 PyPI / CLI 用户，请阅读仓库根目录的 `README_zh.md`；
如果你是在 OpenClaw 环境下使用该技能，请以本目录下的
`SKILL_zh.md` / `SKILL.md` 为主文档。

下面是一个面向技能运维者的简要说明，便于在只浏览
`skills/` 目录时也能看到关键信息。

---

## 能做什么（通过技能）

- 使用 Garmin 用户名/密码登录（支持 MFA）
- 将每日健康汇总同步到 SQLite（步数、总睡眠、压力、Body Battery、SpO2、呼吸、体重等）
- 获取睡眠分期与睡眠评分（`garmin sleep-dump`）
- 获取 HRV（`garmin hrv-dump`）与训练指标（`garmin training-metrics`）
- 获取身体成分（`garmin body-composition`）
- 获取活动列表与完整活动详情（`garmin activities`、`garmin activity-details`）
- 获取女性健康日视图与日历范围（实验性，需 garminconnect 支持且账号启用）
- 输出适合 OpenClaw Agent 的 JSON 结果
- 在 SQLite 中保存原始 JSON 以便后续精细分析

说明：

- 部分指标依赖设备与账号设置（例如睡眠分期、身体成分、女性健康）。
- 女性健康接口需要 garminconnect 提供支持，否则会返回 `UNSUPPORTED_ENDPOINT`。

---

## 在 OpenClaw 中安装（技能视角）

### 第一步：放置技能目录

OpenClaw 会从 `<workspace>/skills`（优先）和 `~/.openclaw/skills`
（共享/本地）加载技能。如果你直接从 GitHub 拷贝，可以类似这样操作：

```bash
git clone https://github.com/ernestyu/clawhealth.git /home/node/.openclaw/workspace/clawhealth_temp
mv /home/node/.openclaw/workspace/clawhealth_temp/skills/clawhealth-garmin /home/node/.openclaw/workspace/skills/
rm -rf /home/node/.openclaw/workspace/clawhealth_temp
```

安装完成后，技能目录通常是：

- `<skillDir>` = `/home/node/.openclaw/workspace/skills/clawhealth-garmin`

如果通过 ClawHub 安装，则路径由 ClawHub 决定（一般也是 workspace
下的 `skills/clawhealth-garmin`）。

### 第二步：依赖（首次运行）

> 建议在安装阶段由 ClawHub 或运维脚本一次性完成依赖安装。以下是手工模式的参考。

**原生 OpenClaw（非 Docker）**：

- 在技能目录下创建虚拟环境并安装依赖：

  ```bash
  cd "$skillDir"
  python -m venv .venv
  . .venv/bin/activate
  pip install "garminconnect>=0.2.1,<0.3.0" "garth>=0.5.0,<0.6.0"
  ```

**Docker OpenClaw**：

- 推荐使用 `ernestyu/openclaw-patched` 镜像（已预装依赖）；
- 若仍使用官方镜像，可在容器内运行 `bootstrap_deps.py`：

  ```bash
  docker exec -it openclaw sh -lc '
    cd /home/node/.openclaw/workspace/skills/clawhealth-garmin && \
    python bootstrap_deps.py
  '
  ```

### 第三步：配置用户名与密码

你可以通过两种方式配置 Garmin 凭据：

**方式 A：手工创建 `.env` 与密码文件**

```bash
cd "$skillDir"
printf "CLAWHEALTH_GARMIN_USERNAME=you@example.com\nCLAWHEALTH_GARMIN_PASSWORD_FILE=./garmin_pass.txt\n" > .env
printf "YOUR_GARMIN_PASSWORD" > garmin_pass.txt
chmod 600 .env garmin_pass.txt
```

**方式 B：在容器中执行一段脚本**

```bash
docker exec -it openclaw sh -lc '
  cd /home/node/.openclaw/workspace/skills/clawhealth-garmin && \
  printf "CLAWHEALTH_GARMIN_USERNAME=you@example.com\nCLAWHEALTH_GARMIN_PASSWORD_FILE=./garmin_pass.txt\n" > .env && \
  printf "YOUR_GARMIN_PASSWORD" > garmin_pass.txt && \
  chmod 600 .env garmin_pass.txt && \
  echo "配置完成，请回到聊天界面触发登录。"
'
```

说明：

- 相对路径（例如 `./garmin_pass.txt`）会由 `run_clawhealth.py`
  解释为以技能目录为 base 的路径；
- 不要把 `.env` 和密码文件提交到 git，并注意权限控制。

### 第四步：登录（含 MFA）与同步

在实际使用中，登录过程通常由 OpenClaw/Agent 触发，你也可以直接在容器里测试：

```bash
cd "$skillDir"
python run_clawhealth.py garmin login --username you@example.com --json
# 收到验证码后：
python run_clawhealth.py garmin login --mfa-code 123456 --json

# 同步与查询
python run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
python run_clawhealth.py daily-summary --date 2026-03-03 --json
```

### 可选：高级接口

女性健康、活动详情等高级接口可按需调用：

```bash
python run_clawhealth.py garmin sleep-dump --date 2026-03-03 --json
python run_clawhealth.py garmin body-composition --date 2026-03-03 --json
python run_clawhealth.py garmin activities --since 2026-03-01 --until 2026-03-03 --json
python run_clawhealth.py garmin activity-details --activity-id 123456789 --json
python run_clawhealth.py garmin menstrual --date 2026-03-03 --json
python run_clawhealth.py garmin menstrual-calendar --since 2026-03-01 --until 2026-03-31 --json
```

---

## 快速校验

本目录提供了一些简单的检查脚本：

```bash
python {baseDir}/validate_skill.py
python {baseDir}/test_minimal.py
```

建议在修改 SKILL 后跑一遍，以确保行为和 ClawHub 规范符合预期。

# clawhealth-garmin（OpenClaw 技能）

说明：ClawHub/技能中心通常只读取 `SKILL.md`，因此 `SKILL.md` 保持英文。
此文件是中文补充说明，方便国内用户查看。

## 功能

- Garmin Connect 登录（支持 MFA）
- 同步每日健康摘要到本地 SQLite
- 输出 JSON 便于 OpenClaw agent 使用

## 前置条件

- Python 3.10+
- 可访问 Garmin Connect 的网络环境
- Garmin 账号（可能需要 MFA）

Docker 用户可选：使用已预装依赖的镜像 `ernestyu/openclaw-patched`。

## 配置

1) 在 `{baseDir}/.env` 填写配置（参考 `{baseDir}/ENV.example`）。

推荐使用密码文件 `CLAWHEALTH_GARMIN_PASSWORD_FILE`，避免明文密码环境变量。

2) 如需安装依赖：

```bash
python {baseDir}/bootstrap_deps.py
```

说明：

- 技能目录自带 `clawhealth` 代码（`{baseDir}/vendor/`）。
- 该脚本只安装第三方依赖（`garth`、`garminconnect`）到 `{baseDir}/.venv`。
- `{baseDir}/run_clawhealth.py` 若检测到 venv 会自动切换运行。

## 常用命令

```bash
python {baseDir}/run_clawhealth.py garmin login --json
python {baseDir}/run_clawhealth.py garmin login --mfa-code 123456 --json
python {baseDir}/run_clawhealth.py garmin sync --since 2026-03-01 --until 2026-03-03 --json
python {baseDir}/run_clawhealth.py daily-summary --date 2026-03-03 --json
```


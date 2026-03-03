# clawhealth 技术路线与 CLI 设计草案（Garmin 第一阶段）

> 本文是 clawhealth 的设计蓝本，取代早期“Flask+REST+MCP 服务端”的重方案。
> 当前目标：**CLI-first + 本地 SQLite + Garmin（个人账号）**。

---

## 1. 项目定位（重新定义）

- clawhealth 是一个 **面向 OpenClaw / Agent 的健康数据 CLI 工具箱**。
- 第一阶段只支持 **Garmin Connect 个人账号**，后续可以扩展其他 provider（Huami、Suunto 等）。
- 交互原则：
  - **所有与 Agent 的交互尽量走 CLI**（命令行 + JSON 输出），不强制跑 REST API 服务；
  - 人类也可以直接用同一套 CLI 调试。

---

## 2. 存储与边界：独立健康 SQLite，不改动现有 DB

### 2.1 独立健康 DB

- clawhealth 不往 Clawkb / OpenClaw 自己的 DB 里塞健康数据。
- 使用专门的 SQLite 文件，例如：
  - 默认路径：`/opt/clawhealth/data/health.db`
  - 或通过环境变量 / CLI 参数覆盖：`--db /path/to/health.db`

### 2.2 模型（UHM 的简化版）

第一阶段先只做「最小但有用」的日聚合 + 同步记录：

- `uhm_daily`：
  - `date_local` (YYYY-MM-DD)
  - `timezone` / `offset_to_utc_min`
  - `sleep_total_min`, `sleep_score`
  - `rhr_bpm`, `steps`, `distance_m`, `calories_total`
  - `stress_avg`, `body_battery_start`, `body_battery_end`
  - `weight_kg`
  - `extra_metrics` (JSON 文本，放长尾指标)
  - `source_vendor` (固定 'garmin')
  - `driver_version`, `mapping_version`, `raw_ref`, `ingested_at`

- `sync_runs`：
  - `run_id`, `started_at`, `ended_at`
  - `stage` (sync / download / import)
  - `status` (running / success / error)
  - `range_start`, `range_end`
  - `error_code`, `error_message`
  - `driver_version`

（后续可以按需要补充 `uhm_activity` 等表，第一版先聚焦日级 trend。）

### 2.3 单位与时间规范（硬规则）

- 距离：米（m）
- 体重：千克（kg）
- 能量：千卡（kcal）
- 时间：分钟/秒在 schema 中固定，不混用；
- 所有事件时间统一用 UTC（ISO 或 epoch），辅以 `timezone` + `offset_to_utc_min` 来还原本地日期线。

---

## 3. Driver 技术栈选型：python-garminconnect + garth

### 3.1 不再依赖 GarminDb CLI

- `garmindb_cli.py` / GarminDb 仓库只作为历史经验参考，不再作为 clawhealth 的依赖：
  - 它偏重、包依赖多、功能范围大（Fitbit/MSHealth/Jupyter 等），和我们要的轻量 CLI 不契合；
  - 交互模式是为人类设计的，不适合 Agent 自动化。

### 3.2 python-garminconnect 作为高层 API

- 使用社区维护良好的 `python-garminconnect` 作为高层数据访问库：
  - 提供登录、拉取睡眠/日汇总/活动等 API；
  - 生态成熟、示例齐全。

### 3.3 garth 作为底层认证与会话管理

- `garth` 提供 Garmin SSO + Connect 的认证与 MFA 支持：
  - 支持 OAuth token 持久化到文件（类似 `GARTH_HOME`）；
  - 支持自定义 MFA handler（我们不必依赖 `input()`）。

### 3.4 组合方式

第一阶段 driver 选择：

- **官方组合：`python-garminconnect`（高层） + `garth`（底层认证）**；
- clawhealth 不直接操作裸 HTTP，而是通过这一层封装。

---

## 4. CLI 形状（Garmin 第一阶段）

### 4.1 顶层命令

```bash
clawhealth garmin login      # 完成用户名/密码/MFA 登录，写入会话
clawhealth garmin sync       # 用现有会话拉取数据并更新 SQLite
clawhealth garmin status     # 查看同步状态 & 数据新鲜度
clawhealth daily-summary     # 给人/Agent 看的某日摘要视图
```

未来可以扩展其它 provider 子命令（`clawhealth huami ...` 等），但 CLI 结构保持类似。

### 4.2 `clawhealth garmin login`

职责：

- 用 `python-garminconnect` + `garth` 完成登录；
- 将会话/Token 写入指定的 `config_dir`（默认 `/opt/clawhealth/config`）；
- 支持「两步登录」：
  - 第一次调用发现需要 MFA → 返回一个错误码 `NEED_MFA`，不阻塞等待输入；
  - 第二次调用携带 `--mfa-code` 完成验证。

参数草案：

```bash
clawhealth garmin login \
  --username YOUR_EMAIL \
  --password-file /path/to/pass.txt \
  --config-dir /opt/clawhealth/config \
  [--mfa-code 123456] \
  [--json]
```

行为：

- 无 `--mfa-code` 情况下：
  - 登录成功：返回 `{ ok: true, auth_state: "AUTH_OK" }`（当 `--json` 时 JSON 输出）；
  - 遇到 MFA：返回 `{ ok: false, error_code: "NEED_MFA", message: "MFA required" }`；
- 携带 `--mfa-code` 时：
  - 正确：写入会话文件，并返回 `AUTH_OK`；
  - 错误/过期：返回 `AUTH_FAILED`。

Agent 使用方式：

1. 调用 `clawhealth garmin login --username ... --password-file ... --json`；
2. 若看到 `NEED_MFA`，向用户要验证码；
3. 拿到验证码后，再调用一次 `--mfa-code`；
4. 成功后，后续 `sync/status` 都复用这个会话，直到 token 失效。

### 4.3 `clawhealth garmin sync`

职责：

- 读取 `config_dir` 下的会话；
- 从 Garmin Connect 拉取指定日期范围内的数据；
- 将数据映射到 UHM（`uhm_daily` 等）写入 SQLite；
- 记录一次同步 run 到 `sync_runs`。

示例：

```bash
clawhealth garmin sync \
  --since 2026-03-01 \
  --until 2026-03-03 \
  --config-dir /opt/clawhealth/config \
  --db /opt/clawhealth/data/health.db \
  [--json]
```

行为要点：

- 如会话无效，返回：

  ```json
  {
    "ok": false,
    "error_code": "AUTH_CHALLENGE_REQUIRED",
    "message": "Session expired or invalid; please re-run login with MFA.",
    "auth_state": "NEED_MFA"
  }
  ```

- 如正常：
  - 对每一天拉取数据（睡眠、步数、RHR 等），写入/更新 `uhm_daily`；
  - 写 `sync_runs` 记录这次同步范围、状态与错误信息（如果有）。

### 4.4 `clawhealth garmin status`

职责：

- 从 `sync_runs`/`uhm_daily` 中计算：
  - 最近一次成功同步时间；
  - 当前数据新鲜度（距今多少小时/天）；
  - 已覆盖的日期范围。

示例：

```bash
clawhealth garmin status --db /opt/clawhealth/data/health.db --json
```

典型输出：

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

Agent 可以用它来判断是否需要提示用户“最近没同步数据”。

### 4.5 `clawhealth daily-summary`

职责：

- 读取 `uhm_daily`，输出某日的简明摘要，适合直接粘进 prompt 或给人看。

示例：

```bash
clawhealth daily-summary --date 2026-03-02 --db /opt/clawhealth/data/health.db
```

输出（人类/Agent 都看得懂的短文本）：

```text
2026-03-02 健康概要（来源：Garmin，本地 UHM_v1）
- 睡眠：7.4 小时，睡眠得分 82（深睡 1.5h，REM 2.0h）
- 静息心率：52 bpm
- 步数：10,432 步（约 7.8 km）
- 总能量消耗：2,150 kcal（活动 650 kcal）
- 压力：日均 23 / 峰值 65
- 身体电量：起床 78 → 睡前 43
- 体重：68.2 kg
```

（后续可以再加 `--json` 输出结构化版本。）

---

## 5. 与 OpenClaw / Agent 的集成方式

- 不强制 MCP/REST，默认由 OpenClaw 通过 CLI 调用：
  - `clawhealth garmin status --json` → 读 JSON，判断是否需要同步；
  - `clawhealth garmin sync --json` → 触发同步，并根据错误码处理 MFA/过期；
  - `clawhealth daily-summary --date ...` → 直接拼进日报/对话。

- 未来如需要 MCP 工具，可以在 OpenClaw 一侧增加一个轻量 wrapper，把这些 CLI 封装为 MCP tool（不必把 Flask 放回 clawhealth 内部）。

---

## 6. 后续演进路线（简版）

1. **阶段 1**：
   - 实现 `garmin login/sync/status` 与 `daily-summary` 的基本功能；
   - SQLite schema 覆盖 `uhm_daily` + `sync_runs`；
   - 文档对齐（README/README_zh + CLI_HELP_SPEC）。

2. **阶段 2**：
   - 丰富 UHM 模型（活动事件 uhm_activity 等）；
   - 增加更多查询 CLI（`export-series` 之类）。

3. **阶段 3**：
   - 根据实际使用效果，决定是否需要 MCP wrapper / Web UI；
   - 考虑加入其他 provider（Huami 等），但坚持 CLI-first、SQLite-only 的架构原则。

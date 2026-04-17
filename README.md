# hermes-config

用于统一管理当前 Hermes agent 的可版本化配置、规则、记忆与技能快照。

## 设计原则

- **与项目代码仓库隔离**：不会影响 `~/projects/*` 下各项目的 Git。
- **与 Hermes 源码仓库隔离**：Hermes 源码单独放在 `hermes-agent-config` 仓库中管理。
- **默认不上传敏感信息**：运行态数据、日志、数据库、会话记录、缓存、密钥等不纳入版本控制。
- **记忆/要求可统一管理**：会同步 Hermes 的用户偏好与环境记忆快照，便于审阅和回溯。

## 当前跟踪内容

同步脚本会把下列内容导出到 `tracked/hermes/`：

- `SOUL.md`
- `memories/USER.md`
- `memories/MEMORY.md`
- `skills/`
- `config.yaml` 的**脱敏副本**

> 注意：`~/.hermes/config.yaml` 中若包含 API Key、Token、密码等字段，仓库中只保存脱敏后的副本，不直接提交真实密钥。

## 常用脚本

```bash
python3 scripts/sync_hermes_config.py
bash scripts/commit_and_push.sh
```

- `sync_hermes_config.py`：从 `~/.hermes` 导出可版本化内容到当前仓库
- `commit_and_push.sh`：同步、生成详细提交信息、提交并推送到 GitHub

## 目录结构

```text
tracked/hermes/              # 脱敏/筛选后的可版本化配置快照
scripts/                     # 同步与提交脚本
```

---
name: hermes-ubuntu-stack-migration
description: Build and deliver a reusable Ubuntu installation/migration kit for recreating this user's Hermes Agent workstation, including Hermes, Claude Code, Codex, Gemini, cc-switch, CodeIndex conventions, manual docs, automation script, verification, and email delivery.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, ubuntu, migration, bootstrap, claude-code, codex, cc-switch, codeindex, email]
    related_skills: [hermes-agent, claude-code, codex, himalaya]
---

# Hermes Ubuntu Stack Migration Kit

Use this skill when the user asks to recreate, migrate, package, or document an Ubuntu system similar to their current Hermes workstation, especially including Hermes Agent, Claude Code, Codex, cc-switch, CodeIndex, gateway/email, or directory conventions.

## Core user expectations

- Reply in Chinese.
- Do **not** paste long installation manuals directly into WeChat; long messages may be replaced by `⚠️ Response truncated due to output length limit`.
- Generate files locally, package them, email the complete package to `50803169@qq.com`, and only send a compact WeChat summary.
- Do not include secrets, tokens, OAuth state, mailbox authorization codes, Weixin credentials, or raw `~/.hermes/.env` contents in the package.
- The user's standard CodeIndex convention is `~/projects/CodeIndex/CreateIndex.py` (central script), not project-local copies.
- cc-switch may be a private/local repo; make scripts accept `CC_SWITCH_REPO=...` instead of hardcoding.
- The package must include not only installers but also the user's agent configuration/rules snapshot: Hermes `config.yaml`, `personality.md`, skills/profiles/scripts, Claude settings/rules, Codex config, cc-switch config-like files, and repo metadata. Redact secrets rather than omitting the existence of those files.
- The user's Hermes setup is split across multiple Git repos; always discover and record them rather than assuming one repo.

## Recommended workflow

1. **Inspect current environment** with tools, do not assume from memory:
   ```bash
   lsb_release -ds || . /etc/os-release && echo "$PRETTY_NAME"
   uname -m
   node --version || true
   npm --version || true
   python3 --version || true
   git --version || true
   tmux -V || true
   command -v hermes || true; hermes --version || true
   command -v claude || true; claude --version || true
   command -v codex || true; codex --version || true
   command -v gemini || true; gemini --version || true
   [ -d ~/cc-switch ] && echo ~/cc-switch
   [ -d ~/.hermes/hermes-agent ] && echo ~/.hermes/hermes-agent
   [ -f ~/.codex/config.toml ] && echo ~/.codex/config.toml
   ```

2. **Create a kit directory**, for example:
   ```text
   /tmp/hermes-ubuntu-kit/
   ```

3. **Generate these files**:
   - `README.md` — overview and quick start
   - `MANUAL_INSTALL.md` — manual Ubuntu install instructions
   - `MIGRATION_CHECKLIST.md` — old/new machine checklist and smoke tests
   - `install-hermes-stack.sh` — automatic bootstrap script
   - `config-templates/hermes.env.example`
   - `config-templates/codex.config.toml.example`
   - `config-templates/hermes-config-notes.md`
   - `config-snapshot/` — redacted current configuration and rules snapshot
   - `repo-metadata/` — Git repo remotes/branches/HEAD/status/unpushed commits
   - `restore-scripts/restore-config-snapshot.sh` — helper to restore non-secret config
   - `REPOSITORIES.md` — human-readable list of effective repos and warnings

4. **Discover split Git repos before generating the installer**:
   ```bash
   python3 - <<'PY'
   from pathlib import Path
   import subprocess
   roots=[Path.home()/'.hermes', Path.home()/'agent-configs', Path.home()/'projects', Path.home()/'.codex', Path.home()/'.claude']
   for root in roots:
       if not root.exists(): continue
       for gitdir in root.rglob('.git'):
           repo = gitdir.parent
           if any(x in repo.parts for x in ['node_modules','cache','sessions','logs']): continue
           def run(args):
               try: return subprocess.check_output(args,cwd=repo,text=True,stderr=subprocess.STDOUT,timeout=10).strip()
               except Exception as e: return f'ERR {e}'
           print('\n###', repo)
           print('branch:', run(['git','branch','--show-current']))
           print('status:', run(['git','status','--short','--branch']))
           print('head:', run(['git','log','-1','--oneline','--decorate']))
           print('remotes:\n'+run(['git','remote','-v']))
   PY
   ```
   In the validated environment, important repos were:
   - `~/.hermes/hermes-agent` → `git@ssh.github.com:liuli263/hermes-agent-config.git` (custom Hermes Agent code, not just upstream)
   - `~/agent-configs/hermes-config` → `git@ssh.github.com:liuli263/hermes-config.git` (configuration/memory/skills snapshot)
   - `~/projects/CodeIndex` → `git@ssh.github.com:liuli263/CodeIndex.git` (central CodeIndex; check for unpushed commits)

5. **Automatic install script should:**
   - require non-root execution and use `sudo` only for apt
   - install apt prerequisites: `ca-certificates curl wget git unzip zip tar jq build-essential python3 python3-venv python3-pip python3-dev tmux ripgrep fd-find git-lfs openssh-client libssl-dev pkg-config xdg-utils`
   - install Node.js 22.x if needed
   - create `~/.local/bin`, `~/.hermes`, `~/.hermes/node/bin`, `~/projects`, `~/agent-configs`
   - install Hermes via official installer for bootstrapping:
     ```bash
     curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
     ```
   - then clone/check out the user's effective Hermes Agent repo, not just upstream, when known:
     ```bash
     HERMES_REPO="${HERMES_REPO:-git@ssh.github.com:liuli263/hermes-agent-config.git}"
     HERMES_UPSTREAM_REPO="${HERMES_UPSTREAM_REPO:-https://github.com/NousResearch/hermes-agent.git}"
     HERMES_COMMIT="${HERMES_COMMIT:-f60a3733}"
     git clone "$HERMES_REPO" "$HOME/.hermes/hermes-agent"
     (cd "$HOME/.hermes/hermes-agent" && git remote add upstream "$HERMES_UPSTREAM_REPO" || true)
     (cd "$HOME/.hermes/hermes-agent" && git fetch origin && git checkout "$HERMES_COMMIT" || true)
     ```
   - clone/check out the separate Hermes config snapshot repo when known:
     ```bash
     HERMES_CONFIG_REPO="${HERMES_CONFIG_REPO:-git@ssh.github.com:liuli263/hermes-config.git}"
     HERMES_CONFIG_COMMIT="${HERMES_CONFIG_COMMIT:-adb9706}"
     git clone "$HERMES_CONFIG_REPO" "$HOME/agent-configs/hermes-config" || true
     (cd "$HOME/agent-configs/hermes-config" && git fetch origin && git checkout "$HERMES_CONFIG_COMMIT" || true)
     ```
   - set npm prefix to `~/.hermes/node`
   - install CLIs:
     ```bash
     npm install -g @anthropic-ai/claude-code @openai/codex
     npm install -g @google/gemini-cli || true
     ```
   - add `~/.local/bin` and `~/.hermes/node/bin` to shell PATH
   - create a secrets template at `~/.hermes/.env` only if missing, chmod 600
   - create minimal `~/.codex/config.toml` if missing
   - optionally clone/build cc-switch only if `CC_SWITCH_REPO` is supplied
   - optionally clone CodeIndex only if `CODEINDEX_REPO` is supplied
   - print next steps: `hermes setup`, `hermes model`, `claude auth login`, `codex login`, gateway setup.

5. **Manual doc should include**:
   - system dependencies
   - Node.js 22 installation
   - Hermes install/setup/doctor
   - Claude Code install/auth/smoke test
   - Codex install/auth/config/smoke test
   - cc-switch clone/build with private repo placeholder
   - CodeIndex central path convention
   - Gateway install/start/status/log checks
   - QQ Mail authorization-code note if discussing email

6. **Security section must explicitly exclude**:
   - `~/.hermes/.env`
   - `~/.hermes/auth.json`
   - `~/.codex/auth.json`
   - `~/.claude` credential files/login state
   - API keys, SMTP passwords, QQ authorization codes, Weixin tokens

8. **Create a redacted configuration snapshot**:
   - Include live/current files and rule directories where they exist:
     - `~/.hermes/config.yaml`
     - `~/.hermes/personality.md`
     - `~/.hermes/skills/`
     - `~/.hermes/profiles/`
     - `~/.hermes/scripts/`
     - `~/.codex/config.toml`
     - `~/.claude/` settings/rules/commands/agents/plugins metadata where safe
     - `~/cc-switch` config-like files (`*.json`, `*.toml`, `*.yaml`, `*.yml`, `*.md`, `*config*`, `package.json`)
     - `~/agent-configs/hermes-config` sanitized contents
   - Exclude runtime/heavy dirs: `.git`, `node_modules`, `cache`, `logs`, `sessions`, `venv`, `.venv`, `__pycache__`, build outputs.
   - Redact lines where keys or filenames match: `api_key`, `token`, `secret`, `password`, `authorization`, `auth_code`, `access_token`, `refresh_token`, `id_token`, `cookie`, `session`, `smtp.*pass`, `email_password`, `anthropic_auth`.
   - Keep `.env` only as `.env.redacted`; never package raw credentials.
   - Add `repo-metadata/*.md` with `git remote -v`, `git status --short --branch`, `git log -1`, upstream, unpushed commits, and recent history.
   - Add a restore helper that copies only non-secret config and tells the user to manually merge `config.yaml` / refill `.env`.

9. **Verify package**:
   ```bash
   chmod +x /tmp/hermes-ubuntu-kit/install-hermes-stack.sh
   bash -n /tmp/hermes-ubuntu-kit/install-hermes-stack.sh
   cd /tmp
   tar -czf hermes-ubuntu-kit.tar.gz hermes-ubuntu-kit
   sha256sum /tmp/hermes-ubuntu-kit.tar.gz > /tmp/hermes-ubuntu-kit.tar.gz.sha256
   find /tmp/hermes-ubuntu-kit -maxdepth 3 -type f -printf '%p\t%s bytes\n' | sort
   ```
   If `shellcheck` is unavailable, state that `bash -n` passed.

8. **Email delivery**:
   - Use the email skill / SMTP fallback.
   - In this environment, QQ SMTP can work from `~/.hermes/.env` using `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` or fallback equivalents.
   - Attach both `.tar.gz` and `.sha256`.
   - Include README/manual/checklist in the email body so the user can read without extracting.
   - After sending, report only a compact WeChat summary with path and SHA256.

## Pitfalls learned

- WeChat long-form manuals can be fully replaced by `⚠️ Response truncated due to output length limit`; avoid direct long replies.
- Python heredoc nesting can produce syntax errors when embedding large f-strings; if sending email via Python, prefer writing a standalone `/tmp/send_*.py` file or construct the body with safe string concatenation.
- Do not claim email was sent until SMTP returns success.
- Do not hardcode private repo URLs for cc-switch; use environment variables. For this user's own Hermes/CodeIndex repos, do record the discovered effective repo URLs and commits in `repo-metadata/` and make installer defaults overridable.
- The user's Hermes Agent code may contain local fixes that are already pushed to `liuli263/hermes-agent-config.git`; do not install only upstream `NousResearch/hermes-agent` or the new machine may miss fixes.
- The user's Hermes configuration/memory/skills may be split into `~/agent-configs/hermes-config`; include that repo metadata and a sanitized snapshot.
- Always check for unpushed commits in important repos. In one run, `~/projects/CodeIndex` was ahead of `origin/main` by 1 commit; report this because a fresh clone from remote would miss it unless pushed.
- Include agent rule files and user-facing configuration snapshots; a pure installer script is insufficient for this user's migration expectation.
- Run a heuristic secret scan on the prepared directory before emailing. Expect false positives from docs/examples/URLs, but inspect any real-looking unredacted assignments.
- WeChat interruptions can cancel long tool executions; if a packaging command is interrupted, rerun from a standalone script rather than assuming it completed.

## Final WeChat summary template

```text
已处理完成，请查收邮箱 50803169@qq.com。

本地文件：
/tmp/hermes-ubuntu-kit/
/tmp/hermes-ubuntu-kit.tar.gz
/tmp/hermes-ubuntu-kit.tar.gz.sha256

SHA256：<hash>

包里包含自动安装脚本、手动说明、迁移检查清单和配置模板；不包含任何密钥/token/登录态。
```

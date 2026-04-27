---
name: codex
description: Delegate coding tasks to OpenAI Codex CLI agent. Use for building features, refactoring, PR reviews, and batch issue fixing. Requires the codex CLI and a git repository.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
    related_skills: [claude-code, hermes-agent]
---

# Codex CLI

Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.

## Prerequisites

- Codex installed: `npm install -g @openai/codex`
- OpenAI API key configured
- **Must run inside a git repository** — Codex refuses to run outside one
- Use `pty=true` in terminal calls — Codex is an interactive terminal app

## One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

## Multimodal / Image Reading

Codex CLI can also read attached images via `--image`, which is useful when Hermes vision tools are unavailable or failing.

### Analyze a local screenshot with a prompt argument
```bash
codex exec --skip-git-repo-check --cd /tmp/workdir \
  --image /path/to/screenshot.jpg \
  'Read the Chinese text in this screenshot. If an authorization code is visible, copy it exactly. Do not guess.'
```

### Robust pattern: send the prompt on stdin
This worked reliably in this environment when passing a local image:
```bash
PROMPT='Read this screenshot and answer: 1) what page is this, 2) if a code is visible, copy it exactly, 3) if unclear, say unclear. Do not guess.'
printf '%s' "$PROMPT" | codex exec \
  --skip-git-repo-check \
  --cd "$(mktemp -d)" \
  --image /path/to/screenshot.jpg \
  -
```

Use this pattern for OCR-like extraction from screenshots, mobile UI captures, setup pages, or other local images when you need a second path besides Hermes vision.

## Background Mode (Long Tasks)

```
# Start in background with PTY
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--full-auto` | Sandboxed but auto-approves file changes in workspace |
| `--yolo` | No sandbox, no approvals (fastest, most dangerous) |

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex --yolo exec 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="codex --yolo exec 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Rules

1. **Always use `pty=true`** — Codex is an interactive terminal app and hangs without a PTY
2. **Git repo required** — Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch
3. **Use `exec` for one-shots** — `codex exec "prompt"` runs and exits cleanly
4. **`--full-auto` for building** — auto-approves changes within the sandbox
5. **Background for long tasks** — use `background=true` and monitor with `process` tool
6. **Don't interfere** — monitor with `poll`/`log`, be patient with long-running tasks
7. **Parallel is fine** — run multiple Codex processes at once for batch work

## Environment Pitfalls

- In some sandboxed environments, Codex's internal `apply_patch`/sandbox helper can fail with errors like `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`.
- When that happens, **do not keep retrying the patch tool indefinitely**. Fall back to ordinary shell-based writes/edits inside the repo (for example, `cat > file`, `node/python` file writes, or Hermes `write_file`/`patch` outside Codex).
- If Codex reports patch-tool failure but can still run shell commands, let it continue with shell writes and then independently verify the result with Hermes tools (`read_file`, `terminal`, browser checks, tests).
- If `codex login status` fails with `missing field 'id_token'`, inspect `~/.codex/auth.json` before assuming the API key itself is bad. We observed a stale/incompatible auth file shaped like `{ "OPENAI_API_KEY": "...", "tokens": { "access_token": "...", "refresh_token": "..." } }` that newer Codex rejected because it expected an `id_token` field.
- Safe diagnostic pattern for that auth error: back up `~/.codex/auth.json`, temporarily move it aside, then retry `codex login status` and a one-shot `codex exec` with a fresh environment. If the login-status parse error disappears, the on-disk auth file is the blocker rather than the CLI binary.
- With a custom provider in `~/.codex/config.toml` (for example `model_provider = "yxai"` with `base_url = "https://yxai.chat/v1"`), do not assume a key stored only in `auth.json` will actually be forwarded to `/v1/responses`. In this environment, bypassing the malformed auth file still produced `403 Forbidden: 当前请求未包含token`, so provider-specific auth wiring must be verified separately from CLI login state.

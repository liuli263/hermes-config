---
name: gemini-cli
description: Use Gemini CLI for interactive or headless agent tasks; includes installation verification and minimal non-interactive smoke tests.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, Gemini, Google, CLI, Headless, Smoke-Test]
    related_skills: [claude-code, codex, hermes-agent]
---

# Gemini CLI

Use Gemini CLI for interactive or non-interactive agent tasks. This skill captures the practical smoke-test flow that worked in this environment.

## When to use

- Verify Gemini CLI is installed and callable
- Run a minimal headless test before relying on it for real work
- Check supported flags when the CLI behavior is unknown

## Prerequisites

- Gemini CLI installed and on PATH
- Authentication already configured in the environment

## Fast verification flow

### 1. Check command path and version
```bash
command -v gemini && echo '---' && gemini --version
```

### 2. Inspect CLI help to confirm headless flags
```bash
gemini --help
```

Important findings:
- Gemini defaults to **interactive mode**
- Use `-p` / `--prompt` for **non-interactive headless mode**
- Use `-o text|json|stream-json` to control output format

### 3. Run a minimal one-shot smoke test
```bash
gemini -p 'Reply with exactly: Gemini OK' -o text
```

Expected result:
```text
Gemini OK
```

## Hermes usage pattern

Use Hermes terminal with PTY enabled for safest compatibility:
```json
terminal(command="gemini -p 'Reply with exactly: Gemini OK' -o text", pty=true, timeout=180, workdir="/path/to/project")
```

## Recommended usage

- For quick verification: `gemini -p '...' -o text`
- For structured automation: prefer `-o json` or `-o stream-json` when supported by your workflow
- Set `workdir` to the project directory you want Gemini to reason about

## Pitfalls

1. **Interactive by default** — if you omit `-p`, Gemini launches interactively instead of returning a one-shot result.
2. **Check help first when uncertain** — `gemini --help` clearly exposes the headless flags and output-format options.
3. **Use PTY in Hermes terminal calls** when treating it like an interactive agent CLI, even for simple checks.

## Rules for Hermes agents

1. First confirm installation with `command -v gemini` and `gemini --version`.
2. If headless syntax is not already known, inspect `gemini --help` before guessing flags.
3. Prefer a tiny smoke test (`Reply with exactly: Gemini OK`) before attempting real work.
4. Report both installation status and smoke-test success to the user.

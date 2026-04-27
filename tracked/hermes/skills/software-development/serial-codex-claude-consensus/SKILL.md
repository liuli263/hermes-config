---
name: serial-codex-claude-consensus
description: Orchestrate Codex and Claude Code in a strict serial consensus loop for development analysis, planning, performance review, bug diagnosis, and implementation approval workflows.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [codex, claude-code, consensus, code-review, planning, performance]
    related_skills: [codex, claude-code, plan, requesting-code-review]
---

# Serial Codex ↔ Claude Code Consensus Workflow

Use this skill whenever the user asks for development-related analysis, planning, bug diagnosis, code review, performance optimization, or implementation strategy and expects Codex and Claude Code involvement.

## Core rule

Do **not** send commands to Codex and Claude Code concurrently.

Always run a serial round-robin loop:

1. Codex speaks first.
2. Claude Code reviews Codex's output.
3. Feed Claude Code's review back to Codex.
4. Repeat until both sides explicitly converge or no material disagreement remains.
5. Only then summarize or proceed to implementation.

This is especially important for this user's workflow preference.

## Safety mode before user approval

For analysis/planning/review tasks where the user has not explicitly approved code changes:

- Tell both agents: `禁止修改任何代码 / do not modify code`.
- Use read-only tool permissions where possible.
- If using Claude Code print mode, prefer `--allowedTools 'Read,Bash'` for review/analysis.
- For Codex, include an explicit prompt: `只读分析，禁止修改任何代码`.
- Do not commit or push.

Only after the user explicitly approves implementation should Codex be allowed to modify code. Claude Code should normally review rather than implement unless the user specifically asks otherwise.

## Practical orchestration pattern

### 1. Prepare context

- Locate the project path.
- Generate/update CodeIndex first when useful, using the central script required by the user:

```bash
python3 /home/liuli/projects/CodeIndex/CreateIndex.py /path/to/project
```

- Save intermediate agent outputs to `/tmp/...` files so the next agent can review the exact text without relying on chat memory.

### 2. First Codex pass

Run Codex first, serially:

```bash
codex exec --skip-git-repo-check '你是性能优化/代码分析顾问。请只读分析 /path/to/project ... 禁止修改任何代码。输出：瓶颈定位、可执行方案、风险、验证标准。'
```

Use `pty=true` from Hermes terminal when invoking Codex.

### 3. Save Codex output

Write the distilled Codex output to a temp file, e.g.:

```text
/tmp/<project>_codex_analysis.txt
```

### 4. Claude Code review

Run Claude Code after Codex finishes:

```bash
claude -p "请只读评审 /tmp/<project>_codex_analysis.txt 中 Codex 的方案。禁止修改代码。请结合 /path/to/project 代码判断：哪些建议正确、哪些有风险或不优先、遗漏哪些关键点，并给出优先级路线图。" --allowedTools 'Read,Bash' --max-turns 8
```

### 5. Save Claude review

Write Claude Code's review to a temp file, e.g.:

```text
/tmp/<project>_claude_review.txt
```

### 6. Feed Claude back to Codex

Run Codex again after Claude finishes:

```bash
codex exec --skip-git-repo-check '请只读阅读 /tmp/<project>_claude_review.txt，并结合 /path/to/project 代码回应：是否同意 Claude Code 的修正？若不同意请逐条说明；若同意，请输出双方达成一致后的最终方案、优先级和验证标准。禁止修改代码。'
```

### 7. Determine consensus

Consensus is reached when:

- Codex explicitly agrees with Claude Code's corrections, or
- Codex lists remaining disagreements and they are minor/non-blocking, or
- A subsequent Claude review confirms no material disagreement remains.

If material disagreement remains, continue the loop:

```text
Codex final/disagreement -> Claude Code review -> Codex response -> ...
```

Do not stop after only one side's opinion unless the user explicitly asks for a single-agent answer.

## Deliverables

For planning/analysis tasks, save a markdown plan under the project:

```text
/path/to/project/.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md
```

Include:

- Background and scope
- The serial Codex/Claude process used
- Consensus conclusion
- Prioritized roadmap (P0/P1/P2/P3)
- Deferred items and rationale
- Verification standards
- Risks and rollback criteria

## Email record requirement

For this user, detailed Codex ↔ Claude Code discussion records must be emailed to:

```text
50803169@qq.com
```

Include at minimum:

- Summary of the serial rounds
- Final consensus plan path
- Attachments or inline text for Codex output, Claude review, and final plan

If `himalaya` is unavailable, use the configured SMTP fallback from `~/.hermes/.env` when present (`EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`/`EMAIL_ADDRESS`, `EMAIL_SMTP_PASSWORD`/`EMAIL_PASSWORD`).

## Example outcome from newaiplan performance review

A successful use of this workflow for `/home/liuli/projects/newaiplan` found:

- Codex identified `LocalAlignmentTune` + O(n²) `SpacingUniformityScore` as the main performance hotspot.
- Claude Code agreed but corrected priority/risk details:
  - `LocalSwapImprove` spatial-indexing was lower priority and risky.
  - Parallelism concerns were overstated because the code already guarded against nested scheme/restart parallelism.
  - Low-risk omissions included duplicate `BuildSegments`, repeated `context.Edges.Max(...)` in `BoundaryDistanceWeightAt`, and LINQ allocation in `SolutionSimilarity`.
- Codex accepted Claude Code's corrections.
- Final consensus prioritized:
  - P0: `SpacingUniformityScore` incremental/affected-set evaluation, reuse `BuildSegments`, precompute `outerWeight`.
  - P1: reduce `LocalAlignmentTune` allocation, filter `AlignmentTuneCandidates` before candidate generation, reduce `EstimateMaxBoundaryDistance` scan density.
  - P2: `LayoutAlignmentScore` neighbor pruning, `SolutionSimilarity` allocation reduction.
  - P3: static/span orientation arrays.

## Pitfalls

- Do not use parallel `delegate_task` for Codex and Claude in this workflow; it violates the user's requested sequencing.
- Do not let either agent modify code during planning unless the user explicitly approved implementation.
- Do not treat Codex's first answer as final; Claude must review it and Codex must respond to that review.
- Do not omit the email record for this user.
- If CodeIndex creation with `python` fails, retry with `python3`.

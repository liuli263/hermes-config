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

Use this skill whenever the user asks for development-related analysis, planning, bug diagnosis, test-failure/root-cause investigation, code review, performance optimization, or implementation strategy and expects Codex and Claude Code involvement. For this user, bug/test-failure/root-cause investigations must also go through Codex → Claude Code confirmation before treating the cause as established.

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

Only after the user explicitly approves implementation should Codex be allowed to modify code. Once implementation is approved, continue automatically across agreed phases without asking for per-phase confirmation; ask only for material decisions, unexpected risks, or blockers. Claude Code should normally review rather than implement unless the user specifically asks otherwise.

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

## Real-time user forwarding requirement

For this user, whenever Hermes receives a reply/output from Codex or Claude Code during the collaboration loop, immediately forward that agent reply to the user in the current chat before continuing to the next agent. Do not wait until the end-of-task summary. The forwarded content must be the complete original reply, not a summary. If the raw output is very long, split it into multiple chat messages and send all parts in order; do not replace the full content with only a file path or excerpt. After forwarding, immediately continue to the next serial step yourself unless a genuine user decision/approval is required; do not pause and wait for the user to ask whether the task is still continuing. Still include the complete text in the final email record.

## Implementation phase discipline

When the user explicitly approves implementation:

- Codex may modify code; Claude Code remains reviewer unless the user says otherwise.
- Keep phases small; after each phase run the agreed checks/tests, then commit with a detailed Chinese message and push only if checks pass.
- If a baseline check fails before or during a behavior-neutral/config-only step, stop implementation for that phase, do not commit/push, and switch to systematic debugging: have Codex investigate the failing baseline, forward the full output, then have Claude review the diagnosis. Treat this as a blocker until the root cause is understood or the user explicitly decides to proceed despite the known baseline failure.
- Before resuming after an environment/gateway restart, check `git status --short --branch`, active processes, and relevant diffs to reconstruct state; tell the user whether work was interrupted or only paused at a known blocker.

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

## Implementation-phase operating loop

After the user explicitly approves implementation:

1. Codex implements one agreed phase only.
2. Codex must run verification (`git diff --check`, project tests, `git status --short`) and only commit/push if verification passes.
3. Immediately forward Codex's complete implementation report to the user.
4. Immediately run Claude Code review on that commit; do not wait for the user to ask.
5. Immediately forward Claude Code's complete review to the user.
6. If Claude finds issues, send the review back to Codex for a fix commit, then repeat review.
7. If Claude approves, automatically continue to the next agreed phase unless there is a material design decision, unexpected risk, failed test, or blocker.

For long-running work, avoid silent gaps: proactively send short progress updates at phase start, after each agent begins, when each agent finishes, when a review starts, when any command is interrupted/retried, and after any long period without visible output. Do this even if there is no complete new agent reply yet; do not wait for the user to ask. If progress stalls or the user asks whether work is still running, check `process list`, `git status --short --branch`, recent commits, and active `codex`/`claude`/`dotnet`/`vstest` processes, then report the exact state before continuing. If a stale test process remains after the agent already finished and the repo is clean, terminate it before continuing so it does not look like active work. If a session/gateway reset is imminent or occurs mid-task, preserve the live project state in the next response/session notes when possible: current branch, latest commits, dirty files, completed phase, pending next action, and any agent output still needing review/forwarding.

To prevent lost or truncated agent output, redirect each Codex/Claude run to a timestamped log under `/tmp` (or use `tee`) and ask the agent to end with a concise final report containing operation record, verification result, commit hash, and push result. Avoid broad exploratory commands in prompts that can flood output (for example `rg ... src tests` across a large tree); instruct agents to inspect targeted files or CodeIndex first. If a Hermes terminal result is truncated, immediately recover the full text from the saved log before forwarding or emailing. If a Codex command times out or is interrupted after output suggests it already committed/pushed, do not assume failure: immediately verify with `git status --short --branch`, `git log --oneline --decorate -5`, `git show --stat HEAD`, active process checks, and rerun the required final validation (`git diff --check`, project tests) before deciding whether to proceed to Claude review. If Claude print mode fails with `Reached max turns`, rerun with a higher `--max-turns` before treating the review as failed. If Claude/API returns 403/502, times out, or a command is interrupted, immediately tell the user the exact interruption state, check active processes and repo status, then retry with a small `claude -p "ping"` health check before restarting the real review.

When Claude rejects a Codex implementation, do not proceed to the next phase. Forward the full review, send the review back to Codex as a fix task, require Codex to commit/push a fix, then run Claude review again. Repeat until Claude explicitly says `通过` / no material issue remains.

For performance-regression fixes, prefer behavior-based tests or low-intrusion counters/hooks over source-text string scans. Source-text tests are usually weak because they can pass while behavior regresses. If adding a test hook (e.g. an internal static construction callback), ensure it is null by default, cleaned in `finally`, thread-safe when counted, and scoped by a unique plan/test id to avoid parallel-test cross-talk.

For user-requested performance comparisons after an implementation, do not infer speedup from correctness tests. Run an actual benchmark using the user's specified entrypoint/data, compare against a baseline worktree, and report averages/medians/min/max plus limitations. If the baseline cannot build due an unrelated runner/tooling gap, ask/confirm or use a temporary baseline worktree branch with the smallest compile-only fix that does not touch the performance path; clearly label it as `main-tempfix`, do not push it, and keep raw CSV/summary artifacts under `/tmp` for review.

When merging a completed feature branch back to `main`, remember that untracked generated artifacts (for example `.hermes/` or `codeindex/`) may reappear on `main` if `.gitignore` changes only exist on the feature branch. Do not treat known generated directories as a code conflict. Safely handle them before merge by temporarily moving them to `/tmp` or otherwise preserving them, then merge/test/push, and restore if needed. Never delete unknown user files without confirmation.

## Test-failure/root-cause investigations

Bug, test-failure, and unexpected-behavior investigations also require the serial workflow. Codex may investigate first, but Hermes must not treat the root cause as final until Claude Code has reviewed and confirmed it. If tests fail during an implementation phase:

- Do not commit/push the phase unless the user explicitly approved committing a known-failing state.
- Forward Codex's failure/root-cause report in full.
- Run Claude Code review of the root-cause report.
- Only after consensus decide whether to fix tests, fix production code, or change the execution plan.

## Pitfalls

- Do not use parallel `delegate_task` for Codex and Claude in this workflow; it violates the user's requested sequencing.
- Do not let either agent modify code during planning unless the user explicitly approved implementation.
- After implementation approval, do not pause between phases waiting for the user unless there is a real decision/blocker; keep the serial Codex→Claude loop moving.
- Do not treat Codex's first answer as final; Claude must review it and Codex must respond to that review.
- Do not treat bug/test-failure root cause as confirmed until Claude Code reviews Codex's investigation.
- Do not omit the email record for this user.
- If CodeIndex creation with `python` fails, retry with `python3`.

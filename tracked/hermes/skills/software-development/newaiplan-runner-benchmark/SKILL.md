---
name: newaiplan-runner-benchmark
description: Benchmark NewAIPlan performance using NewAIPlan.Runner and test fixtures, including comparing a refactor branch against main with a temporary compile-only baseline fix when needed.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [newaiplan, benchmark, runner, performance, dotnet]
    related_skills: [serial-codex-claude-consensus]
---

# NewAIPlan Runner Benchmark

Use this skill when the user asks how much a `newaiplan` change improved performance, especially when they specify using `NewAIPlan.Runner` and the test fixture data.

## Key principles

- Do **not** infer performance from `dotnet test` correctness results.
- Use the user's requested entrypoint and data. For the known workflow, use `NewAIPlan.Runner` with:
  - `test/NewAIPlan.Tests/fixtures/sites/site-01.json`
  - `test/NewAIPlan.Tests/fixtures/configs/config-01.json`
  - `test/NewAIPlan.Tests/fixtures/products/products-01.json`
  - `test/NewAIPlan.Tests/fixtures/inputs/input-01.json`
- Keep the main working tree clean. Use `/tmp` worktrees or temporary clones.
- Report limitations: fixture-only, small sample size, same machine noise, temporary baseline fixes if used.

## Standard workflow

1. Confirm the project state:

```bash
cd /home/liuli/projects/newaiplan
git status --short --branch
git rev-parse HEAD
```

2. Create independent worktrees under `/tmp`:

```bash
rm -rf /tmp/newaiplan-main-runner-bench-fix /tmp/newaiplan-refactor-runner-bench
git worktree add -b temp/main-runner-bench-fix /tmp/newaiplan-main-runner-bench-fix main
git worktree add /tmp/newaiplan-refactor-runner-bench refactor/plan-pipeline-modules
```

3. If `main` Runner cannot build because `HtmlPlanViewerExporter` is missing, apply a **temporary compile-only fix** in the main worktree only:

- Add `src/NewAIPlan/Output/HtmlPlanViewerExporter.cs` with a minimal static `Export(string planJson)` implementation.
- Do not touch `PlanPipeline`, packing algorithms, fixture files, or benchmark data.
- Commit locally for traceability if desired:

```bash
git -C /tmp/newaiplan-main-runner-bench-fix add src/NewAIPlan/Output/HtmlPlanViewerExporter.cs
git -C /tmp/newaiplan-main-runner-bench-fix commit -m 'Temp fix runner html exporter'
```

Clearly label this baseline as `main-tempfix` and never push it.

4. Build both versions in Release before timing:

```bash
dotnet build /tmp/newaiplan-main-runner-bench-fix/src/NewAIPlan.Runner/NewAIPlan.Runner.csproj -c Release
dotnet build /tmp/newaiplan-refactor-runner-bench/src/NewAIPlan.Runner/NewAIPlan.Runner.csproj -c Release
```

5. Run benchmarks using `dotnet <dll>` or `dotnet run -c Release --no-build` with explicit fixture arguments. Do **1 warmup + at least 5 official runs** per version, interleaving official runs if possible:

```text
site config products input outputRoot
```

6. Capture these metrics:

- external wall-clock time
- Runner `Pipeline` time
- Runner `Total measured`
- `WeightedPackingPerformance.elapsedMs`
- `WeightedPackingPerformance.selectedSearchMs`
- `WeightedPackingPerformance.solutionTotalMs`

The Runner writes JSON outputs under each run directory; parse `result.json` log entries where `source == "WeightedPackingPerformance"` and `message == "加权排布性能汇总。"`.

7. Produce a CSV and summary JSON under `/tmp`, e.g.:

```text
/tmp/newaiplan-runner-bench-results-YYYYMMDD-HHMM/runs.csv
/tmp/newaiplan-runner-bench-results-YYYYMMDD-HHMM/summary.json
```

8. Report a table with average / median / min / max and improvement percentage:

```text
(main_avg - refactor_avg) / main_avg * 100
```

Positive means the refactor is faster. Highlight the most relevant metrics: wall-clock, Runner Pipeline, Runner Total measured, WPP elapsedMs, and WPP solutionTotalMs.

## Known result example

For `main-tempfix` based on `dd2247a` vs `refactor dce9313` using the standard fixture and 5 official runs:

| Metric | main-tempfix avg ms | refactor avg ms | Improvement |
|---|---:|---:|---:|
| Wall-clock | 1242.8 | 987.1 | +20.6% |
| Runner Pipeline | 1036.4 | 766.8 | +26.0% |
| Runner Total measured | 1201.4 | 947.0 | +21.2% |
| WPP elapsedMs | 969.1 | 693.1 | +28.5% |
| WPP solutionTotalMs | 961.6 | 685.7 | +28.7% |

`WPP selectedSearchMs` may be noisy and can regress in one run while overall pipeline improves; report it but do not use it alone as the headline metric.

## Pitfalls

- If `main` does not build, do not silently compare against nothing. Either report that no comparison is possible or use a clearly labeled `main-tempfix` if the user approves.
- Do not include build time in official timing.
- Do not mutate or push `main` just for benchmarking.
- Clean up or at least disclose temporary worktrees. Use `git worktree remove` when no longer needed.

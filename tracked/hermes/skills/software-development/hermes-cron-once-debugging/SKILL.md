---
name: hermes-cron-once-debugging
description: Diagnose Hermes one-shot cron jobs that appear not to run, especially when last_run_at stays unset or jobs disappear from list after execution.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Hermes one-shot cron debugging

Use this when a user reports that a one-shot cron job "did not run", `last_run_at` did not update, or the job disappeared from `cronjob list`.

## Core findings

1. `cronjob run` success is **not** proof of synchronous execution. It can mean the job was accepted and will run on the next scheduler tick.
2. For one-shot jobs, `cronjob list` is **not a reliable success signal**. A successful once job may be removed from `jobs.json` immediately after execution.
3. Stronger proof comes from files under `~/.hermes/cron/output/<job_id>/`.
4. After the observability fix, each run should also leave `latest_run.json` beside the markdown output file.

## Fast triage procedure

1. **Check source first**
   - Read `cron/jobs.py`, `cron/scheduler.py`, and `tools/cronjob_tools.py`.
   - Confirm whether the suspected behavior is true in code before speculating.

2. **Do not trust `cronjob list` alone**
   - If a once job is missing from the list, treat that as ambiguous.
   - It may mean deleted, never created, or already executed and auto-removed.

3. **Check output artifacts**
   - Inspect `~/.hermes/cron/output/<job_id>/`.
   - Expected files after the observability fix:
     - timestamped markdown output like `2026-04-18_16-57-02.md`
     - `latest_run.json`

4. **Interpret `latest_run.json`**
   - `success: true` means the job body finished successfully.
   - `output_file` points to the saved markdown output.
   - `delivery_error` captures send failures.
   - `delivery_metadata` may contain platform/chat/message identifiers.
   - `error` captures execution failures even if the job was removed from `jobs.json`.

5. **Verify both failure and success paths**
   - In an isolated `HERMES_HOME`, run one self-test without provider config to verify failure still leaves `latest_run.json`.
   - Then copy real `config.yaml` and `.env` into an isolated `HERMES_HOME` and verify a successful one-shot run also leaves both files.

## Repro/self-test pattern

Use an isolated home so you do not pollute the real scheduler state:

```bash
source venv/bin/activate
export REAL_HERMES_HOME=/home/liuli/.hermes
export HERMES_HOME=$(mktemp -d)
mkdir -p "$HERMES_HOME"
cp "$REAL_HERMES_HOME/config.yaml" "$HERMES_HOME/config.yaml"
cp "$REAL_HERMES_HOME/.env" "$HERMES_HOME/.env"
```

Then create a one-shot job due in the past and execute a tick:

```python
from datetime import datetime, timedelta, timezone
from cron.jobs import create_job
from cron.scheduler import tick

schedule = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0).isoformat()
job = create_job(
    prompt='请只回复：self-test-ok',
    schedule=schedule,
    name='once-selftest-success',
    deliver='local',
)
executed = tick(verbose=False)
```

Then inspect:

```bash
$HERMES_HOME/cron/output/<job_id>/latest_run.json
$HERMES_HOME/cron/output/<job_id>/<timestamp>.md
```

## Implementation note

If one-shot post-run observability is missing, add a helper in `cron/jobs.py` that writes a structured JSON record atomically, and call it from `cron/scheduler.py` immediately after output save / delivery handling but before returning control.

## Testing checklist

- Add a unit test that `save_job_run_record()` writes `latest_run.json`.
- Add a scheduler test that `tick()` calls the run-record writer.
- Re-run:

```bash
source venv/bin/activate
python -m pytest -n0 tests/cron/test_jobs.py tests/cron/test_scheduler.py -q
```

Use `-n0` if parallel mode introduces confusing mock-related failures during diagnosis.

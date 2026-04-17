---
name: hermes-email-gateway-debugging
description: Debug and de-noise Hermes email gateway issues using real local source, tests, and live runtime verification. Covers unauthorized email warnings, IMAP parsing errors, and restart/log validation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, gateway, email, imap, logging, debugging, runtime-verification]
    related_skills: [systematic-debugging, test-driven-development, hermes-agent]
---

# Hermes Email Gateway Debugging

Use this skill when Hermes `gateway run` shows email-related warnings/errors such as:

- `Unauthorized user: ... on email`
- `IMAP fetch error: unknown encoding: unknown-8bit`
- `Failed to parse message uid=...: expected string or bytes-like object, got 'Header'`
- noisy inbox-driven logs that look scary but may be expected filtering

## Core principles

1. **Inspect local code + live runtime; do not speculate.**
2. **Separate issue classes before patching:**
   - authorization/log-noise
   - message parsing robustness
   - shutdown/drain lifecycle
3. **Treat runtime proof as mandatory.** Code/tests alone do not prove the running gateway picked up the fix.
4. **Make the smallest safe change.** Prefer log-level changes or narrow heuristics over broad behavior changes.

## Known source locations

### Unauthorized email warnings
In `gateway/run.py`, `_handle_message()` contains the shared unauthorized branch:

```python
elif not self._is_user_authorized(source):
    logger.warning("Unauthorized user: %s (%s) on %s", ...)
```

This applies to all platforms, including email. Because email messages are wrapped as `chat_type="dm"` with `user_id=sender email`, ordinary inbound mail from unknown senders can create warning spam.

### Email automated-sender heuristics
In `gateway/platforms/email.py`:

- `_NOREPLY_PATTERNS`
- `_AUTOMATED_HEADERS`
- `_is_automated_sender(...)`

The adapter already skips many automated senders before dispatch, but this will not catch all newsletters/marketing mail. Some messages still reach `_handle_message()` and become unauthorized-user logs.

### Parsing robustness clues
Also in `gateway/platforms/email.py`:

- charset alias map should handle `unknown-8bit` / `unknown_8bit`
- header decoding paths must tolerate `email.header.Header` objects, not just `str`/`bytes`

## Recommended workflow

### 1) Confirm the symptom is current, not historical
Check the running gateway process and its start time first.

Use terminal commands like:

```bash
ps -ef | grep 'gateway run' | grep -v grep
ps -p <PID> -o lstart=,etime=,cmd=
```

Then search logs **after the confirmed restart time** so old noise is not mistaken for a live regression.

## 2) Map each log line to exact code
For authorization noise:
- inspect `gateway/run.py` around `_handle_message()` unauthorized branch

For email filtering/parsing:
- inspect `gateway/platforms/email.py`
- look for `_is_automated_sender`, `_decode_header_value`, and fetch/dispatch flow

Do **not** conflate these categories.

## 3) Decide the minimal fix
### If the issue is unauthorized warning spam on email
Preferred minimal fix:
- keep authorization logic unchanged
- keep non-email platforms at `WARNING`
- downgrade **email unauthorized logs** to `INFO`

Reason: email inboxes naturally receive third-party senders; this is often expected filtering, not an operational warning.

Implementation pattern in `gateway/run.py`:

```python
unauthorized_log = logger.info if source.platform == Platform.EMAIL else logger.warning
unauthorized_log(
    "Unauthorized user: %s (%s) on %s",
    source.user_id,
    source.user_name,
    source.platform.value,
)
```

This preserves visibility without polluting warning-level logs.

### If the issue is a real parser failure
Patch email parsing in `gateway/platforms/email.py`, not the shared gateway authorization path.

## 4) Use TDD for behavior changes
Before changing production code, add a focused test.

Recommended regression coverage for de-noising:
- email unauthorized sender logs at `INFO`, not `WARNING`
- non-email unauthorized sender still logs at `WARNING`

Suggested test file:
- `tests/gateway/test_email_unauthorized_logging.py`

## 5) Run focused tests first, then related regressions
Example:

```bash
source venv/bin/activate
python3 -m pytest tests/gateway/test_email_unauthorized_logging.py -q
python3 -m pytest tests/gateway/test_internal_event_bypass_pairing.py tests/gateway/test_gateway_shutdown.py tests/gateway/test_email_unauthorized_logging.py -q
```

Do not stop after the narrow test; verify nearby gateway behavior too.

## 6) Verify live runtime after code changes
After patching:
1. restart the gateway process/service
2. confirm a new PID or new start timestamp
3. search logs only after that restart time
4. verify:
   - email unauthorized messages no longer appear as warnings
   - no regression in pairing behavior on other platforms
   - parsing errors (`unknown-8bit`, `Header`) remain quiet

## Pitfalls

- **Do not call email unauthorized warnings a parsing bug.** They are separate paths.
- **Do not overfit automated-sender heuristics first** if the real problem is log severity.
- **Do not trust old logs** without restart-time scoping.
- **Do not broadly lower all unauthorized warnings**; email is a special case because inbox traffic is inherently noisy.
- **Do not skip runtime verification** after tests pass.

## Good completion criteria

You are done only when all of the following are true:
- code path root cause identified from source
- minimal patch applied
- focused regression tests pass
- related gateway tests pass
- live gateway process restarted/confirmed
- post-restart logs show the intended behavior change

## Quick checklist

- [ ] Confirm running PID and start time
- [ ] Correlate exact log to exact code path
- [ ] Inspect `gateway/platforms/email.py` heuristics before patching
- [ ] Separate authorization noise from parser failures
- [ ] Add failing test first
- [ ] Apply minimal fix
- [ ] Run focused + related tests
- [ ] Restart gateway
- [ ] Verify post-restart logs only

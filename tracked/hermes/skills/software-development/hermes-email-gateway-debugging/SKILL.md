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

### Email UID high-water processing
In `gateway/platforms/email.py`, inbound polling should be based on a persisted UID high-water state at `~/.hermes/email_gateway_state.json`, not on IMAP `UNSEEN` flags. Important invariants:

- Search with `UID <last_uid+1>:*`, never rely on `UNSEEN` for gateway delivery.
- On first run or UIDVALIDITY change, set a safe baseline to the current max UID / `UIDNEXT-1` and do not process historical mail.
- For ordinary user mail that must be dispatched, advance `last_uid` only after `_dispatch_message()` succeeds.
- If dispatch raises, log the error and do not advance UID, so the same message is retried on the next poll.
- For paths that do not need dispatch (fetch failure, self-sent mail, automated sender skip, parse failure), continue advancing UID so bad/skipped messages do not block the mailbox forever.
- Tests should explicitly cover dispatch failure preserving `last_uid` and retrying the same UID.

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
- **Do not trust only `hermes gateway status` / systemd status.** The service can be `inactive/dead` while a manually-started gateway process is still running (for example `.../python3 .../hermes gateway`). Always check `ps -ef | grep -E 'hermes gateway|gateway run'` too.
- **Do not assume logs are in `gateway.log`.** In this environment, live email gateway events may be in `~/.hermes/logs/agent.log`; check both `agent.log` and `errors.log` when `gateway.log` is absent.
- **Beware background tail watch buffering.** Hermes background-process watch notifications can continue delivering already-matched output from killed/exited `tail -F` sessions, and `tail -F` may replay old content after log rotation/reopen. Always check the `session_id`, process status, and log timestamps before treating a notification as live.
- **For true live email gateway monitoring, prefer a timestamp-gated, email-only stream.** Start from the current timestamp and filter out older log lines as well as unrelated `checkpoint_manager`, Weixin, or generic gateway noise, e.g. `SINCE="$(date '+%Y-%m-%d %H:%M:%S')"; tail -n 0 -F ~/.hermes/logs/agent.log ~/.hermes/logs/errors.log 2>/dev/null | awk -v since="$SINCE" 'BEGIN{IGNORECASE=1} /^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}/ {ts=substr($0,1,19); if (ts < since) next} /\\[Email\\]|IMAP|SMTP|Unauthorized user|Sent reply|New message from/ {print; fflush()}'`.
- **Do not assume `GATEWAY_ALLOW_ALL_USERS=true` overrides `EMAIL_ALLOWED_USERS`.** If `EMAIL_ALLOWED_USERS` exists, only exact addresses in that comma-separated allowlist are authorized for email. A sender such as `qingguo9999@gmail.com` will be logged as unauthorized if the allowlist contains a different Gmail address.
- **Do not assume `GATEWAY_ALLOW_ALL_USERS=true` overrides `EMAIL_ALLOWED_USERS`.** If `EMAIL_ALLOWED_USERS` exists, only exact addresses in that comma-separated allowlist are authorized for email. A sender such as `qingguo9999@gmail.com` will be logged as unauthorized if the allowlist contains a different Gmail address.
- **Do not assume logs are in `gateway.log`.** In this environment, live email gateway events may be in `~/.hermes/logs/agent.log`; check both `agent.log` and `errors.log` when `gateway.log` is absent.
- **Avoid noisy realtime log watchers.** `process` watch notifications can continue delivering buffered matches from already-killed background sessions, and `tail -F` may replay old content after log rotation/reopen. For live gateway/email monitoring, prefer a fresh watcher with `tail -n 0`, narrow gateway/email grep patterns, and an explicit timestamp cutoff so old log lines cannot be mistaken for new events. Always confirm with `process(action="list")` which session is actually running.
- **Do not assume `GATEWAY_ALLOW_ALL_USERS=true` overrides `EMAIL_ALLOWED_USERS`.** If `EMAIL_ALLOWED_USERS` exists, only exact addresses in that comma-separated allowlist are authorized for email. A sender such as `qingguo9999@gmail.com` will be logged as unauthorized if the allowlist contains a different Gmail address.
- **Do not skip unread-mail backlog checks.** A large INBOX unseen count can make the email adapter repeatedly process old messages and create noisy unauthorized logs; inspect `UNSEEN` and allowed-sender unseen messages before concluding new test mail is ignored.
- **When the user wants to avoid processing old email, create a clean baseline deliberately.** Snapshot the current `UNSEEN` count/range, then mark current unseen INBOX messages `\\Seen` so only future mail is treated as new. Report the count before/after and be explicit that this changes mailbox read state.
- **For immediate sender authorization without gateway restart, pairing approval can be used.** Adding the sender to `~/.hermes/pairing/email-approved.json` is read dynamically by `PairingStore.is_approved()`, while changes to `EMAIL_ALLOWED_USERS` in `.env` may require restarting a long-running gateway process to be picked up.
- **Do not broadly lower all unauthorized warnings**; email is a special case because inbox traffic is inherently noisy.
- **Do not skip runtime verification** after tests pass.

## Live diagnostic snippets validated in this environment

### Check for manual gateway process even when systemd says stopped

```bash
hermes gateway status || true
ps -ef | grep -E 'hermes gateway|gateway run|run_gateway|gateway/run' | grep -v grep || true
ps -p <PID> -o pid,lstart,etime,pcpu,pmem,rss,stat,cmd
```

### Check actual email gateway logs

```bash
# gateway.log may not exist; agent.log often contains email adapter events
grep -iE 'Adapter initialized for .*@|New message from|Unauthorized user:|Sent reply|IMAP|SMTP|email' \
  ~/.hermes/logs/agent.log ~/.hermes/logs/errors.log 2>/dev/null | tail -200
```

For **live-only** monitoring, avoid starting with `tail -n 80` plus watch patterns: the initial historical replay can repeatedly trigger background-process notifications and look like fresh errors. Prefer `tail -n 0 -F` after first inspecting recent context:

```bash
# First inspect history explicitly, then start a clean live tail that only emits new appended lines.
grep -iE 'Adapter initialized for .*@|New message from|Unauthorized user:|Sent reply|IMAP|SMTP|email|ERROR|WARNING' \
  ~/.hermes/logs/agent.log ~/.hermes/logs/errors.log 2>/dev/null | tail -120

tail -n 0 -F ~/.hermes/logs/agent.log ~/.hermes/logs/errors.log
```

If a Hermes background process was already created with `tail -n 80 -F` and watch patterns, kill it and replace it with `tail -n 0 -F`. Be aware that queued watch notifications from the old process may still arrive briefly after kill; identify them by the old session id and by timestamps older than the new live-tail start time.

If unrelated historical `ERROR` lines (for example `tools.checkpoint_manager: Git command failed: git add -A ... CodeIndex`) keep triggering notifications, switch to a gateway/email-specific live filter instead of watching generic `ERROR`:

```bash
stdbuf -oL -eL tail -n 0 -F ~/.hermes/logs/agent.log ~/.hermes/logs/errors.log 2>/dev/null \
  | stdbuf -oL -eL grep -iE 'gateway|\[Email\]|IMAP|SMTP|Unauthorized user|Sent reply|New message from'
```

This isolates true gateway/email activity and avoids checkpoint-manager or unrelated agent errors. Note that even `tail -n 0 -F` can appear to replay older lines if the log is reopened/rotated/truncated by the running process; always compare event timestamps with the live-tail start time and ignore old-session buffered notifications.

Look for patterns like:
- `[Email] Adapter initialized for 50803169@qq.com` — email adapter is active
- `[Email] New message from ...` — IMAP polling is working
- `Unauthorized user: ... on email` — sender was read but not authorized
- `Sent reply to ...` — SMTP reply actually went out

### Check allowlist and unread backlog without exposing secrets

```bash
python3 - <<'PY'
import os, imaplib, email
from pathlib import Path
from email.header import decode_header
from email.utils import parseaddr

def load_env():
    for raw in (Path.home()/'.hermes'/'.env').read_text(errors='ignore').splitlines():
        line = raw.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def dec(v):
    if not v:
        return ''
    out = ''
    for part, enc in decode_header(v):
        out += part.decode(enc or 'utf-8', errors='replace') if isinstance(part, bytes) else str(part)
    return out

load_env()
allowed = {a.strip().lower() for a in os.getenv('EMAIL_ALLOWED_USERS', '').split(',') if a.strip()}
M = imaplib.IMAP4_SSL(os.getenv('EMAIL_IMAP_HOST', 'imap.qq.com'), 993)
M.login(os.environ['EMAIL_ADDRESS'], os.environ['EMAIL_PASSWORD'])
M.select('INBOX')
code, data = M.search(None, 'UNSEEN')
ids = data[0].split() if code == 'OK' and data and data[0] else []
print('UNSEEN', len(ids), 'allowed_count', len(allowed))
for mid in ids[-30:]:
    code, fd = M.fetch(mid, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
    raw = next((x[1] for x in fd if isinstance(x, tuple)), b'')
    msg = email.message_from_bytes(raw)
    _, addr = parseaddr(dec(msg.get('From')))
    print(mid.decode(), 'AUTH' if addr.lower() in allowed else 'NOAUTH', addr, '|', dec(msg.get('Subject'))[:120])
M.logout()
PY
```

Use this to separate:
- email adapter not running
- IMAP not receiving mail
- sender not authorized
- mail buried among many old unseen messages

### Create a clean baseline so old unread mail is not processed

Only do this when the user explicitly wants to avoid old-mail processing, because it marks messages as read in the real mailbox.

```bash
python3 - <<'PY'
import os, imaplib
from pathlib import Path

for raw in (Path.home()/'.hermes'/'.env').read_text(errors='ignore').splitlines():
    line = raw.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

M = imaplib.IMAP4_SSL(os.getenv('EMAIL_IMAP_HOST', 'imap.qq.com'), 993)
M.login(os.environ['EMAIL_ADDRESS'], os.environ['EMAIL_PASSWORD'])
M.select('INBOX')
code, data = M.search(None, 'UNSEEN')
ids = data[0].split() if code == 'OK' and data and data[0] else []
print('UNSEEN_TO_MARK', len(ids))
for i in range(0, len(ids), 200):
    M.store(b','.join(ids[i:i+200]).decode(), '+FLAGS', '\\Seen')
code, data = M.search(None, 'UNSEEN')
remaining = data[0].split() if code == 'OK' and data and data[0] else []
print('UNSEEN_AFTER', len(remaining))
M.logout()
PY
```

### Authorize a sender without relying on a gateway restart

If the gateway is already running and you cannot safely restart it, add the sender to the dynamic pairing-approved store as well as `.env`:

```bash
python3 - <<'PY'
import json, time
from pathlib import Path
addr = 'sender@example.com'
p = Path.home()/'.hermes'/'pairing'/'email-approved.json'
p.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(p.read_text()) if p.exists() else {}
data[addr] = {'user_name': addr, 'approved_at': time.time()}
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('approved', addr)
PY
```

Still update `EMAIL_ALLOWED_USERS` for persistence/config clarity; pairing approval is a runtime-friendly bridge.

### Test-mail caveat with QQ SMTP

QQ SMTP may reject spoofed `From:` values that do not match the authenticated account, with errors such as `550 The mail may contain inappropriate words or content` or `503 Send command mailfrom first`. A `Reply-To:` header is not equivalent to a real sender for Hermes authorization because the email adapter authorizes the parsed `From` address. For a true allowlist test, send from the actual authorized mailbox or configure that mailbox's own SMTP credentials.

## Good completion criteria

You are done only when all of the following are true:
- code path root cause identified from source
- minimal patch applied
- focused regression tests pass
- related gateway tests pass
- live gateway process restarted/confirmed
- post-restart logs show the intended behavior change

## Live email-command testing workflow

Use this when a user says email instructions are not reacting, or asks to test Email gateway from a specific sender.

### 1) Verify the actual running gateway, not only systemd
`hermes gateway status` / `systemctl --user status hermes-gateway` can say the user service is stopped while a manually launched process is still running, for example:

```bash
ps -ef | grep -E 'hermes gateway|gateway run|/home/.*/\.local/bin/hermes gateway' | grep -v grep
```

Also check logs in `~/.hermes/logs/agent.log`; some installs may not have `~/.hermes/logs/gateway.log` even though gateway logging is active.

### 2) Avoid processing old email before testing
If the mailbox has many historical unread messages, Hermes will keep polling them and may repeatedly log `New message from ...` / unauthorized noise. Before a controlled test, create a clean baseline:

```python
import imaplib, os
M = imaplib.IMAP4_SSL(os.getenv('EMAIL_IMAP_HOST', 'imap.qq.com'), 993)
M.login(os.environ['EMAIL_ADDRESS'], os.environ['EMAIL_PASSWORD'])
M.select('INBOX')
code, data = M.search(None, 'UNSEEN')
ids = data[0].split() if code == 'OK' and data and data[0] else []
for i in range(0, len(ids), 200):
    M.store(b','.join(ids[i:i+200]).decode(), '+FLAGS', '\\Seen')
M.logout()
```

Only do this after the user explicitly agrees that old unread messages may be marked read.

### 3) Authorize the intended sender robustly
For Email, the main check is `EMAIL_ALLOWED_USERS`, but a running gateway process may not reload `.env` until restart. If restart is blocked or risky, pairing approval is dynamically read from disk and can be used as a live authorization path:

```python
from pathlib import Path
import json, time
p = Path.home()/'.hermes'/'pairing'/'email-approved.json'
p.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(p.read_text()) if p.exists() else {}
data['sender@example.com'] = {'user_name': 'sender@example.com', 'approved_at': time.time()}
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
```

For persistent config, still add the sender to `EMAIL_ALLOWED_USERS` in `~/.hermes/.env`.

### 4) Do not fake sender identity with QQ SMTP
QQ SMTP usually rejects attempts to send mail with a forged `From:` such as testing `From: other@qq.com` while authenticated as `50803169@qq.com`. Errors observed include:

- `503 Send command mailfrom first`
- `550 The mail may contain inappropriate words or content.`

A message with `Reply-To: target@qq.com` is **not equivalent** to a message whose real `From` is that address; Hermes authorizes against the parsed sender email. For an end-to-end sender test, the user must send from the actual authorized account or provide that account's SMTP credentials.

### 5) Confirm delivery with IMAP, not assumptions
After the user says they sent mail, poll IMAP and inspect headers:

```python
M.select('INBOX')
code, data = M.search(None, 'UNSEEN')
# FETCH BODY.PEEK[HEADER.FIELDS (FROM REPLY-TO SUBJECT DATE)] for recent ids
```

If nothing appears in INBOX, search all folders with `M.list()` + `M.select(folder, readonly=True)` and `SEARCH FROM "sender@example.com"`. If no folder contains it, the message did not reach the mailbox as that sender.

### 6) Interpret logs carefully
Relevant markers:

- `[Email] Adapter initialized for ...` means Email adapter started.
- `[Email] New message from ...` means IMAP saw a message and dispatched it toward gateway handling.
- `Unauthorized user: ... on email` means sender was not authorized.
- `Sent reply to ...` or platform-specific send logs mean SMTP reply was attempted/succeeded.

Checkpoint errors like `tools.checkpoint_manager: Git command failed: git add -A ... embedded git repository ... agent-smoke-test` can be unrelated noise from the active session and may obscure email results. Do not confuse them with SMTP/IMAP failure.

## Quick checklist

- [ ] Confirm running PID and start time; do not trust systemd status alone
- [ ] Check `~/.hermes/logs/agent.log` as well as `gateway.log`
- [ ] Correlate exact log to exact code path
- [ ] Inspect `gateway/platforms/email.py` heuristics before patching
- [ ] Separate authorization noise from parser failures
- [ ] If testing, mark old unread messages read only with user approval
- [ ] Add intended sender to `EMAIL_ALLOWED_USERS` and, if needed for live process, `pairing/email-approved.json`
- [ ] Do not use forged `From` for QQ SMTP tests; require real sender or credentials
- [ ] Confirm incoming test mail via IMAP header search across folders
- [ ] Add failing test first for code behavior changes
- [ ] Apply minimal fix
- [ ] Run focused + related tests
- [ ] Restart gateway when config reload is required and allowed
- [ ] Verify post-restart/live logs only

---
name: hermes-weixin-message-splitting-debugging
description: Debug and fix Hermes Weixin outbound text that appears truncated or missing characters, especially for Chinese/multiline replies.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, weixin, gateway, debugging, chinese, messaging]
    related_skills: [systematic-debugging, test-driven-development, hermes-agent]
---

# Hermes Weixin Message Splitting Debugging

## When to use

Use when Hermes replies sent through the Weixin gateway seem to:
- lose a few characters,
- look incomplete in Chinese,
- arrive as fragmented bubbles,
- or differ visually from the model's original reply.

This workflow is for **source-first diagnosis** in the Hermes repo, not guesswork about encoding.

## Core lesson

For this codebase, apparent "missing Chinese characters" may be caused by **message splitting before send**, not by UTF-8 corruption.

In particular, check whether Weixin is splitting a short multiline reply into multiple chunks/bubbles.

## Relevant files

- `gateway/platforms/weixin.py`
- `tests/gateway/test_weixin.py`
- sometimes `gateway/platforms/base.py`
- `gateway/run.py`
- `gateway/display_config.py`
- `tests/gateway/test_display_config.py`

## Investigation workflow

1. **Locate the actual send path first**
   - Search for `_split_text_for_weixin_delivery`
   - Search for `_split_text(` in `WeixinAdapter`
   - Search for where `chunks` are iterated and sent with `_send_text_chunk(...)`

2. **Confirm whether a single reply becomes multiple chunks**
   - Inspect the flow around:
     - `_split_text_for_weixin_delivery(...)`
     - `_split_delivery_units_for_weixin(...)`
     - `_looks_like_chatty_line_for_weixin(...)`
     - `_should_split_short_chat_block_for_weixin(...)`
   - Verify whether `send()` does something like:
     - format message
     - split into chunks
     - loop over chunks and send each separately

3. **Do not jump to encoding conclusions**
   - If the symptom is only on Weixin and especially with short/multiline Chinese text, first suspect **chunking heuristics**.
   - Email-side MIME issues like `unknown-8bit` are separate unless the exact same path is involved.

4. **Write/flip a regression test before patching**
   - In `tests/gateway/test_weixin.py`, add or update a focused test using a short Chinese multiline example such as:
     - `"第一行\n第二行\n第三行"`
   - Run the single test first to get a red failure.

5. **Apply the minimal fix**
   - Preferred default behavior: if content is already under `MAX_MESSAGE_LENGTH`, keep it as **one bubble**.
   - Preserve explicit legacy behavior only when line-by-line splitting is intentionally enabled via config/flag.

6. **Re-run tests**
   - First run the targeted regression test.
   - Then run the full Weixin test file:
     - `python -m pytest tests/gateway/test_weixin.py -q`

7. **Restart the gateway and verify runtime pickup**
   - Use the repo venv first:
     - `source venv/bin/activate`
   - Then:
     - `hermes gateway restart`
     - `hermes gateway status`
   - If status still shows draining, note that code is fixed but runtime cutover may still be pending.

## Proven root cause patterns

### Pattern A: Weixin-side chunking of short multiline Chinese replies

A confirmed failure mode in this repo was:
- `WeixinAdapter.send()` split one formatted reply into `chunks`
- `_split_text_for_weixin_delivery(...)` split even when the message was not over the max length
- short Chinese multiline replies were treated as "chatty" and broken into multiple bubbles
- users perceived this as missing/truncated text

### Pattern B: Global streaming incorrectly enabling fallback sends on non-editable Weixin

Another confirmed failure mode was:
- `WeixinAdapter` does **not** support message editing (`SUPPORTS_MESSAGE_EDITING = False`)
- but `gateway/run.py` could still enable streaming when global `display.streaming = true`
- that forced Weixin onto the stream-consumer fallback send path instead of stable final-only delivery
- the result could look like "last few Chinese characters are missing" or the tail of the reply never fully arriving
- this contradicted the code comments/intent that Weixin should default to final-only unless explicitly overridden

Debug this by checking together:
- `gateway/run.py`
- `gateway/display_config.py`
- actual runtime config in `~/.hermes/config.yaml`, especially:
  - `display.streaming`
  - `display.platforms.weixin.streaming`

## Cron auto-delivery observability lesson

When the symptom is specifically **"cron job ran, produced text, but Weixin chat seems to show nothing"**, do **not** rely on the cron session alone.

Important repo-specific behavior discovered during investigation:

- `cron/scheduler.py:_deliver_result(...)` handles cron auto-delivery after `final_response` is produced.
- Successful cron delivery returns `None` and logs success, but does **not** persist a send receipt like `message_id` back into the cron session or job record.
- `tests/cron/test_scheduler.py` explicitly asserts that **cron deliveries should NOT mirror into the gateway session**.
- Therefore a cron session whose final message is just the generated body may still have attempted delivery; absence of a send receipt in that session is **not proof of non-delivery**.
- `last_status = ok` means the agent run succeeded.
- Delivery success/failure is tracked separately via `last_delivery_error`.

So for cron + Weixin incidents, separate these questions:
1. Did the job execute and generate a response?
2. Was auto-delivery configured to the expected Weixin target?
3. Did `last_delivery_error` record a send failure?
4. Are there adapter/log signals of delivery, even if the session lacks a mirrored receipt?

Practical verification sequence that worked in this repo:

```bash
# 1) Confirm the scheduled job exists and inspect last_status / last_delivery_error
hermes cron list

# 2) Inspect persisted cron output directly
ls ~/.hermes/cron/output/<job_id>/

# 3) Read the latest run artifact to distinguish "generation failed" vs
#    "content generated but client didn't visibly receive it"
```

Typical artifact path shape:
- `~/.hermes/cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md`

If the markdown artifact contains a full `## Response` section with the final digest/body, then:
- the cron agent run succeeded,
- content generation succeeded,
- and any remaining issue is downstream in delivery visibility / client appearance / adapter delivery reliability.

Do not confuse:
- **content generation success**,
- **cron auto-delivery attempt**,
- **session mirroring**, and
- **user-visible appearance in the Weixin client**.

## Proven minimal fixes

### Fix for chunking-default bug

In compact/default mode, when `len(content) <= max_length`, return:

```python
[content]
```

instead of auto-splitting based on short-chat heuristics.

Keep explicit legacy split behavior behind the config/flag path rather than the default path.

### Fix for non-editable-platform streaming bug

Introduce a shared resolver for streaming enablement (for example in `gateway/display_config.py`) with this precedence:

1. explicit per-platform override: `display.platforms.<platform>.streaming`
2. if the adapter does **not** support editing, default to `False`
3. otherwise follow global streaming (`display.streaming` / `StreamingConfig`)

In `gateway/run.py`, compute effective streaming with adapter capability awareness instead of blindly inheriting the global toggle.

Safe runtime mitigation before/while patching code:

```bash
hermes config set display.platforms.weixin.streaming false
hermes gateway restart
```

## Pitfalls

- Do **not** patch blindly based on the word "encoding".
- Do **not** treat a successful API send as proof the user saw the full intended text.
- Do **not** broaden the fix into unrelated formatting or markdown refactors.
- Do **not** skip the focused regression test; the old behavior may already be encoded in tests and must be intentionally updated.

## Verification checklist

- [ ] A Chinese multiline regression test exists
- [ ] The test fails before the patch
- [ ] The patch only changes Weixin chunking behavior
- [ ] If streaming/final-only behavior is involved, there is a regression test for non-editable platforms vs global streaming
- [ ] `tests/gateway/test_weixin.py` passes fully
- [ ] `tests/gateway/test_display_config.py` passes when touching streaming resolution
- [ ] Gateway restart/status has been checked
- [ ] Final summary explains whether the issue came from chunk splitting, global streaming resolution, or both

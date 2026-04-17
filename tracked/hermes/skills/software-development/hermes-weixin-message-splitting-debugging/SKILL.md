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
- sometimes `gateway/run.py`

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

## Proven root cause pattern

A confirmed failure mode in this repo was:
- `WeixinAdapter.send()` split one formatted reply into `chunks`
- `_split_text_for_weixin_delivery(...)` split even when the message was not over the max length
- short Chinese multiline replies were treated as "chatty" and broken into multiple bubbles
- users perceived this as missing/truncated text

## Proven minimal fix

In compact/default mode, when `len(content) <= max_length`, return:

```python
[content]
```

instead of auto-splitting based on short-chat heuristics.

Keep explicit legacy split behavior behind the config/flag path rather than the default path.

## Pitfalls

- Do **not** patch blindly based on the word "encoding".
- Do **not** treat a successful API send as proof the user saw the full intended text.
- Do **not** broaden the fix into unrelated formatting or markdown refactors.
- Do **not** skip the focused regression test; the old behavior may already be encoded in tests and must be intentionally updated.

## Verification checklist

- [ ] A Chinese multiline regression test exists
- [ ] The test fails before the patch
- [ ] The patch only changes Weixin chunking behavior
- [ ] `tests/gateway/test_weixin.py` passes fully
- [ ] Gateway restart/status has been checked
- [ ] Final summary explains that the issue was chunk splitting, not necessarily byte-level loss

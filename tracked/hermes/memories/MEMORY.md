This environment has Claude Code installed and callable as `claude` from /home/liuli/.hermes/node/bin/claude; auth status uses ANTHROPIC_AUTH_TOKEN with base URL https://yxai.chat.
§
This environment also has Codex CLI and Gemini CLI installed and working: `codex` at /home/liuli/.hermes/node/bin/codex (codex-cli 0.121.0, provider yxai) and `gemini` at /home/liuli/.hermes/node/bin/gemini (0.38.1).
§
CodeIndex repo is cloned locally at /home/liuli/projects/CodeIndex and should be used as the default prompt/index-first workflow reference when a project has a codeindex/ directory.
§
This Hermes environment has QQ email configured as 50803169@qq.com, and direct SMTP sending works after updating the QQ mailbox authorization code on 2026-04-16.
§
在 adc.acsbim.com:7002 的项目空间页，进入“创意产业园”等项目时，优先定位项目名称文字后点击其下方的项目图片/封面图；比直接点击文字更容易触发实际跳转。
§
For Hermes one-shot cron debugging: do not treat `cronjob list` as authoritative after execution; successful once jobs may disappear from jobs.json. Prefer ~/.hermes/cron/output/<job_id>/ plus latest_run.json as the stronger execution proof.
§
Cron one-shot observability in hermes-agent: commit 46c19957 added cron.jobs.save_job_run_record() and scheduler writes ~/.hermes/cron/output/<job_id>/latest_run.json with success/output_file/deliver/delivery_error/delivery_metadata/error so once jobs can be verified even after removal from jobs.json.
§
In this Hermes setup, cron deliver=origin can fail to resolve a Weixin target ('no delivery target resolved for deliver=origin'), while explicit deliver='weixin:<chat_id>' succeeds and reaches the chat; latest_run.json captures this reliably.
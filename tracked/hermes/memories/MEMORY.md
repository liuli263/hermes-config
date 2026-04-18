本环境可用 claude/codex/gemini 三个 CLI agent；claude 路径 /home/liuli/.hermes/node/bin/claude，认证走 ANTHROPIC_AUTH_TOKEN + https://yxai.chat。
§
codex=/home/liuli/.hermes/node/bin/codex（0.121.0, provider yxai），gemini=/home/liuli/.hermes/node/bin/gemini（0.38.1）。
§
中央 CodeIndex 仓库在 /home/liuli/projects/CodeIndex；项目若需索引，默认参考该仓库与 index-first 工作流。
§
This Hermes environment has QQ email configured as 50803169@qq.com, and direct SMTP sending works after updating the QQ mailbox authorization code on 2026-04-16.
§
在 adc.acsbim.com:7002 的项目空间页，进入“创意产业园”等项目时，优先定位项目名称文字后点击其下方的项目图片/封面图；比直接点击文字更容易触发实际跳转。
§
For Hermes one-shot cron debugging: do not treat `cronjob list` as authoritative after execution; successful once jobs may disappear from jobs.json. Prefer ~/.hermes/cron/output/<job_id>/ plus latest_run.json as the stronger execution proof.
§
Cron one-shot observability in hermes-agent: commit 46c19957 added cron.jobs.save_job_run_record() and scheduler writes ~/.hermes/cron/output/<job_id>/latest_run.json with success/output_file/deliver/delivery_error/delivery_metadata/error so once jobs can be verified even after removal from jobs.json.
§
本环境 Weixin cron deliver=origin 已修复并验证；一次性 cron 的执行证明优先看 ~/.hermes/cron/output/<job_id>/latest_run.json，而非 cronjob list。
§
User wants a daily 03:00 China-time Hermes cache cleanup cron that removes files older than 24 hours from ~/.hermes/cache/documents and ~/.hermes/cache/screenshots only.
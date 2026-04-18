User wants a daily 7:00 AM (China time) digest of the world's top 10 news stories delivered in this WeChat chat, in Simplified Chinese.
§
User prefers Codex as the primary coding agent and Claude Code as auxiliary; use Codex whenever feasible because the user has a cheap Codex plan.
§
User wants me to use the CodeIndex program to optimize prompts and reduce token usage during development whenever the repository/tool is accessible in the environment.
§
User wants a work-completion summary after tasks are finished.
§
User prefers replies in Chinese.
§
用户要求：凡是我修改代码后，都默认自动运行相关测试或最小验证，不需要再提醒。
§
用户要求把 Hermes 相关配置、代码以及关于 agent 的记忆/要求统一纳入 GitHub 管理；不同 agent 分开存放；后续相关变更默认按该方向处理，并尽量自动提交且备注详细。
§
用户要求不要使用项目内置的 CodeIndex 副本；后续项目统一使用中央脚本 /home/liuli/projects/CodeIndex/CreateIndex.py 生成项目根 codeindex/。
§
用户希望把可复用的网站操作能力（如 adc.acsbim.com 流程）封装成 Hermes 技能，并尽量附带可落地的 Python 程序/脚本模板，方便后续直接调用。
§
用户希望排查/修复过程中不要反复确认，默认持续推进，并每隔5分钟主动汇报一次进度。
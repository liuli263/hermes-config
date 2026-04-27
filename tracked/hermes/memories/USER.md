User wants a daily 7:00 AM (China time) digest of the world's top 10 news stories delivered in this WeChat chat, in Simplified Chinese.
§
用户偏好：中文回复；编码优先 Codex、Claude 辅助；开发中尽量用 CodeIndex 降 token；任务完成后给总结。
§
用户要求统一使用中央脚本 /home/liuli/projects/CodeIndex/CreateIndex.py 在项目根生成 codeindex/，不要用项目内置 CodeIndex 副本。
§
用户希望把可复用网站自动化流程封装成 Hermes 技能，并尽量附可直接运行的 Python 模板。
§
用户的长期执行准则：收到任务后立即开始、少废话；除非绝对必要不要询问，默认自动推进直到完成；任务执行中每隔5分钟主动汇报进度直到结束；任务完成后要总结任务并提炼知识经验，写入记忆/技能；完成所有相关代码与配置的commit提交，若提交暂时失败可创建临时定时任务在稍后自动完成并删除；任务结束后必须向用户发送一份任务总结汇报。
§
用户的求职筛选偏好：上班地点需在蒙特利尔西岛柯克兰市车程30分钟内；时薪不低于20加元；优先可居家办公、年假长、福利好；语言上英语优先，法语可用。
§
用户要求：今后所有研发相关任务（含方案设计、代码评审、bug定位）统一采用多代理流程：先让 Codex 与 Claude Code 多轮讨论形成完善方案；在用户未明确同意方案前，必须明确禁止两者修改任何代码；只有用户明确同意方案并确认开始改代码后，才交给 Codex 实施修改；Claude 不负责改代码，但 Codex 改完后必须交给 Claude 做评审；评审通过后才允许由 Codex 提交 git；提交信息必须为中文且详细；提交后还必须自动 push 到远端。以后凡开发相关任务都按此规则执行。
§
用户补充要求：所有历史沟通记录都需要通过邮件补充发送到 50803169@qq.com。
§
用户新增规则：所有开发相关工作（包括性能评估）都应优先安排 Codex 和 Claude Code 执行，而不是由 Hermes 亲自做；执行时要求 Codex 与 Claude Code 相互辩论，直到达成一致。
§
用户新增规则：凡 Codex 与 Claude Code 在任务中的辩论、沟通、达成一致过程，详细记录都必须邮件发送到 50803169@qq.com。
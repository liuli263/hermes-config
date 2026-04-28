User wants a daily 7:00 AM (China time) digest of the world's top 10 news stories delivered in this WeChat chat, in Simplified Chinese.
§
用户偏好：中文回复；编码优先 Codex、Claude 辅助；开发中尽量用 CodeIndex 降 token；任务完成后给总结。
§
CodeIndex规则：条件默认用中央脚本 `python3 /home/liuli/projects/CodeIndex/CreateIndex.py` 生成/读项目 `codeindex/`；适合大/陌生项目、多代理交接、符号定位。小项目或目标文件明确可直接 rg/read_file。索引只作导航，关键逻辑/调用关系须回源码验证；少量改动可 `--files`。
§
用户希望把可复用网站自动化流程封装成 Hermes 技能，并尽量附可直接运行的 Python 模板。
§
用户要求：开发任务一旦已明确批准开始实施，Hermes 应自动连续推进各阶段，不要每阶段停下来等用户确认；只有遇到实质性决策、风险或阻塞才询问。
§
用户的求职筛选偏好：上班地点需在蒙特利尔西岛柯克兰市车程30分钟内；时薪不低于20加元；优先可居家办公、年假长、福利好；语言上英语优先，法语可用。
§
用户要求：今后所有研发相关任务（含方案设计、代码评审、bug/测试失败/异常根因调查、性能评估）统一采用 Codex ↔ Claude Code 串行多代理流程；根因调查也必须由 Codex 调查后交 Claude Code 审查确认，不能只由 Codex/Hermes 单方定论；在用户未明确同意方案前禁止两者修改代码；用户同意后由 Codex 实施，Claude 评审；评审通过后 Codex 用中文详细提交并 push。
§
用户补充要求：所有历史沟通记录都需要通过邮件补充发送到 50803169@qq.com。
§
用户新增规则：所有开发相关工作（包括性能评估）都应优先安排 Codex 和 Claude Code 执行，而不是由 Hermes 亲自做；执行时要求 Codex 与 Claude Code 相互辩论，直到达成一致。
§
用户新增规则：凡 Codex 与 Claude Code 在任务中的辩论、沟通、达成一致过程，详细记录都必须邮件发送到 50803169@qq.com。
§
用户要求：调度 Codex 和 Claude Code 工作时不要同时发送命令；必须按串行回合制进行：先让 Codex 处理/提出意见，再让 Claude Code 评审并给出建议，再把 Claude Code 的回复转交给 Codex 继续给意见，如此反复，直到双方达成一致。
§
用户要求：Codex/Claude 协作时，Hermes 收到任一方回复后必须立即把完整原文转发给用户；超过微信约2000字限制时自动分多条发送，不能截断或只给摘要/路径；不要等任务结束再汇总。
§
用户强烈要求长任务必须自动主动汇报进展；阶段开始/agent启动/agent完成/审查启动/命令中断或重试/长时间无输出/阻塞都要立刻发简短状态更新，不要等用户催问。
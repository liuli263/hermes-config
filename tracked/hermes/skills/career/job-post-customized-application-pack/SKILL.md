---
name: job-post-customized-application-pack
description: 接收职位信息后，结合企业调研与简历 JSON，生成职位分析、定制简历、面试资料、多语言 Word 文件，归档到 resume/dept，并发送到指定邮箱。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [career, resume, interview, cover-letter, email, docx, job-matching]
---

# 接收职位信息并生成定制化求职材料

## 目标
接收到职位信息后，快速完成以下任务：
1. 检索企业信息（福利、员工评价、业务情况、技术栈、面试风格等）
2. 结合 `latest_sanitized_profile.json` 做岗位匹配分析
3. 生成职位分析报告
4. 生成定制化简历（中 / 英 / 法）
5. 生成面试与求职材料包（中 / 英 / 法）
6. 检查所有附件中的占位敏感信息是否已恢复为真实信息
7. 将结果归档到 `resume/dept/职位_公司_时间/`
8. 通过邮件发送全部 Word 附件到 `50803169@qq.com`
9. 完成后在微信里汇报总结

## 依赖输入
本技能默认读取：
- `resume/json/latest_sanitized_profile.json`（分析用）
- `resume/json/latest_real_profile.json`（最终导出用）
- `resume/json/latest_mapping.json`（如需要）
- `resume/request/current_requirements.json`（职位匹配标准）

## 执行步骤
1. 先用 `web` / 搜索工具检索企业资料，至少覆盖：
   - 官网 / 产品 / 主营业务
   - LinkedIn 公司页 / careers 页面
   - Glassdoor / Indeed / Reddit / 新闻等员工评价或舆情
   - 薪酬、福利、团队文化、稳定性（能找到就写）
   - 优先按 `references/company-research-checklist.md` 的字段采集，并保留来源链接与可信度标注。
2. 若用户有明确地理筛选条件（例如通勤半小时内），必须额外查公司 office / locations 页面，先定位办公地址，再判断是否值得继续投递；不要只看 JD 文本。
3. 若用户特别关心远程、福利、年假、语言环境、签证支持等，必须将这些项单独列为“已确认 / 未确认 / 员工提及但未官方确认”，不能混成泛泛文化描述。
4. 结构化整理职位信息：
   - 岗位职责
   - 硬技能 / 软技能
   - 脑洞强度 / 沟通强度 / owner 意识 / 管理跨度
   - 语言要求
   - 地域、签证、远程要求
4. 读取脱敏简历 JSON 与求职要求 JSON，先做匹配分析。
5. 整理好研究结论后，运行 `scripts/customize_application.py` 生成文档。
6. 文档生成后，运行脚本内建校验，确认占位敏感信息（如 `Alex Martin`）都已经替换为真实信息；若未替换，立即修复。
7. 若环境里没有 `python-docx`，可直接生成最小可用的 OOXML `.docx`（zip 包含 `[Content_Types].xml`、`_rels/.rels`、`word/document.xml`、`docProps/*`）；不要因为缺少库就停在说明阶段。
8. 使用 SMTP 将所有 `.docx` 附件发到 `50803169@qq.com`。
9. 在微信回报：
   - 职位匹配度评分
   - 已生成文件数量
   - 归档目录
   - 邮件发送结果
10. 公司调研报告优先按 `templates/company_research_report_template.md` 的结构输出，至少包含：一页摘要、详细报告、表格汇总、来源清单。

## 产物目录规范
默认根目录：
- 优先 `RESUME_ROOT`
- 否则 `~/resume`

目标目录：
- `resume/dept/职位_公司_时间/`

目录内建议至少包含：
- `job_analysis_zh.docx`
- `job_analysis_en.docx`
- `job_analysis_fr.docx`
- `resume_zh.docx`
- `resume_en.docx`
- `resume_fr.docx`
- `interview_pack_zh.docx`
- `interview_pack_en.docx`
- `interview_pack_fr.docx`
- `company_research_report.md`
- `manifest.json`
- `job_posting.txt`
- `company_research.txt`

## 命令示例
```bash
python3 scripts/customize_application.py \
  --position "Senior AI Product Manager" \
  --company "Example Corp" \
  --job-text-file /tmp/job.txt \
  --research-text-file /tmp/company_research.txt \
  --requirements-json ~/resume/request/current_requirements.json \
  --sanitized-json ~/resume/json/latest_sanitized_profile.json \
  --real-json ~/resume/json/latest_real_profile.json \
  --send-email
```

## 输出要求
脚本必须输出 JSON，至少包含：
- `resume_root`
- `task_dir`
- `score`
- `generated_files`
- `email_sent`
- `email_to`
- `validation`
- `summary`

## 邮件要求
- 收件人：`50803169@qq.com`
- 标题格式：`职位_公司_时间_AI定制化简历任务`
- 使用本机 SMTP 环境变量发送
- 若 SMTP 不可用，必须在输出 JSON 里明确失败原因

## 注意事项
- 研究与分析阶段默认使用脱敏 JSON。
- 导出最终对外文件时，必须恢复真实信息。
- 若 `/resume` 不可写，应自动回退到 `~/resume` 或 `RESUME_ROOT`。
- 任务结束后的“通过微信总结”由当前会话最终回复承担。

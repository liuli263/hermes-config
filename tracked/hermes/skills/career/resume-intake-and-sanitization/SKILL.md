---
name: resume-intake-and-sanitization
description: 接收简历文件并统一归档：原件按日期入库到 history，提取脱敏 JSON 到 resume/json，真实资料仅本地保留，后续 AI 分析默认使用脱敏资料。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [career, resume, sanitization, privacy, intake]
---

# 接收简历并汇总存储

## 目标
1. 将用户发送的所有简历原件按接收日期归档，避免覆盖
2. 将简历内容转成 JSON 做汇总
3. 生成脱敏版 JSON 供后续 AI 分析使用
4. 保留真实版 JSON 仅本地使用
5. 完成后在微信里给出总结

## 存储规范
默认根目录：
- 优先 `RESUME_ROOT`
- 否则 `~/resume`

使用目录：
- `resume/hA829istory/`：原始简历归档
- `resume/json/`：真实 / 脱敏结构化数据

主要文件：
- `resume/json/latest_real_profile.json`
- `resume/json/latest_sanitized_profile.json`
- `resume/json/latest_mapping.json`
- `resume/json/YYYY-MM-DD_HHMMSS_resume_summary.json`

## 执行步骤
1. 接收到简历附件后，先保存原件。
2. 若是 PDF / 图片扫描件 / DOCX：
   - 先用 `ocr-and-documents` 技能提取文本
   - 再运行本技能脚本做归档和脱敏
3. 执行 `scripts/intake_resume.py`：
   - 原始文件复制到 `hA829istory/`，文件名前缀加入接收日期
   - 解析文本中的姓名、电话、邮箱、地址、出生日期等敏感信息
   - 生成真实 JSON 与脱敏 JSON
   - 保存映射表，供后续恢复真实信息
4. 后续 AI 分析时，优先读取 `latest_sanitized_profile.json`
5. 若需要正式投递材料，再结合 `latest_real_profile.json` 还原真实信息
6. 完成后在微信回报：
   - 已入库文件名
   - 脱敏 JSON 路径
   - 真实 JSON 路径（仅本地）

## 命令示例
```bash
python3 scripts/intake_resume.py \
  --input-file /path/to/resume.pdf \
  --text-file /tmp/resume_extracted.txt
```

或：

```bash
python3 scripts/intake_resume.py \
  --input-file /path/to/resume.md \
  --text "Jean Dupont\nTéléphone: +33 6 12 34 56 78\nEmail: jean@example.com"
```

## 输出要求
脚本必须输出 JSON，至少包含：
- `resume_root`
- `history_file`
- `real_json`
- `sanitized_json`
- `mapping_json`
- `detected_fields`
- `summary`

## 脱敏要求
至少替换：
- 姓名
- 电话
- 邮箱
- 住址 / 城市 / 邮编
- 出生日期（如明显出现）
- 身份证 / 护照号（如出现）

占位值示例：
- 姓名 → `Alex Martin`
- 电话 → `+33 6 00 00 00 00`
- 邮箱 → `alex.martin@example.com`
- 地址 → `10 Rue Exemple, Paris 75000, France`

## 注意事项
- 若用户只发来附件而无可解析文本，不要臆造内容；先提取文本再入库。
- 所有 AI 总结、职位匹配、面试分析都默认使用脱敏 JSON。
- 真值映射只保存在本地目录，不在对外分享文件中暴露。
- 任务结束后的“通过微信总结”由当前会话最终回复承担。

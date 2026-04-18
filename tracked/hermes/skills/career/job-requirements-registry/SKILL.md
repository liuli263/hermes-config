---
name: job-requirements-registry
description: 更新/登记求职要求：提示历史要求、采集新要求、汇总保存到 resume/request，并在完成后通过微信回报总结。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [career, resume, recruiting, requirements, weixin]
---

# 更新 / 登记求职要求

适用场景：用户要更新、补充、确认自己的求职偏好与筛选标准，并将其作为后续职位匹配度分析的统一标准。

## 目标
1. 提示用户之前的求职要求（如果已有）
2. 询问并收集最新要求
3. 将要求保存到 `resume/request/`
4. 维护一份最新汇总文件，供后续职位匹配技能直接读取
5. 完成后在微信里给出简短总结

## 存储规范
默认根目录：
- 优先使用环境变量 `RESUME_ROOT`
- 否则使用 `~/resume`

本技能使用：
- `request/`：历史快照与最新汇总

主要文件：
- `resume/request/current_requirements.md`
- `resume/request/current_requirements.json`
- `resume/request/YYYY-MM-DD_HHMMSS_requirements.md`
- `resume/request/YYYY-MM-DD_HHMMSS_requirements.json`

## 执行步骤
1. 先检查 `resume/request/current_requirements.md` 与 `current_requirements.json` 是否存在。
2. 如果存在，先向用户展示“上次要求摘要”，再继续追问。
3. 使用 `clarify` 询问用户以下信息（允许自由回答）：
   - 目标岗位 / 职能方向
   - 行业偏好
   - 城市 / 国家 / 签证限制
   - 薪资范围
   - 语言要求
   - 必须满足条件
   - 不能接受的条件
   - 对远程/出差/加班/管理跨度/技术栈的偏好
4. 将用户原始回答整理为结构化 JSON，并生成中文摘要 Markdown。
5. 运行 `scripts/update_job_requirements.py` 写入历史快照与最新汇总。
6. 完成后在当前微信对话发送总结：
   - 已更新哪些要求
   - 存储路径
   - 后续职位匹配会默认使用这套标准

## 命令示例
```bash
python3 scripts/update_job_requirements.py \
  --text-file /tmp/requirements.txt \
  --source weixin
```

或：

```bash
python3 scripts/update_job_requirements.py \
  --text "目标岗位：AI 产品经理；地点：巴黎/蒙特利尔；语言：中英法；不能接受纯销售岗" \
  --source weixin
```

## 输出要求
脚本必须输出 JSON，至少包含：
- `resume_root`
- `snapshot_markdown`
- `snapshot_json`
- `current_markdown`
- `current_json`
- `summary`

## 微信回报模板
可直接复用：

> 求职要求已更新。
> - 核心方向：...
> - 必须条件：...
> - 排除项：...
> - 已保存：`~/resume/request/...`
> 后续我会按这份标准评估职位匹配度。

## 注意事项
- 若 `/resume` 不可写，不要失败；自动回退到 `~/resume` 或 `RESUME_ROOT`。
- 不要覆盖历史快照。
- 最新汇总文件必须始终更新，供下游技能读取。
- 任务结束后的“通过微信总结”由当前会话最终回复承担。

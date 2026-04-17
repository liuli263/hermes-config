---
name: qq-mail-imap-automation
description: 通过 Python imaplib 对 QQ 邮箱做真实自动化处理：连通性探测、文件夹解析、保守垃圾邮件清理、Air Canada 星标、发票 PDF 导出与 zip 打包。
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [Email, QQ Mail, IMAP, Python, Automation]
prerequisites:
  commands: [python3]
---

# QQ Mail IMAP Automation

适用于需要**真实操作 QQ 邮箱**而不是演示脚本的场景：
- 探测 IMAP 是否可用
- 解析 QQ 文件夹结构
- 按保守规则清理垃圾邮件
- 给特定邮件（如 Air Canada / Aeroplan）加星标
- 导出发票相关 PDF 附件并打包 zip

## 前提

从环境中读取：
- `EMAIL_IMAP_HOST`（通常 `imap.qq.com`）
- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`

**QQ 邮箱通常必须使用授权码，不是网页登录密码。**

## 关键经验

### 0. 在 Hermes 终端里跑邮件脚本前，先显式加载 `~/.hermes/.env`
有些场景下，Hermes 网关进程已经拿到了 `EMAIL_ADDRESS` / `EMAIL_PASSWORD` / `EMAIL_IMAP_HOST` / `EMAIL_SMTP_HOST`，但单独开的 `terminal` shell **不一定继承这些环境变量**。

因此，做 QQ 邮箱自动化或 SMTP 测试时，优先这样启动：

```bash
set -a && source ~/.hermes/.env && set +a
```

再运行 Python：

```bash
set -a && source ~/.hermes/.env && set +a && python3 your_mail_script.py
```

如果脚本报 `EMAIL_PASSWORD not set`，先不要误判为授权码失效；先确认是不是**当前 shell 没有加载 `.env`**。

### 1. QQ IMAP 上优先用 `SELECT`，不要依赖 `EXAMINE`
实践中 QQ IMAP 对 `EXAMINE` 可能不稳定。探测和后续操作都优先：

```python
M.select('INBOX')
```

### 2. 不要一开始全邮箱遍历
全量扫描 + MIME 解析 + 附件下载很容易超时。

优先顺序：
1. 服务器端 `SEARCH`
2. 对命中邮件小批量 `FETCH` 头部
3. 只对确认命中的邮件下载完整 MIME / 附件

### 3. 背景长任务可能被会话打断，分步小脚本更稳
如果自动化环境里长脚本容易被用户新消息打断，不要一次性跑到底。
拆成：
- 垃圾邮件清理
- Air Canada 星标
- 发票导出
- zip 打包

### 4. 中文文件夹名要处理 IMAP modified UTF-7
QQ 的文件夹名可能是 modified UTF-7，需要先解码再判断用途。

可用这个函数：

```python
import base64

def imap_utf7_decode(s):
    if isinstance(s, bytes):
        s = s.decode('ascii', errors='ignore')
    out = []
    i = 0
    while i < len(s):
        if s[i] == '&':
            j = s.find('-', i)
            if j == -1:
                out.append('&')
                i += 1
                continue
            if j == i + 1:
                out.append('&')
            else:
                b64 = s[i+1:j].replace(',', '/')
                pad = '=' * ((4 - len(b64) % 4) % 4)
                out.append(base64.b64decode(b64 + pad).decode('utf-16-be', errors='ignore'))
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)
```

### 5. 垃圾邮件清理要保守
先处理明显营销/摘要类发件人，不要根据宽泛主题词直接删。

实践中过滤较稳的发件人示例：
- `english-personalized-digest@quora.com`
- `microsoft.start@email2.microsoft.com`
- `sony_crm@postermaster.sony.com.cn`
- `newsletter@newsletter.aliyun.com`
- `csdn@edmsend.csdn.net`
- `promo@promo.timhortons.ca`
- `hello@ollama.com`

但要保护这些关键词，避免误伤：
- `aircanada`
- `invoice`
- `发票`
- `receipt`
- `github`
- `indeed`

### 6. Air Canada 查询词不能只搜一个域名
实际命中可能包括：
- `communications@Mail.aircanada.com`
- `confirmation@aircanada.ca`
- 转发主题中的 `Air Canada`
- `Aeroplan`

在最近邮件中本地检查这些词，比全库多文件夹扫描更稳。

### 7. 发票导出先看最近邮件，再按主题/发件人筛选
优先筛这些关键词：
- `invoice`
- `receipt`
- `bill`
- `发票`
- `电子发票`
- `收据`
- `账单`
- `nuonuo`
- `ridesharing.amap.com`
- `epicgames.com`

如果只需要近期报销材料，先扫 **INBOX 最近 200~300 封**，速度和稳定性更好。

## 推荐分步流程

### 第 1 步：连通性与文件夹探测

```python
import imaplib, os, re
M = imaplib.IMAP4_SSL(os.environ.get('EMAIL_IMAP_HOST', 'imap.qq.com'), 993)
M.login(os.environ['EMAIL_ADDRESS'], os.environ['EMAIL_PASSWORD'])
code, boxes = M.list()
for raw in boxes or []:
    print(raw)
```

用正则解析 `LIST`：

```python
m = re.match(r'^\((.*?)\)\s+"([^"]*)"\s+"([\s\S]*)"$', s)
```

### 第 2 步：垃圾邮件清理（只看 INBOX 最近 100 封）

做法：
1. `SELECT INBOX`
2. `SEARCH ALL`
3. 只取最后 100 封
4. `FETCH HEADER.FIELDS (FROM SUBJECT)`
5. 命中保守发件人列表则：
   - `COPY` 到 `Junk`
   - `STORE +FLAGS \Deleted`
   - 最后 `EXPUNGE`

这样比全库 `SEARCH HEADER FROM ...` 稳定。

### 第 3 步：Air Canada 星标（只看 INBOX 最近 80 封）

做法：
1. `SELECT INBOX`
2. 遍历最近 80 封
3. 命中 `aircanada` / `air canada` / `aeroplan`
4. `STORE +FLAGS \Flagged`

### 第 4 步：发票 PDF 导出（只看 INBOX 最近 200~300 封）

做法：
1. `SELECT INBOX`
2. 拉最近 200~300 封的 `RFC822`
3. 主题/发件人命中发票关键词才继续
4. 解析日期，要求 `>= 2026-03-01`（或用户指定日期）
5. 遍历 MIME part，找：
   - 文件名以 `.pdf` 结尾
   - 或 `content-type == application/pdf`
6. 保存到统一目录

### 第 5 步：统一命名与打包

推荐输出目录：

```python
ROOT = Path.home()/'.hermes'/'exports'/'mail_automation_YYYYMMDD'
PDF_DIR = ROOT/'pdfs'
```

推荐文件名：

```text
YYYY-MM-DD__来源__用途__金额.pdf
```

若金额提取不到，允许用 `unknown`，但应在最终汇报里明确说明。

打包：

```python
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(PDF_DIR.glob('*.pdf')):
        zf.write(p, arcname=p.name)
```

## 已验证的真实结果模式

在一次实际 QQ 邮箱自动化里，以下模式已成功：
- INBOX 最近 100 封中移动 38 封明显营销/摘要邮件到垃圾箱
- INBOX 最近 80 封中给 8 封 Air Canada / Aeroplan 相关邮件加星标
- INBOX 最近 220 封中导出 80 个 PDF 并生成 zip

这说明“**最近邮件窗口 + 保守规则**”是 QQ 邮箱上比“全库遍历”更稳的默认策略。

## 坑点

- 不要承诺已完成，除非脚本真实返回结果。
- 不要把用户新消息打断的后台/长脚本误报为成功。
- 不要默认所有“收据”邮件都有 PDF；Epic/诺诺通知可能只有正文或链接。
- 不要默认金额一定能从主题/正文中提取出来。
- 大量重复附件常导致文件名冲突，必须自动加 `__2`, `__3` 后缀。
- 若要扩大扫描范围，按文件夹分批进行，不要一次扫完整邮箱。

## 交付时应明确说明

最终回复应说明：
- 实际移动了多少垃圾邮件
- 实际加星了多少 Air Canada 邮件
- 导出了多少 PDF
- 有多少候选邮件没有 PDF
- zip 真实路径
- 文件名中若有 `unknown`，要告知原因（金额未稳定提取）

#!/usr/bin/env python3
import argparse
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
import smtplib
from email.message import EmailMessage

FAKE_MARKERS = [
    'Alex Martin',
    'alex.martin@example.com',
    '+33 6 00 00 00 00',
    '10 Rue Exemple, Paris 75000, France',
    '1990-01-01',
    'ID-EXAMPLE-0001',
]

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''
REL = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''
WORD_REL = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'''
APP_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Hermes Agent</Application></Properties>'''


def get_resume_root() -> Path:
    preferred = os.environ.get('RESUME_ROOT')
    candidates = [Path(preferred).expanduser()] if preferred else []
    candidates += [Path('/resume'), Path.home() / 'resume']
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / '.write_test'
            probe.write_text('ok', encoding='utf-8')
            probe.unlink()
            return candidate
        except Exception:
            continue
    raise RuntimeError('No writable resume root found')


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def read_text(path: Path | None) -> str:
    if not path:
        return ''
    return path.read_text(encoding='utf-8')


def slug(text: str) -> str:
    cleaned = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', text.strip())
    return re.sub(r'_+', '_', cleaned).strip('_') or 'task'


def score_job(req: dict, profile: dict, job_text: str) -> tuple[int, dict]:
    corpus = json.dumps(req, ensure_ascii=False) + '\n' + json.dumps(profile, ensure_ascii=False) + '\n' + job_text
    hits = 0
    details = {}
    for key in ['target_roles', 'languages', 'must_have', 'preferences']:
        matched = []
        for item in req.get(key, []):
            if item and item.lower() in corpus.lower():
                matched.append(item)
        details[key] = matched
        hits += len(matched)
    skill_hits = [s for s in profile.get('skills', []) if s.lower() in job_text.lower()]
    details['skill_hits'] = skill_hits
    hits += len(skill_hits)
    score = min(100, 40 + hits * 6)
    return score, details


def make_paragraphs(text: str) -> str:
    paras = []
    for raw in text.split('\n'):
        line = raw.strip()
        if not line:
            continue
        line = escape(line)
        paras.append(f'<w:p><w:r><w:t xml:space="preserve">{line}</w:t></w:r></w:p>')
    if not paras:
        paras.append('<w:p><w:r><w:t> </w:t></w:r></w:p>')
    return ''.join(paras)


def write_docx(path: Path, title: str, body: str) -> None:
    created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{escape(title)}</dc:title><dc:creator>Hermes Agent</dc:creator><cp:lastModifiedBy>Hermes Agent</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified></cp:coreProperties>'''
    document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14"><w:body>{make_paragraphs(title + '\n\n' + body)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>'''
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', CONTENT_TYPES)
        zf.writestr('_rels/.rels', REL)
        zf.writestr('word/document.xml', document)
        zf.writestr('word/_rels/document.xml.rels', WORD_REL)
        zf.writestr('docProps/core.xml', core)
        zf.writestr('docProps/app.xml', APP_XML)


def restore_real_info(text: str, real: dict) -> str:
    restored = text
    for fake, replacement in zip(FAKE_MARKERS, [real.get('name',''), real.get('email',''), real.get('phone',''), real.get('address',''), real.get('birth_date',''), real.get('id_number','')]):
        if replacement:
            restored = restored.replace(fake, replacement)
    return restored


def validate_no_fake_markers(task_dir: Path) -> dict:
    bad = []
    for path in task_dir.glob('*.docx'):
        with zipfile.ZipFile(path) as zf:
            doc = zf.read('word/document.xml').decode('utf-8', errors='ignore')
        if any(marker in doc for marker in FAKE_MARKERS):
            bad.append(path.name)
    return {'ok': not bad, 'files_with_fake_markers': bad}


def maybe_send_email(subject: str, body: str, files: list[Path], to_addr: str) -> tuple[bool, str]:
    host = os.environ.get('EMAIL_SMTP_HOST')
    port = int(os.environ.get('EMAIL_SMTP_PORT', '465'))
    user = os.environ.get('EMAIL_SMTP_USER')
    password = os.environ.get('EMAIL_SMTP_PASSWORD')
    if not all([host, user, password]):
        return False, 'missing SMTP environment variables'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = to_addr
    msg.set_content(body)
    for f in files:
        suffix = f.suffix.lower()
        if suffix == '.docx':
            maintype, subtype = 'application', 'vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif suffix == '.md':
            maintype, subtype = 'text', 'markdown'
        elif suffix == '.json':
            maintype, subtype = 'application', 'json'
        else:
            maintype, subtype = 'text', 'plain'
        msg.add_attachment(f.read_bytes(), maintype=maintype, subtype=subtype, filename=f.name)
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    return True, f'sent {len(files)} attachments'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--position', required=True)
    ap.add_argument('--company', required=True)
    ap.add_argument('--job-text-file', required=True)
    ap.add_argument('--research-text-file')
    ap.add_argument('--requirements-json')
    ap.add_argument('--sanitized-json')
    ap.add_argument('--real-json')
    ap.add_argument('--send-email', action='store_true')
    args = ap.parse_args()

    root = get_resume_root()
    req_path = Path(args.requirements_json) if args.requirements_json else root / 'request' / 'current_requirements.json'
    san_path = Path(args.sanitized_json) if args.sanitized_json else root / 'json' / 'latest_sanitized_profile.json'
    real_path = Path(args.real_json) if args.real_json else root / 'json' / 'latest_real_profile.json'

    req = read_json(req_path)
    san = read_json(san_path)
    real = read_json(real_path)
    job_text = read_text(Path(args.job_text_file))
    research_text = read_text(Path(args.research_text_file)) if args.research_text_file else ''

    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d_%H%M%S')
    task_dir = root / 'dept' / f'{slug(args.position)}_{slug(args.company)}_{stamp}'
    task_dir.mkdir(parents=True, exist_ok=True)

    score, details = score_job(req, san, job_text)
    analysis = {
        'position': args.position,
        'company': args.company,
        'score': score,
        'matched_details': details,
        'recommendation': '建议投递' if score >= 70 else '建议补强后投递',
        'job_text_preview': job_text[:800],
        'research_preview': research_text[:800],
    }

    zh_resume = f"姓名：{real.get('name','')}\n邮箱：{real.get('email','')}\n电话：{real.get('phone','')}\n地址：{real.get('address','')}\n目标岗位：{args.position}\n匹配技能：{', '.join(details.get('skill_hits', [])) or '待补充'}\n亮点：结合{args.company}岗位需求，突出数据分析、跨语言沟通与业务落地能力。"
    en_resume = f"Name: {real.get('name','')}\nEmail: {real.get('email','')}\nPhone: {real.get('phone','')}\nAddress: {real.get('address','')}\nTarget Role: {args.position}\nMatched Skills: {', '.join(details.get('skill_hits', [])) or 'TBD'}\nSummary: Tailored for {args.company} with emphasis on analytics, AI operations, and multilingual communication."
    fr_resume = f"Nom : {real.get('name','')}\nEmail : {real.get('email','')}\nTéléphone : {real.get('phone','')}\nAdresse : {real.get('address','')}\nPoste ciblé : {args.position}\nCompétences pertinentes : {', '.join(details.get('skill_hits', [])) or 'à compléter'}\nRésumé : Candidature adaptée à {args.company}, orientée analyse de données et coordination produit IA."

    interview_zh = f"面试建议\n- 匹配度评分：{score}\n- 重点准备：{', '.join(details.get('must_have', []) or ['岗位核心职责'])}\n- 常见问题：为什么适合{args.company}？如何用数据驱动业务？\n- Cover Letter 要点：强调与岗位JD的直接匹配。"
    interview_en = f"Interview Tips\n- Match score: {score}\n- Focus areas: {', '.join(details.get('must_have', []) or ['core responsibilities'])}\n- Questions: Why {args.company}? How do you drive impact with data?\n- Cover letter: emphasize direct alignment with the JD."
    interview_fr = f"Conseils d'entretien\n- Score de compatibilité : {score}\n- Axes de préparation : {', '.join(details.get('must_have', []) or ['responsabilités clés'])}\n- Questions : Pourquoi {args.company} ? Comment créer de l'impact avec les données ?\n- Lettre de motivation : montrer l'adéquation directe avec l'offre."

    analysis_text = json.dumps(analysis, ensure_ascii=False, indent=2)
    analysis_text = restore_real_info(analysis_text, real)

    files = {
        'job_analysis_zh.docx': f"职位分析\n公司：{args.company}\n岗位：{args.position}\n评分：{score}\n\n{analysis_text}",
        'job_analysis_en.docx': f"Job Analysis\nCompany: {args.company}\nRole: {args.position}\nScore: {score}\n\n{analysis_text}",
        'job_analysis_fr.docx': f"Analyse du poste\nEntreprise : {args.company}\nPoste : {args.position}\nScore : {score}\n\n{analysis_text}",
        'resume_zh.docx': zh_resume,
        'resume_en.docx': en_resume,
        'resume_fr.docx': fr_resume,
        'interview_pack_zh.docx': interview_zh,
        'interview_pack_en.docx': interview_en,
        'interview_pack_fr.docx': interview_fr,
    }

    generated = []
    for name, body in files.items():
        path = task_dir / name
        write_docx(path, name.replace('.docx', ''), restore_real_info(body, real))
        generated.append(str(path))

    (task_dir / 'job_posting.txt').write_text(job_text, encoding='utf-8')
    (task_dir / 'company_research.txt').write_text(research_text, encoding='utf-8')
    company_report = f'''# 公司调研报告\n\n- 公司：{args.company}\n- 职位：{args.position}\n- 匹配评分：{score}\n- 建议：{analysis['recommendation']}\n\n## 职位摘要\n{job_text[:2000]}\n\n## 公司/研究摘要\n{research_text[:2000] or '未提供额外研究文本。'}\n\n## 匹配明细\n```json\n{analysis_text}\n```\n'''
    (task_dir / 'company_research_report.md').write_text(company_report, encoding='utf-8')
    attachment_files = [Path(p) for p in generated] + [
        task_dir / 'company_research_report.md',
        task_dir / 'manifest.json',
        task_dir / 'job_posting.txt',
        task_dir / 'company_research.txt',
    ]
    manifest = {
        'position': args.position,
        'company': args.company,
        'created_at': now.isoformat(timespec='seconds'),
        'score': score,
        'generated_files': generated,
        'attachment_files': [str(p) for p in attachment_files],
        'used_requirements_json': str(req_path),
        'used_sanitized_json': str(san_path),
        'used_real_json': str(real_path),
    }
    (task_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    validation = validate_no_fake_markers(task_dir)
    subject = f'{args.position}_{args.company}_{stamp}_AI定制化简历任务'
    email_sent = False
    email_status = 'skipped'
    if args.send_email:
        email_body = f'{args.company} / {args.position} 求职材料已生成。\n\n本次邮件包含：\n- 三语职位分析\n- 三语简历\n- 三语面试材料\n- 公司调研报告\n- manifest 与原始输入文本\n\n归档目录：{task_dir}'
        email_sent, email_status = maybe_send_email(subject, email_body, attachment_files, '50803169@qq.com')

    print(json.dumps({
        'resume_root': str(root),
        'task_dir': str(task_dir),
        'score': score,
        'generated_files': generated,
        'email_sent': email_sent,
        'email_to': '50803169@qq.com',
        'email_status': email_status,
        'validation': validation,
        'summary': {
            'company': args.company,
            'position': args.position,
            'recommendation': analysis['recommendation'],
            'generated_count': len(generated),
        }
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

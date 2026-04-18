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
def load_local_env() -> None:
    env_path = Path.home() / '.hermes' / '.env'
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_local_env()

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


def bullets(items: list[str], prefix: str = '- ') -> str:
    out = []
    for item in items:
        s = str(item).strip()
        if s:
            out.append(f'{prefix}{s}')
    return '\n'.join(out)


def compact_skills(profile: dict, limit: int = 12) -> list[str]:
    return [s for s in profile.get('skills', []) if s][:limit]


def format_experience_blocks(profile: dict) -> tuple[str, str, str]:
    exps = profile.get('work_experience', []) or []
    zh_blocks, en_blocks, fr_blocks = [], [], []
    for exp in exps:
        period = exp.get('period', '')
        title = exp.get('title', '')
        company = exp.get('company', '')
        details = [d for d in exp.get('details', []) if d][:6]
        header = f'{period} | {title} | {company}'.strip(' |')
        zh_blocks.append(header + ('\n' + bullets(details, '• ') if details else ''))
        en_blocks.append(header + ('\n' + bullets(details, '- ') if details else ''))
        fr_blocks.append(header + ('\n' + bullets(details, '• ') if details else ''))
    return '\n\n'.join(zh_blocks), '\n\n'.join(en_blocks), '\n\n'.join(fr_blocks)


def job_focus_points(job_text: str, detail_matches: dict) -> list[str]:
    focus = []
    checks = [
        ('API', 'API / microservices validation'),
        ('SQL', 'SQL and data validation'),
        ('Jenkins', 'CI/CD collaboration'),
        ('GitLab', 'CI/CD collaboration'),
        ('Kafka', 'event-driven / message flow validation'),
        ('Postman', 'API testing tooling'),
        ('Swagger', 'REST contract validation'),
        ('Jira', 'defect lifecycle management'),
        ('Agile', 'Agile / Scrum delivery'),
        ('UAT', 'UAT support and business-rule validation'),
        ('Confluence', 'documentation and cross-team traceability'),
    ]
    lower = job_text.lower()
    for token, label in checks:
        if token.lower() in lower and label not in focus:
            focus.append(label)
    for item in detail_matches.get('must_have', []):
        if item not in focus:
            focus.append(item)
    return focus[:8]


def translate_focus_points(points: list[str], lang: str) -> list[str]:
    mapping = {
        'API / microservices validation': {
            'zh': 'API / 微服务接口验证',
            'fr': 'validation des API et microservices',
        },
        'SQL and data validation': {
            'zh': 'SQL 与数据校验',
            'fr': 'validation SQL et contrôle des données',
        },
        'CI/CD collaboration': {
            'zh': 'CI/CD 协作与交付链路',
            'fr': 'collaboration CI/CD et chaîne de livraison',
        },
        'event-driven / message flow validation': {
            'zh': '事件流 / 消息流验证',
            'fr': 'validation des flux événementiels et messages',
        },
        'API testing tooling': {
            'zh': 'API 测试工具链',
            'fr': 'outillage de test API',
        },
        'REST contract validation': {
            'zh': 'REST 接口契约验证',
            'fr': 'validation des contrats REST',
        },
        'defect lifecycle management': {
            'zh': '缺陷全生命周期跟踪',
            'fr': 'gestion du cycle de vie des anomalies',
        },
        'Agile / Scrum delivery': {
            'zh': 'Agile / Scrum 交付协作',
            'fr': 'livraison Agile / Scrum',
        },
        'UAT support and business-rule validation': {
            'zh': 'UAT 支持与业务规则验证',
            'fr': 'support UAT et validation des règles d’affaires',
        },
        'documentation and cross-team traceability': {
            'zh': '文档协同与跨团队可追踪性',
            'fr': 'documentation et traçabilité inter-équipes',
        },
        'API测试': {'zh': 'API 测试', 'fr': 'tests API'},
        'SQL': {'zh': 'SQL', 'fr': 'SQL'},
        '手工测试': {'zh': '手工测试', 'fr': 'tests manuels'},
        '自动化测试': {'zh': '自动化测试', 'fr': 'automatisation des tests'},
        'Agile/Scrum': {'zh': 'Agile / Scrum', 'fr': 'Agile / Scrum'},
        '缺陷跟踪': {'zh': '缺陷跟踪', 'fr': 'suivi des anomalies'},
    }
    if lang == 'en':
        return points
    translated = []
    for point in points:
        translated.append(mapping.get(point, {}).get(lang, point))
    return translated


def localized_skills(skill_hits: list[str], lang: str) -> str:
    if not skill_hits:
        return {'zh': '待补充', 'fr': 'à compléter', 'en': 'TBD'}[lang]
    return ', '.join(skill_hits)


def first_line(text: str) -> str:
    return text.splitlines()[0].strip() if text.strip() else ''


def render_experience_localized(profile: dict, lang: str) -> str:
    exps = profile.get('work_experience', []) or []
    blocks = []
    for exp in exps:
        period = exp.get('period', '')
        title = exp.get('title', '')
        company = exp.get('company', '')
        details = [d for d in exp.get('details', []) if d][:5]
        header = f'{period} | {title} | {company}'.strip(' |')
        if lang == 'zh':
            prefix = '• '
        elif lang == 'fr':
            prefix = '• '
        else:
            prefix = '- '
        block = header
        if details:
            block += '\n' + bullets(details, prefix)
        blocks.append(block)
    return '\n\n'.join(blocks)


def build_role_summaries(company: str, position: str, summary_text: str, focus_zh: list[str], focus_en: list[str], focus_fr: list[str]) -> tuple[str, str, str]:
    base = first_line(summary_text)
    zh = f'拥有 10+ 年软件测试经验，覆盖功能、集成、回归与数据校验场景。结合既有 API、SQL、缺陷跟踪与自动化实践，可快速支持 {company} 的 {position} 岗位在敏捷团队中的质量保障工作。重点匹配：' + '、'.join(focus_zh[:4]) + '。'
    en = f'QA professional with 10+ years of experience across functional, integration, regression, and data-validation testing. Well aligned with the {position} role at {company} through hands-on API, SQL, defect-management, and progressive automation experience. Focus areas: ' + ', '.join(focus_en[:4]) + '.'
    fr = f'Professionnelle QA avec plus de 10 ans d’expérience en tests fonctionnels, d’intégration, de régression et validation de données. Le profil correspond bien au poste de {position} chez {company} grâce à l’expérience concrète en API, SQL, gestion des anomalies et automatisation progressive. Priorités : ' + ', '.join(focus_fr[:4]) + '.'
    if base:
        zh += f' 原始简历摘要：{base}'
        en += f' Base resume summary: {base}'
        fr += f' Résumé source : {base}'
    return zh, en, fr


def build_interview_questions(company: str, lang: str) -> list[str]:
    questions = {
        'zh': [
            f'为什么你适合 {company} 这个 API / 集成导向的 QA 岗位？',
            '你如何设计 API、集成、回归三层测试策略？',
            '你如何用 SQL 做数据校验并定位缺陷根因？',
            '你如何支持 UAT，并与 BA / Dev / DevOps 协作推进发布？',
            '你会如何逐步推进自动化，而不是一开始就过度设计？',
        ],
        'en': [
            f'Why are you a strong fit for this API and integration-oriented QA role at {company}?',
            'How would you structure API, integration, and regression testing for this team?',
            'How do you use SQL to validate data and isolate defects?',
            'How do you support UAT while coordinating with BA, developers, and DevOps?',
            'How would you introduce automation progressively without over-engineering?',
        ],
        'fr': [
            f'Pourquoi êtes-vous un bon match pour ce poste QA orienté API et intégration chez {company} ?',
            'Comment structureriez-vous une stratégie de tests API, intégration et régression ?',
            'Comment utilisez-vous SQL pour valider les données et isoler les anomalies ?',
            'Comment soutenez-vous le UAT avec les BA, développeurs et DevOps ?',
            'Comment feriez-vous progresser l’automatisation sans surconcevoir la solution ?',
        ],
    }
    return questions[lang]


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
    host = os.environ.get('EMAIL_SMTP_HOST', 'smtp.qq.com')
    port = int(os.environ.get('EMAIL_SMTP_PORT', '465'))
    user = os.environ.get('EMAIL_SMTP_USER') or os.environ.get('EMAIL_ADDRESS')
    password = os.environ.get('EMAIL_SMTP_PASSWORD') or os.environ.get('EMAIL_PASSWORD')
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

    skill_hits = details.get('skill_hits', []) or compact_skills(real)
    summary_text = real.get('summary', '') or san.get('summary', '') or '待补充职业概述'
    languages = ', '.join(real.get('languages', []) or san.get('languages', []) or ['French'])
    focus_points_en = job_focus_points(job_text, details)
    focus_points_zh = translate_focus_points(focus_points_en, 'zh')
    focus_points_fr = translate_focus_points(focus_points_en, 'fr')
    focus_zh = bullets(focus_points_zh, '• ') or '• 岗位核心职责'
    focus_en = bullets(focus_points_en, '- ') or '- Core job responsibilities'
    focus_fr = bullets(focus_points_fr, '• ') or '• Responsabilités clés'
    zh_exp = render_experience_localized(real, 'zh')
    en_exp = render_experience_localized(real, 'en')
    fr_exp = render_experience_localized(real, 'fr')
    zh_summary, en_summary, fr_summary = build_role_summaries(args.company, args.position, summary_text, focus_points_zh, focus_points_en, focus_points_fr)

    zh_resume = f"姓名：{real.get('name','')}\n邮箱：{real.get('email','')}\n电话：{real.get('phone','')}\n地址：{real.get('address','')}\n目标岗位：{args.position}\n\n职业概述：\n{zh_summary}\n\n核心技能：\n{localized_skills(skill_hits, 'zh')}\n\n语言：{languages}\n\n精选工作经历：\n{zh_exp or '待补充'}\n\n岗位匹配重点：\n{focus_zh}\n\n投递提醒：\n• CGI 该岗位技能匹配度高。\n• 办公地点与 onsite 频率仍需向 recruiter 确认，避免不满足西岛通勤偏好。"
    en_resume = f"Name: {real.get('name','')}\nEmail: {real.get('email','')}\nPhone: {real.get('phone','')}\nAddress: {real.get('address','')}\nTarget Role: {args.position}\n\nProfessional Summary:\n{en_summary}\n\nCore Skills:\n{localized_skills(skill_hits, 'en')}\n\nLanguages: {languages}\n\nSelected Experience:\n{en_exp or 'TBD'}\n\nRole Alignment:\n{focus_en}\n\nApplication Notes:\n- Strong technical alignment with the CGI QA role.\n- Exact office location and onsite cadence should still be confirmed with the recruiter."
    fr_resume = f"Nom : {real.get('name','')}\nEmail : {real.get('email','')}\nTéléphone : {real.get('phone','')}\nAdresse : {real.get('address','')}\nPoste ciblé : {args.position}\n\nProfil professionnel :\n{fr_summary}\n\nCompétences clés :\n{localized_skills(skill_hits, 'fr')}\n\nLangues : {languages}\n\nExpériences sélectionnées :\n{fr_exp or 'à compléter'}\n\nPoints d'adéquation avec le poste :\n{focus_fr}\n\nPoints de vigilance :\n• Bonne adéquation technique avec le poste CGI.\n• Il reste à confirmer le lieu exact de rattachement et la fréquence de présence au bureau."

    interview_zh = f"面试建议\n匹配度评分：{score}\n\n优先准备主题：\n{focus_zh}\n\n可展开案例：\n{bullets(skill_hits[:6], '• ')}\n\n高概率问题：\n{bullets(build_interview_questions(args.company, 'zh'), '• ')}\n\n建议回答方向：\n• 为什么适合{args.company}：强调 API、SQL、回归/集成测试、缺陷跟踪与 Agile 协作经验。\n• 如何支撑 UAT / 缺陷闭环：结合测试环境维护、日志分析、数据校验与 Jira 跟踪经历。\n• 如何逐步推进自动化：结合 Selenium、CI/CD、回归测试经验说明分阶段落地方案。\n• 通勤/办公方式问题：主动询问 office location 与 hybrid 频率，避免后续 mismatch。\n\n建议举例经历：\n{zh_exp or '待补充具体项目案例'}"
    interview_en = f"Interview Tips\nMatch score: {score}\n\nPriority focus areas:\n{focus_en}\n\nExamples to prepare:\n{bullets(skill_hits[:6], '- ')}\n\nLikely questions:\n{bullets(build_interview_questions(args.company, 'en'), '- ')}\n\nSuggested answer angles:\n- Why {args.company}: emphasize API, SQL, regression/integration testing, defect lifecycle ownership, and Agile collaboration.\n- UAT and defect lifecycle support: use examples from environment setup, defect tracking, log analysis, and data validation.\n- Progressive test automation: connect Selenium and CI/CD experience to practical rollout steps.\n- Work model discussion: clarify office location and hybrid cadence early in the process.\n\nExperience examples:\n{en_exp or 'Prepare concrete project stories.'}"
    interview_fr = f"Conseils d'entretien\nScore de compatibilité : {score}\n\nAxes prioritaires :\n{focus_fr}\n\nExemples à préparer :\n{bullets(skill_hits[:6], '• ')}\n\nQuestions probables :\n{bullets(build_interview_questions(args.company, 'fr'), '• ')}\n\nAngles de réponse conseillés :\n• Pourquoi {args.company} : mettre en avant l'expérience API, SQL, tests de régression/intégration, gestion des anomalies et collaboration Agile.\n• Support UAT et cycle de vie des anomalies : s'appuyer sur l'expérience en environnements de test, analyse de logs et validation de données.\n• Automatisation progressive : relier Selenium et CI/CD à un plan de montée en maturité réaliste.\n• Modalité de travail : confirmer tôt le lieu exact et la fréquence hybride.\n\nExpériences à citer :\n{fr_exp or 'Préparer des exemples de projets concrets.'}"

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

#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

FAKE = {
    'name': 'Alex Martin',
    'phone': '+33 6 00 00 00 00',
    'email': 'alex.martin@example.com',
    'address': '10 Rue Exemple, Paris 75000, France',
    'birth_date': '1990-01-01',
    'id_number': 'ID-EXAMPLE-0001',
}

SKILL_PATTERNS = [
    'Jira', 'Selenium', 'Git', 'SVN', 'Jenkins', 'Java', 'JavaScript', 'HTML', 'XML',
    'JSP', 'ASP.NET', 'ASP', 'PowerShell', 'SQL Server', 'Oracle', 'Access', 'SQL',
    'Windows Server', 'Active Directory', 'Agile', 'Scrum', 'CI/CD', 'HP ALM',
    'API', 'HTTP', 'BIOS', 'HDD', 'SSD', 'RAM', 'Virtualization', 'Tests manuels',
    'Tests automatisés', 'Tests fonctionnels', 'Tests de régression', 'Tests d’intégration',
    'Tests d\'intégration', 'Burn-In tests'
]

SECTION_ALIASES = {
    'summary': ['profil professionnel', 'professional summary', 'profile', 'summary'],
    'skills': ['compétences techniques', 'skills', 'technical skills', 'outils et technologies'],
    'experience': ['expériences', 'experience', 'work experience', 'professional experience'],
    'education': ['formation', 'education', 'études', 'academic background'],
    'certifications': ['certifications', 'certification'],
    'languages': ['langues', 'languages'],
}



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


def extract_docx_text(path: Path) -> str:
    with ZipFile(path) as zf:
        xml = zf.read('word/document.xml').decode('utf-8', errors='ignore')
    text = re.sub(r'</w:p>', '\n', xml)
    text = re.sub(r'<[^>]+>', '', text)
    replacements = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&apos;': "'",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).read_text(encoding='utf-8')
    if args.input_file:
        p = Path(args.input_file)
        suffix = p.suffix.lower()
        if suffix in {'.txt', '.md'}:
            return p.read_text(encoding='utf-8')
        if suffix == '.docx':
            return extract_docx_text(p)
    raise SystemExit('Provide --text, --text-file, or a supported --input-file (.txt/.md/.docx)')


def normalize_line(line: str) -> str:
    return re.sub(r'\s+', ' ', line.strip())


def looks_like_heading(line: str) -> bool:
    lowered = normalize_line(line).lower().rstrip(':')
    return any(lowered == alias for aliases in SECTION_ALIASES.values() for alias in aliases)


def detect_section(line: str) -> str | None:
    lowered = normalize_line(line).lower().rstrip(':')
    for name, aliases in SECTION_ALIASES.items():
        if lowered in aliases:
            return name
    return None


def pick_name(lines: list[str]) -> str:
    for line in lines[:12]:
        s = normalize_line(line)
        if not s or len(s) > 60 or any(ch.isdigit() for ch in s):
            continue
        if '@' in s or ':' in s or '•' in s or '|' in s:
            continue
        if looks_like_heading(s):
            continue
        if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', s):
            return s
        words = s.split()
        if not (2 <= len(words) <= 4):
            continue
        if all(re.fullmatch(r"[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’.-]+", w) for w in words):
            return s
    return ''


def pick_phone(raw: str) -> str:
    candidates = re.findall(r'(\+?\d[\d\s\-()]{7,}\d)', raw)
    for candidate in candidates:
        digits = re.sub(r'\D', '', candidate)
        if len(digits) < 8:
            continue
        if re.fullmatch(r'(19|20)\d{2}(19|20)?\d{2}', digits):
            continue
        if '-' in candidate and ' ' not in candidate and len(digits) <= 8:
            continue
        return candidate.strip()
    return ''


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {'header': []}
    current = 'header'
    for raw_line in lines:
        line = normalize_line(raw_line)
        if not line:
            continue
        section = detect_section(line)
        if section:
            current = section
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def extract_skills(raw: str, skill_lines: list[str], experience_lines: list[str]) -> list[str]:
    corpus = '\n'.join(skill_lines + experience_lines + [raw])
    hits = []
    for pattern in SKILL_PATTERNS:
        if re.search(rf'(?i)(?<!\w){re.escape(pattern)}(?!\w)', corpus):
            hits.append(pattern)
    return sorted(dict.fromkeys(hits), key=str.lower)


def merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        line = normalize_line(line)
        if not line:
            continue
        if not merged:
            merged.append(line)
            continue
        prev = merged[-1]
        starts_new_item = (
            line.startswith('•')
            or looks_like_heading(line)
            or re.fullmatch(r'(?:19|20)\d{2}(?:\s*[-–]\s*(?:19|20)\d{2}|\s*[-–]\s*présent)?', line, flags=re.I)
            or prev.endswith(('.', ':', ';', '!', '?'))
        )
        if starts_new_item:
            merged.append(line)
        else:
            merged[-1] = prev + ' ' + line
    return merged


def parse_experience(lines: list[str]) -> list[dict]:
    lines = [normalize_line(x) for x in lines if normalize_line(x)]
    entries = []
    i = 0
    year_re = r'(?:19|20)\d{2}(?:\s*[-–]\s*(?:19|20)\d{2}|\s*[-–]\s*présent)?'
    while i < len(lines):
        line = lines[i]
        if re.fullmatch(year_re, line, flags=re.I):
            period = line
            title = lines[i + 1] if i + 1 < len(lines) else ''
            company = lines[i + 2] if i + 2 < len(lines) else ''
            bullets: list[str] = []
            current = ''
            j = i + 3
            while j < len(lines):
                nxt = lines[j]
                if re.fullmatch(year_re, nxt, flags=re.I):
                    break
                if nxt.lower().startswith(('responsabilités', 'responsibilities')):
                    j += 1
                    continue
                if nxt.startswith('•'):
                    if current:
                        bullets.append(current.strip())
                    current = nxt.lstrip('•').strip()
                else:
                    if current:
                        current = current + ' ' + nxt.strip()
                    else:
                        current = nxt.strip()
                j += 1
            if current:
                bullets.append(current.strip())
            entries.append({
                'period': period,
                'title': title,
                'company': company,
                'details': bullets,
            })
            i = j
            continue
        i += 1
    return entries


def detect_language(raw: str) -> str:
    lower = raw.lower()
    french_markers = ['profil professionnel', 'compétences', 'expériences', 'responsabilités', 'tests logiciels']
    english_markers = ['professional summary', 'experience', 'responsibilities', 'skills']
    french_score = sum(marker in lower for marker in french_markers) + len(re.findall(r'[éèàùçêâîôûëïü]', raw.lower()))
    english_score = sum(marker in lower for marker in english_markers)
    if french_score > english_score:
        return 'fr'
    if english_score > french_score:
        return 'en'
    return ''


def extract_languages(raw: str, detected_language: str = '') -> list[str]:
    found = []
    for lang in ['French', 'Français', 'English', 'Anglais', '中文', 'Chinese']:
        if re.search(rf'(?i)(?<!\w){re.escape(lang)}(?!\w)', raw):
            found.append(lang)
    if detected_language == 'fr' and not any(x in found for x in ['French', 'Français']):
        found.append('French')
    if detected_language == 'en' and not any(x in found for x in ['English', 'Anglais']):
        found.append('English')
    return found


def detect(raw: str) -> tuple[dict, dict]:
    lines = [normalize_line(line) for line in raw.splitlines() if normalize_line(line)]
    sections = split_sections(lines)
    summary_lines = sections.get('summary', [])
    skill_lines = sections.get('skills', [])
    experience_lines = sections.get('experience', [])
    education_lines = sections.get('education', [])
    certification_lines = sections.get('certifications', [])
    language_lines = sections.get('languages', [])

    experience_entries = parse_experience(experience_lines)
    skills = extract_skills(raw, skill_lines, experience_lines)
    detected_language = detect_language(raw)
    education_lines = merge_wrapped_lines(education_lines)
    certification_lines = merge_wrapped_lines(certification_lines)
    profile = {
        'name': pick_name(lines),
        'phone': '',
        'email': '',
        'address': '',
        'birth_date': '',
        'id_number': '',
        'detected_language': detected_language,
        'summary': ' '.join(merge_wrapped_lines(summary_lines)).strip(),
        'skills': skills,
        'work_experience': experience_entries,
        'education': education_lines,
        'certifications': certification_lines,
        'languages': sorted(dict.fromkeys(extract_languages('\n'.join(language_lines) + '\n' + raw, detected_language))),
        'experience': '\n'.join(merge_wrapped_lines(experience_lines)).strip() or raw,
        'raw_text': raw,
        'section_text': sections,
    }
    mapping = {}

    email = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', raw)
    if email:
        profile['email'] = email.group(0)
        mapping['email'] = profile['email']
    phone = pick_phone(raw)
    if phone:
        profile['phone'] = phone
        mapping['phone'] = profile['phone']
    bday = re.search(r'(19\d{2}|20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})', raw)
    if bday:
        profile['birth_date'] = bday.group(0)
        mapping['birth_date'] = profile['birth_date']
    id_match = re.search(r'([A-Z]{1,2}\d{6,}|\d{17}[\dXx])', raw)
    if id_match:
        profile['id_number'] = id_match.group(0)
        mapping['id_number'] = profile['id_number']

    for line in lines[:12]:
        lowered = line.lower()
        if any(k in lowered for k in ['street', 'road', 'avenue', 'paris', 'adresse', 'address', '地址', 'rue']) and len(line) > 8:
            profile['address'] = line
            mapping['address'] = line
            break

    if profile['name']:
        mapping['name'] = profile['name']

    return profile, mapping


def sanitize_text(raw: str, mapping: dict) -> str:
    sanitized = raw
    for key, real in mapping.items():
        if real:
            sanitized = sanitized.replace(real, FAKE[key])
    return sanitized


def sanitize_profile(profile: dict, mapping: dict) -> dict:
    sanitized = json.loads(json.dumps(profile, ensure_ascii=False))
    for key, fake_value in FAKE.items():
        if sanitized.get(key):
            sanitized[key] = fake_value
    sanitized['raw_text'] = sanitize_text(profile.get('raw_text', ''), mapping)
    sanitized['experience'] = sanitize_text(profile.get('experience', ''), mapping)
    if sanitized.get('summary'):
        sanitized['summary'] = sanitize_text(sanitized['summary'], mapping)
    for entry in sanitized.get('work_experience', []):
        entry['title'] = sanitize_text(entry.get('title', ''), mapping)
        entry['company'] = sanitize_text(entry.get('company', ''), mapping)
        entry['details'] = [sanitize_text(item, mapping) for item in entry.get('details', [])]
    sanitized['education'] = [sanitize_text(item, mapping) for item in sanitized.get('education', [])]
    sanitized['certifications'] = [sanitize_text(item, mapping) for item in sanitized.get('certifications', [])]
    sanitized['section_text'] = {k: [sanitize_text(item, mapping) for item in v] for k, v in sanitized.get('section_text', {}).items()}
    return sanitized


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input-file')
    ap.add_argument('--text')
    ap.add_argument('--text-file')
    args = ap.parse_args()

    raw = load_text(args)
    root = get_resume_root()
    hist = root / 'hA829istory'
    js = root / 'json'
    hist.mkdir(parents=True, exist_ok=True)
    js.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d_%H%M%S')

    src = Path(args.input_file) if args.input_file else None
    original_name = src.name if src else 'resume.txt'
    history_name = f"{stamp}_{original_name}"
    history_file = hist / history_name
    if src and src.exists():
        shutil.copy2(src, history_file)
    else:
        history_file.write_text(raw, encoding='utf-8')

    real_profile, mapping = detect(raw)
    sanitized_profile = sanitize_profile(real_profile, mapping)

    real_json = js / f'{stamp}_real_profile.json'
    sanitized_json = js / f'{stamp}_sanitized_profile.json'
    mapping_json = js / f'{stamp}_mapping.json'
    latest_real = js / 'latest_real_profile.json'
    latest_san = js / 'latest_sanitized_profile.json'
    latest_map = js / 'latest_mapping.json'
    summary_json = js / f'{stamp}_resume_summary.json'

    summary_payload = {
        'history_file': str(history_file),
        'detected_fields': sorted([k for k, v in mapping.items() if v]),
        'skills': real_profile.get('skills', []),
        'work_experience_count': len(real_profile.get('work_experience', [])),
        'education_count': len(real_profile.get('education', [])),
        'created_at': now.isoformat(timespec='seconds'),
    }

    for path, payload in [
        (real_json, real_profile), (sanitized_json, sanitized_profile), (mapping_json, mapping),
        (latest_real, real_profile), (latest_san, sanitized_profile), (latest_map, mapping),
        (summary_json, summary_payload)
    ]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'resume_root': str(root),
        'history_file': str(history_file),
        'real_json': str(real_json),
        'sanitized_json': str(sanitized_json),
        'mapping_json': str(mapping_json),
        'detected_fields': sorted([k for k, v in mapping.items() if v]),
        'summary': {
            'original_name': original_name,
            'skills': real_profile.get('skills', []),
            'work_experience_count': len(real_profile.get('work_experience', [])),
            'education_count': len(real_profile.get('education', [])),
            'sanitized_name': sanitized_profile.get('name', ''),
        }
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

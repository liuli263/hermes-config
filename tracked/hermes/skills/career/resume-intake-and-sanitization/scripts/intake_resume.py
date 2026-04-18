#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

FAKE = {
    'name': 'Alex Martin',
    'phone': '+33 6 00 00 00 00',
    'email': 'alex.martin@example.com',
    'address': '10 Rue Exemple, Paris 75000, France',
    'birth_date': '1990-01-01',
    'id_number': 'ID-EXAMPLE-0001',
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


def load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).read_text(encoding='utf-8')
    if args.input_file:
        p = Path(args.input_file)
        if p.suffix.lower() in {'.txt', '.md'}:
            return p.read_text(encoding='utf-8')
    raise SystemExit('Provide --text, --text-file, or a text-like --input-file')


def looks_like_heading(line: str) -> bool:
    lowered = line.strip().lower()
    bad_prefixes = [
        'profil', 'profile', 'summary', 'professional summary', 'compétences', 'skills',
        'expériences', 'experience', 'responsabilités', 'responsibilities', 'education',
    ]
    return any(lowered.startswith(prefix) for prefix in bad_prefixes)


def pick_name(lines: list[str]) -> str:
    for line in lines[:12]:
        s = line.strip()
        if not s or len(s) > 60 or any(ch.isdigit() for ch in s):
            continue
        if '@' in s or ':' in s or '•' in s:
            continue
        if looks_like_heading(s):
            continue
        if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', s):
            return s
        words = s.split()
        if not (2 <= len(words) <= 4):
            continue
        if all(re.fullmatch(r"[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+", w) for w in words):
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


def detect(raw: str) -> tuple[dict, dict]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    profile = {
        'name': pick_name(lines),
        'phone': '',
        'email': '',
        'address': '',
        'birth_date': '',
        'id_number': '',
        'skills': [],
        'experience': raw,
        'raw_text': raw,
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

    for line in lines[1:8]:
        if any(k in line.lower() for k in ['street', 'road', 'avenue', 'paris', '地址', 'rue']) and len(line) > 8:
            profile['address'] = line
            mapping['address'] = line
            break

    if profile['name']:
        mapping['name'] = profile['name']

    skill_hits = re.findall(r'\b(Python|SQL|Excel|Tableau|Power BI|Product|AI|ML|NLP|Docker|Kubernetes|French|English)\b', raw, flags=re.I)
    profile['skills'] = sorted({s for s in skill_hits})
    return profile, mapping


def sanitize_text(raw: str, mapping: dict) -> str:
    sanitized = raw
    for key, real in mapping.items():
        if real:
            sanitized = sanitized.replace(real, FAKE[key])
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
    sanitized_raw = sanitize_text(raw, mapping)
    sanitized_profile = dict(real_profile)
    for key, fake_value in FAKE.items():
        if sanitized_profile.get(key):
            sanitized_profile[key] = fake_value
    sanitized_profile['raw_text'] = sanitized_raw
    sanitized_profile['experience'] = sanitized_raw

    real_json = js / f'{stamp}_real_profile.json'
    sanitized_json = js / f'{stamp}_sanitized_profile.json'
    mapping_json = js / f'{stamp}_mapping.json'
    latest_real = js / 'latest_real_profile.json'
    latest_san = js / 'latest_sanitized_profile.json'
    latest_map = js / 'latest_mapping.json'
    summary_json = js / f'{stamp}_resume_summary.json'

    for path, payload in [
        (real_json, real_profile), (sanitized_json, sanitized_profile), (mapping_json, mapping),
        (latest_real, real_profile), (latest_san, sanitized_profile), (latest_map, mapping),
        (summary_json, {
            'history_file': str(history_file),
            'detected_fields': sorted([k for k, v in mapping.items() if v]),
            'skills': real_profile.get('skills', []),
            'created_at': now.isoformat(timespec='seconds'),
        })
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
            'sanitized_name': sanitized_profile.get('name', ''),
        }
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

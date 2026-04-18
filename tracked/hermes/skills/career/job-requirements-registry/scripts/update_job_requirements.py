#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


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
        return args.text.strip()
    if args.text_file:
        return Path(args.text_file).read_text(encoding='utf-8').strip()
    return ''


def split_items(value: str) -> list[str]:
    parts = re.split(r'[\n;,，；]+', value)
    return [p.strip(' -•\t') for p in parts if p.strip(' -•\t')]


def extract_fields(raw_text: str) -> dict:
    fields = {
        'target_roles': [],
        'industries': [],
        'locations': [],
        'salary_range': '',
        'languages': [],
        'must_have': [],
        'deal_breakers': [],
        'preferences': [],
        'raw_text': raw_text,
    }
    label_map = {
        '目标岗位': 'target_roles', '岗位': 'target_roles', '职能方向': 'target_roles',
        '行业偏好': 'industries', '行业': 'industries',
        '城市': 'locations', '地点': 'locations', '国家': 'locations', '地区': 'locations',
        '薪资': 'salary_range', '薪资范围': 'salary_range',
        '语言': 'languages', '语言要求': 'languages',
        '必须条件': 'must_have', '必须满足': 'must_have',
        '不能接受': 'deal_breakers', '排除项': 'deal_breakers',
        '偏好': 'preferences', '其他偏好': 'preferences',
    }
    for line in raw_text.splitlines():
        if '：' in line:
            key, value = line.split('：', 1)
        elif ':' in line:
            key, value = line.split(':', 1)
        else:
            continue
        key = key.strip()
        value = value.strip()
        mapped = label_map.get(key)
        if not mapped or not value:
            continue
        if mapped == 'salary_range':
            fields[mapped] = value
        else:
            fields[mapped].extend(split_items(value))
    return fields


def make_markdown(data: dict, source: str, now: datetime) -> str:
    def bullets(items: list[str]) -> str:
        return '\n'.join(f'- {x}' for x in items) if items else '- 未填写'

    return f'''# 求职要求汇总\n\n- 更新时间：{now.isoformat(timespec="seconds")}\n- 来源：{source}\n\n## 目标岗位\n{bullets(data.get('target_roles', []))}\n\n## 行业偏好\n{bullets(data.get('industries', []))}\n\n## 地点 / 国家\n{bullets(data.get('locations', []))}\n\n## 薪资范围\n- {data.get('salary_range') or '未填写'}\n\n## 语言要求\n{bullets(data.get('languages', []))}\n\n## 必须条件\n{bullets(data.get('must_have', []))}\n\n## 不能接受\n{bullets(data.get('deal_breakers', []))}\n\n## 其他偏好\n{bullets(data.get('preferences', []))}\n\n## 原始描述\n```text\n{data.get('raw_text', '').strip()}\n```\n'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--text')
    ap.add_argument('--text-file')
    ap.add_argument('--source', default='unknown')
    args = ap.parse_args()

    raw_text = load_text(args)
    if not raw_text:
        raise SystemExit('Provide --text or --text-file')

    root = get_resume_root()
    req_dir = root / 'request'
    req_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d_%H%M%S')
    data = extract_fields(raw_text)
    data.update({'updated_at': now.isoformat(timespec='seconds'), 'source': args.source})
    md = make_markdown(data, args.source, now)

    snapshot_md = req_dir / f'{stamp}_requirements.md'
    snapshot_json = req_dir / f'{stamp}_requirements.json'
    current_md = req_dir / 'current_requirements.md'
    current_json = req_dir / 'current_requirements.json'

    snapshot_md.write_text(md, encoding='utf-8')
    snapshot_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    current_md.write_text(md, encoding='utf-8')
    current_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    summary = {
        'target_roles': data['target_roles'],
        'locations': data['locations'],
        'must_have_count': len(data['must_have']),
        'deal_breakers_count': len(data['deal_breakers']),
    }
    print(json.dumps({
        'resume_root': str(root),
        'snapshot_markdown': str(snapshot_md),
        'snapshot_json': str(snapshot_json),
        'current_markdown': str(current_md),
        'current_json': str(current_json),
        'summary': summary,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path('/home/liuli/.hermes')
DEST_ROOT = REPO_ROOT / 'tracked' / 'hermes'

COPY_FILES = [
    'SOUL.md',
    'memories/USER.md',
    'memories/MEMORY.md',
]
COPY_DIRS = [
    'skills',
]
SECRET_PATTERNS = [
    re.compile(r'^(\s*)(api_key|token|secret|password|authorization_code)(\s*:\s*)([^#\n]+)(.*)$', re.IGNORECASE),
]
INLINE_SECRET_RE = re.compile(r'(https?://[^\s]+:[^\s@]+@)')


def redact_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        replaced = line
        for pattern in SECRET_PATTERNS:
            match = pattern.match(replaced)
            if match:
                replaced = f"{match.group(1)}{match.group(2)}{match.group(3)}REDACTED{match.group(5)}"
                break
        replaced = INLINE_SECRET_RE.sub('https://REDACTED@', replaced)
        lines.append(replaced)
    return '\n'.join(lines) + ('\n' if text.endswith('\n') else '')


def reset_dest() -> None:
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)


def copy_file(rel_path: str) -> None:
    src = SOURCE_ROOT / rel_path
    dst = DEST_ROOT / rel_path
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding='utf-8', errors='ignore'), encoding='utf-8')


def copy_dir(rel_path: str) -> None:
    src = SOURCE_ROOT / rel_path
    dst = DEST_ROOT / rel_path
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def write_redacted_config() -> None:
    src = SOURCE_ROOT / 'config.yaml'
    if not src.exists():
        return
    dst = DEST_ROOT / 'config.yaml'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(redact_text(src.read_text(encoding='utf-8', errors='ignore')), encoding='utf-8')


def write_manifest() -> None:
    manifest = DEST_ROOT / 'SYNC_MANIFEST.md'
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
    manifest.write_text(
        '\n'.join([
            '# Sync Manifest',
            '',
            f'- Source: `{SOURCE_ROOT}`',
            f'- Generated at: `{generated_at}`',
            '- Config file is stored as a redacted copy.',
            '- Runtime state, logs, sessions, caches, database, locks, and `.env` are intentionally excluded.',
            '',
        ]),
        encoding='utf-8',
    )


def main() -> None:
    reset_dest()
    for rel_path in COPY_FILES:
        copy_file(rel_path)
    for rel_path in COPY_DIRS:
        copy_dir(rel_path)
    write_redacted_config()
    write_manifest()
    print(f'Synced Hermes config snapshot into {DEST_ROOT}')


if __name__ == '__main__':
    main()

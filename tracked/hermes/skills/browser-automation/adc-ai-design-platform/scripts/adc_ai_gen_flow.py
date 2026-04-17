#!/usr/bin/env python3
"""ADC AI 生图结果下载辅助脚本。

用途：
1. 将 ADC 页面中已经拿到的结果图 URL 下载到本地
2. 自动根据文件头判断 jpg/png，避免“扩展名是 .png 但真实内容是 JPEG”
3. 输出最终保存路径，供后续 Weixin 原生直发使用

说明：
- 这个脚本不负责登录 ADC，也不直接驱动浏览器；
- 推荐由浏览器自动化先拿到 result image URL，再调用本脚本下载。
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from typing import Tuple

import requests


def sniff_ext(data: bytes, fallback: str = '.bin') -> str:
    if data.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return '.gif'
    if data.startswith(b'RIFF') and b'WEBP' in data[:16]:
        return '.webp'
    return fallback


def download(url: str, out_dir: str, stem: str = 'adc-ai-gen-result') -> Tuple[str, int, str]:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.content
    ext = sniff_ext(data, fallback='.img')
    target_dir = pathlib.Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f'{stem}{ext}'
    target.write_bytes(data)
    return str(target), len(data), resp.headers.get('content-type', '')


def main() -> int:
    parser = argparse.ArgumentParser(description='Download ADC generated image and normalize extension')
    parser.add_argument('url', help='ADC 结果图 URL')
    parser.add_argument('--out-dir', default='/tmp', help='输出目录，默认 /tmp')
    parser.add_argument('--stem', default='adc-ai-gen-result', help='输出文件名前缀')
    args = parser.parse_args()

    path, size, ctype = download(args.url, args.out_dir, args.stem)
    print(path)
    print(size)
    print(ctype)
    return 0


if __name__ == '__main__':
    sys.exit(main())

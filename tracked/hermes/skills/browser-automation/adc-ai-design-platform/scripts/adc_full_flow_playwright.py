#!/usr/bin/env python3
"""ADC 站点完整流程自动化模板（Playwright 版骨架）。

能力范围：
1. 登录 ADC
2. 进入项目空间并点击项目封面图
3. 进入 AI绘图 -> AI生图
4. 点击开始创作并轮询生成状态
5. 提取结果图 URL
6. 下载结果图并按真实文件头修正扩展名

说明：
- 这是“可复用模板/骨架”，便于后续改造成真正独立程序；
- 依赖 Playwright：pip install playwright && playwright install chromium
- 若需要接 Hermes 的 Weixin 原生直发，建议在 Hermes 运行环境内追加 send_weixin_direct 调用。
"""

from __future__ import annotations

import argparse
import pathlib
import time
from typing import Optional

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

LOGIN_URL = 'https://adc.acsbim.com:7002/#/Login'


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


def download_result(url: str, out_dir: str, stem: str = 'adc-ai-gen-result') -> str:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.content
    ext = sniff_ext(data, '.img')
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f'{stem}{ext}'
    target.write_bytes(data)
    return str(target)


def click_project_cover(page, project_name: str) -> None:
    js = """
    (projectName) => {
      const img = [...document.querySelectorAll('img.masonry-img')]
        .find(el => (el.getAttribute('alt') || '').trim() === projectName);
      if (!img) return false;
      ['mouseover','mousedown','mouseup','click'].forEach(type =>
        img.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }))
      );
      return true;
    }
    """
    ok = page.evaluate(js, project_name)
    if not ok:
        raise RuntimeError(f'未找到项目封面图: {project_name}')


def get_result_image_url(page) -> Optional[str]:
    js = """
    () => {
      const byAlt = [...document.querySelectorAll('img')]
        .find(i => (i.alt || '').includes('创作结果'));
      if (byAlt?.src) return byAlt.src;
      const byClass = [...document.querySelectorAll('img.compare-image')].find(i => i.src);
      return byClass?.src || null;
    }
    """
    return page.evaluate(js)


def wait_for_generation(page, timeout_sec: int = 300) -> str:
    start = time.time()
    while time.time() - start < timeout_sec:
        body = page.evaluate("() => document.body.innerText")
        img_url = get_result_image_url(page)
        if '下载图片' in body and img_url:
            return img_url
        page.wait_for_timeout(5000)
    raise TimeoutError('等待 ADC 出图超时')


def main() -> int:
    parser = argparse.ArgumentParser(description='ADC full-flow automation skeleton')
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--project', default='创意产业园')
    parser.add_argument('--out-dir', default='/tmp')
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto(LOGIN_URL, wait_until='networkidle')

        page.get_by_placeholder('输入账号').fill(args.username)
        page.get_by_placeholder('输入密码').fill(args.password)
        page.get_by_role('button', name='登录').click()

        page.wait_for_timeout(3000)
        page.get_by_text('项目空间').click()
        page.wait_for_timeout(3000)

        click_project_cover(page, args.project)
        page.wait_for_timeout(4000)

        page.get_by_text('AI绘图').click()
        page.wait_for_timeout(1000)
        page.get_by_text('AI生图').click()
        page.wait_for_timeout(3000)

        page.get_by_text('开始创作').click()
        img_url = wait_for_generation(page)
        saved = download_result(img_url, args.out_dir)

        print(saved)
        browser.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

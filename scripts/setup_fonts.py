#!/usr/bin/env python3
"""
setup_fonts.py — 一键下载字体到 assets/fonts/

下载后 render_image.py 会自动使用本地字体，无需联网渲染。

用法：
    python scripts/setup_fonts.py

字体来源：
    - Noto Serif SC (Regular/Bold/Black) — Google Fonts CDN
    - Space Mono (Regular/Bold)          — Google Fonts CDN

依赖：
    pip install requests
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("缺少依赖，请先运行：pip install requests")

FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"

# Google Fonts CSS2 API —— 用 Chrome UA 拿 woff2，再解析出文件 URL
FONT_QUERIES = [
    {
        "css_url": "https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&display=swap",
        "family": "Noto Serif SC",
        "weight_names": {"400": "Regular", "700": "Bold", "900": "Black"},
        "prefix": "NotoSerifSC",
    },
    {
        "css_url": "https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700&display=swap",
        "family": "Space Mono",
        "weight_names": {"400": "Regular", "700": "Bold"},
        "prefix": "SpaceMono",
    },
]

# Playwright/Chromium 内置 woff2 支持，本地 file:// 路径也可读
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def parse_font_faces(css_text: str, family: str) -> list[dict]:
    """
    解析 Google Fonts CSS 中的 @font-face 块，
    返回 [{"weight": "400", "url": "...", "format": "woff2"}, ...]
    仅保留 font-style: normal 的条目。
    """
    results = []
    # 匹配完整 @font-face 块
    blocks = re.findall(r"@font-face\s*\{([^}]+)\}", css_text, re.DOTALL)
    for block in blocks:
        style_match = re.search(r"font-style:\s*(\w+)", block)
        if style_match and style_match.group(1) != "normal":
            continue
        weight_match = re.search(r"font-weight:\s*(\d+)", block)
        url_match = re.search(r"src:\s*url\(([^)]+)\)\s+format\('?([^)']+)'?\)", block)
        if weight_match and url_match:
            results.append(
                {
                    "weight": weight_match.group(1),
                    "url": url_match.group(1).strip(),
                    "format": url_match.group(2).strip(),
                }
            )
    return results


def download_file(session: requests.Session, url: str, dest: Path) -> bool:
    """下载单个文件，返回是否成功。"""
    try:
        resp = session.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        size_kb = len(resp.content) // 1024
        print(f"  ✓  {dest.name}  ({size_kb} KB)")
        return True
    except Exception as exc:
        print(f"  ✗  下载失败：{url}\n     原因：{exc}")
        return False


def main() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    total_ok = 0
    total_skip = 0
    total_fail = 0

    for font in FONT_QUERIES:
        print(f"\n── {font['family']} ──")
        try:
            css_resp = session.get(font["css_url"], headers=HEADERS, timeout=15)
            css_resp.raise_for_status()
        except Exception as exc:
            print(f"  ✗  获取字体列表失败：{exc}")
            continue

        faces = parse_font_faces(css_resp.text, font["family"])

        # 对 CJK 字体，Google 会按 unicode-range 拆成多个子集文件
        # 按 weight 分组，每个 weight 可能有多个子集
        weight_files: dict[str, list[dict]] = {}
        for face in faces:
            weight_files.setdefault(face["weight"], []).append(face)

        for weight, subsets in sorted(weight_files.items()):
            wname = font["weight_names"].get(weight, f"W{weight}")
            ext = subsets[0]["format"].replace("woff2", "woff2").replace("truetype", "ttf")
            if ext not in ("woff2", "ttf", "otf"):
                ext = "woff2"

            if len(subsets) == 1:
                # 单文件字体（如 Space Mono）
                fname = f"{font['prefix']}-{wname}.{ext}"
                dest = FONT_DIR / fname
                if dest.exists():
                    print(f"  –  {fname}（已存在，跳过）")
                    total_skip += 1
                else:
                    ok = download_file(session, subsets[0]["url"], dest)
                    total_ok += ok
                    total_fail += not ok
            else:
                # 多子集字体（如 Noto Serif SC）：下载所有子集
                for i, subset in enumerate(subsets, 1):
                    fname = f"{font['prefix']}-{wname}-subset{i:03d}.{ext}"
                    dest = FONT_DIR / fname
                    if dest.exists():
                        total_skip += 1
                        continue
                    ok = download_file(session, subset["url"], dest)
                    total_ok += ok
                    total_fail += not ok

    print(
        f"\n完成：下载 {total_ok} 个，跳过 {total_skip} 个（已存在），失败 {total_fail} 个"
    )
    print(f"字体目录：{FONT_DIR.resolve()}")

    if total_fail == 0:
        print("\n✓  下次运行 render_image.py 将自动使用本地字体，无需联网。")
    else:
        print("\n⚠  部分字体下载失败，render_image.py 将回退到 CDN 或系统字体。")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate EPUB cover from HTML template with intelligent theme detection.
Uses Playwright to render HTML and take screenshot.

Adapted from qiaomu-epub-book-generator (MIT License).
Changes: replaced hardcoded /tmp/ paths with tempfile.gettempdir() for Windows compatibility.
"""

import sys
import os
import tempfile
from pathlib import Path

THEMES = {
    "tech": {
        "keywords": ["技术", "编程", "代码", "开发", "AI", "Claude", "Agent", "LLM", "算法", "架构", "前端", "后端", "数据", "机器学习"],
        "gradient": "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
        "accent": "#00d4ff",
        "pattern": "circuit"
    },
    "business": {
        "keywords": ["创业", "商业", "管理", "营销", "增长", "产品", "运营", "战略", "投资", "融资"],
        "gradient": "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        "accent": "#f39c12",
        "pattern": "grid"
    },
    "design": {
        "keywords": ["设计", "美学", "艺术", "视觉", "UI", "UX", "品牌", "创意", "排版"],
        "gradient": "linear-gradient(135deg, #2d1b69 0%, #5b247a 50%, #8b3a8b 100%)",
        "accent": "#ff6b9d",
        "pattern": "dots"
    },
    "literature": {
        "keywords": ["文学", "小说", "诗歌", "散文", "故事", "传记", "历史", "哲学", "思想"],
        "gradient": "linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e8ba3 100%)",
        "accent": "#ffd89b",
        "pattern": "lines"
    },
    "science": {
        "keywords": ["科学", "物理", "化学", "生物", "数学", "研究", "实验", "理论", "发现"],
        "gradient": "linear-gradient(135deg, #134e5e 0%, #71b280 100%)",
        "accent": "#a8e6cf",
        "pattern": "hexagon"
    },
    "personal": {
        "keywords": ["成长", "学习", "方法", "思考", "笔记", "总结", "反思", "日记", "随笔"],
        "gradient": "linear-gradient(135deg, #3a1c71 0%, #d76d77 50%, #ffaf7b 100%)",
        "accent": "#ffeaa7",
        "pattern": "wave"
    }
}


def detect_theme(title, subtitle="", author=""):
    text = f"{title} {subtitle} {author}".lower()
    scores = {}
    for theme_name, theme_data in THEMES.items():
        score = sum(1 for keyword in theme_data["keywords"] if keyword.lower() in text)
        scores[theme_name] = score
    best_theme = max(scores, key=scores.get)
    return best_theme if scores[best_theme] > 0 else "tech"


def get_pattern_svg(pattern_type, accent_color):
    patterns = {
        "circuit": f'''
            <svg width="100%" height="100%" style="position:absolute;top:0;left:0;opacity:0.08;">
                <defs>
                    <pattern id="circuit" x="0" y="0" width="100" height="100" patternUnits="userSpaceOnUse">
                        <circle cx="10" cy="10" r="2" fill="{accent_color}"/>
                        <line x1="10" y1="10" x2="50" y2="10" stroke="{accent_color}" stroke-width="1"/>
                        <line x1="50" y1="10" x2="50" y2="50" stroke="{accent_color}" stroke-width="1"/>
                        <circle cx="50" cy="50" r="2" fill="{accent_color}"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#circuit)"/>
            </svg>''',
        "grid": f'''
            <svg width="100%" height="100%" style="position:absolute;top:0;left:0;opacity:0.05;">
                <defs>
                    <pattern id="grid" x="0" y="0" width="50" height="50" patternUnits="userSpaceOnUse">
                        <path d="M 50 0 L 0 0 0 50" fill="none" stroke="{accent_color}" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)"/>
            </svg>''',
        "dots": f'''
            <svg width="100%" height="100%" style="position:absolute;top:0;left:0;opacity:0.1;">
                <defs>
                    <pattern id="dots" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
                        <circle cx="20" cy="20" r="3" fill="{accent_color}"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#dots)"/>
            </svg>''',
        "lines": f'''
            <svg width="100%" height="100%" style="position:absolute;top:0;left:0;opacity:0.06;">
                <defs>
                    <pattern id="lines" x="0" y="0" width="10" height="10" patternUnits="userSpaceOnUse">
                        <line x1="0" y1="0" x2="0" y2="10" stroke="{accent_color}" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#lines)"/>
            </svg>''',
        "hexagon": f'''
            <svg width="100%" height="100%" style="position:absolute;top:0;left:0;opacity:0.08;">
                <defs>
                    <pattern id="hexagon" x="0" y="0" width="56" height="100" patternUnits="userSpaceOnUse">
                        <path d="M28 0 L56 25 L56 75 L28 100 L0 75 L0 25 Z" fill="none" stroke="{accent_color}" stroke-width="1"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#hexagon)"/>
            </svg>''',
        "wave": f'''
            <svg width="100%" height="100%" style="position:absolute;top:0;left:0;opacity:0.07;">
                <defs>
                    <pattern id="wave" x="0" y="0" width="100" height="50" patternUnits="userSpaceOnUse">
                        <path d="M0 25 Q25 0, 50 25 T100 25" fill="none" stroke="{accent_color}" stroke-width="2"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#wave)"/>
            </svg>'''
    }
    return patterns.get(pattern_type, patterns["circuit"])


def generate_cover_html(title, subtitle="", author="", output_path=None, theme=None):
    """Generate HTML cover page. Returns output path."""
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), "epub_cover.html")

    if theme is None:
        theme = detect_theme(title, subtitle, author)

    theme_data = THEMES.get(theme, THEMES["tech"])
    gradient = theme_data["gradient"]
    accent = theme_data["accent"]
    pattern = get_pattern_svg(theme_data["pattern"], accent)

    print(f"  Cover theme: {theme}")

    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1600, initial-scale=1.0">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: 1600px; height: 2560px;
    background: {gradient};
    font-family: 'Noto Serif SC', serif;
    position: relative; overflow: hidden;
}}
.pattern {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }}
.accent-block {{ position: absolute; top: 15%; left: 0; width: 30%; height: 5%; background: {accent}; opacity: 0.9; z-index: 1; }}
.accent-circle {{ position: absolute; bottom: 20%; right: 10%; width: 200px; height: 200px; border-radius: 50%; background: {accent}; opacity: 0.15; z-index: 1; }}
.title-zone {{ position: absolute; top: 25%; left: 0; right: 0; padding: 0 120px; z-index: 2; }}
.title {{ font-size: 96px; font-weight: 900; color: #ffffff; line-height: 1.2; letter-spacing: 0.02em; text-shadow: 0 4px 30px rgba(0,0,0,0.5); margin-bottom: 60px; }}
.subtitle {{ font-size: 36px; font-weight: 400; color: #e0e0e0; line-height: 1.5; opacity: 0.9; }}
.author-zone {{ position: absolute; bottom: 8%; left: 0; right: 0; text-align: center; z-index: 2; }}
.author {{ font-size: 40px; font-weight: 400; color: {accent}; letter-spacing: 0.15em; text-shadow: 0 0 20px {accent}60; }}
.separator {{ width: 200px; height: 3px; background: linear-gradient(90deg, transparent, {accent}, transparent); margin: 0 auto 40px; box-shadow: 0 0 20px {accent}80; }}
.border {{ position: absolute; top: 2px; left: 2px; right: 2px; bottom: 2px; border: 3px solid #888; opacity: 0.3; z-index: 3; pointer-events: none; }}
</style>
</head>
<body>
<div class="pattern">{pattern}</div>
<div class="accent-block"></div>
<div class="accent-circle"></div>
<div class="title-zone">
    <div class="title">{title}</div>
    {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
</div>
{f'''<div class="author-zone">
    <div class="separator"></div>
    <div class="author">{author}</div>
</div>''' if author else ''}
<div class="border"></div>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path


def screenshot_cover(html_path, output_image=None):
    """Take screenshot of HTML cover using Playwright. Returns output path or None."""
    if output_image is None:
        output_image = os.path.join(tempfile.gettempdir(), "epub_cover.jpg")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  Warning: Playwright not installed, cannot generate HTML cover")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 2560}, device_scale_factor=2)
            page.goto(Path(html_path).resolve().as_uri())
            page.wait_for_timeout(2000)
            page.screenshot(path=output_image, type='jpeg', quality=95)
            browser.close()
        return output_image
    except Exception as e:
        print(f"  Warning: HTML cover screenshot failed: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gen_cover_html.py <title> [subtitle] [author] [output_image] [theme]")
        print(f"Themes: {', '.join(THEMES.keys())}")
        sys.exit(1)

    _title = sys.argv[1]
    _subtitle = sys.argv[2] if len(sys.argv) > 2 else ""
    _author = sys.argv[3] if len(sys.argv) > 3 else ""
    _out = sys.argv[4] if len(sys.argv) > 4 else None
    _theme = sys.argv[5] if len(sys.argv) > 5 else None

    _html = generate_cover_html(_title, _subtitle, _author, theme=_theme)
    _img = screenshot_cover(_html, _out)
    print(f"Cover: {_img}")

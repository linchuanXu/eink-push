#!/usr/bin/env python3
"""
Professional book cover generator using SVG with multiple layout styles.
Follows industry best practices: proper typography hierarchy, visual zones, color theory.

Adapted from qiaomu-epub-book-generator (MIT License).
Changes: replaced hardcoded /tmp/ paths with tempfile.gettempdir() for Windows compatibility.
"""

import sys
import os
import tempfile
from pathlib import Path

THEMES = {
    "tech": {
        "keywords": ["技术", "编程", "代码", "开发", "ai", "claude", "agent", "llm", "算法", "架构", "前端", "后端", "数据", "机器学习"],
        "primary": "#1a1a2e",
        "secondary": "#16213e",
        "accent": "#00d4ff",
        "text": "#ffffff",
        "subtitle_text": "#e0e0e0"
    },
    "business": {
        "keywords": ["创业", "商业", "管理", "营销", "增长", "产品", "运营", "战略", "投资", "融资"],
        "primary": "#0f3460",
        "secondary": "#16213e",
        "accent": "#f39c12",
        "text": "#ffffff",
        "subtitle_text": "#e8e8e8"
    },
    "design": {
        "keywords": ["设计", "美学", "艺术", "视觉", "ui", "ux", "品牌", "创意", "排版"],
        "primary": "#2d1b69",
        "secondary": "#5b247a",
        "accent": "#ff6b9d",
        "text": "#ffffff",
        "subtitle_text": "#f0e6ff"
    },
    "literature": {
        "keywords": ["文学", "小说", "诗歌", "散文", "故事", "传记", "历史", "哲学", "思想"],
        "primary": "#1e3c72",
        "secondary": "#2a5298",
        "accent": "#ffd89b",
        "text": "#ffffff",
        "subtitle_text": "#e8e8e8"
    },
    "science": {
        "keywords": ["科学", "物理", "化学", "生物", "数学", "研究", "实验", "理论", "发现"],
        "primary": "#134e5e",
        "secondary": "#71b280",
        "accent": "#a8e6cf",
        "text": "#ffffff",
        "subtitle_text": "#e8f5e9"
    },
    "personal": {
        "keywords": ["成长", "学习", "方法", "思考", "笔记", "总结", "反思", "日记", "随笔"],
        "primary": "#3a1c71",
        "secondary": "#d76d77",
        "accent": "#ffaf7b",
        "text": "#ffffff",
        "subtitle_text": "#fff3e0"
    }
}

LAYOUTS = {
    "minimal": {
        "title_y": "32%",
        "title_size": "150px",
        "subtitle_y": "52%",
        "subtitle_size": "52px",
        "author_y": "88%",
        "author_size": "60px",
        "visual_element": "geometric_blocks"
    },
    "classic": {
        "title_y": "34%",
        "title_size": "140px",
        "subtitle_y": "54%",
        "subtitle_size": "50px",
        "author_y": "90%",
        "author_size": "56px",
        "visual_element": "horizontal_lines"
    },
    "modern": {
        "title_y": "30%",
        "title_size": "160px",
        "subtitle_y": "52%",
        "subtitle_size": "56px",
        "author_y": "86%",
        "author_size": "64px",
        "visual_element": "diagonal_accent"
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


def wrap_chinese_text(text, max_chars_per_line=12):
    if len(text) <= max_chars_per_line:
        return [text]
    lines = []
    current_line = ""
    for char in text:
        if len(current_line) >= max_chars_per_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line += char
    if current_line:
        lines.append(current_line)
    return lines


def generate_visual_element(layout_style, theme_colors, width=1600, height=2560):
    accent = theme_colors["accent"]

    if layout_style == "geometric_blocks":
        return f'''
        <rect x="0" y="{height * 0.12}" width="{width * 0.45}" height="{height * 0.06}" fill="{accent}" opacity="0.95"/>
        <rect x="0" y="{height * 0.12}" width="{width * 0.45}" height="{height * 0.06}" fill="{accent}" opacity="0.3" filter="url(#glow)"/>
        <rect x="{width * 0.65}" y="{height * 0.62}" width="{width * 0.32}" height="{height * 0.04}" fill="{accent}" opacity="0.85"/>
        <rect x="{width * 0.72}" y="{height * 0.68}" width="{width * 0.18}" height="{height * 0.025}" fill="{accent}" opacity="0.6"/>
        <circle cx="{width * 0.88}" cy="{height * 0.22}" r="{width * 0.12}" fill="{accent}" opacity="0.12"/>
        <circle cx="{width * 0.88}" cy="{height * 0.22}" r="{width * 0.09}" fill="none" stroke="{accent}" stroke-width="2" opacity="0.25"/>
        <circle cx="{width * 0.08}" cy="{height * 0.75}" r="8" fill="{accent}" opacity="0.8"/>
        <circle cx="{width * 0.12}" cy="{height * 0.77}" r="6" fill="{accent}" opacity="0.6"/>
        '''
    elif layout_style == "horizontal_lines":
        return f'''
        <line x1="0" y1="{height * 0.40}" x2="{width}" y2="{height * 0.40}" stroke="{accent}" stroke-width="4" opacity="0.9"/>
        <line x1="{width * 0.1}" y1="{height * 0.405}" x2="{width * 0.9}" y2="{height * 0.405}" stroke="{accent}" stroke-width="2" opacity="0.5"/>
        <line x1="0" y1="{height * 0.80}" x2="{width * 0.6}" y2="{height * 0.80}" stroke="{accent}" stroke-width="3" opacity="0.8"/>
        <line x1="{width * 0.65}" y1="{height * 0.80}" x2="{width}" y2="{height * 0.80}" stroke="{accent}" stroke-width="3" opacity="0.8"/>
        <rect x="{width * 0.05}" y="{height * 0.18}" width="{width * 0.25}" height="6" fill="{accent}" opacity="0.9"/>
        <rect x="{width * 0.75}" y="{height * 0.65}" width="{width * 0.2}" height="4" fill="{accent}" opacity="0.7"/>
        '''
    elif layout_style == "diagonal_accent":
        return f'''
        <polygon points="0,{height * 0.58} {width * 0.5},{height * 0.52} {width * 0.5},{height * 0.68} 0,{height * 0.74}"
                 fill="{accent}" opacity="0.25"/>
        <polygon points="0,{height * 0.58} {width * 0.5},{height * 0.52} {width * 0.5},{height * 0.54} 0,{height * 0.60}"
                 fill="{accent}" opacity="0.5"/>
        <rect x="{width * 0.05}" y="{height * 0.16}" width="{width * 0.22}" height="6" fill="{accent}" opacity="0.95"/>
        <rect x="{width * 0.05}" y="{height * 0.18}" width="{width * 0.15}" height="4" fill="{accent}" opacity="0.7"/>
        <rect x="{width * 0.7}" y="{height * 0.75}" width="{width * 0.25}" height="5" fill="{accent}" opacity="0.85"/>
        <circle cx="{width * 0.92}" cy="{height * 0.78}" r="12" fill="{accent}" opacity="0.9"/>
        '''
    return ""


def generate_svg_cover(title, subtitle="", author="", output_path=None,
                       theme=None, layout="minimal", width=1600, height=2560):
    """Generate professional book cover in SVG format. Returns the output path."""
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), "epub_cover.svg")

    if theme is None:
        theme = detect_theme(title, subtitle, author)

    theme_colors = THEMES.get(theme, THEMES["tech"])
    layout_config = LAYOUTS.get(layout, LAYOUTS["minimal"])

    print(f"  Cover theme: {theme} | layout: {layout}")

    title_lines = wrap_chinese_text(title, max_chars_per_line=10)
    subtitle_lines = wrap_chinese_text(subtitle, max_chars_per_line=16) if subtitle else []

    title_y_base = int(height * float(layout_config["title_y"].strip('%')) / 100)
    subtitle_y_base = int(height * float(layout_config["subtitle_y"].strip('%')) / 100)
    author_y = int(height * float(layout_config["author_y"].strip('%')) / 100)

    title_svg = ""
    line_height = int(layout_config["title_size"].strip('px')) * 1.2
    for i, line in enumerate(title_lines):
        y_pos = title_y_base + (i * line_height)
        title_svg += f'<text x="50%" y="{y_pos}" class="title">{line}</text>\n'

    subtitle_svg = ""
    if subtitle_lines:
        sub_line_height = int(layout_config["subtitle_size"].strip('px')) * 1.3
        for i, line in enumerate(subtitle_lines):
            y_pos = subtitle_y_base + (i * sub_line_height)
            subtitle_svg += f'<text x="50%" y="{y_pos}" class="subtitle">{line}</text>\n'

    visual_elements = generate_visual_element(
        layout_config["visual_element"], theme_colors, width, height
    )

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{theme_colors['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{theme_colors['secondary']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&amp;display=swap');
      .title {{
        font-family: 'Noto Serif SC', serif;
        font-size: {layout_config['title_size']};
        font-weight: 900;
        fill: {theme_colors['text']};
        text-anchor: middle;
        dominant-baseline: middle;
      }}
      .subtitle {{
        font-family: 'Noto Serif SC', serif;
        font-size: {layout_config['subtitle_size']};
        font-weight: 400;
        fill: {theme_colors['subtitle_text']};
        text-anchor: middle;
        dominant-baseline: middle;
      }}
      .author {{
        font-family: 'Noto Serif SC', serif;
        font-size: {layout_config['author_size']};
        font-weight: 400;
        fill: {theme_colors['accent']};
        text-anchor: middle;
        dominant-baseline: middle;
        letter-spacing: 0.1em;
      }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bgGradient)"/>
  {visual_elements}
  {title_svg}
  {subtitle_svg}
  <text x="50%" y="{author_y}" class="author">{author}</text>
  <rect x="2" y="2" width="{width-4}" height="{height-4}"
        fill="none" stroke="#888" stroke-width="3" opacity="0.3"/>
</svg>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    return output_path


def convert_svg_to_image(svg_path, output_image=None, quality=95):
    """Convert SVG to JPEG using Playwright. Returns output path or None on failure."""
    if output_image is None:
        output_image = os.path.join(tempfile.gettempdir(), "epub_cover.jpg")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  Warning: Playwright not installed, cannot generate SVG cover")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 2560}, device_scale_factor=2)
            page.goto(Path(svg_path).resolve().as_uri())
            page.wait_for_timeout(3000)
            page.screenshot(path=output_image, type='jpeg', quality=quality)
            browser.close()
        return output_image
    except Exception as e:
        print(f"  Warning: SVG cover conversion failed: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gen_cover_svg.py <title> [subtitle] [author] [output_image] [theme] [layout]")
        print(f"Themes: {', '.join(THEMES.keys())}")
        print(f"Layouts: {', '.join(LAYOUTS.keys())}")
        sys.exit(1)

    _title = sys.argv[1]
    _subtitle = sys.argv[2] if len(sys.argv) > 2 else ""
    _author = sys.argv[3] if len(sys.argv) > 3 else ""
    _out = sys.argv[4] if len(sys.argv) > 4 else None
    _theme = sys.argv[5] if len(sys.argv) > 5 else None
    _layout = sys.argv[6] if len(sys.argv) > 6 else "minimal"

    _svg = generate_svg_cover(_title, _subtitle, _author, theme=_theme, layout=_layout)
    _img = convert_svg_to_image(_svg, _out)
    print(f"Cover: {_img}")

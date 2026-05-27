#!/usr/bin/env python3
"""
render_book_epub.py — Markdown → EPUB 电子书（阅星曈推送）

流程：Markdown → ebooklib EPUB（含图片下载、SVG→PNG、封面生成）→ 可直接推送

用法：
    python render_book_epub.py <input.md> [--output out.epub] [--title 标题] [--author 作者]
                               [--cover-svg | --cover-html | --cover 图片路径]
                               [--cover-theme THEME] [--cover-layout LAYOUT]
                               [--subtitle 副标题] [--image-quality 88]
                               [--image-width 480] [--push]

依赖：
    pip install ebooklib markdown Pillow playwright
    playwright install chromium
"""

import argparse
import atexit
import hashlib
import html as html_module
import io
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from urllib.parse import unquote, urlparse
from pathlib import Path

from PIL import Image
from ebooklib import epub
import markdown

_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR.parent))
from render_book import convert_markdown_tables_to_text

COVER_THEMES = ("tech", "business", "design", "literature", "science", "personal")
COVER_LAYOUTS = ("minimal", "classic", "modern")

# ─── CSS ──────────────────────────────────────────────────────────────────────

CHAPTER_CSS = """
body {
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
                 "Noto Sans CJK SC", "Source Han Sans CN", sans-serif;
    line-height: 1.8;
    margin: 1em;
    padding: 0;
    font-size: 1em;
    color: #1a1a1a;
}
h1 { font-size: 1.6em; font-weight: bold; margin: 0 0 0.5em 0; color: #111; line-height: 1.3; }
h2 { font-size: 1.3em; font-weight: bold; margin: 1.5em 0 0.5em 0; color: #222; }
h3 { font-size: 1.1em; font-weight: bold; margin: 1.2em 0 0.4em 0; color: #333; }
h4 { font-size: 1.05em; font-weight: bold; margin: 1em 0 0.3em 0; color: #444; }
p  { margin: 0 0 0.8em 0; text-align: justify; }
strong, b { font-weight: bold; color: #000; }
em, i { font-style: italic; }
blockquote {
    border-left: 3px solid #ccc;
    padding-left: 1em;
    margin: 1em 0;
    color: #444;
    background: #f9f9f9;
}
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
.metadata { color: #666; font-size: 0.85em; margin-bottom: 1em; }
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
pre {
    background: #f8f8f8;
    border-left: 3px solid #0066cc;
    border-radius: 4px;
    padding: 1em;
    overflow-x: auto;
    margin: 1em 0;
    font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Code",
                 "Consolas", "Courier New", monospace;
    font-size: 0.85em;
    line-height: 1.4;
}
code {
    font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Code",
                 "Consolas", "Courier New", monospace;
    font-size: 0.9em;
    background: #f0f0f0;
    padding: 0.2em 0.4em;
    border-radius: 3px;
}
pre code { background: none; padding: 0; }
ul, ol { margin: 0.5em 0 1em 1.5em; padding: 0; }
li { margin: 0.3em 0; }
.codehilite span[style*="border: 1px solid #FF0000"] { border: none !important; }
"""

# ─── SVG → PNG（共享 Playwright 实例）─────────────────────────────────────────

_svg_browser = None
_svg_playwright = None


def _get_svg_browser():
    global _svg_browser, _svg_playwright
    if _svg_browser is None:
        try:
            from playwright.sync_api import sync_playwright
            _svg_playwright = sync_playwright().start()
            _svg_browser = _svg_playwright.chromium.launch(headless=True)
        except Exception as e:
            print(f"  Warning: Cannot start Playwright for SVG: {e}")
            return None
    return _svg_browser


def _close_svg_browser():
    global _svg_browser, _svg_playwright
    if _svg_browser:
        _svg_browser.close()
        _svg_browser = None
    if _svg_playwright:
        _svg_playwright.stop()
        _svg_playwright = None


atexit.register(_close_svg_browser)


def convert_svg_to_png(svg_data, width=480):
    """Convert SVG bytes to PNG using a shared Playwright browser instance."""
    browser = _get_svg_browser()
    if not browser:
        return None
    svg_path = png_path = None
    try:
        tmp_dir = tempfile.gettempdir()
        tag = hashlib.sha256(svg_data).hexdigest()[:12]
        svg_path = os.path.join(tmp_dir, f"epub_svg_{tag}.svg")
        png_path = os.path.join(tmp_dir, f"epub_svg_{tag}.png")

        with open(svg_path, 'wb') as f:
            f.write(svg_data)

        page = browser.new_page(viewport={"width": width, "height": 800})
        try:
            page.goto(Path(svg_path).resolve().as_uri())
            page.wait_for_timeout(800)
            dims = page.evaluate("""() => {
                const svg = document.querySelector('svg');
                if (!svg) return null;
                const r = svg.getBoundingClientRect();
                return { width: r.width, height: r.height };
            }""")
            if dims:
                page.set_viewport_size({
                    "width": max(int(dims['width']), 100),
                    "height": max(int(dims['height']), 100)
                })
                page.wait_for_timeout(300)
            page.screenshot(path=png_path, full_page=True)
        finally:
            page.close()

        with open(png_path, 'rb') as f:
            png_data = f.read()

        return png_data
    except Exception as e:
        print(f"  Warning: SVG conversion failed: {e}")
        return None
    finally:
        for path in (svg_path, png_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass


# ─── 图片压缩 ──────────────────────────────────────────────────────────────────

def validate_epub_options(image_quality, image_width):
    """Return CLI validation errors for EPUB image options."""
    errors = []
    if not 1 <= image_quality <= 100:
        errors.append("--image-quality 必须在 1..100 之间")
    if image_width <= 0:
        errors.append("--image-width 必须大于 0")
    return errors


def compress_image(img_data, target_width=480, jpeg_quality=88):
    """Compress image (bytes or file path) to JPEG. Returns bytes or None."""
    try:
        if isinstance(img_data, (str, Path)):
            img = Image.open(img_data)
        else:
            img = Image.open(io.BytesIO(img_data))

        if img.mode == 'RGBA':
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        if img.width > target_width:
            ratio = target_width / img.width
            img = img.resize((target_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

        out = io.BytesIO()
        img.save(out, format='JPEG', quality=jpeg_quality, optimize=True)
        return out.getvalue()
    except Exception as e:
        print(f"  Warning: Image compression failed: {e}")
        return None


# ─── 图片下载 ──────────────────────────────────────────────────────────────────

def _is_remote_url(url):
    return urlparse(url).scheme in {"http", "https"}


def _resolve_local_image_path(url, base_dir=None):
    parsed = urlparse(url)
    if parsed.scheme == "file":
        path_text = unquote(parsed.path)
        if os.name == "nt" and re.match(r"^/[A-Za-z]:", path_text):
            path_text = path_text[1:]
        return Path(path_text)

    path = Path(unquote(url))
    if path.is_absolute():
        return path
    return Path(base_dir or Path.cwd()) / path


def download_image(url, timeout=15, base_dir=None):
    """Download image from URL or local path, auto-converting SVG to PNG."""
    try:
        if url.startswith('blob:') or url.startswith('data:'):
            return None

        url_lower = url.split('?')[0].lower()
        is_svg_url = url_lower.endswith('.svg')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'image/png, image/jpeg, image/webp, image/svg+xml, image/*'
        }

        if not _is_remote_url(url):
            local_path = _resolve_local_image_path(url, base_dir)
            if not local_path.exists():
                print(f"  Warning: Local file not found: {local_path}")
                return None
            with open(local_path, 'rb') as f:
                data = f.read()
            content_type = ''
        else:
            # Strip CDN webp params
            clean_url = url
            if not is_svg_url and ('format,webp' in url or 'format/webp' in url):
                clean_url = re.sub(r'/format,webp', '', url)
                clean_url = re.sub(r'/format/webp', '', clean_url)
                clean_url = re.sub(r'/resize,w_\d+', '/resize,w_1000', clean_url)

            req = urllib.request.Request(clean_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get('Content-Type', '')
                data = resp.read()

        # Detect SVG
        is_svg = (
            is_svg_url
            or 'svg' in content_type
            or data[:5] == b'<?xml'
            or data[:4] == b'<svg'
            or data[:200].find(b'<svg') >= 0
        )
        if is_svg:
            print(f"    Converting SVG: {url_lower.split('/')[-1]}")
            return convert_svg_to_png(data)

        # Skip HTML error pages
        if content_type.startswith('text/html') or data[:15].lstrip().startswith(b'<!DOCTYPE'):
            return None

        # Validate raster image
        try:
            img_test = Image.open(io.BytesIO(data))
            img_test.load()
        except Exception:
            base_url = url.split('?')[0]
            if base_url != url:
                try:
                    req2 = urllib.request.Request(base_url, headers=headers)
                    with urllib.request.urlopen(req2, timeout=timeout) as r2:
                        data = r2.read()
                    Image.open(io.BytesIO(data)).load()
                except Exception:
                    return None
            else:
                return None

        return data
    except Exception as e:
        print(f"  Warning: Failed to download {url[:80]}: {e}")
        return None


# ─── 图片嵌入 ──────────────────────────────────────────────────────────────────

def embed_images(markdown_text, book, image_width=480, jpeg_quality=88, base_dir=None):
    """Download all images in markdown, embed in EPUB, replace URLs with epub paths.

    Returns (modified_markdown, image_count, total_bytes).
    """
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = list(re.finditer(img_pattern, markdown_text))
    if not matches:
        return markdown_text, 0, 0

    url_to_epub_path = {}
    total_bytes = 0

    for m in matches:
        url = m.group(2)
        if url in url_to_epub_path:
            continue
        data = download_image(url, base_dir=base_dir)
        if not data:
            continue
        compressed = compress_image(data, image_width, jpeg_quality)
        if not compressed:
            continue

        h = hashlib.md5(url.encode()).hexdigest()[:8]
        epub_path = f"images/img_{h}.jpg"
        book.add_item(epub.EpubItem(
            uid=f"img_{h}",
            file_name=epub_path,
            media_type="image/jpeg",
            content=compressed
        ))
        url_to_epub_path[url] = epub_path
        total_bytes += len(compressed)

    def replacer(m):
        url = m.group(2)
        return f'![{m.group(1)}]({url_to_epub_path[url]})' if url in url_to_epub_path else m.group(0)

    return re.sub(img_pattern, replacer, markdown_text), len(url_to_epub_path), total_bytes


# ─── Markdown 解析 ─────────────────────────────────────────────────────────────

def parse_frontmatter(content):
    """Extract title and author from YAML frontmatter. Returns (title, author, body)."""
    title = author = None
    if not content.startswith('---\n'):
        return title, author, content
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return title, author, content
    for line in parts[1].splitlines():
        stripped = line.strip()
        if stripped.startswith('title:'):
            val = stripped[6:].strip().strip('"\'')
            if val:
                title = val
        elif stripped.startswith('author:'):
            val = stripped[7:].strip().strip('"\'')
            if val:
                author = val
    return title, author, parts[2]


def extract_title(content):
    """Extract title from first # heading."""
    for line in content.splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return None


def has_reader_preface(content):
    """Return True when pre-## content has more than a standalone book title."""
    saw_first_nonblank = False
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not saw_first_nonblank:
            saw_first_nonblank = True
            if stripped.startswith("# "):
                continue
        return True
    return False


def strip_leading_heading(content, title):
    """Remove a leading Markdown heading when build_xhtml already renders it."""
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match and match.group(2).strip() == title:
            del lines[idx]
            while lines and not lines[0].strip():
                del lines[0]
            return "\n".join(lines)
        return content
    return content


def split_chapters(body):
    """Split content on ## headings. Returns [(chapter_title, content), ...]."""
    lines = body.split('\n')
    chapters = []
    cur_title = None
    cur_lines = []
    preface_lines = []
    in_fence = False

    for line in lines:
        if re.match(r"^\s*(```+|~~~+)", line):
            in_fence = not in_fence

        if not in_fence and line.startswith('## '):
            if cur_title is not None:
                chapters.append((cur_title, '\n'.join(cur_lines).strip()))
            elif any(ln.strip() for ln in preface_lines):
                preface = '\n'.join(preface_lines).strip()
                if has_reader_preface(preface):
                    preface_title = extract_title(preface) or "前言"
                    chapters.append((preface_title, strip_leading_heading(preface, preface_title)))
            cur_title = line[3:].strip()
            cur_lines = []
        else:
            if cur_title is not None:
                cur_lines.append(line)
            else:
                preface_lines.append(line)

    if cur_title is not None:
        chapters.append((cur_title, '\n'.join(cur_lines).strip()))
    elif any(ln.strip() for ln in preface_lines):
        preface = '\n'.join(preface_lines).strip()
        if has_reader_preface(preface):
            preface_title = extract_title(preface) or "正文"
            chapters.append((preface_title, strip_leading_heading(preface, preface_title)))

    return chapters


# ─── XHTML 生成 ────────────────────────────────────────────────────────────────

_MD_EXTENSIONS = ['extra', 'codehilite', 'nl2br', 'sane_lists']
_MD_EXT_CONFIG = {'codehilite': {'noclasses': True, 'pygments_style': 'default'}}


def md_to_html(text):
    text = convert_markdown_tables_to_text(text)
    return markdown.markdown(text, extensions=_MD_EXTENSIONS, extension_configs=_MD_EXT_CONFIG)


def fix_xhtml(html_str):
    html_str = re.sub(r'<br\s*>', '<br/>', html_str)
    html_str = re.sub(r'<hr\s*>', '<hr/>', html_str)
    html_str = re.sub(r'<img([^/]*?)>', r'<img\1/>', html_str)
    html_str = re.sub(r'border:\s*1px\s+solid\s+#FF0000;?\s*', '', html_str)
    html_str = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)', '&amp;', html_str)
    return html_str


def build_xhtml(title, body_html):
    escaped = html_module.escape(title)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>{escaped}</title>
<style type="text/css">
{CHAPTER_CSS}
</style>
</head>
<body>
<h1>{escaped}</h1>
{body_html}
</body>
</html>"""


# ─── 封面生成 ──────────────────────────────────────────────────────────────────

def generate_cover(args, book_title, chapter_count):
    """Generate cover image bytes based on CLI args. Returns bytes or None."""
    subtitle = args.subtitle or f"{chapter_count} chapters"

    if args.cover:
        cover_path = Path(args.cover).expanduser()
        if cover_path.exists():
            data = compress_image(cover_path, target_width=1400, jpeg_quality=95)
            print(f"  Cover: {cover_path}")
            return data
        print(f"  Warning: Cover image not found: {cover_path}")
        return None

    if args.cover_svg:
        try:
            sys.path.insert(0, str(_SCRIPT_DIR))
            from gen_cover_svg import generate_svg_cover, convert_svg_to_image
            svg_path = generate_svg_cover(
                book_title, subtitle, args.author,
                theme=args.cover_theme, layout=args.cover_layout
            )
            img_path = convert_svg_to_image(svg_path)
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            print(f"  Warning: SVG cover failed: {e}")
        return None

    if args.cover_html:
        try:
            sys.path.insert(0, str(_SCRIPT_DIR))
            from gen_cover_html import generate_cover_html, screenshot_cover
            html_path = generate_cover_html(
                book_title, subtitle, args.author, theme=args.cover_theme
            )
            img_path = screenshot_cover(html_path)
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            print(f"  Warning: HTML cover failed: {e}")
        return None

    return None


# ─── 主流程 ────────────────────────────────────────────────────────────────────

def build_epub(args):
    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"[ERROR] 文件不存在：{md_path}", file=sys.stderr)
        sys.exit(1)

    raw = md_path.read_text(encoding='utf-8')
    fm_title, fm_author, body = parse_frontmatter(raw)

    book_title = args.title or fm_title or extract_title(body) or md_path.stem
    book_author = args.author or fm_author or "龙虾"

    out_path = Path(args.output) if args.output else md_path.with_suffix('.epub')

    print(f"Generating EPUB...")
    print(f"  Input : {md_path}")
    print(f"  Output: {out_path}")
    print(f"  Title : {book_title}")
    print(f"  Author: {book_author}")

    # Split into chapters
    chapters_data = split_chapters(body)
    if not chapters_data:
        chapters_data = [(book_title, body)]
        print(f"  Chapters: 1 (single)")
    else:
        print(f"  Chapters: {len(chapters_data)} (split by ## headings)")

    # Build book
    book = epub.EpubBook()
    book.set_identifier(f'epub-{hashlib.md5(book_title.encode()).hexdigest()[:12]}')
    book.set_title(book_title)
    book.set_language('zh')
    book.add_author(book_author)

    # Cover
    cover_data = generate_cover(args, book_title, len(chapters_data))
    if cover_data:
        book.set_cover("cover.jpg", cover_data)

    # Process chapters
    epub_chapters = []
    toc_items = []
    spine = ['nav']
    total_imgs = 0
    total_img_bytes = 0

    for idx, (ch_title, ch_body) in enumerate(chapters_data, 1):
        print(f"  [{idx}/{len(chapters_data)}] {ch_title}")

        ch_body, img_count, img_bytes = embed_images(
            ch_body, book, args.image_width, args.image_quality, base_dir=md_path.parent
        )
        total_imgs += img_count
        total_img_bytes += img_bytes
        if img_count > 0:
            print(f"    → {img_count} images ({img_bytes / 1024:.1f} KB)")

        body_html = fix_xhtml(md_to_html(ch_body))
        xhtml = build_xhtml(ch_title, body_html)

        fname = f"chapter_{idx:03d}.xhtml"
        ch = epub.EpubHtml(title=ch_title, file_name=fname, lang='zh')
        ch.set_content(xhtml.encode('utf-8'))

        book.add_item(ch)
        epub_chapters.append(ch)
        toc_items.append(epub.Link(fname, ch_title, f"ch{idx}"))
        spine.append(ch)

    book.toc = toc_items
    book.spine = spine
    book.add_item(epub.EpubNcx())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(out_path), book, {
        'epub3_pages': False,
        'epub3_landmark': False,
        'spine_direction': True
    })

    _close_svg_browser()

    size_kb = out_path.stat().st_size / 1024
    print(f"\n[OK] 已生成：{out_path}")
    print(f"     大小：{size_kb:.0f} KB  |  章节：{len(epub_chapters)}  |  图片：{total_imgs}")
    return str(out_path)


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Markdown → EPUB 电子书（阅星曈推送）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 .epub 文件路径（默认：与输入同名）")
    parser.add_argument("--title", "-t", help="书名（默认：从 frontmatter 或 # 标题提取）")
    parser.add_argument("--author", "-a", default="龙虾", help="作者（默认：龙虾）")
    parser.add_argument("--push", action="store_true", help="生成后立即推送到设备")

    cover_group = parser.add_mutually_exclusive_group()
    cover_group.add_argument("--cover-svg", action="store_true", help="生成 SVG 封面（KDP 1600×2560）")
    cover_group.add_argument("--cover-html", action="store_true", help="生成 HTML 封面")
    cover_group.add_argument("--cover", help="自定义封面图片路径（JPG/PNG）")
    parser.add_argument("--cover-theme", choices=COVER_THEMES, help="封面主题（默认自动检测）")
    parser.add_argument("--cover-layout", choices=COVER_LAYOUTS, default="minimal", help="SVG 布局（默认：minimal）")
    parser.add_argument("--subtitle", help="封面副标题")

    parser.add_argument("--image-quality", type=int, default=88, help="JPEG 质量 1-100（默认：88）")
    parser.add_argument("--image-width", type=int, default=480, help="图片最大宽度 px（默认：480）")

    args = parser.parse_args()
    option_errors = validate_epub_options(args.image_quality, args.image_width)
    if option_errors:
        parser.error("; ".join(option_errors))
    output = build_epub(args)
    print(f"OUTPUT:{output}")

    if args.push:
        push_script = _SCRIPT_DIR.parent / "push_to_device.py"
        result = subprocess.run(
            [sys.executable, str(push_script), output],
            cwd=str(_SCRIPT_DIR.parent.parent),
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()

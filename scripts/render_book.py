#!/usr/bin/env python3
"""
render_epub.py — Markdown → EPUB 3 电子书

用法：
    python render_epub.py <input.md> [options]

选项：
    --output, -o   输出 EPUB 路径（默认与输入同目录，同名 .epub）
    --title, -t    书名（默认取 Markdown 第一个 H1 标题）
    --author, -a   作者（默认「龙虾」）
    --cover        封面图片路径（可选，推荐 300×400 灰阶 PNG）
    --lang         语言代码（默认 zh）

输入 Markdown 格式约定：
    - 第一行 H1（# 标题）将作为书名（如未通过 --title 指定）
    - ## 开头的章节自动拆分为 EPUB chapter
    - 为墨水屏兼容，仅保留：标题（H1/H2/H3）、段落、**粗体**、*斜体*
    - 列表项 → 前缀「· 」段落；引用块 → 带引号段落；代码块 → 整段丢弃

依赖：
    pip install ebooklib markdown Pillow
    render_image.py（同目录，提供图片编码）
"""

from __future__ import annotations

import argparse
import re
import sys
import io
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─── EPUB 内嵌样式 ─────────────────────────────────────────────────────────────

EPUB_CSS = """
/* 极简样式：兼容弱 CSS 的墨水屏阅读器，仅标题/正文/加粗等 */
body {
  font-family: serif;
  font-size: 1em;
  line-height: 1.6;
  color: #000000;
  background: #ffffff;
  margin: 0.8em;
}

h1 {
  font-size: 1.35em;
  font-weight: bold;
  margin: 0 0 0.5em;
}
h2 {
  font-size: 1.15em;
  font-weight: bold;
  margin: 1em 0 0.4em;
}
h3 {
  font-size: 1.05em;
  font-weight: bold;
  margin: 0.8em 0 0.3em;
}

p {
  margin: 0 0 0.6em;
}

strong, b {
  font-weight: bold;
}
em, i {
  font-style: italic;
}

hr {
  border: none;
  border-top: 1px solid #000000;
  margin: 1em 0;
}

img {
  max-width: 100%;
  height: auto;
}

/* 封面页：图片全屏撑满，无边距 */
body.cover-body {
  margin: 0;
  padding: 0;
  background: #000000;
}
body.cover-body img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
"""

# ─── Markdown 解析 ─────────────────────────────────────────────────────────────

def extract_title_from_md(content: str) -> str:
    """从 Markdown 内容中提取第一个 H1 标题。"""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return "无题"


def split_chapters(content: str) -> list[dict]:
    """
    将 Markdown 文本按 ## 章节分割。
    返回：[{"title": str, "content": str}, ...]
    第一个 ## 之前的内容（如有）放入前言章节，并去除顶部的 H1 书名行（已用作书籍标题）。
    """
    lines = content.splitlines(keepends=True)
    chapters: list[dict] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            if current_lines:
                chapters.append({
                    "title": current_title,
                    "content": "".join(current_lines).strip(),
                })
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        chapters.append({
            "title": current_title,
            "content": "".join(current_lines).strip(),
        })

    # 如果没有 ## 分隔，整个文档作为一章
    if not chapters:
        chapters = [{"title": "", "content": content.strip()}]

    # 前言章节（title == ""）去掉顶部的 H1 书名行，避免和封面页重复
    preamble = chapters[0]
    if not preamble["title"]:
        preamble["content"] = re.sub(r'^#\s+[^\n]*\n?', '', preamble["content"]).strip()

    return chapters


def _strip_unsupported_html(html: str) -> str:
    """
    后处理：将列表、引用块、代码块降级为纯段落，保留标题/加粗/斜体/段落。
    - <ul>/<ol> → 每个 <li> 文本变成一行 <p>，前缀「· 」
    - <blockquote> → 内容提取为 <p>，加引号
    - <pre><code>...</code></pre> → 整块丢弃
    - 行内 <code> → 保留文字，去掉标签
    - <hr> → 保留（封面分隔线）
    """
    # 去掉 <pre>...</pre>（含 fenced code）
    html = re.sub(r'<pre[^>]*>.*?</pre>', '', html, flags=re.DOTALL)

    # 行内 <code> → 纯文字
    html = re.sub(r'<code[^>]*>(.*?)</code>', r'\1', html, flags=re.DOTALL)

    # <li>…</li> → <p>· …</p>
    html = re.sub(r'<li>(.*?)</li>', r'<p>· \1</p>', html, flags=re.DOTALL)

    # 去掉 <ul>/<ol> 标签（内容已转为 <p>）
    html = re.sub(r'</?(?:ul|ol)[^>]*>', '', html)

    # <blockquote> 内容 → 加引号前缀的段落
    def _bq(m: re.Match) -> str:
        inner = m.group(1).strip()
        inner = re.sub(r'<p>(.*?)</p>', r'<p>"\1"</p>', inner, flags=re.DOTALL)
        if not inner.startswith('<p>'):
            inner = f'<p>"{inner}"</p>'
        return inner
    html = re.sub(r'<blockquote>(.*?)</blockquote>', _bq, html, flags=re.DOTALL)

    return html


def md_to_html_body(md_content: str) -> str:
    """
    将 Markdown 转换为 HTML body 内容。
    仅保留：标题、段落、**粗体**、*斜体*。
    列表 → 前缀「· 」段落，引用 → 带引号段落，代码块 → 整段去掉。
    """
    try:
        import markdown as md_lib
    except ImportError:
        print("[ERROR] markdown 未安装。运行：pip install markdown")
        sys.exit(1)

    html = md_lib.markdown(
        md_content,
        extensions=["markdown.extensions.sane_lists", "markdown.extensions.fenced_code"],
    )
    return _strip_unsupported_html(html)


# ─── 封面生成 ─────────────────────────────────────────────────────────────────

def generate_cover_html(title: str, author: str, date_str: str) -> str:
    """
    epub spine 封面页：直接全屏显示 cover.jpg。
    cover.jpg 已通过 set_cover() 注册为 manifest cover-image，
    此页引用同一张图，保证缩略图和翻页封面完全一致。
    """
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
</head>
<body class="cover-body">
<img src="cover.jpg" alt="{title}"/>
</body>
</html>"""


def _build_cover_html(title: str, author: str, date_str: str) -> str:
    """
    生成封面截图用的 HTML（非 epub spine 内嵌页，仅用于 Playwright 截图）。
    标题若含全角/半角冒号自动拆为主标题 + 副标题。
    """
    # 拆主标题 / 副标题
    for sep in ("：", ":"):
        if sep in title:
            main_title, subtitle = title.split(sep, 1)
            break
    else:
        main_title, subtitle = title, ""

    subtitle_html = (
        f'<div class="subtitle">{subtitle}</div>' if subtitle else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  width: 480px; height: 800px;
  background: #fff;
  overflow: hidden;
  font-family: 'Noto Serif SC', serif;
  color: #000;
}}
.top {{
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 460px;
  background: #000;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 0 44px 44px;
}}
.main-title {{
  font-size: 72px;
  font-weight: 900;
  line-height: 1.1;
  color: #fff;
  letter-spacing: 4px;
  word-break: break-all;
}}
.subtitle {{
  font-size: 34px;
  font-weight: 400;
  color: #fff;
  margin-top: 14px;
  letter-spacing: 2px;
}}
.divider {{
  position: absolute;
  top: 460px; left: 0; right: 0;
  height: 8px;
  background: #000;
}}
.bottom {{
  position: absolute;
  top: 468px; left: 0; right: 0; bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 44px;
  gap: 18px;
}}
.author {{
  font-size: 38px;
  font-weight: 700;
  color: #000;
  letter-spacing: 4px;
}}
.date {{
  font-family: 'Space Mono', monospace;
  font-size: 20px;
  color: #000;
  letter-spacing: 3px;
}}
.badge {{
  position: absolute;
  bottom: 32px; right: 44px;
  font-family: 'Space Mono', monospace;
  font-size: 14px;
  color: #000;
  letter-spacing: 3px;
  text-transform: uppercase;
  border: 2px solid #000;
  padding: 4px 10px;
}}
</style>
</head>
<body>

<div class="top">
  <div class="main-title">{main_title}</div>
  {subtitle_html}
</div>

<div class="divider"></div>

<div class="bottom">
  <div class="author">{author}</div>
  <div class="date">{date_str}</div>
</div>

<div class="badge">EPUB</div>

</body>
</html>"""


def generate_cover_jpeg(
    title: str,
    author: str,
    date_str: str,
    width: int = 480,
    height: int = 800,
) -> Optional[bytes]:
    """
    用 Playwright 截图 HTML 封面，返回 JPEG bytes。
    Playwright 不可用时退回 Pillow 纯色兜底（保证 epub 合规）。
    """
    import tempfile, os

    html_str = _build_cover_html(title, author, date_str)

    # ── Playwright 路径 ──────────────────────────────────────
    try:
        _scripts_dir = str(Path(__file__).parent)
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from render_image import screenshot_html as _screenshot

        tmp = tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        )
        try:
            tmp.write(html_str)
            tmp.close()
            png_bytes = _screenshot(Path(tmp.name), width, height, inject_fonts=True)
        finally:
            os.unlink(tmp.name)

        from PIL import Image as _PilImg
        img = _PilImg.open(io.BytesIO(png_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        print("[INFO] 封面：HTML 截图生成")
        return buf.getvalue()

    except Exception as e:
        print(f"[WARN] Playwright 封面截图失败（{e}），退回 Pillow 兜底")

    # ── Pillow 兜底：纯白 + 黑色标题文字 ────────────────────
    try:
        from PIL import Image as _Img, ImageDraw as _Draw
        img = _Img.new("RGB", (width, height), (255, 255, 255))
        draw = _Draw.Draw(img)
        draw.rectangle([20, 20, width - 20, height - 20], outline=(0, 0, 0), width=3)
        # 标题居中（默认字体，无法加载自定义字体时的最后保障）
        draw.text((width // 2, height // 2), title, fill=(0, 0, 0), anchor="mm")
        draw.text((width // 2, height // 2 + 60), author, fill=(80, 80, 80), anchor="mm")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
        print("[INFO] 封面：Pillow 兜底生成")
        return buf.getvalue()
    except Exception as e2:
        print(f"[WARN] Pillow 封面兜底也失败（{e2}），epub 将无封面图片")
        return None


def chapter_to_html(title: str, body_html: str) -> str:
    """将一章的 HTML body 包裹成完整的 XHTML 文件。"""
    title_tag = f"<h2>{title}</h2>\n" if title else ""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<link rel="stylesheet" type="text/css" href="../styles/style.css"/>
</head>
<body>
{title_tag}{body_html}
</body>
</html>"""


# ─── 图片处理 ─────────────────────────────────────────────────────────────────

def _load_render_image():
    """懒加载 render_image 里的图片编码函数（同目录）。"""
    import sys as _sys
    _scripts_dir = str(Path(__file__).parent)
    if _scripts_dir not in _sys.path:
        _sys.path.insert(0, _scripts_dir)
    from render_image import png_bytes_to_xtg_xth, XtgXthParams
    return png_bytes_to_xtg_xth, XtgXthParams


def convert_image_to_xtg(img_path: Path) -> Optional[bytes]:
    """
    读取图片并转为 XTG bytes（1bit 黑白，适合墨水屏快刷）。
    失败时返回 None（静默跳过）。
    """
    try:
        from PIL import Image
        png_bytes_to_xtg_xth, XtgXthParams = _load_render_image()

        img = Image.open(img_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        xtg_bytes, _ = png_bytes_to_xtg_xth(buf.getvalue(), XtgXthParams())
        return xtg_bytes
    except Exception as e:
        print(f"[WARN] 图片转 XTG 失败，跳过：{img_path}  ({e})")
        return None


# ─── EPUB 构建 ────────────────────────────────────────────────────────────────

def build_epub(
    md_path: Path,
    output_path: Path,
    title: Optional[str] = None,
    author: str = "龙虾",
    cover_path: Optional[Path] = None,
    lang: str = "zh",
) -> str:
    try:
        from ebooklib import epub
    except ImportError:
        print("[ERROR] ebooklib 未安装。运行：pip install ebooklib")
        sys.exit(1)

    # ── 读取 Markdown ──────────────────────────────────────────
    content = md_path.read_text(encoding="utf-8")
    md_dir = md_path.parent

    # ── 解析标题 ───────────────────────────────────────────────
    if not title:
        title = extract_title_from_md(content)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # ── 创建 EPUB book ─────────────────────────────────────────
    book = epub.EpubBook()
    book.set_identifier(f"eink-push-{uuid.uuid4().hex[:8]}")
    book.set_title(title)
    book.set_language(lang)
    book.add_author(author)
    book.add_metadata("DC", "date", date_str)

    # ── CSS ────────────────────────────────────────────────────
    css_item = epub.EpubItem(
        uid="style",
        file_name="styles/style.css",
        media_type="text/css",
        content=EPUB_CSS.encode("utf-8"),
    )
    book.add_item(css_item)

    # ── 封面图片（manifest cover-image，设备必需） ─────────────
    cover_jpeg: Optional[bytes] = None
    if cover_path and cover_path.exists():
        # 用户提供了图片：转为标准 JPEG
        try:
            from PIL import Image as _PilImg
            _img = _PilImg.open(cover_path).convert("RGB")
            _img.thumbnail((480, 800))
            _buf = io.BytesIO()
            _img.save(_buf, format="JPEG", quality=88)
            cover_jpeg = _buf.getvalue()
            print(f"[INFO] 使用封面图片：{cover_path.name}")
        except Exception as e:
            print(f"[WARN] 封面图片处理失败（{e}），将自动生成文字封面")

    if cover_jpeg is None:
        # 无外部图片：用 Pillow 生成纯文字封面
        cover_jpeg = generate_cover_jpeg(title, author, date_str)
        if cover_jpeg:
            print("[INFO] 自动生成文字封面图片")

    if cover_jpeg:
        # create_page=False：禁止 ebooklib 自动生成 cover.xhtml，
        # 由下方手动添加的 cover_html 作为封面页，避免重复
        book.set_cover("cover.jpg", cover_jpeg, create_page=False)

    # 封面 HTML 页（spine 内翻页用，与封面图片并存）
    cover_html = epub.EpubHtml(
        uid="cover",
        file_name="cover.xhtml",
        title="封面",
        lang=lang,
    )
    cover_html.content = generate_cover_html(title, author, date_str).encode("utf-8")
    cover_html.add_item(css_item)
    book.add_item(cover_html)

    # ── 处理 Markdown 中的图片引用（替换路径，嵌入文件） ───────
    image_items: dict[str, str] = {}
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    def embed_image(match: re.Match) -> str:
        alt = match.group(1)
        img_ref = match.group(2)
        if img_ref.startswith("http"):
            return match.group(0)
        img_file = (md_dir / img_ref).resolve()
        if not img_file.exists():
            return match.group(0)
        if str(img_file) not in image_items:
            xtg_bytes = convert_image_to_xtg(img_file)
            if xtg_bytes:
                # 保留原文件名，换 .xtg 扩展名
                epub_img_path = f"images/{img_file.stem}.xtg"
                book.add_item(epub.EpubItem(
                    uid=f"img-{len(image_items)}",
                    file_name=epub_img_path,
                    media_type="application/octet-stream",
                    content=xtg_bytes,
                ))
                image_items[str(img_file)] = epub_img_path
        if str(img_file) in image_items:
            return f'![{alt}](../{image_items[str(img_file)]})'
        return match.group(0)

    content = img_pattern.sub(embed_image, content)

    # ── 分章节 ─────────────────────────────────────────────────
    chapters_data = split_chapters(content)
    epub_chapters: list[epub.EpubHtml] = []

    for i, ch in enumerate(chapters_data):
        if not ch["content"] and not ch["title"]:
            continue
        body_html = md_to_html_body(ch["content"])
        chapter_xhtml = chapter_to_html(ch["title"], body_html)

        ch_item = epub.EpubHtml(
            uid=f"chapter-{i}",
            file_name=f"chapter_{i:02d}.xhtml",
            title=ch["title"] or title,
            lang=lang,
        )
        ch_item.content = chapter_xhtml.encode("utf-8")
        ch_item.add_item(css_item)
        book.add_item(ch_item)
        epub_chapters.append(ch_item)

    # ── 目录 & Spine ───────────────────────────────────────────
    nonempty = [c for c in chapters_data if c["content"] or c["title"]]
    toc_items = [
        epub.Link(ch_item.file_name, ch_data["title"], f"toc-{i}")
        for i, (ch_item, ch_data) in enumerate(zip(epub_chapters, nonempty))
        if ch_data["title"]
    ]

    book.toc = toc_items if toc_items else epub_chapters
    # cover 第一，nav 标记为 linear=no（目录不占阅读页序）
    book.spine = [cover_html] + epub_chapters + [("nav", "no")]

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # ── 写出 ───────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    print(f"[OK] EPUB 已生成：{output_path}  ({output_path.stat().st_size // 1024} KB)")
    print(f"[INFO] 章节数：{len(epub_chapters)}  标题：{title}")

    return str(output_path)


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 Markdown 文件打包为 EPUB 3 电子书",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("--output", "-o", default=None,
                        help="输出 EPUB 路径（默认与输入同名 .epub）")
    parser.add_argument("--title", "-t", default=None,
                        help="书名（默认取 Markdown 第一个 H1 标题）")
    parser.add_argument("--author", "-a", default="龙虾",
                        help="作者名（默认「龙虾」）")
    parser.add_argument("--cover", default=None,
                        help="封面图片路径（可选）")
    parser.add_argument("--lang", default="zh",
                        help="语言代码（默认 zh）")

    args = parser.parse_args()

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"[ERROR] 文件不存在：{md_path}")
        sys.exit(1)

    output_path = Path(args.output).resolve() if args.output else md_path.with_suffix(".epub")
    cover_path = Path(args.cover).resolve() if args.cover else None

    result = build_epub(
        md_path=md_path,
        output_path=output_path,
        title=args.title,
        author=args.author,
        cover_path=cover_path,
        lang=args.lang,
    )

    print(f"OUTPUT:{result}")


if __name__ == "__main__":
    main()

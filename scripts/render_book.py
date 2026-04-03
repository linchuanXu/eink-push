#!/usr/bin/env python3
"""
render_book.py — Markdown → XTC 翻页集（墨水屏电子书，快刷 1-bit）

流程：Markdown → marknative（Node.js）→ 分页 PNG → XTG → XTC

用法：
    python render_book.py <input.md> [--output|-o output.xtc] [--title|-t 标题] [--author|-a 作者] [--push]

依赖：
    Node.js >= 18 + npm install marknative（在项目根目录执行一次）
    pip install Pillow
"""

import argparse
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from render_image import XtgXthParams, png_bytes_to_xtg_xth, encode_xtc

_SCRIPT_DIR = Path(__file__).parent
_NODE_SCRIPT = _SCRIPT_DIR / "render_book_pages.mjs"

# Pillow 9+：Resampling 枚举；旧版回退到 Image.BOX / Image.LANCZOS
_RES_BOX = getattr(getattr(Image, "Resampling", Image), "BOX", Image.BOX)
_RES_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)


def _resize_to_device(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """marknative 输出 2×（960×1600）时，用 BOX 缩小比 LANCZOS 更少糊边。"""
    w, h = img.size
    if (w, h) == (target_w, target_h):
        return img
    if w == target_w * 2 and h == target_h * 2:
        return img.resize((target_w, target_h), _RES_BOX)
    return img.resize((target_w, target_h), _RES_LANCZOS)


def _check_node():
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError("node 返回非零退出码")
    except (FileNotFoundError, RuntimeError):
        print(
            "[ERROR] 未找到 Node.js。请安装 Node.js >= 18：https://nodejs.org/",
            file=sys.stderr,
        )
        sys.exit(1)


def _check_marknative():
    pkg_json = _SCRIPT_DIR.parent / "node_modules" / "marknative" / "package.json"
    if not pkg_json.exists():
        print(
            "[ERROR] marknative 未安装。在项目根目录运行：npm install marknative",
            file=sys.stderr,
        )
        sys.exit(1)


_FRONTMATTER_SKIP = {"style"}  # 不展示给读者的纯渲染提示字段
_YAML_BLOCK_SCALARS = {">", "|", "|-", ">-", ">+", "|+"}


def _strip_yaml_quotes(val: str) -> str:
    """去掉 YAML 字符串两端的单/双引号。"""
    if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
        return val[1:-1]
    return val


def preprocess_markdown(md_text: str) -> str:
    """将 YAML frontmatter 转换为正文：title → # 标题，其余字段平铺为纯文本。

    边界处理：
    - 无 frontmatter 或缺少闭合 --- → 原样返回
    - 缩进行 / 列表项 / YAML 注释 → 跳过（不解析为字段）
    - 块标量（> |） → 跳过整个字段值
    - 值含冒号（如 URL）→ 只按第一个 : 分割，完整保留余下部分
    - 带引号的值 → 去掉外层引号
    - parts 全空时 → 返回 body 原文（不丢内容）
    """
    if not md_text:
        return md_text

    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return md_text

    end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), None)
    if end is None:
        return md_text

    meta_lines = lines[1:end]
    body = "\n".join(lines[end + 1:]).lstrip("\n")

    title: str | None = None
    extras: list[str] = []
    skip_indented = False  # 遇到块标量后跳过后续缩进行

    for line in meta_lines:
        stripped = line.strip()

        # 空行 / YAML 注释
        if not stripped or stripped.startswith("#"):
            continue

        # 缩进行（块标量内容 / 列表项续行）
        if line[:1] in (" ", "\t"):
            continue

        # 列表项（顶格 - 开头，值为列表）
        if stripped.startswith("- "):
            continue

        if ":" not in stripped:
            continue

        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()

        # 块标量：值为 > 或 | 等，实际内容在后续缩进行中（我们跳过）
        if not val or val in _YAML_BLOCK_SCALARS:
            skip_indented = True
            continue

        skip_indented = False
        val = _strip_yaml_quotes(val)

        if not val:
            continue

        if key == "title":
            title = val
        elif key not in _FRONTMATTER_SKIP:
            extras.append(val)

    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    if extras:
        parts.append("\n".join(extras))
    if body:
        parts.append(body)

    # 至少保留 body，避免返回空字符串
    return "\n\n".join(parts) if parts else body


def extract_title_from_md(md_text: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def build_book(
    md_path: str,
    output_path: str = None,
    title: str = None,
    author: str = "龙虾",
) -> str:
    _check_node()
    _check_marknative()

    md_path = Path(md_path).resolve()
    if not md_path.exists():
        print(f"[ERROR] 文件不存在：{md_path}", file=sys.stderr)
        sys.exit(1)

    md_text = preprocess_markdown(md_path.read_text(encoding="utf-8"))

    if not title:
        title = extract_title_from_md(md_text)

    if not output_path:
        output_path = md_path.with_suffix(".xtc")
    output_path = Path(output_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        processed_md = Path(tmp_dir) / "input.md"
        processed_md.write_text(md_text, encoding="utf-8")
        result = subprocess.run(
            ["node", str(_NODE_SCRIPT), str(processed_md), tmp_dir],
            capture_output=True,
            text=True,
            cwd=str(_SCRIPT_DIR.parent),
        )
        if result.returncode != 0:
            print(
                f"[ERROR] marknative 渲染失败：\n{result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            info = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            print(
                f"[ERROR] 无法解析 Node.js 输出：\n{result.stdout}",
                file=sys.stderr,
            )
            sys.exit(1)

        png_files = info["files"]
        if not png_files:
            print("[ERROR] marknative 未生成任何页面", file=sys.stderr)
            sys.exit(1)

        _TARGET_W, _TARGET_H = 480, 800
        params = XtgXthParams(dither=25, sharpen=25, threshold=132)
        xtg_pages = []
        for png_file in png_files:
            png_bytes = Path(png_file).read_bytes()
            # marknative renders at 2x DPR; downsample to device resolution
            img = Image.open(io.BytesIO(png_bytes))
            if img.size != (_TARGET_W, _TARGET_H):
                img = _resize_to_device(img, _TARGET_W, _TARGET_H)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()
            xtg_bytes, _ = png_bytes_to_xtg_xth(png_bytes, params)
            xtg_pages.append(xtg_bytes)

    xtc_bytes = encode_xtc(xtg_pages, title=title, author=author)
    output_path.write_bytes(xtc_bytes)
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Markdown → XTC 翻页集")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument(
        "--output", "-o", help="输出 .xtc 文件路径（默认：与输入同目录同名）"
    )
    parser.add_argument(
        "--title", "-t", help="书名（默认：Markdown 首行 # 标题）"
    )
    parser.add_argument("--author", "-a", default="龙虾", help="作者（默认：龙虾）")
    parser.add_argument(
        "--push", action="store_true", help="渲染完成后立即推送到设备"
    )
    args = parser.parse_args()

    output = build_book(args.input, args.output, args.title, args.author)
    print(f"[OK] 已生成：{output}")

    if args.push:
        push_script = _SCRIPT_DIR / "push_to_device.py"
        result = subprocess.run(
            [sys.executable, str(push_script), output],
            cwd=str(_SCRIPT_DIR.parent),
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()

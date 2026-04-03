#!/usr/bin/env python3
"""
render_book.py — Markdown → XTC 翻页集（墨水屏电子书，快刷 1-bit）

流程：Markdown → marknative（Node.js）→ 分页 PNG → XTG → XTC

用法：
    python render_book.py <input.md> [--output|-o output.xtc] [--title|-t 标题] [--author|-a 作者]

依赖：
    Node.js >= 18 + npm install marknative（在项目根目录执行一次）
    pip install Pillow
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_image import XtgXthParams, png_bytes_to_xtg_xth, encode_xtc

_SCRIPT_DIR = Path(__file__).parent
_NODE_SCRIPT = _SCRIPT_DIR / "render_book_pages.mjs"


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

    if not title:
        title = extract_title_from_md(md_path.read_text(encoding="utf-8"))

    if not output_path:
        output_path = md_path.with_suffix(".xtc")
    output_path = Path(output_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = subprocess.run(
            ["node", str(_NODE_SCRIPT), str(md_path), tmp_dir],
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

        params = XtgXthParams()
        xtg_pages = []
        for png_file in png_files:
            png_bytes = Path(png_file).read_bytes()
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
    args = parser.parse_args()

    output = build_book(args.input, args.output, args.title, args.author)
    print(f"[OK] 已生成：{output}")


if __name__ == "__main__":
    main()

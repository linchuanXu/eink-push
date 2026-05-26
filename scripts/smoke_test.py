#!/usr/bin/env python3
"""Offline smoke checks for eink-push rendering paths.

This script never pushes to a device. It creates small local fixtures under
output/smoke/ and verifies the card, Markdown book, and EPUB renderers when
their runtime dependencies are available.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMOKE_DIR = ROOT / "output" / "smoke"


def has_python_module(name: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def can_launch_playwright() -> tuple[bool, str]:
    code = """
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, ""
    lines = (result.stderr or result.stdout or "").strip().splitlines()
    for line in lines:
        if "spawn EPERM" in line:
            return False, "spawn EPERM"
        if "Executable doesn't exist" in line:
            return False, "browser executable missing"
    for line in lines:
        if "Error:" in line:
            return False, line.strip()
    return False, lines[-1].strip() if lines else "browser launch failed"


def run_step(label: str, cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
    print(f"[SMOKE] {label}")
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        print(f"[FAIL] {label} failed with exit code {result.returncode}", file=sys.stderr)
        return None
    return result


def has_output_line(result: subprocess.CompletedProcess[str] | None, path: Path) -> bool:
    if result is None:
        return False
    expected = f"OUTPUT:{path}"
    return expected in (result.stdout or "")


def write_fixtures() -> tuple[Path, Path]:
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    html_path = SMOKE_DIR / "smoke-card.html"
    md_path = SMOKE_DIR / "smoke-book.md"

    html_path.write_text(
        """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>eink-push smoke card</title>
  <style>
    body {
      box-sizing: border-box;
      width: 100vw;
      height: 100vh;
      margin: 0;
      padding: 48px;
      overflow: hidden;
      background: #f8f7f2;
      color: #111;
      font-family: sans-serif;
    }
    h1 { margin: 0 0 28px; font-size: 46px; }
    p { font-size: 28px; line-height: 1.5; }
  </style>
</head>
<body>
  <h1>阅星曈 Smoke Test</h1>
  <p>这是一张离线测试卡片，用于验证 HTML 到墨水屏图片格式的渲染链路。</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    md_path.write_text(
        "# 阅星曈 Smoke Test\n\n## 第一章\n\n这是一本离线测试小书，用于验证 Markdown 到 XTC 的渲染链路。\n",
        encoding="utf-8",
    )
    return html_path, md_path


def main() -> int:
    html_path, md_path = write_fixtures()
    failures = 0

    if has_python_module("playwright") and has_python_module("PIL"):
        can_launch, launch_detail = can_launch_playwright()
        if not can_launch:
            print(f"[SKIP] HTML card render cannot launch Playwright Chromium: {launch_detail}")
        else:
            result = run_step(
                "HTML card render",
                [
                    sys.executable,
                    str(ROOT / "scripts" / "render_image.py"),
                    str(html_path),
                    "--preview",
                    "--no-fonts",
                ],
            )
            xth_path = html_path.with_suffix(".xth")
            failures += 0 if (
                result
                and html_path.with_suffix(".preview.png").exists()
                and has_output_line(result, xth_path)
            ) else 1
    else:
        print("[SKIP] HTML card render requires playwright and Pillow.")

    marknative_pkg = ROOT / "node_modules" / "marknative" / "package.json"
    if has_python_module("PIL") and shutil.which("node") and marknative_pkg.exists():
        result = run_step(
            "Markdown book render",
            [
                sys.executable,
                str(ROOT / "scripts" / "render_book.py"),
                str(md_path),
                "--title",
                "阅星曈 Smoke Test",
                "--author",
                "龙虾",
            ],
        )
        xtc_path = md_path.with_suffix(".xtc")
        failures += 0 if result and xtc_path.exists() and has_output_line(result, xtc_path) else 1
    else:
        print("[SKIP] Markdown book render requires Pillow, Node.js, and npm install marknative.")

    if has_python_module("PIL") and has_python_module("ebooklib") and has_python_module("markdown"):
        result = run_step(
            "EPUB render",
            [
                sys.executable,
                str(ROOT / "scripts" / "epub" / "render_book_epub.py"),
                str(md_path),
                "--title",
                "阅星曈 Smoke Test",
                "--author",
                "龙虾",
            ],
        )
        epub_path = md_path.with_suffix(".epub")
        failures += 0 if result and epub_path.exists() and has_output_line(result, epub_path) else 1
    else:
        print("[SKIP] EPUB render requires Pillow, ebooklib, and markdown.")

    if failures:
        print(f"[FAIL] Smoke checks completed with {failures} failure(s).", file=sys.stderr)
        return 1

    print("[OK] Smoke checks completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

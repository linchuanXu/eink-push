#!/usr/bin/env python3
"""
fetch_reading.py — 从星曈云拉取阅读器数据

用法:
    python fetch_reading.py books
        [--keyword 书名关键词] [--format epub|txt]
        [--page N] [--per-page N]

    python fetch_reading.py bookmarks
        [--keyword 完整书名] [--device-id ID] [--format epub|txt]
        [--page N] [--per-page N] [--all]

输出:
    JSON 打印到 stdout，进度信息打印到 stderr。
    AI 助手通过解析 stdout JSON 获取数据。

字段说明（均追加 clean_name）:
    books      → Book[] + pagination
    bookmarks  → Bookmark[] + pagination（已过滤系统占位符「(本章结束)」）

依赖:
    pip install requests
    .credentials.json（由 AI 助手在对话中写入）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests

# ── 复用 push_to_device 的凭证管理与登录 ───────────────────────────────────────
_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from push_to_device import load_credentials, login, BASE_URL, HTTP_TIMEOUT  # noqa: E402


# ─── 书名清洗 ──────────────────────────────────────────────────────────────────

# Z-Library 水印格式（含可选的时间戳后缀变体）：
#   _YYYYMMDD-HHMM
#   _YYYYMMDD-HHMM_YYYY-MM-DD
#   Z-Library 有时还会注入「(Z-Library)」字样
_ZLIBRARY_WATERMARK_RE = re.compile(
    r"_\d{8}-\d{4}(?:_\d{4}-\d{2}-\d{2})?|"   # 时间戳后缀
    r"\s*\(Z-Library\)",                         # Z-Library 括号水印
    re.IGNORECASE,
)


def clean_book_name(raw: str) -> str:
    """
    清洗 book_name 原始文件名，返回可供展示的书名：
    1. 去 Z-Library 时间戳水印（如 `_20260328-1726_2026-03-28`）
    2. 去 Z-Library 括号水印（如 ` (Z-Library)`）
    3. 去文件扩展名（`.epub`、`.txt`）
    """
    name = _ZLIBRARY_WATERMARK_RE.sub("", raw)
    name = re.sub(r"\.(epub|txt)$", "", name, flags=re.IGNORECASE)
    return name.strip()


# ─── API 调用 ──────────────────────────────────────────────────────────────────

def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def fetch_books(
    session: requests.Session,
    token: str,
    *,
    keyword: str = "",
    book_format: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """
    GET /api/v1/reading/my/books
    返回原始响应 dict，每本书追加 clean_name 字段。
    """
    print("[fetch_reading] 正在拉取书架...", file=sys.stderr)
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if keyword:
        params["keyword"] = keyword
    if book_format:
        params["book_format"] = book_format

    res = session.get(
        f"{BASE_URL}/api/v1/reading/my/books",
        headers=_auth_headers(token),
        params=params,
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()

    for book in data.get("books", []):
        book["clean_name"] = clean_book_name(book.get("book_name", ""))

    print(
        f"[fetch_reading] 书架拉取完成，共 {data.get('total', '?')} 本，"
        f"本页 {len(data.get('books', []))} 条。",
        file=sys.stderr,
    )
    return data


def fetch_bookmarks_page(
    session: requests.Session,
    token: str,
    *,
    keyword: str = "",
    device_id: str = "",
    book_format: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """
    GET /api/v1/reading/my/bookmarks（单页）
    自动过滤「(本章结束)」占位符，每条追加 clean_name 字段。
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if keyword:
        params["keyword"] = keyword
    if device_id:
        params["device_id"] = device_id
    if book_format:
        params["book_format"] = book_format

    res = session.get(
        f"{BASE_URL}/api/v1/reading/my/bookmarks",
        headers=_auth_headers(token),
        params=params,
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()

    # 过滤系统占位符书签
    raw_marks = data.get("bookmarks", [])
    filtered = [m for m in raw_marks if m.get("content", "").strip() != "(本章结束)"]
    for mark in filtered:
        mark["clean_name"] = clean_book_name(mark.get("book_name", ""))
    data["bookmarks"] = filtered

    return data


def fetch_bookmarks_all(
    session: requests.Session,
    token: str,
    *,
    keyword: str = "",
    device_id: str = "",
    book_format: str = "",
    per_page: int = 50,
) -> dict[str, Any]:
    """
    自动翻页，拉取所有书签。
    返回结构与单页一致，但 bookmarks 为全量合并列表。
    """
    print("[fetch_reading] 正在拉取全部书签（自动翻页）...", file=sys.stderr)
    all_marks: list[dict] = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        data = fetch_bookmarks_page(
            session,
            token,
            keyword=keyword,
            device_id=device_id,
            book_format=book_format,
            page=page,
            per_page=per_page,
        )
        all_marks.extend(data.get("bookmarks", []))
        total_pages = data.get("pages", 1)
        total = data.get("total", len(all_marks))
        print(
            f"[fetch_reading] 书签第 {page}/{total_pages} 页，"
            f"当前共 {len(all_marks)} 条（服务端总计 {total} 条，过滤前）。",
            file=sys.stderr,
        )
        page += 1

    print(
        f"[fetch_reading] 书签拉取完成，过滤占位符后共 {len(all_marks)} 条。",
        file=sys.stderr,
    )

    return {
        "success": True,
        "bookmarks": all_marks,
        "total": len(all_marks),
        "page": 1,
        "per_page": per_page,
        "pages": 1,
    }


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="从星曈云拉取阅读器数据（书架 / 书签）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── books 子命令 ──────────────────────────────────────────
    p_books = sub.add_parser("books", help="获取书架列表")
    p_books.add_argument("--keyword",  default="", help="按书名模糊搜索")
    p_books.add_argument("--format",   default="", choices=["epub", "txt", ""],
                         help="格式筛选：epub / txt")
    p_books.add_argument("--page",     type=int, default=1)
    p_books.add_argument("--per-page", type=int, default=20, dest="per_page")

    # ── bookmarks 子命令 ──────────────────────────────────────
    p_marks = sub.add_parser("bookmarks", help="获取书签摘录列表")
    p_marks.add_argument("--keyword",   default="",
                         help="按书名过滤（推荐传完整 book_name 精确匹配）")
    p_marks.add_argument("--device-id", default="", dest="device_id",
                         help="按设备 ID 筛选")
    p_marks.add_argument("--format",    default="", choices=["epub", "txt", ""],
                         help="格式筛选：epub / txt")
    p_marks.add_argument("--page",      type=int, default=1)
    p_marks.add_argument("--per-page",  type=int, default=20, dest="per_page")
    p_marks.add_argument("--all",       action="store_true",
                         help="自动翻页拉取全部书签（忽略 --page）")

    args = parser.parse_args()

    try:
        username, password = load_credentials()
        session = requests.Session()
        token = login(session, username, password)

        if args.command == "books":
            result = fetch_books(
                session,
                token,
                keyword=args.keyword,
                book_format=args.format,
                page=args.page,
                per_page=args.per_page,
            )
        else:  # bookmarks
            if args.all:
                result = fetch_bookmarks_all(
                    session,
                    token,
                    keyword=args.keyword,
                    device_id=args.device_id,
                    book_format=args.format,
                    per_page=args.per_page,
                )
            else:
                result = fetch_bookmarks_page(
                    session,
                    token,
                    keyword=args.keyword,
                    device_id=args.device_id,
                    book_format=args.format,
                    page=args.page,
                    per_page=args.per_page,
                )

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        print("\n[!] 已取消。", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"\n✗ 网络超时（>{HTTP_TIMEOUT}s），请检查网络连接后重试。", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到服务器，请检查网络连接。", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status == 401:
            print("\n✗ 账号或密码错误（401）。运行 push_to_device.py --reset-credentials 重新输入。",
                  file=sys.stderr)
        else:
            print(f"\n✗ 服务器返回错误 {status}：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 拉取失败：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

# /// script
# dependencies = ["requests"]
# ///
"""
阅星曈联网搜索工具

调用 /api/v1/search/query，基于阿里云百炼 qwen + enable_search
返回实时联网搜索的 AI 回答与引用来源。

stdout: JSON 响应（供 Agent 解析）
stderr: 进度信息（调试用）

用法：
    python search_query.py "今天 A 股行情如何？"
    python search_query.py "OpenAI 最新发布" --system-prompt "给出详细丰富的资料和数据支持"
"""

DEFAULT_SYSTEM_PROMPT = (
    "请给出详细、丰富的回答，涵盖背景、关键事实、数据和多方观点，"
    "并在结尾列出所有引用来源的标题和链接。"
)

import sys
import argparse
import json
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from xteink_api import BASE_URL, auth_headers, format_http_error, load_credentials, login  # noqa: E402

HTTP_TIMEOUT = 60


def log(msg: str) -> None:
    """进度信息输出到 stderr，不污染 stdout 的 JSON 数据流。"""
    print(msg, file=sys.stderr)


def search(session: requests.Session, token: str, query: str, system_prompt: str = None) -> dict:
    log(f"[2/2] 联网搜索：{query!r}")
    payload = {"query": query}
    if system_prompt:
        payload["system_prompt"] = system_prompt
    res = session.post(
        f"{BASE_URL}/api/v1/search/query",
        json=payload,
        headers=auth_headers(token),
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    log("       ✓ 收到响应")
    return res.json()


def main():
    parser = argparse.ArgumentParser(description="阅星曈联网搜索")
    parser.add_argument("query", help="搜索内容")
    parser.add_argument("--system-prompt", "-s", default=DEFAULT_SYSTEM_PROMPT, help="系统提示词（默认要求详细丰富的回答）")
    args = parser.parse_args()

    if requests is None:
        log("[ERROR] requests 未安装。运行：pip install requests")
        sys.exit(1)

    username, password = load_credentials(error_stream=sys.stderr)
    session = requests.Session()

    try:
        token = login(
            session,
            username,
            password,
            timeout=HTTP_TIMEOUT,
            log=log,
            step_label="[1/2] 登录中...",
        )
        data = search(session, token, args.query, args.system_prompt)
    except requests.exceptions.ConnectionError:
        log(f"[ERROR] 无法连接到 {BASE_URL}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log(f"[ERROR] {format_http_error(e)}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        log("[ERROR] 请求超时（>60s）")
        sys.exit(1)
    except Exception as e:
        log(f"[ERROR] 搜索失败：{e}")
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
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

import json
import sys
import argparse
from pathlib import Path

import requests

BASE_URL = "https://api-prod.xteink.cn"
HTTP_TIMEOUT = 60

_CRED_FILE = Path(__file__).resolve().parent.parent / ".credentials.json"


def load_credentials() -> tuple[str, str]:
    if not _CRED_FILE.exists():
        print(f"[CREDENTIALS_MISSING] 凭证文件不存在：{_CRED_FILE}")
        sys.exit(2)
    try:
        creds = json.loads(_CRED_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[CREDENTIALS_MISSING] 凭证文件损坏（{e}）")
        sys.exit(2)
    username = creds.get("username", "").strip()
    password = creds.get("password", "").strip()
    if not username or not password:
        print(f"[CREDENTIALS_MISSING] 凭证文件缺少 username 或 password")
        sys.exit(2)
    return username, password


def log(msg: str) -> None:
    """进度信息输出到 stderr，不污染 stdout 的 JSON 数据流。"""
    print(msg, file=sys.stderr)


def login(session: requests.Session, username: str, password: str) -> str:
    log("[1/2] 登录中...")
    res = session.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        log(f"[ERROR] 登录失败，响应：{data}")
        sys.exit(1)
    log("       ✓ 登录成功")
    return token


def search(session: requests.Session, token: str, query: str, system_prompt: str = None) -> dict:
    log(f"[2/2] 联网搜索：{query!r}")
    payload = {"query": query}
    if system_prompt:
        payload["system_prompt"] = system_prompt
    res = session.post(
        f"{BASE_URL}/api/v1/search/query",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
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

    username, password = load_credentials()
    session = requests.Session()

    try:
        token = login(session, username, password)
        data = search(session, token, args.query, args.system_prompt)
    except requests.exceptions.ConnectionError:
        log(f"[ERROR] 无法连接到 {BASE_URL}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        log(f"[ERROR] HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        log("[ERROR] 请求超时（>60s）")
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()

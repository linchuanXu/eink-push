#!/usr/bin/env python3
"""Shared Yue Xingtong API helpers for eink-push scripts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    import requests

BASE_URL = "https://api-prod.xteink.cn"
HTTP_TIMEOUT = 30
CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / ".credentials.json"
ENV_CREDENTIAL_PAIRS = (
    ("XTEINK_USERNAME", "XTEINK_PASSWORD"),
    ("YUEXINGTONG_USERNAME", "YUEXINGTONG_PASSWORD"),
)

LogFn = Callable[[str], None]


def credentials_from_env(env: Mapping[str, str] | None = None) -> tuple[str, str] | None:
    """Return username/password from the first complete supported env var pair."""
    values = env if env is not None else os.environ
    for username_key, password_key in ENV_CREDENTIAL_PAIRS:
        username = values.get(username_key, "").strip()
        password = values.get(password_key, "").strip()
        if username and password:
            return username, password
    return None


def env_credentials_status(env: Mapping[str, str] | None = None) -> tuple[str, str]:
    """Return (status, detail) for supported credential env vars."""
    values = env if env is not None else os.environ
    partial_pairs: list[str] = []
    for username_key, password_key in ENV_CREDENTIAL_PAIRS:
        username_present = bool(values.get(username_key, "").strip())
        password_present = bool(values.get(password_key, "").strip())
        if username_present and password_present:
            return "OK", ""
        if username_present or password_present:
            partial_pairs.append(f"{username_key}/{password_key}")
    if partial_pairs:
        return (
            "INVALID",
            "环境变量 " + "、".join(partial_pairs) + " 必须同时设置",
        )
    return "MISSING", "未设置 XTEINK_USERNAME/XTEINK_PASSWORD 环境变量"


def credentials_status(
    cred_file: Path = CREDENTIALS_FILE,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Return (status, detail) for environment or local file credentials."""
    env_status, env_detail = env_credentials_status(env)
    if env_status == "OK":
        return "OK", ""
    if env_status == "INVALID":
        return env_status, env_detail

    if not cred_file.exists():
        return "MISSING", f"凭证文件不存在：{cred_file}"

    try:
        creds = json.loads(cred_file.read_text(encoding="utf-8"))
    except Exception as e:
        return "INVALID", f"凭证文件损坏（{e}）：{cred_file}"

    username = str(creds.get("username", "")).strip()
    password = str(creds.get("password", "")).strip()
    if not username or not password:
        return "INVALID", f"凭证文件缺少 username 或 password：{cred_file}"

    return "OK", ""


def load_credentials(
    cred_file: Path = CREDENTIALS_FILE,
    *,
    error_stream: TextIO | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Load username/password or exit 2 with a machine-recognizable message."""
    env_creds = credentials_from_env(env)
    if env_creds:
        return env_creds

    stream = error_stream or sys.stdout
    status, detail = credentials_status(cred_file, env=env)
    if status != "OK":
        print(f"[CREDENTIALS_{status}] {detail}", file=stream)
        sys.exit(2)

    creds = json.loads(cred_file.read_text(encoding="utf-8"))
    return creds["username"].strip(), creds["password"].strip()


def reset_credentials(cred_file: Path = CREDENTIALS_FILE) -> bool:
    """Delete the credentials file. Returns True when a file was removed."""
    if cred_file.exists():
        cred_file.unlink()
        return True
    return False


def extract_access_token(data: dict[str, Any]) -> str:
    """Extract the access token from known Yue Xingtong login response shapes."""
    token = data.get("access_token") or data.get("token")
    if not token and isinstance(data.get("data"), dict):
        nested = data["data"]
        token = nested.get("access_token") or nested.get("token")
    if not token:
        raise RuntimeError(f"登录失败，响应：{data}")
    return str(token)


def extract_devices(data: Any) -> list[dict[str, Any]]:
    """Extract bound devices from known Yue Xingtong device response shapes."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    candidates = [
        data.get("data"),
        data.get("devices"),
    ]
    if isinstance(data.get("data"), dict):
        candidates.extend([
            data["data"].get("devices"),
            data["data"].get("list"),
            data["data"].get("records"),
        ])

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def normalize_device(device: dict[str, Any]) -> dict[str, str]:
    """Normalize a bound device record to the headers/task shape used by push APIs."""
    device_id = device.get("device_id") or device.get("id")
    if not device_id:
        raise RuntimeError(f"设备响应缺少 device_id/id：{device}")

    device_type = str(device.get("device_type") or device.get("type") or "ESP32C3")
    if device_type not in ("ESP32C3", "ESP32C3_X3"):
        device_type = "ESP32C3"

    return {"id": str(device_id), "type": device_type}


def select_default_device(devices: list[dict[str, Any]]) -> dict[str, str]:
    """Select the currently selected device, or the first device when none is marked."""
    if not devices:
        raise RuntimeError("未找到绑定设备，请先在 App 中绑定设备")
    selected = next((device for device in devices if device.get("selected")), devices[0])
    return normalize_device(selected)


def login(
    session: "requests.Session",
    username: str,
    password: str,
    *,
    timeout: int = HTTP_TIMEOUT,
    log: LogFn | None = print,
    step_label: str = "[1/4] 登录中...",
) -> str:
    """Log in to Yue Xingtong and return an access token."""
    if log:
        log(step_label)
    res = session.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=timeout,
    )
    res.raise_for_status()
    data = res.json()
    token = extract_access_token(data)
    if log:
        log("      ✓ 登录成功")
    return token


def auth_headers(token: str, device: dict | None = None) -> dict[str, str]:
    """Build standard authenticated headers, optionally with device metadata."""
    headers = {"Authorization": f"Bearer {token}"}
    if device:
        headers.update({
            "Device-Id": str(device["id"]),
            "Device-Type": str(device["type"]),
            "Request-Source": "web",
        })
    return headers


def format_http_error(error: Exception) -> str:
    """Return a concise user-facing HTTP error message."""
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", "?")
    text = (getattr(response, "text", "") or "").strip()

    if status == 401:
        return "账号或密码错误（401）。运行 --reset-credentials 或更新环境变量后重新输入。"

    if text:
        if len(text) > 500:
            text = text[:500].rstrip() + "..."
        return f"服务器返回错误 {status}：{text}"

    return f"服务器返回错误 {status}：{error}"

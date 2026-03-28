#!/usr/bin/env python3
"""
星曈云文件推送工具

用法:
    python push_to_device.py <file>
    python push_to_device.py --reset-credentials   # 清除已保存的账号

支持格式：
    .epub             电子书
    .xth              单张高清卡片
    .xtg              单张快刷卡片
    .xtc              多帧快刷图片集
    .xtch             多帧高清图片集
    其他任意格式      通用文件（自动识别 MIME，存入 /Pushed Files）

凭证管理：
    账号密码由 AI 助手在对话中收集后写入 .credentials.json，脚本直接读取，不做交互式询问。
    若凭证文件不存在，脚本退出码 2，由 AI 助手引导用户提供后再重试。
"""

import sys
import os
import json
import hashlib
import argparse
import mimetypes
import requests
from pathlib import Path

BASE_URL = "https://api-prod.xteink.cn"
HTTP_TIMEOUT = 30  # 所有 HTTP 请求统一超时（秒）

# 凭证文件保存在脚本同级父目录（eink-push/.credentials.json），不进 git
_CRED_FILE = Path(__file__).resolve().parent.parent / ".credentials.json"


# ─── 凭证管理 ─────────────────────────────────────────────────────────────────

def load_credentials() -> tuple[str, str]:
    """
    从 .credentials.json 读取账号密码。
    文件不存在或字段缺失时打印 [CREDENTIALS_MISSING] 并以退出码 2 退出，
    由外部调用方（AI 助手）在对话中收集凭证后重试，不做交互式 input()。
    """
    if not _CRED_FILE.exists():
        print(f"[CREDENTIALS_MISSING] 凭证文件不存在：{_CRED_FILE}")
        sys.exit(2)

    try:
        creds = json.loads(_CRED_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[CREDENTIALS_MISSING] 凭证文件损坏（{e}）：{_CRED_FILE}")
        sys.exit(2)

    username = creds.get("username", "").strip()
    password = creds.get("password", "").strip()

    if not username or not password:
        print(f"[CREDENTIALS_MISSING] 凭证文件缺少 username 或 password：{_CRED_FILE}")
        sys.exit(2)

    return username, password


def reset_credentials() -> None:
    """删除凭证文件，AI 助手下次推送前会重新向用户收集账号密码。"""
    if _CRED_FILE.exists():
        _CRED_FILE.unlink()
        print("[✓] 已清除凭证，下次推送时 AI 助手会重新向你确认账号密码。")
    else:
        print("[!] 未找到凭证文件，无需清除。")


# ─── 文件类型映射 ──────────────────────────────────────────────────────────────

MIME_MAP = {
    ".epub": "application/epub+zip",
    ".xth":  "application/octet-stream",
    ".xtg":  "application/octet-stream",
    ".xtc":  "application/octet-stream",
    ".xtch": "application/octet-stream",
}

PREFIX_MAP = {
    ".epub": "uploads/book",
    ".xth":  "uploads/image",
    ".xtg":  "uploads/image",
    ".xtc":  "uploads/image",
    ".xtch": "uploads/image",
}

FOLDER_MAP = {
    ".epub": "/Pushed Books",
    ".xth":  "/Pushed Images",
    ".xtg":  "/Pushed Images",
    ".xtc":  "/Pushed Images",
    ".xtch": "/Pushed Images",
}


def _resolve_file_meta(ext: str) -> tuple[str, str, str]:
    """
    返回 (content_type, prefix, folder)。
    已知格式走固定映射；其余格式用 mimetypes 自动识别 MIME，
    统一上传到 uploads/file 前缀和 /Pushed Files 目录。
    """
    if ext in MIME_MAP:
        return MIME_MAP[ext], PREFIX_MAP[ext], FOLDER_MAP[ext]

    guessed, _ = mimetypes.guess_type(f"file{ext}")
    content_type = guessed or "application/octet-stream"
    return content_type, "uploads/file", "/Pushed Files"


# ─── API 调用 ─────────────────────────────────────────────────────────────────

def md5_of_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def login(session: requests.Session, username: str, password: str) -> str:
    print("[1/4] 登录中...")
    res = session.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise RuntimeError(f"登录失败，响应：{data}")
    print("      ✓ 登录成功")
    return token


def get_default_device(session: requests.Session, token: str) -> dict:
    print("[2/4] 获取绑定设备...")
    headers = {"Authorization": f"Bearer {token}"}
    res = session.get(
        f"{BASE_URL}/api/v1/device/binding",
        headers=headers,
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()

    devices = data if isinstance(data, list) else (data.get("data") or data.get("devices") or [])
    if not devices:
        raise RuntimeError("未找到绑定设备，请先在 App 中绑定设备")

    selected = next((d for d in devices if d.get("selected")), devices[0])
    device_id = str(selected.get("device_id") or selected.get("id"))
    device_type = selected.get("device_type", "ESP32C3")
    if device_type not in ("ESP32C3", "ESP32C3_X3"):
        device_type = "ESP32C3"

    print(f"      ✓ 设备 ID={device_id}  类型={device_type}")
    return {"id": device_id, "type": device_type}


def upload_file(session: requests.Session, token: str, device: dict,
                file_data: bytes, filename: str, content_type: str,
                file_md5: str, file_size: int, prefix: str) -> str:
    """上传文件到 OSS，返回 download_url。"""
    auth_headers = {
        "Authorization":  f"Bearer {token}",
        "Device-Id":      device["id"],
        "Device-Type":    device["type"],
        "Request-Source": "web",
    }

    print("[3/4] 上传文件...")
    print("      → 获取上传签名")
    sig_res = session.post(
        f"{BASE_URL}/api/v1/upload/signature",
        json={
            "filename":     filename,
            "content_type": content_type,
            "file_md5":     file_md5,
            "file_size":    file_size,
            "prefix":       prefix,
        },
        headers=auth_headers,
        timeout=HTTP_TIMEOUT,
    )
    sig_res.raise_for_status()
    sign = sig_res.json()

    if not sign.get("success", True) and not sign.get("download_url"):
        raise RuntimeError(f"获取上传签名失败：{sign}")

    # 秒传：服务端已有该文件
    if sign.get("instant_upload"):
        print("      ✓ 秒传命中，跳过 OSS 上传")
        return sign["download_url"]

    print("      → 上传到 OSS")
    oss_res = requests.post(
        sign["host"],
        files={
            "key":            (None, sign.get("key", "")),
            "policy":         (None, sign.get("policy", "")),
            "OSSAccessKeyId": (None, sign.get("access_key_id", "")),
            "signature":      (None, sign.get("signature", "")),
            "Content-Type":   (None, sign["content_type"]),
            "file":           (filename, file_data, sign["content_type"]),
        },
        timeout=HTTP_TIMEOUT,
    )
    if oss_res.text and "<Error>" in oss_res.text:
        raise RuntimeError(f"OSS 上传失败：{oss_res.text}")
    print("      ✓ OSS 上传完成")

    # 上传回调（失败不影响后续流程）
    try:
        session.post(
            f"{BASE_URL}/api/v1/upload/callback",
            json={
                "oss_key":      sign.get("key", ""),
                "filename":     filename,
                "file_size":    file_size,
                "file_md5":     file_md5,
                "content_type": sign["content_type"],
            },
            headers=auth_headers,
            timeout=HTTP_TIMEOUT,
        )
    except Exception as e:
        print(f"      ! 上传回调失败（不影响结果）：{e}")

    return sign["download_url"]


def push_to_device(session: requests.Session, token: str, device: dict,
                   download_url: str, save_path: str) -> None:
    print("[4/4] 推送到设备...")
    headers = {
        "Authorization":  f"Bearer {token}",
        "Device-Id":      device["id"],
        "Device-Type":    device["type"],
        "Request-Source": "web",
    }
    res = session.post(
        f"{BASE_URL}/api/v1/device/tasks",
        json={
            "device_id": device["id"],
            "file_url":  download_url,
            "save_path": save_path,
        },
        headers=headers,
        timeout=HTTP_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    task_id = (data.get("task") or {}).get("task_id", "")
    print(f"      ✓ 推送成功  任务 ID={task_id}")


# ─── 主入口 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="星曈云文件推送工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", nargs="?", help="要推送的文件（支持任意格式；.epub/.xth/.xtg/.xtc/.xtch 走专属路径，其余存入 /Pushed Files）")
    parser.add_argument(
        "--reset-credentials",
        action="store_true",
        help="清除已保存的账号密码，下次运行时重新输入",
    )
    args = parser.parse_args()

    # ── 重置凭证模式 ───────────────────────────────────────────
    if args.reset_credentials:
        reset_credentials()
        return

    # ── 普通推送模式 ───────────────────────────────────────────
    if not args.file:
        parser.print_help()
        sys.exit(1)

    try:
        file_path = args.file
        if not os.path.isfile(file_path):
            print(f"✗ 文件不存在：{file_path}")
            sys.exit(1)

        ext = os.path.splitext(file_path)[1].lower()
        content_type, prefix, folder = _resolve_file_meta(ext)

        # 凭证优先确认，避免读完大文件才发现账号有问题
        username, password = load_credentials()
        filename  = os.path.basename(file_path)
        save_path = f"{folder}/{filename}"

        with open(file_path, "rb") as f:
            file_data = f.read()

        file_md5  = md5_of_bytes(file_data)
        file_size = len(file_data)

        print(f"文件：{filename}  大小：{file_size:,} 字节  MD5：{file_md5}\n")

        session = requests.Session()
        token   = login(session, username, password)
        device  = get_default_device(session, token)
        dl_url  = upload_file(session, token, device,
                              file_data, filename, content_type,
                              file_md5, file_size, prefix)
        push_to_device(session, token, device, dl_url, save_path)

        print(f"\n完成！设备保存路径：{save_path}")
        print(f"OUTPUT:{save_path}")

    except KeyboardInterrupt:
        print("\n[!] 已取消。")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"\n✗ 网络超时（>{HTTP_TIMEOUT}s），请检查网络连接后重试。")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到服务器，请检查网络连接。")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        if status == 401:
            print(f"\n✗ 账号或密码错误（401）。运行 --reset-credentials 重新输入。")
        else:
            print(f"\n✗ 服务器返回错误 {status}：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 推送失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

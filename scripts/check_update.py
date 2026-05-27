#!/usr/bin/env python3
"""Check whether the installed eink-push Skill is behind the GitHub version."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILL_FILE = ROOT / "SKILL.md"
LATEST_SKILL_URL = (
    "https://raw.githubusercontent.com/linchuanXu/eink-push/master/SKILL.md"
)

OK = "OK"
UPDATE = "UPDATE"
UNKNOWN = "UNKNOWN"
FAIL = "FAIL"


@dataclass
class UpdateCheck:
    status: str
    current_version: str
    latest_version: str | None = None
    detail: str = ""
    update_commands: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "detail": self.detail,
            "update_commands": self.update_commands or [],
        }


def parse_version_tuple(version: str) -> tuple[int, ...] | None:
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", version.strip()):
        return None
    return tuple(int(part) for part in version.strip().split("."))


def compare_versions(current: str, latest: str) -> int:
    """Return -1 when current < latest, 0 when equal, 1 when current > latest."""
    cur = parse_version_tuple(current)
    new = parse_version_tuple(latest)
    if cur is None or new is None:
        return (current > latest) - (current < latest)

    width = max(len(cur), len(new))
    padded_cur = cur + (0,) * (width - len(cur))
    padded_new = new + (0,) * (width - len(new))
    return (padded_cur > padded_new) - (padded_cur < padded_new)


def extract_skill_version(text: str) -> str | None:
    """Extract `version: x.y.z` from the top YAML frontmatter."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    for line in parts[1].splitlines():
        match = re.match(r"^\s*version\s*:\s*['\"]?([^'\"\s]+)", line)
        if match:
            return match.group(1).strip()
    return None


def read_local_version(skill_file: Path = SKILL_FILE) -> str | None:
    if not skill_file.exists():
        return None
    return extract_skill_version(skill_file.read_text(encoding="utf-8"))


def fetch_latest_version(url: str = LATEST_SKILL_URL, timeout: int = 8) -> str | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "eink-push-update-check/1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(256 * 1024)
    return extract_skill_version(data.decode("utf-8", errors="replace"))


def default_update_commands() -> list[str]:
    return [
        "更新技能 https://github.com/linchuanXu/eink-push",
        "或在本地仓库运行：git pull && python scripts/install_skill.py --apply",
    ]


def check_update(
    *,
    skill_file: Path = SKILL_FILE,
    latest_url: str = LATEST_SKILL_URL,
    timeout: int = 8,
) -> UpdateCheck:
    current = read_local_version(skill_file)
    if not current:
        return UpdateCheck(
            FAIL,
            current_version="",
            detail=f"无法从 {skill_file} 读取 version 字段",
        )

    try:
        latest = fetch_latest_version(latest_url, timeout=timeout)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return UpdateCheck(
            UNKNOWN,
            current_version=current,
            detail=f"无法检查 GitHub 最新版本：{exc}",
        )

    if not latest:
        return UpdateCheck(
            UNKNOWN,
            current_version=current,
            detail="远端 SKILL.md 未声明 version 字段",
        )

    cmp = compare_versions(current, latest)
    if cmp < 0:
        return UpdateCheck(
            UPDATE,
            current_version=current,
            latest_version=latest,
            detail=f"当前版本 {current} 落后于最新版本 {latest}",
            update_commands=default_update_commands(),
        )
    if cmp > 0:
        return UpdateCheck(
            OK,
            current_version=current,
            latest_version=latest,
            detail=f"当前版本 {current} 高于远端版本 {latest}",
        )
    return UpdateCheck(
        OK,
        current_version=current,
        latest_version=latest,
        detail=f"当前已是最新版本 {current}",
    )


def print_human(result: UpdateCheck) -> None:
    print(f"[{result.status}] eink-push version: {result.detail}")
    for command in result.update_commands or []:
        print(f"      update: {command}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether eink-push is up to date.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--timeout", type=int, default=8, help="Network timeout in seconds.")
    args = parser.parse_args()

    result = check_update(timeout=args.timeout)
    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(result)

    return 1 if result.status == FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())

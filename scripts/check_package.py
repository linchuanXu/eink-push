#!/usr/bin/env python3
"""Audit tracked and unignored files for a clean eink-push Skill package boundary."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PACKAGE_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "scripts/render_image.py",
    "scripts/render_book.py",
    "scripts/epub/render_book_epub.py",
    "scripts/push_to_device.py",
    "scripts/fetch_reading.py",
    "scripts/search_query.py",
    "scripts/check_environment.py",
    "scripts/xteink_api.py",
    "references/AGENT-WORKFLOWS.md",
    "references/SETUP.md",
    "references/TROUBLESHOOTING.md",
    "assets/templates/base.html",
)

RUNTIME_PATTERNS = (
    "SKILL.md",
    "agents/**",
    "assets/**",
    "references/**",
    "scripts/**",
    "requirements.txt",
    "package.json",
    "package-lock.json",
)

REPO_ONLY_PATTERNS = (
    ".cursor/**",
    ".gitattributes",
    ".gitignore",
    "README.md",
    "landing.html",
    "landing-v2.html",
    "references/MANUAL-TEST-CHECKLIST.md",
    "references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md",
    "scripts/check_installation.py",
    "scripts/check_package.py",
    "scripts/install_skill.py",
    "scripts/smoke_test.py",
    "scripts/verify.py",
    "tests/**",
    "output/.gitkeep",
)

FORBIDDEN_TRACKED_PATTERNS = (
    ".credentials.json",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    ".codegraph/**",
    ".venv/**",
    "venv/**",
    "node_modules/**",
    "output/**",
    "skill-refs/**",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "references/framework-samples/*.xth",
)
FORBIDDEN_EXCEPTIONS = (
    "output/.gitkeep",
)

LOCAL_SCAN_EXCLUDE_DIRS = {
    ".git",
    ".codegraph",
    ".venv",
    "venv",
    "node_modules",
    "output",
    "skill-refs",
    "__pycache__",
}


@dataclass
class PackageAudit:
    tracked_files: list[str]
    missing_required: list[str]
    forbidden_tracked: list[str]
    uncategorized_tracked: list[str]
    runtime_files: list[str]
    repo_only_files: list[str]

    @property
    def status(self) -> str:
        if self.missing_required or self.forbidden_tracked or self.uncategorized_tracked:
            return "FAIL"
        return "OK"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidate_count": len(self.tracked_files),
            "runtime_count": len(self.runtime_files),
            "repo_only_count": len(self.repo_only_files),
            "missing_required": self.missing_required,
            "forbidden_tracked": self.forbidden_tracked,
            "uncategorized_tracked": self.uncategorized_tracked,
            "runtime_files": self.runtime_files,
            "repo_only_files": self.repo_only_files,
        }


def normalize_path(path: str | Path) -> str:
    normalized = Path(path).as_posix()
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def git_tracked_files(root: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).decode("utf-8", errors="replace"))
    return sorted(
        normalize_path(item.decode("utf-8", errors="replace"))
        for item in result.stdout.split(b"\0")
        if item
    )


def fallback_scan_files(root: Path = ROOT) -> list[str]:
    files: list[str] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in LOCAL_SCAN_EXCLUDE_DIRS:
                    stack.append(child)
            elif child.is_file():
                files.append(normalize_path(child.relative_to(root)))
    return sorted(files)


def collect_package_files(root: Path = ROOT) -> list[str]:
    try:
        return git_tracked_files(root)
    except Exception:
        return fallback_scan_files(root)


def audit_package(files: list[str]) -> PackageAudit:
    tracked = sorted({normalize_path(path) for path in files})
    repo_only_files = [path for path in tracked if matches_any(path, REPO_ONLY_PATTERNS)]
    runtime_files = [
        path
        for path in tracked
        if matches_any(path, RUNTIME_PATTERNS) and path not in repo_only_files
    ]
    categorized = set(runtime_files) | set(repo_only_files)
    return PackageAudit(
        tracked_files=tracked,
        missing_required=[path for path in REQUIRED_PACKAGE_FILES if path not in tracked],
        forbidden_tracked=[
            path
            for path in tracked
            if matches_any(path, FORBIDDEN_TRACKED_PATTERNS)
            and not matches_any(path, FORBIDDEN_EXCEPTIONS)
        ],
        uncategorized_tracked=[path for path in tracked if path not in categorized],
        runtime_files=runtime_files,
        repo_only_files=repo_only_files,
    )


def print_human(audit: PackageAudit) -> None:
    print(f"[{audit.status}] Skill package contents audit")
    print(f"Package candidate files: {len(audit.tracked_files)}")
    print(f"Runtime package files: {len(audit.runtime_files)}")
    print(f"Repository-only files: {len(audit.repo_only_files)}")
    for path in audit.missing_required:
        print(f"[MISSING] {path}")
    for path in audit.forbidden_tracked:
        print(f"[FORBIDDEN] {path}")
    for path in audit.uncategorized_tracked:
        print(f"[UNCATEGORIZED] {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit tracked files for Skill package cleanliness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    audit = audit_package(collect_package_files())
    if args.json:
        print(json.dumps(audit.as_dict(), ensure_ascii=False, indent=2))
    else:
        print_human(audit)
    return 1 if audit.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

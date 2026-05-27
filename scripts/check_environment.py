#!/usr/bin/env python3
"""Preflight local runtime dependencies for eink-push.

This script does not read credentials, connect to Yue Xingtong, or push files.
It only checks local tools and packages needed by the render and verification
paths, then prints actionable install commands when something is missing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = str(ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from check_update import check_update, default_update_commands  # noqa: E402
MIN_PYTHON = (3, 10, 0)
MIN_NODE = (18, 0, 0)

OK = "OK"
MISSING = "MISSING"
FAIL = "FAIL"
UPDATE = "UPDATE"
UNKNOWN = "UNKNOWN"


@dataclass
class CheckResult:
    key: str
    label: str
    status: str
    detail: str
    fix_commands: list[str] = field(default_factory=list)
    required: bool = True

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "detail": self.detail,
            "fix_commands": self.fix_commands,
            "required": self.required,
        }


def parse_semver(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def version_at_least(current: tuple[int, int, int], minimum: tuple[int, int, int]) -> bool:
    return current >= minimum


def run_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def check_python_version() -> CheckResult:
    current = sys.version_info[:3]
    if version_at_least(current, MIN_PYTHON):
        return CheckResult(
            "python",
            "Python",
            OK,
            f"{current[0]}.{current[1]}.{current[2]}",
        )
    return CheckResult(
        "python",
        "Python",
        FAIL,
        f"{current[0]}.{current[1]}.{current[2]} found; Python >= 3.10 is required",
        ["Install Python >= 3.10 and rerun this command from the Skill directory."],
    )


def check_python_module(import_name: str, package_name: str) -> CheckResult:
    if importlib.util.find_spec(import_name):
        return CheckResult(import_name, package_name, OK, "installed")
    return CheckResult(
        import_name,
        package_name,
        MISSING,
        "not importable",
        ["python -m pip install -r requirements.txt"],
    )


def check_playwright_chromium() -> CheckResult:
    if not importlib.util.find_spec("playwright"):
        return CheckResult(
            "playwright-chromium",
            "Playwright Chromium",
            MISSING,
            "playwright package is not installed",
            ["python -m pip install -r requirements.txt", "python -m playwright install chromium"],
        )

    code = """
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    browser.close()
"""
    try:
        result = run_command([sys.executable, "-c", code], timeout=45)
    except subprocess.TimeoutExpired:
        return CheckResult(
            "playwright-chromium",
            "Playwright Chromium",
            FAIL,
            "browser launch timed out",
            ["python -m playwright install chromium"],
        )
    if result.returncode == 0:
        return CheckResult("playwright-chromium", "Playwright Chromium", OK, "launch OK")

    output = (result.stderr or result.stdout or "").strip()
    if "Executable doesn't exist" in output:
        detail = "browser executable missing"
        fixes = ["python -m playwright install chromium"]
    elif "spawn EPERM" in output:
        detail = "current environment blocked browser launch with spawn EPERM"
        fixes = ["Rerun in a local terminal that allows launching Playwright Chromium."]
    else:
        detail = output.splitlines()[-1] if output else "browser launch failed"
        fixes = ["python -m playwright install chromium"]

    return CheckResult("playwright-chromium", "Playwright Chromium", FAIL, detail, fixes)


def check_node() -> CheckResult:
    if not shutil.which("node"):
        return CheckResult(
            "node",
            "Node.js",
            MISSING,
            "node executable not found; Node.js >= 18 is required for Markdown book rendering",
            ["Install Node.js >= 18 from https://nodejs.org/"],
        )

    result = run_command(["node", "--version"])
    version_text = (result.stdout or result.stderr or "").strip()
    version = parse_semver(version_text)
    if result.returncode == 0 and version and version_at_least(version, MIN_NODE):
        return CheckResult("node", "Node.js", OK, version_text)

    detail = version_text or "unable to read node version"
    return CheckResult(
        "node",
        "Node.js",
        FAIL,
        f"{detail}; Node.js >= 18 is required",
        ["Install Node.js >= 18 from https://nodejs.org/"],
    )


def check_npm() -> CheckResult:
    if shutil.which("npm"):
        return CheckResult("npm", "npm", OK, "available")
    return CheckResult(
        "npm",
        "npm",
        MISSING,
        "npm executable not found; required to install marknative",
        ["Install Node.js >= 18 from https://nodejs.org/"],
    )


def check_marknative() -> CheckResult:
    package_json = ROOT / "node_modules" / "marknative" / "package.json"
    if package_json.exists():
        return CheckResult("marknative", "marknative", OK, str(package_json.relative_to(ROOT)))
    return CheckResult(
        "marknative",
        "marknative",
        MISSING,
        "node_modules/marknative is missing in this Skill directory",
        ["npm install marknative"],
    )


def check_skill_update() -> CheckResult:
    result = check_update(timeout=5)
    if result.status == UPDATE:
        return CheckResult(
            "skill-update",
            "eink-push Skill",
            UPDATE,
            result.detail,
            result.update_commands or default_update_commands(),
            required=False,
        )
    if result.status == OK:
        return CheckResult("skill-update", "eink-push Skill", OK, result.detail, required=False)
    return CheckResult(
        "skill-update",
        "eink-push Skill",
        UNKNOWN,
        result.detail,
        required=False,
    )


def collect_checks() -> list[CheckResult]:
    checks = [
        check_skill_update(),
        check_python_version(),
        check_python_module("requests", "requests"),
        check_python_module("PIL", "Pillow"),
        check_python_module("playwright", "playwright"),
        check_python_module("ebooklib", "ebooklib"),
        check_python_module("markdown", "markdown"),
        check_python_module("yaml", "PyYAML"),
        check_playwright_chromium(),
        check_node(),
        check_npm(),
        check_marknative(),
    ]
    return checks


def has_blocking_failures(checks: list[CheckResult]) -> bool:
    return any(check.required and check.status in {MISSING, FAIL} for check in checks)


def print_human(checks: list[CheckResult]) -> None:
    for check in checks:
        print(f"[{check.status}] {check.label}: {check.detail}")
        if check.status != OK and check.fix_commands:
            for command in check.fix_commands:
                print(f"      fix: {command}")

    if has_blocking_failures(checks):
        print("[FAIL] Environment preflight found missing or broken dependencies.")
    else:
        print("[OK] Environment preflight passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local dependencies for eink-push.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    checks = collect_checks()
    if args.json:
        print(json.dumps({"checks": [check.as_dict() for check in checks]}, ensure_ascii=False, indent=2))
    else:
        print_human(checks)

    return 1 if has_blocking_failures(checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())

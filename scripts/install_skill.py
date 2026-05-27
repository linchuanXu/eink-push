#!/usr/bin/env python3
"""Install or sync the runtime eink-push Skill files into a local Skill root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from check_package import ROOT, audit_package, collect_package_files, matches_any, normalize_path  # noqa: E402

SKILL_NAME = "eink-push"
PROTECTED_TARGET_PATTERNS = (
    ".credentials.json",
    "node_modules/**",
    "output/**",
    ".venv/**",
    "venv/**",
    "__pycache__/**",
    "scripts/**/__pycache__/**",
    "*.pyc",
    "*.pyo",
    "*.pyd",
)


@dataclass
class InstallPlan:
    target: Path
    copy_files: list[str]
    update_files: list[str]
    unchanged_files: list[str]
    extra_files: list[str]
    audit_issues: list[str]

    @property
    def status(self) -> str:
        return "FAIL" if self.audit_issues else "OK"

    @property
    def will_change(self) -> bool:
        return bool(self.copy_files or self.update_files)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "target": str(self.target),
            "copy_files": self.copy_files,
            "update_files": self.update_files,
            "unchanged_files": self.unchanged_files,
            "extra_files": self.extra_files,
            "audit_issues": self.audit_issues,
        }


def default_target() -> Path:
    code_home = os.environ.get("CODEX_HOME")
    base = Path(code_home) if code_home else Path.home() / ".codex"
    return base / "skills" / SKILL_NAME


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_file():
            files.append(normalize_path(path.relative_to(root)))
    return sorted(files)


def is_protected_target_extra(path: str) -> bool:
    return matches_any(path, PROTECTED_TARGET_PATTERNS)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_target_path(source_root: Path, target: Path) -> list[str]:
    """Return safety issues for install targets that could pollute the source tree."""
    issues: list[str] = []
    if target.name != SKILL_NAME:
        issues.append(f"target directory should be named {SKILL_NAME}: {target}")
    if is_relative_to(target, source_root):
        issues.append(f"target must not be inside the source repository: {target}")
    if is_relative_to(source_root, target):
        issues.append(f"target must not contain the source repository: {target}")
    return issues


def build_install_plan(source_root: Path, target: Path) -> InstallPlan:
    audit = audit_package(collect_package_files(source_root))
    audit_issues = [
        *validate_target_path(source_root, target),
        *[f"missing required package file: {path}" for path in audit.missing_required],
        *[f"forbidden package file: {path}" for path in audit.forbidden_tracked],
        *[f"uncategorized package file: {path}" for path in audit.uncategorized_tracked],
    ]
    if audit_issues:
        return InstallPlan(target, [], [], [], [], audit_issues)

    copy_files: list[str] = []
    update_files: list[str] = []
    unchanged_files: list[str] = []

    for rel_path in audit.runtime_files:
        source = source_root / rel_path
        destination = target / rel_path
        if not destination.exists():
            copy_files.append(rel_path)
        elif file_sha256(source) == file_sha256(destination):
            unchanged_files.append(rel_path)
        else:
            update_files.append(rel_path)

    runtime_set = set(audit.runtime_files)
    extra_files = [
        path
        for path in list_files(target)
        if path not in runtime_set and not is_protected_target_extra(path)
    ]

    return InstallPlan(
        target=target,
        copy_files=copy_files,
        update_files=update_files,
        unchanged_files=unchanged_files,
        extra_files=extra_files,
        audit_issues=[],
    )


def apply_install_plan(source_root: Path, plan: InstallPlan) -> None:
    if plan.status != "OK":
        raise RuntimeError("cannot apply a failed install plan")

    for rel_path in [*plan.copy_files, *plan.update_files]:
        source = source_root / rel_path
        destination = plan.target / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def print_human(plan: InstallPlan, *, applied: bool, applied_plan: InstallPlan | None = None) -> None:
    mode = "applied" if applied else "dry-run"
    print(f"[{plan.status}] eink-push install plan ({mode})")
    print(f"Target: {plan.target}")
    if plan.audit_issues:
        for issue in plan.audit_issues:
            print(f"[ISSUE] {issue}")
        return
    if applied_plan:
        print(
            f"Applied: {len(applied_plan.copy_files)} copied, "
            f"{len(applied_plan.update_files)} updated"
        )
    print(f"Copy: {len(plan.copy_files)}")
    print(f"Update: {len(plan.update_files)}")
    print(f"Unchanged: {len(plan.unchanged_files)}")
    print(f"Extra target files: {len(plan.extra_files)}")
    for path in plan.copy_files:
        print(f"[COPY] {path}")
    for path in plan.update_files:
        print(f"[UPDATE] {path}")
    for path in plan.extra_files:
        print(f"[EXTRA] {path}")
    if not applied:
        print("Run again with --apply to copy/update runtime files.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install/sync eink-push runtime Skill files.")
    parser.add_argument("--target", type=Path, default=default_target(), help="Target Skill directory.")
    parser.add_argument("--apply", action="store_true", help="Copy/update files. Default is dry-run.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    plan = build_install_plan(ROOT, args.target)
    applied_plan: InstallPlan | None = None
    if args.apply and plan.status == "OK":
        applied_plan = plan
        apply_install_plan(ROOT, plan)
        plan = build_install_plan(ROOT, args.target)

    if args.json:
        data = plan.as_dict()
        data["applied"] = args.apply and plan.status == "OK"
        if applied_plan:
            data["applied_copy_files"] = applied_plan.copy_files
            data["applied_update_files"] = applied_plan.update_files
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_human(plan, applied=args.apply and plan.status == "OK", applied_plan=applied_plan)

    return 1 if plan.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

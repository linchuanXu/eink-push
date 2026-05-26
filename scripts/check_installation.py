#!/usr/bin/env python3
"""Audit local Skill installation roots for eink-push duplicates or drift."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "eink-push"
DEFAULT_SCAN_DEPTH = 3


@dataclass
class SkillRecord:
    path: Path
    name: str
    description: str
    skill_md_sha256: str
    openai_yaml_sha256: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def is_current_repo(self) -> bool:
        return same_path(self.path, ROOT)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "name": self.name,
            "description_chars": len(self.description),
            "description_estimated_tokens": estimate_prompt_tokens(self.description),
            "skill_md_sha256": self.skill_md_sha256,
            "openai_yaml_sha256": self.openai_yaml_sha256,
            "is_current_repo": self.is_current_repo,
            "errors": self.errors,
        }


def same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return a.absolute() == b.absolute()


def estimate_prompt_tokens(text: str) -> int:
    return (len(text.encode("utf-8")) + 3) // 4


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_skill_frontmatter(skill_md: Path) -> tuple[dict[str, Any], list[str]]:
    errors = []
    try:
        raw = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        return {}, [f"cannot read SKILL.md: {e}"]

    if not raw.startswith("---\n"):
        return {}, ["SKILL.md frontmatter missing"]

    match = re.match(r"^---\n(.*?)\n---", raw, re.DOTALL)
    if not match:
        return {}, ["SKILL.md frontmatter closing marker missing"]

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except Exception as e:
        return {}, [f"cannot parse frontmatter: {e}"]

    if not isinstance(frontmatter, dict):
        return {}, ["SKILL.md frontmatter is not a mapping"]

    return frontmatter, errors


def read_skill_record(skill_dir: Path) -> SkillRecord:
    skill_md = skill_dir / "SKILL.md"
    frontmatter, errors = parse_skill_frontmatter(skill_md)
    openai_yaml = skill_dir / "agents" / "openai.yaml"
    return SkillRecord(
        path=skill_dir,
        name=str(frontmatter.get("name", "")).strip(),
        description=str(frontmatter.get("description", "")).strip(),
        skill_md_sha256=file_sha256(skill_md) if skill_md.exists() else "",
        openai_yaml_sha256=file_sha256(openai_yaml) if openai_yaml.exists() else None,
        errors=errors,
    )


def default_skill_roots() -> list[Path]:
    roots = [ROOT]
    home = Path.home()
    code_home = os.environ.get("CODEX_HOME")
    if code_home:
        roots.append(Path(code_home) / "skills")
    roots.extend([
        home / ".codex" / "skills",
        home / ".agents" / "skills",
    ])
    return unique_existing_dirs(roots)


def unique_existing_dirs(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_dir():
            continue
        if any(same_path(path, existing) for existing in unique):
            continue
        unique.append(path)
    return unique


def iter_skill_dirs(root: Path, max_depth: int = DEFAULT_SCAN_DEPTH) -> list[Path]:
    skill_dirs = []
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if (current / "SKILL.md").exists():
            skill_dirs.append(current)
            continue
        if depth >= max_depth:
            continue
        try:
            children = [child for child in current.iterdir() if child.is_dir()]
        except OSError:
            continue
        stack.extend((child, depth + 1) for child in children)
    return sorted(skill_dirs)


def collect_records(roots: list[Path]) -> list[SkillRecord]:
    records = []
    seen: list[Path] = []
    for root in roots:
        for skill_dir in iter_skill_dirs(root):
            if any(same_path(skill_dir, existing) for existing in seen):
                continue
            seen.append(skill_dir)
            record = read_skill_record(skill_dir)
            if record.name == SKILL_NAME or SKILL_NAME in skill_dir.name:
                records.append(record)
    return sorted(records, key=lambda record: str(record.path).lower())


def audit(records: list[SkillRecord], require_installed: bool = False) -> tuple[str, list[str]]:
    issues = []
    installed = [record for record in records if not record.is_current_repo]

    if require_installed and not installed:
        issues.append("no installed eink-push copy found outside the current source repo")

    if len(installed) > 1:
        issues.append("multiple installed eink-push copies found")

    current = next((record for record in records if record.is_current_repo), None)
    if current:
        for record in installed:
            if record.skill_md_sha256 != current.skill_md_sha256:
                issues.append(f"installed SKILL.md differs from source: {record.path}")
            if record.openai_yaml_sha256 != current.openai_yaml_sha256:
                issues.append(f"installed agents/openai.yaml differs from source: {record.path}")

    for record in records:
        issues.extend(f"{record.path}: {error}" for error in record.errors)

    return ("FAIL" if issues else "OK"), issues


def print_human(records: list[SkillRecord], status: str, issues: list[str]) -> None:
    print(f"[{status}] eink-push installation audit")
    if not records:
        print("No eink-push SKILL.md found in scanned roots.")
    for record in records:
        location = "source repo" if record.is_current_repo else "installed copy"
        print(f"- {record.path} ({location})")
        print(
            "  "
            f"description: {len(record.description)} chars, "
            f"~{estimate_prompt_tokens(record.description)} tokens"
        )
    for issue in issues:
        print(f"[ISSUE] {issue}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local eink-push Skill installations.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="Fail when no installed copy is found outside the current source repo.",
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Extra Skill root to scan. Can be passed multiple times.",
    )
    args = parser.parse_args()

    roots = unique_existing_dirs(default_skill_roots() + [Path(root) for root in args.root])
    records = collect_records(roots)
    status, issues = audit(records, require_installed=args.require_installed)

    if args.json:
        print(json.dumps({
            "status": status,
            "roots": [str(root) for root in roots],
            "records": [record.as_dict() for record in records],
            "issues": issues,
        }, ensure_ascii=False, indent=2))
    else:
        print_human(records, status, issues)

    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the offline verification suite for eink-push."""

from __future__ import annotations

import subprocess
import sys
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_SKILL_FRONTMATTER_KEYS = {
    "name",
    "version",
    "description",
    "license",
    "allowed-tools",
    "metadata",
}
ALLOWED_OPENAI_INTERFACE_KEYS = {
    "display_name",
    "short_description",
    "icon_small",
    "icon_large",
    "brand_color",
    "default_prompt",
}
MAX_SKILL_DESCRIPTION_CHARS = 220
MAX_SKILL_DESCRIPTION_ESTIMATED_TOKENS = 90
REQUIRED_SKILL_DESCRIPTION_PHRASES = (
    "阅星曈",
    "Yue Xingtong",
    "墨水屏",
    "推送",
    "书架",
    "阅读进度",
    "书签",
    "EPUB",
)
FORBIDDEN_SKILL_DESCRIPTION_PHRASES = (
    "帮我查一下",
    "搜一下",
    "最新资讯",
    "现在什么情况",
    "今天的",
)
MAX_SKILL_BODY_LINES = 500
REQUIRED_SKILL_BODY_REFERENCES = (
    "references/AGENT-WORKFLOWS.md",
    "references/ONBOARDING-COPY.md",
    "references/SETUP.md",
    "references/TROUBLESHOOTING.md",
    "references/design-guide.md",
)
FORBIDDEN_SKILL_BODY_REFERENCES = (
    "README.md",
    "landing.html",
    "landing-v2.html",
    "references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md",
    "references/MANUAL-TEST-CHECKLIST.md",
)
RESOURCE_REFERENCE_RE = re.compile(
    r"(?:\{baseDir\}/)?((?:scripts|references|assets)/[^\s`\"')，。；、]+)"
)

PY_FILES = [
    "scripts/check_environment.py",
    "scripts/check_installation.py",
    "scripts/check_package.py",
    "scripts/install_skill.py",
    "scripts/xteink_api.py",
    "scripts/push_to_device.py",
    "scripts/fetch_reading.py",
    "scripts/search_query.py",
    "scripts/setup_fonts.py",
    "scripts/render_image.py",
    "scripts/render_book.py",
    "scripts/epub/gen_cover_html.py",
    "scripts/epub/gen_cover_svg.py",
    "scripts/epub/render_book_epub.py",
    "scripts/smoke_test.py",
    "scripts/verify.py",
]


def estimate_prompt_tokens(text: str) -> int:
    """Match skill-cleaner's rough UTF-8 byte budget heuristic."""
    return (len(text.encode("utf-8")) + 3) // 4


def validate_skill_description_budget(description: str) -> list[str]:
    """Return frontmatter description issues that would hurt triggering or budget."""
    issues = []
    if not description:
        issues.append("description is required")

    if len(description) > MAX_SKILL_DESCRIPTION_CHARS:
        issues.append(
            f"description must be <= {MAX_SKILL_DESCRIPTION_CHARS} characters "
            f"(found {len(description)})"
        )

    estimated_tokens = estimate_prompt_tokens(description)
    if estimated_tokens > MAX_SKILL_DESCRIPTION_ESTIMATED_TOKENS:
        issues.append(
            f"description estimated budget must be <= "
            f"{MAX_SKILL_DESCRIPTION_ESTIMATED_TOKENS} tokens (found {estimated_tokens})"
        )

    missing = [phrase for phrase in REQUIRED_SKILL_DESCRIPTION_PHRASES if phrase not in description]
    if missing:
        issues.append("description missing trigger phrase(s): " + ", ".join(missing))

    forbidden = [phrase for phrase in FORBIDDEN_SKILL_DESCRIPTION_PHRASES if phrase in description]
    if forbidden:
        issues.append(
            "description contains over-broad search trigger phrase(s): "
            + ", ".join(forbidden)
        )

    return issues


def skill_body_from_text(text: str) -> str:
    match = re.match(r"^---\n.*?\n---\n?", text, re.DOTALL)
    return text[match.end():] if match else text


def referenced_resources(text: str) -> list[str]:
    return sorted(set(RESOURCE_REFERENCE_RE.findall(text)))


def validate_skill_body_progressive_disclosure(
    text: str,
    *,
    root: Path = ROOT,
) -> list[str]:
    """Return issues that make SKILL.md too large or reference-stale."""
    issues: list[str] = []
    body = skill_body_from_text(text)
    body_lines = body.splitlines()
    if len(body_lines) > MAX_SKILL_BODY_LINES:
        issues.append(
            f"SKILL.md body must be <= {MAX_SKILL_BODY_LINES} lines "
            f"(found {len(body_lines)})"
        )

    for required in REQUIRED_SKILL_BODY_REFERENCES:
        if required not in body:
            issues.append(f"SKILL.md body missing required reference: {required}")

    for forbidden in FORBIDDEN_SKILL_BODY_REFERENCES:
        if forbidden in body:
            issues.append(f"SKILL.md body should not reference repo-only file: {forbidden}")

    for reference in referenced_resources(body):
        if not (root / reference).exists():
            issues.append(f"SKILL.md references missing resource: {reference}")
        if reference.startswith("references/") and len(Path(reference).parts) > 2:
            issues.append(f"SKILL.md should link references one level deep: {reference}")

    return issues


def run(label: str, cmd: list[str]) -> bool:
    print(f"[VERIFY] {label}")
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        print(f"[FAIL] {label} exited {result.returncode}", file=sys.stderr)
        return False
    return True


def validate_skill_metadata() -> bool:
    print("[VERIFY] Skill metadata")
    skill_md = ROOT / "SKILL.md"
    try:
        raw = skill_md.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("SKILL.md must be UTF-8 without BOM")

        text = raw.decode("utf-8")
        if not text.startswith("---\n"):
            raise ValueError("SKILL.md frontmatter must start with '---' and use LF line endings")

        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not match:
            raise ValueError("SKILL.md frontmatter closing marker was not found")

        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            raise ValueError("SKILL.md frontmatter must be a YAML mapping")

        unexpected = set(frontmatter) - ALLOWED_SKILL_FRONTMATTER_KEYS
        if unexpected:
            allowed = ", ".join(sorted(ALLOWED_SKILL_FRONTMATTER_KEYS))
            extra = ", ".join(sorted(unexpected))
            raise ValueError(f"unexpected frontmatter key(s): {extra}. Allowed: {allowed}")

        name = str(frontmatter.get("name", "")).strip()
        description = str(frontmatter.get("description", "")).strip()
        if name != "eink-push":
            raise ValueError("SKILL.md frontmatter name must be 'eink-push'")
        description_issues = validate_skill_description_budget(description)
        if description_issues:
            raise ValueError(
                "SKILL.md frontmatter description failed budget/trigger checks: "
                + "; ".join(description_issues)
            )
        body_issues = validate_skill_body_progressive_disclosure(text)
        if body_issues:
            raise ValueError(
                "SKILL.md body failed progressive disclosure checks: "
                + "; ".join(body_issues)
            )

    except Exception as e:
        print(f"[FAIL] Skill metadata: {e}", file=sys.stderr)
        return False

    print("[OK] Skill metadata valid.")
    return True


def validate_openai_yaml() -> bool:
    print("[VERIFY] agents/openai.yaml")
    openai_yaml = ROOT / "agents" / "openai.yaml"
    try:
        raw = openai_yaml.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("agents/openai.yaml must be UTF-8 without BOM")
        if b"\r\n" in raw:
            raise ValueError("agents/openai.yaml must use LF line endings")

        data = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("agents/openai.yaml must be a YAML mapping")

        interface = data.get("interface")
        if not isinstance(interface, dict):
            raise ValueError("agents/openai.yaml must contain an interface mapping")

        unexpected = set(interface) - ALLOWED_OPENAI_INTERFACE_KEYS
        if unexpected:
            allowed = ", ".join(sorted(ALLOWED_OPENAI_INTERFACE_KEYS))
            extra = ", ".join(sorted(unexpected))
            raise ValueError(f"unexpected interface key(s): {extra}. Allowed: {allowed}")

        display_name = str(interface.get("display_name", "")).strip()
        short_description = str(interface.get("short_description", "")).strip()
        default_prompt = str(interface.get("default_prompt", "")).strip()

        if not display_name:
            raise ValueError("interface.display_name is required")
        if not (25 <= len(short_description) <= 64):
            raise ValueError("interface.short_description must be 25-64 characters")
        if "$eink-push" not in default_prompt:
            raise ValueError("interface.default_prompt must explicitly mention $eink-push")

    except Exception as e:
        print(f"[FAIL] agents/openai.yaml: {e}", file=sys.stderr)
        return False

    print("[OK] agents/openai.yaml valid.")
    return True


def validate_onboarding_docs() -> bool:
    print("[VERIFY] Onboarding docs")
    try:
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        onboarding_text = (ROOT / "references" / "ONBOARDING-COPY.md").read_text(encoding="utf-8")
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")

        required_skill = [
            "references/ONBOARDING-COPY.md",
            "--check-credentials --auth",
            "XTEINK_USERNAME",
            "XTEINK_PASSWORD",
        ]
        missing_skill = [item for item in required_skill if item not in skill_text]
        if missing_skill:
            raise ValueError("SKILL.md missing onboarding hook(s): " + ", ".join(missing_skill))

        required_onboarding = [
            "--check-credentials",
            "--check-credentials --auth",
            "--reset-credentials",
            "XTEINK_USERNAME",
            "XTEINK_PASSWORD",
            "翻页电子书",
            '明确说 "EPUB"',
        ]
        missing_onboarding = [item for item in required_onboarding if item not in onboarding_text]
        if missing_onboarding:
            raise ValueError(
                "references/ONBOARDING-COPY.md missing item(s): "
                + ", ".join(missing_onboarding)
            )

        forbidden_onboarding = [
            "长文 / 分析报告 / 书 → EPUB",
            "按章节归整的 EPUB",
            "smoke_test.py",
        ]
        found_forbidden = [item for item in forbidden_onboarding if item in onboarding_text]
        if found_forbidden:
            raise ValueError(
                "references/ONBOARDING-COPY.md has stale EPUB default wording: "
                + ", ".join(found_forbidden)
            )

        required_readme = [
            "--check-credentials",
            "--check-credentials --auth",
            "AUTH_OK",
            "XTEINK_USERNAME",
            "XTEINK_PASSWORD",
        ]
        missing_readme = [item for item in required_readme if item not in readme_text]
        if missing_readme:
            raise ValueError("README.md missing credential check item(s): " + ", ".join(missing_readme))

    except Exception as e:
        print(f"[FAIL] Onboarding docs: {e}", file=sys.stderr)
        return False

    print("[OK] Onboarding docs valid.")
    return True


def validate_credential_docs() -> bool:
    print("[VERIFY] Credential docs")
    try:
        files = {
            "SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "references/SETUP.md": (ROOT / "references" / "SETUP.md").read_text(encoding="utf-8"),
            "references/TROUBLESHOOTING.md": (
                ROOT / "references" / "TROUBLESHOOTING.md"
            ).read_text(encoding="utf-8"),
        }

        for path, text in files.items():
            missing = [
                item
                for item in ("XTEINK_USERNAME", "XTEINK_PASSWORD", ".credentials.json")
                if item not in text
            ]
            if missing:
                raise ValueError(f"{path} missing credential source item(s): " + ", ".join(missing))

        if "YUEXINGTONG_USERNAME" not in files["SKILL.md"]:
            raise ValueError("SKILL.md must mention YUEXINGTONG_USERNAME alias")
        if "环境变量" not in files["references/TROUBLESHOOTING.md"]:
            raise ValueError("TROUBLESHOOTING must mention environment variable recovery")

    except Exception as e:
        print(f"[FAIL] Credential docs: {e}", file=sys.stderr)
        return False

    print("[OK] Credential docs valid.")
    return True


def validate_environment_docs() -> bool:
    print("[VERIFY] Environment docs")
    try:
        files = {
            "SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "references/SETUP.md": (ROOT / "references" / "SETUP.md").read_text(encoding="utf-8"),
            "references/TROUBLESHOOTING.md": (
                ROOT / "references" / "TROUBLESHOOTING.md"
            ).read_text(encoding="utf-8"),
        }

        for path, text in files.items():
            if "scripts/check_environment.py" not in text:
                raise ValueError(f"{path} must reference scripts/check_environment.py")

        if "Python >= 3.10" not in files["SKILL.md"]:
            raise ValueError("SKILL.md must declare Python >= 3.10 compatibility")
        if "Python 3.10+" not in files["README.md"]:
            raise ValueError("README.md must mention Python 3.10+")
        if "Python >= 3.10" not in files["references/SETUP.md"]:
            raise ValueError("references/SETUP.md must mention Python >= 3.10")
        if "fix:" not in files["references/SETUP.md"] or "fix:" not in files["references/TROUBLESHOOTING.md"]:
            raise ValueError("SETUP and TROUBLESHOOTING must mention check_environment fix commands")

    except Exception as e:
        print(f"[FAIL] Environment docs: {e}", file=sys.stderr)
        return False

    print("[OK] Environment docs valid.")
    return True


def validate_fetch_reading_docs() -> bool:
    print("[VERIFY] Fetch reading docs")
    try:
        files = {
            "SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "references/AGENT-WORKFLOWS.md": (
                ROOT / "references" / "AGENT-WORKFLOWS.md"
            ).read_text(encoding="utf-8"),
            "references/MANUAL-TEST-CHECKLIST.md": (
                ROOT / "references" / "MANUAL-TEST-CHECKLIST.md"
            ).read_text(encoding="utf-8"),
        }

        required = {
            "SKILL.md": [
                "默认加 `--compact --limit 50`",
                "默认加 `--compact --limit 100`",
            ],
            "references/AGENT-WORKFLOWS.md": [
                "books [--keyword 关键词] [--format epub|txt] [--per-page 50] --compact --limit 50",
                'bookmarks --keyword "完整book_name原始值" --all --compact --limit 100',
                "bookmarks --all --compact --limit 100",
                "需要完整整理时可去掉 `--limit`；需要服务端原始字段时去掉 `--compact`。",
            ],
            "references/MANUAL-TEST-CHECKLIST.md": [
                "python scripts/fetch_reading.py books --compact --limit 10",
                "python scripts/fetch_reading.py bookmarks --all --compact --limit 20",
                "`returned`、`available_in_response`、`truncated`",
            ],
        }

        for path, needles in required.items():
            missing = [needle for needle in needles if needle not in files[path]]
            if missing:
                raise ValueError(f"{path} missing compact/limit guidance: " + ", ".join(missing))

    except Exception as e:
        print(f"[FAIL] Fetch reading docs: {e}", file=sys.stderr)
        return False

    print("[OK] Fetch reading docs valid.")
    return True


def validate_trigger_phrases() -> bool:
    print("[VERIFY] Trigger phrases")
    try:
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter_match = re.match(r"^---\n(.*?)\n---", skill_text, re.DOTALL)
        if not frontmatter_match:
            raise ValueError("SKILL.md frontmatter missing")

        frontmatter = yaml.safe_load(frontmatter_match.group(1))
        description = str(frontmatter.get("description", ""))
        body = skill_text[frontmatter_match.end():]

        required_body_phrases = [
            "把这段发到阅星曈",
            "做成墨水屏卡片",
            "生成 EPUB 发到设备",
            "看一下我的书架",
            "整理《书名》的书签",
        ]
        missing = [phrase for phrase in required_body_phrases if phrase not in body]
        if missing:
            raise ValueError("SKILL.md missing high-value trigger phrase(s): " + ", ".join(missing))

        forbidden_description_phrases = [
            "把这段发到阅星曈",
            "做成墨水屏卡片",
            "生成 EPUB 发到设备",
            "看一下我的书架",
            "整理《书名》的书签",
        ]
        leaked = [phrase for phrase in forbidden_description_phrases if phrase in description]
        if leaked:
            raise ValueError(
                "frontmatter description should not list full example phrases: "
                + ", ".join(leaked)
            )

    except Exception as e:
        print(f"[FAIL] Trigger phrases: {e}", file=sys.stderr)
        return False

    print("[OK] Trigger phrases valid.")
    return True


def validate_preview_policy() -> bool:
    print("[VERIFY] Preview policy")
    try:
        files = {
            "SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "references/SETUP.md": (ROOT / "references" / "SETUP.md").read_text(encoding="utf-8"),
            "references/AGENT-WORKFLOWS.md": (
                ROOT / "references" / "AGENT-WORKFLOWS.md"
            ).read_text(encoding="utf-8"),
        }

        if "python scripts/render_image.py assets/templates/base.html --preview" not in files["README.md"]:
            raise ValueError("README.md must show --preview for local card render checks")
        if "python scripts/render_image.py assets/templates/base.html --preview" not in files["references/SETUP.md"]:
            raise ValueError("references/SETUP.md must show --preview for local card render checks")

        workflow_text = files["references/AGENT-WORKFLOWS.md"]
        required_workflow = [
            "开发调试或排障时可加 `--preview`",
            "正式 Skill 推送命令默认不带 `--preview`",
        ]
        missing = [item for item in required_workflow if item not in workflow_text]
        if missing:
            raise ValueError("references/AGENT-WORKFLOWS.md missing preview policy: " + ", ".join(missing))

        push_command_re = re.compile(r"render_image\.py[^\n]*--push[^\n]*--preview|render_image\.py[^\n]*--preview[^\n]*--push")
        for path in ("SKILL.md", "references/AGENT-WORKFLOWS.md"):
            if push_command_re.search(files[path]):
                raise ValueError(f"{path} must not make --preview part of formal push commands")

    except Exception as e:
        print(f"[FAIL] Preview policy: {e}", file=sys.stderr)
        return False

    print("[OK] Preview policy valid.")
    return True


def validate_installation_audit_docs() -> bool:
    print("[VERIFY] Installation audit docs")
    try:
        files = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md": (
                ROOT / "references" / "SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md"
            ).read_text(encoding="utf-8"),
        }

        for path, text in files.items():
            if "scripts/check_installation.py" not in text:
                raise ValueError(f"{path} must reference scripts/check_installation.py")
            if "scripts/install_skill.py" not in text:
                raise ValueError(f"{path} must reference scripts/install_skill.py")

        optimization_text = files["references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md"]
        if "--require-installed" not in optimization_text:
            raise ValueError("optimization plan must mention --require-installed")
        if "--apply" not in optimization_text:
            raise ValueError("optimization plan must mention install_skill.py --apply")
        if "--target" not in files["README.md"] or "--target" not in optimization_text:
            raise ValueError("README.md and optimization plan must mention install_skill.py --target")
        if "源码目录" not in optimization_text:
            raise ValueError("optimization plan must warn against installing inside source checkout")

    except Exception as e:
        print(f"[FAIL] Installation audit docs: {e}", file=sys.stderr)
        return False

    print("[OK] Installation audit docs valid.")
    return True


def validate_package_audit_docs() -> bool:
    print("[VERIFY] Package audit docs")
    try:
        files = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md": (
                ROOT / "references" / "SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md"
            ).read_text(encoding="utf-8"),
        }

        for path, text in files.items():
            if "scripts/check_package.py" not in text:
                raise ValueError(f"{path} must reference scripts/check_package.py")

        optimization_text = files["references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md"]
        for item in (".credentials.json", "node_modules", "output"):
            if item not in optimization_text:
                raise ValueError(
                    "optimization plan must mention forbidden package content: " + item
                )

    except Exception as e:
        print(f"[FAIL] Package audit docs: {e}", file=sys.stderr)
        return False

    print("[OK] Package audit docs valid.")
    return True


def main() -> int:
    checks = [
        (
            "Python syntax",
            [sys.executable, "-m", "py_compile", *PY_FILES],
        ),
        (
            "Unit tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        ),
        (
            "Environment preflight",
            [sys.executable, "scripts/check_environment.py"],
        ),
        (
            "Skill installation audit",
            [sys.executable, "scripts/check_installation.py"],
        ),
        (
            "Skill package contents audit",
            [sys.executable, "scripts/check_package.py"],
        ),
        (
            "Credentials structure",
            [sys.executable, "scripts/push_to_device.py", "--check-credentials"],
        ),
        (
            "Offline smoke test",
            [sys.executable, "scripts/smoke_test.py"],
        ),
    ]

    failed = []
    if not validate_skill_metadata():
        failed.append("Skill metadata")
    if not validate_openai_yaml():
        failed.append("agents/openai.yaml")
    if not validate_onboarding_docs():
        failed.append("Onboarding docs")
    if not validate_credential_docs():
        failed.append("Credential docs")
    if not validate_environment_docs():
        failed.append("Environment docs")
    if not validate_fetch_reading_docs():
        failed.append("Fetch reading docs")
    if not validate_trigger_phrases():
        failed.append("Trigger phrases")
    if not validate_preview_policy():
        failed.append("Preview policy")
    if not validate_installation_audit_docs():
        failed.append("Installation audit docs")
    if not validate_package_audit_docs():
        failed.append("Package audit docs")
    failed.extend(label for label, cmd in checks if not run(label, cmd))
    if failed:
        print("[FAIL] Verification failed: " + ", ".join(failed), file=sys.stderr)
        return 1

    print("[OK] Verification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import unittest

from scripts.verify import (
    MAX_SKILL_DESCRIPTION_CHARS,
    MAX_SKILL_BODY_LINES,
    estimate_prompt_tokens,
    referenced_resources,
    validate_skill_description_budget,
    validate_skill_body_progressive_disclosure,
)
import tempfile
from pathlib import Path


VALID_DESCRIPTION = (
    "将内容推送到阅星曈/Yue Xingtong 墨水屏设备；生成卡片、翻页图片集、"
    "Markdown/EPUB 电子书；查询书架、阅读进度、书签摘录；在阅星曈推送场景中调用联网搜索。"
)


class PromptBudgetTests(unittest.TestCase):
    def test_estimate_prompt_tokens_uses_utf8_bytes(self):
        self.assertEqual(estimate_prompt_tokens("abcd"), 1)
        self.assertEqual(estimate_prompt_tokens("abcde"), 2)


class SkillDescriptionBudgetTests(unittest.TestCase):
    def test_valid_description_passes(self):
        self.assertEqual(validate_skill_description_budget(VALID_DESCRIPTION), [])

    def test_empty_description_fails(self):
        issues = validate_skill_description_budget("")
        self.assertTrue(any("required" in issue for issue in issues))

    def test_long_description_fails(self):
        description = VALID_DESCRIPTION + "补充说明" * MAX_SKILL_DESCRIPTION_CHARS
        issues = validate_skill_description_budget(description)
        self.assertTrue(any("characters" in issue for issue in issues))
        self.assertTrue(any("estimated budget" in issue for issue in issues))

    def test_missing_trigger_phrase_fails(self):
        issues = validate_skill_description_budget("推送内容到一个阅读设备。")
        self.assertTrue(any("missing trigger phrase" in issue for issue in issues))

    def test_overbroad_search_trigger_fails(self):
        description = VALID_DESCRIPTION + "用户问最新资讯或搜一下时使用。"
        issues = validate_skill_description_budget(description)
        self.assertTrue(any("over-broad search trigger" in issue for issue in issues))


class SkillProgressiveDisclosureTests(unittest.TestCase):
    def make_root(self, *paths: str) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        for path in paths:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
        return tmp

    def valid_body(self) -> str:
        return "\n".join([
            "Read `{baseDir}/references/AGENT-WORKFLOWS.md`.",
            "Read `{baseDir}/references/ONBOARDING-COPY.md`.",
            "Read `{baseDir}/references/SETUP.md`.",
            "Read `{baseDir}/references/TROUBLESHOOTING.md`.",
            "Read `{baseDir}/references/design-guide.md`.",
            "Run `{baseDir}/scripts/render_image.py`.",
            "Use `{baseDir}/assets/templates/base.html`.",
        ])

    def test_referenced_resources_extracts_basedir_paths(self):
        self.assertEqual(
            referenced_resources("Run `{baseDir}/scripts/render_image.py` and `references/SETUP.md`."),
            ["references/SETUP.md", "scripts/render_image.py"],
        )

    def test_valid_body_passes(self):
        required = [
            "references/AGENT-WORKFLOWS.md",
            "references/ONBOARDING-COPY.md",
            "references/SETUP.md",
            "references/TROUBLESHOOTING.md",
            "references/design-guide.md",
            "scripts/render_image.py",
            "assets/templates/base.html",
        ]
        with self.make_root(*required) as tmp:
            issues = validate_skill_body_progressive_disclosure(self.valid_body(), root=Path(tmp))

        self.assertEqual(issues, [])

    def test_body_line_limit_fails(self):
        body = self.valid_body() + "\n" + "\n".join("line" for _ in range(MAX_SKILL_BODY_LINES + 1))
        issues = validate_skill_body_progressive_disclosure(body)
        self.assertTrue(any("body must be <=" in issue for issue in issues))

    def test_missing_required_reference_fails(self):
        issues = validate_skill_body_progressive_disclosure("Read `references/SETUP.md`.")
        self.assertTrue(any("missing required reference" in issue for issue in issues))

    def test_missing_resource_fails(self):
        with self.make_root(
            "references/AGENT-WORKFLOWS.md",
            "references/ONBOARDING-COPY.md",
            "references/SETUP.md",
            "references/TROUBLESHOOTING.md",
            "references/design-guide.md",
        ) as tmp:
            body = self.valid_body() + "\nRun `{baseDir}/scripts/missing.py`."
            issues = validate_skill_body_progressive_disclosure(body, root=Path(tmp))

        self.assertTrue(any("missing resource" in issue for issue in issues))

    def test_repo_only_reference_fails(self):
        issues = validate_skill_body_progressive_disclosure(self.valid_body() + "\nSee README.md.")
        self.assertTrue(any("repo-only file" in issue for issue in issues))

    def test_nested_reference_fails(self):
        with self.make_root(
            "references/AGENT-WORKFLOWS.md",
            "references/ONBOARDING-COPY.md",
            "references/SETUP.md",
            "references/TROUBLESHOOTING.md",
            "references/design-guide.md",
            "references/deep/path.md",
        ) as tmp:
            body = self.valid_body() + "\nRead `{baseDir}/references/deep/path.md`."
            issues = validate_skill_body_progressive_disclosure(body, root=Path(tmp))

        self.assertTrue(any("one level deep" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()

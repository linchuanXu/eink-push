import tempfile
import unittest
from pathlib import Path

from scripts.check_installation import (
    ROOT,
    SkillRecord,
    audit,
    collect_records,
    estimate_prompt_tokens,
    iter_skill_dirs,
    parse_skill_frontmatter,
    unique_existing_dirs,
)


SKILL_TEXT = """---
name: eink-push
description: Push to 阅星曈/Yue Xingtong.
---

# Skill
"""


class InstallationParsingTests(unittest.TestCase):
    def test_parse_skill_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text(SKILL_TEXT, encoding="utf-8")
            frontmatter, errors = parse_skill_frontmatter(skill_md)

        self.assertEqual(errors, [])
        self.assertEqual(frontmatter["name"], "eink-push")

    def test_parse_skill_frontmatter_reports_missing_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_md = Path(tmp) / "SKILL.md"
            skill_md.write_text("name: eink-push", encoding="utf-8")
            _, errors = parse_skill_frontmatter(skill_md)

        self.assertTrue(any("frontmatter missing" in error for error in errors))

    def test_estimate_prompt_tokens_uses_utf8_bytes(self):
        self.assertEqual(estimate_prompt_tokens("abcd"), 1)
        self.assertEqual(estimate_prompt_tokens("abcde"), 2)


class InstallationDiscoveryTests(unittest.TestCase):
    def test_unique_existing_dirs_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.assertEqual(unique_existing_dirs([path, path]), [path])

    def test_iter_skill_dirs_finds_nested_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "group" / "eink-push"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(SKILL_TEXT, encoding="utf-8")

            self.assertEqual(iter_skill_dirs(root), [skill_dir])

    def test_collect_records_filters_to_eink_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "eink-push"
            other_dir = root / "other"
            skill_dir.mkdir()
            other_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(SKILL_TEXT, encoding="utf-8")
            (other_dir / "SKILL.md").write_text(
                "---\nname: other\n"
                "description: Other skill.\n---\n",
                encoding="utf-8",
            )

            records = collect_records([root])

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "eink-push")


class InstallationAuditTests(unittest.TestCase):
    def make_record(
        self,
        path: Path,
        *,
        skill_hash: str = "same",
        openai_hash: str | None = "same-ui",
    ) -> SkillRecord:
        return SkillRecord(
            path=path,
            name="eink-push",
            description="Push to 阅星曈/Yue Xingtong.",
            skill_md_sha256=skill_hash,
            openai_yaml_sha256=openai_hash,
        )

    def test_audit_allows_source_only_by_default(self):
        status, issues = audit([self.make_record(ROOT)])
        self.assertEqual((status, issues), ("OK", []))

    def test_audit_can_require_installed_copy(self):
        status, issues = audit([self.make_record(ROOT)], require_installed=True)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("no installed" in issue for issue in issues))

    def test_audit_reports_multiple_installed_copies(self):
        records = [
            self.make_record(ROOT),
            self.make_record(Path("C:/skills/eink-push-a")),
            self.make_record(Path("C:/skills/eink-push-b")),
        ]
        status, issues = audit(records)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("multiple installed" in issue for issue in issues))

    def test_audit_reports_installed_drift(self):
        records = [
            self.make_record(ROOT, skill_hash="source", openai_hash="source-ui"),
            self.make_record(Path("C:/skills/eink-push"), skill_hash="old", openai_hash="old-ui"),
        ]
        status, issues = audit(records)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("SKILL.md differs" in issue for issue in issues))
        self.assertTrue(any("openai.yaml differs" in issue for issue in issues))

    def test_audit_reports_runtime_file_drift(self):
        with tempfile.TemporaryDirectory() as target_tmp:
            installed = Path(target_tmp) / "eink-push"
            installed.mkdir()
            (installed / "SKILL.md").write_text("different runtime", encoding="utf-8")
            records = [
                self.make_record(ROOT),
                self.make_record(installed),
            ]

            status, issues = audit(records, runtime_files=["SKILL.md"])

        self.assertEqual(status, "FAIL")
        self.assertTrue(any("runtime files differ" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()

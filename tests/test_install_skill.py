import tempfile
import unittest
from pathlib import Path

from scripts.check_package import REQUIRED_PACKAGE_FILES
from scripts.install_skill import (
    apply_install_plan,
    build_install_plan,
    default_target,
    is_protected_target_extra,
    validate_target_path,
)


class InstallSkillTests(unittest.TestCase):
    def make_source(self, root: Path) -> None:
        for rel_path in REQUIRED_PACKAGE_FILES:
            target = root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"source:{rel_path}", encoding="utf-8")

    def test_default_target_uses_codex_home(self):
        self.assertTrue(str(default_target()).replace("\\", "/").endswith("/skills/eink-push"))

    def test_protected_target_extras_are_not_reported(self):
        self.assertTrue(is_protected_target_extra(".credentials.json"))
        self.assertTrue(is_protected_target_extra("node_modules/pkg/index.js"))
        self.assertTrue(is_protected_target_extra("scripts/__pycache__/render_image.cpython-311.pyc"))
        self.assertTrue(is_protected_target_extra("scripts/epub/__pycache__/gen_cover_svg.cpython-311.pyc"))
        self.assertFalse(is_protected_target_extra("old.txt"))

    def test_validate_target_rejects_source_directory(self):
        with tempfile.TemporaryDirectory() as source_tmp:
            source = Path(source_tmp)
            issues = validate_target_path(source, source)

        self.assertTrue(any("inside the source" in issue for issue in issues))

    def test_validate_target_rejects_source_child(self):
        with tempfile.TemporaryDirectory() as source_tmp:
            source = Path(source_tmp)
            issues = validate_target_path(source, source / "skills" / "eink-push")

        self.assertTrue(any("inside the source" in issue for issue in issues))

    def test_validate_target_rejects_parent_of_source(self):
        with tempfile.TemporaryDirectory() as parent_tmp:
            parent = Path(parent_tmp)
            source = parent / "eink-push"
            source.mkdir()
            issues = validate_target_path(source, parent)

        self.assertTrue(any("contain the source" in issue for issue in issues))

    def test_validate_target_rejects_wrong_directory_name(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as target_tmp:
            issues = validate_target_path(Path(source_tmp), Path(target_tmp) / "wrong-name")

        self.assertTrue(any("should be named eink-push" in issue for issue in issues))

    def test_build_plan_for_empty_target_copies_runtime_files(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as target_tmp:
            source = Path(source_tmp)
            target = Path(target_tmp) / "eink-push"
            self.make_source(source)

            plan = build_install_plan(source, target)

        self.assertEqual(plan.status, "OK")
        self.assertIn("SKILL.md", plan.copy_files)
        self.assertEqual(plan.update_files, [])

    def test_build_plan_detects_updates_and_extras(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as target_tmp:
            source = Path(source_tmp)
            target = Path(target_tmp) / "eink-push"
            self.make_source(source)
            (target / "SKILL.md").parent.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text("old", encoding="utf-8")
            (target / "old.txt").write_text("extra", encoding="utf-8")
            (target / ".credentials.json").write_text("protected", encoding="utf-8")
            (target / "scripts" / "__pycache__").mkdir(parents=True, exist_ok=True)
            (target / "scripts" / "__pycache__" / "render_image.cpython-311.pyc").write_bytes(b"protected")

            plan = build_install_plan(source, target)

        self.assertIn("SKILL.md", plan.update_files)
        self.assertEqual(plan.extra_files, ["old.txt"])

    def test_apply_install_plan_copies_files(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as target_tmp:
            source = Path(source_tmp)
            target = Path(target_tmp) / "eink-push"
            self.make_source(source)
            plan = build_install_plan(source, target)

            apply_install_plan(source, plan)

            self.assertTrue((target / "SKILL.md").exists())
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "source:SKILL.md")


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from scripts.check_package import (
    REQUIRED_PACKAGE_FILES,
    audit_package,
    fallback_scan_files,
    matches_any,
    normalize_path,
)


class PackagePatternTests(unittest.TestCase):
    def test_normalize_path_uses_forward_slashes(self):
        self.assertEqual(normalize_path(Path("scripts") / "check_package.py"), "scripts/check_package.py")

    def test_matches_any_supports_globs(self):
        self.assertTrue(matches_any("output/card.xth", ("output/**",)))
        self.assertFalse(matches_any("scripts/render_image.py", ("output/**",)))


class PackageAuditTests(unittest.TestCase):
    def test_minimal_required_package_passes(self):
        audit = audit_package(list(REQUIRED_PACKAGE_FILES))

        self.assertEqual(audit.status, "OK")
        self.assertEqual(audit.missing_required, [])
        self.assertEqual(audit.forbidden_tracked, [])
        self.assertEqual(audit.uncategorized_tracked, [])

    def test_missing_required_file_fails(self):
        files = [path for path in REQUIRED_PACKAGE_FILES if path != "SKILL.md"]
        audit = audit_package(files)

        self.assertEqual(audit.status, "FAIL")
        self.assertIn("SKILL.md", audit.missing_required)

    def test_forbidden_tracked_file_fails(self):
        audit = audit_package([*REQUIRED_PACKAGE_FILES, ".credentials.json", "output/card.xth"])

        self.assertEqual(audit.status, "FAIL")
        self.assertIn(".credentials.json", audit.forbidden_tracked)
        self.assertIn("output/card.xth", audit.forbidden_tracked)

    def test_uncategorized_tracked_file_fails(self):
        audit = audit_package([*REQUIRED_PACKAGE_FILES, "scratch.txt"])

        self.assertEqual(audit.status, "FAIL")
        self.assertEqual(audit.uncategorized_tracked, ["scratch.txt"])

    def test_repo_only_files_are_allowed_but_not_runtime(self):
        audit = audit_package([
            *REQUIRED_PACKAGE_FILES,
            "README.md",
            "tests/test_check_package.py",
            "references/MANUAL-TEST-CHECKLIST.md",
            "references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md",
            "scripts/check_package.py",
            "scripts/install_skill.py",
            "scripts/verify.py",
        ])

        self.assertEqual(audit.status, "OK")
        self.assertIn("README.md", audit.repo_only_files)
        self.assertIn("references/MANUAL-TEST-CHECKLIST.md", audit.repo_only_files)
        self.assertIn("scripts/install_skill.py", audit.repo_only_files)
        self.assertNotIn("README.md", audit.runtime_files)
        self.assertNotIn("references/SKILL-CLEANER-AND-EINK-PUSH-OPTIMIZATION.md", audit.runtime_files)
        self.assertNotIn("scripts/verify.py", audit.runtime_files)


class PackageScanTests(unittest.TestCase):
    def test_fallback_scan_excludes_local_generated_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text("skill", encoding="utf-8")
            (root / "output").mkdir()
            (root / "output" / "card.xth").write_text("generated", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "pkg.js").write_text("generated", encoding="utf-8")

            files = fallback_scan_files(root)

        self.assertEqual(files, ["SKILL.md"])


if __name__ == "__main__":
    unittest.main()

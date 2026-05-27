import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_update import (
    FAIL,
    OK,
    UPDATE,
    UNKNOWN,
    check_update,
    compare_versions,
    extract_skill_version,
    parse_version_tuple,
)


class SkillVersionParsingTests(unittest.TestCase):
    def test_extracts_version_from_frontmatter(self):
        text = "---\nname: eink-push\nversion: 1.2.3\n---\n# Skill"

        self.assertEqual(extract_skill_version(text), "1.2.3")

    def test_missing_frontmatter_version_returns_none(self):
        self.assertIsNone(extract_skill_version("# Skill"))

    def test_parse_version_tuple(self):
        self.assertEqual(parse_version_tuple("1.2.3"), (1, 2, 3))
        self.assertIsNone(parse_version_tuple("v1.2.3"))

    def test_compare_versions_pads_missing_parts(self):
        self.assertEqual(compare_versions("1.2", "1.2.0"), 0)
        self.assertEqual(compare_versions("1.2.0", "1.3.0"), -1)
        self.assertEqual(compare_versions("1.4.0", "1.3.9"), 1)


class UpdateCheckTests(unittest.TestCase):
    def write_skill(self, text: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "SKILL.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reports_update_when_remote_is_newer(self):
        local = self.write_skill("---\nversion: 1.0.0\n---\n")
        with patch("scripts.check_update.fetch_latest_version", return_value="1.1.0"):
            result = check_update(skill_file=local)

        self.assertEqual(result.status, UPDATE)
        self.assertEqual(result.current_version, "1.0.0")
        self.assertEqual(result.latest_version, "1.1.0")
        self.assertTrue(result.update_commands)

    def test_reports_ok_when_versions_match(self):
        local = self.write_skill("---\nversion: 1.0.0\n---\n")
        with patch("scripts.check_update.fetch_latest_version", return_value="1.0.0"):
            result = check_update(skill_file=local)

        self.assertEqual(result.status, OK)

    def test_network_failure_is_nonfatal_unknown(self):
        local = self.write_skill("---\nversion: 1.0.0\n---\n")
        with patch("scripts.check_update.fetch_latest_version", side_effect=OSError("offline")):
            result = check_update(skill_file=local)

        self.assertEqual(result.status, UNKNOWN)

    def test_missing_local_version_is_fail(self):
        local = self.write_skill("---\nname: eink-push\n---\n")

        result = check_update(skill_file=local)

        self.assertEqual(result.status, FAIL)


if __name__ == "__main__":
    unittest.main()

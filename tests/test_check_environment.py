import unittest

from scripts.check_environment import (
    FAIL,
    MISSING,
    OK,
    CheckResult,
    has_blocking_failures,
    parse_semver,
    version_at_least,
)


class VersionParsingTests(unittest.TestCase):
    def test_parse_node_style_version(self):
        self.assertEqual(parse_semver("v22.19.0"), (22, 19, 0))

    def test_parse_partial_version(self):
        self.assertEqual(parse_semver("Python 3.10"), (3, 10, 0))

    def test_parse_invalid_version(self):
        self.assertIsNone(parse_semver("not a version"))

    def test_version_at_least(self):
        self.assertTrue(version_at_least((22, 0, 0), (18, 0, 0)))
        self.assertFalse(version_at_least((16, 20, 2), (18, 0, 0)))


class BlockingFailureTests(unittest.TestCase):
    def test_ok_checks_are_not_blocking(self):
        checks = [CheckResult("python", "Python", OK, "3.11")]
        self.assertFalse(has_blocking_failures(checks))

    def test_missing_required_check_is_blocking(self):
        checks = [CheckResult("node", "Node.js", MISSING, "missing")]
        self.assertTrue(has_blocking_failures(checks))

    def test_fail_required_check_is_blocking(self):
        checks = [CheckResult("browser", "Browser", FAIL, "failed")]
        self.assertTrue(has_blocking_failures(checks))

    def test_missing_optional_check_is_not_blocking(self):
        checks = [CheckResult("font", "Font", MISSING, "missing", required=False)]
        self.assertFalse(has_blocking_failures(checks))


if __name__ == "__main__":
    unittest.main()

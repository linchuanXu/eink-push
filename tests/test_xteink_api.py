import json
import tempfile
import unittest
from pathlib import Path

from scripts.xteink_api import (
    auth_headers,
    credentials_from_env,
    credentials_status,
    env_credentials_status,
    extract_access_token,
    extract_devices,
    format_http_error,
    load_credentials,
    normalize_device,
    select_default_device,
)


class CredentialsStatusTests(unittest.TestCase):
    def test_complete_env_credentials_are_ok(self):
        status, detail = credentials_status(
            Path("missing.json"),
            env={"XTEINK_USERNAME": "u", "XTEINK_PASSWORD": "p"},
        )
        self.assertEqual((status, detail), ("OK", ""))

    def test_env_credentials_support_yuexingtong_aliases(self):
        self.assertEqual(
            credentials_from_env({
                "YUEXINGTONG_USERNAME": "u",
                "YUEXINGTONG_PASSWORD": "p",
            }),
            ("u", "p"),
        )

    def test_complete_alias_pair_wins_over_partial_primary_pair(self):
        status, detail = env_credentials_status({
            "XTEINK_USERNAME": "partial",
            "YUEXINGTONG_USERNAME": "u",
            "YUEXINGTONG_PASSWORD": "p",
        })

        self.assertEqual((status, detail), ("OK", ""))

    def test_partial_env_credentials_are_invalid(self):
        status, detail = env_credentials_status({"XTEINK_USERNAME": "u"})
        self.assertEqual(status, "INVALID")
        self.assertIn("XTEINK_USERNAME/XTEINK_PASSWORD", detail)

    def test_partial_env_credentials_take_precedence_over_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".credentials.json"
            path.write_text(json.dumps({"username": "file-u", "password": "file-p"}), encoding="utf-8")
            status, detail = credentials_status(path, env={"XTEINK_USERNAME": "env-u"})

        self.assertEqual(status, "INVALID")
        self.assertIn("环境变量", detail)

    def test_load_credentials_prefers_env_over_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".credentials.json"
            path.write_text(json.dumps({"username": "file-u", "password": "file-p"}), encoding="utf-8")
            creds = load_credentials(
                path,
                env={"XTEINK_USERNAME": "env-u", "XTEINK_PASSWORD": "env-p"},
            )

        self.assertEqual(creds, ("env-u", "env-p"))

    def test_missing_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, _ = credentials_status(Path(tmp) / ".credentials.json")
        self.assertEqual(status, "MISSING")

    def test_invalid_json_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".credentials.json"
            path.write_text("{bad", encoding="utf-8")
            status, _ = credentials_status(path)
        self.assertEqual(status, "INVALID")

    def test_missing_fields_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".credentials.json"
            path.write_text(json.dumps({"username": "u"}), encoding="utf-8")
            status, _ = credentials_status(path)
        self.assertEqual(status, "INVALID")

    def test_valid_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".credentials.json"
            path.write_text(json.dumps({"username": "u", "password": "p"}), encoding="utf-8")
            status, detail = credentials_status(path)
        self.assertEqual((status, detail), ("OK", ""))


class AuthHeadersTests(unittest.TestCase):
    def test_token_only_headers(self):
        self.assertEqual(auth_headers("tok"), {"Authorization": "Bearer tok"})

    def test_device_headers(self):
        self.assertEqual(
            auth_headers("tok", {"id": "dev1", "type": "ESP32C3"}),
            {
                "Authorization": "Bearer tok",
                "Device-Id": "dev1",
                "Device-Type": "ESP32C3",
                "Request-Source": "web",
            },
        )


class ApiResponseParsingTests(unittest.TestCase):
    def test_extract_access_token_from_top_level_shapes(self):
        self.assertEqual(extract_access_token({"access_token": "a"}), "a")
        self.assertEqual(extract_access_token({"token": "b"}), "b")

    def test_extract_access_token_from_nested_data(self):
        self.assertEqual(extract_access_token({"data": {"access_token": "nested"}}), "nested")

    def test_extract_access_token_raises_when_missing(self):
        with self.assertRaisesRegex(RuntimeError, "登录失败"):
            extract_access_token({"data": {}})

    def test_extract_devices_from_known_shapes(self):
        devices = [{"id": "a"}, {"id": "b"}]
        self.assertEqual(extract_devices(devices), devices)
        self.assertEqual(extract_devices({"devices": devices}), devices)
        self.assertEqual(extract_devices({"data": devices}), devices)
        self.assertEqual(extract_devices({"data": {"devices": devices}}), devices)
        self.assertEqual(extract_devices({"data": {"records": devices}}), devices)

    def test_normalize_device_accepts_aliases_and_fallback_type(self):
        self.assertEqual(
            normalize_device({"device_id": 123, "device_type": "ESP32C3_X3"}),
            {"id": "123", "type": "ESP32C3_X3"},
        )
        self.assertEqual(
            normalize_device({"id": "dev", "type": "UNKNOWN"}),
            {"id": "dev", "type": "ESP32C3"},
        )

    def test_normalize_device_requires_id(self):
        with self.assertRaisesRegex(RuntimeError, "device_id/id"):
            normalize_device({"device_type": "ESP32C3"})

    def test_select_default_device_prefers_selected(self):
        self.assertEqual(
            select_default_device([
                {"id": "first"},
                {"id": "second", "selected": True, "type": "ESP32C3_X3"},
            ]),
            {"id": "second", "type": "ESP32C3_X3"},
        )

    def test_select_default_device_raises_when_empty(self):
        with self.assertRaisesRegex(RuntimeError, "未找到绑定设备"):
            select_default_device([])


class FormatHttpErrorTests(unittest.TestCase):
    def test_401_error_mentions_reset(self):
        err = Exception("unauthorized")
        err.response = type("Response", (), {"status_code": 401, "text": "bad credentials"})()

        self.assertEqual(
            format_http_error(err),
            "账号或密码错误（401）。运行 --reset-credentials 或更新环境变量后重新输入。",
        )

    def test_error_includes_response_text(self):
        err = Exception("server error")
        err.response = type("Response", (), {"status_code": 500, "text": "boom"})()

        self.assertEqual(format_http_error(err), "服务器返回错误 500：boom")

    def test_long_response_text_is_truncated(self):
        err = Exception("server error")
        err.response = type("Response", (), {"status_code": 500, "text": "x" * 600})()

        message = format_http_error(err)

        self.assertLess(len(message), 560)
        self.assertTrue(message.endswith("..."))


if __name__ == "__main__":
    unittest.main()

import unittest
from io import StringIO
from unittest.mock import patch

from scripts.push_to_device import _resolve_file_meta, reset_credentials, upload_file


class FakeJsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload

    def post(self, *args, **kwargs):
        return FakeJsonResponse(self.payload)


class ResolveFileMetaTests(unittest.TestCase):
    def test_known_epub_goes_to_books(self):
        self.assertEqual(
            _resolve_file_meta(".epub"),
            ("application/epub+zip", "uploads/book", "/Pushed Books"),
        )

    def test_known_image_goes_to_images(self):
        self.assertEqual(
            _resolve_file_meta(".xth"),
            ("application/octet-stream", "uploads/image", "/Pushed Images"),
        )

    def test_unknown_file_uses_mimetype_and_files_folder(self):
        self.assertEqual(
            _resolve_file_meta(".pdf"),
            ("application/pdf", "uploads/file", "/Pushed Files"),
        )


class ResetCredentialsTests(unittest.TestCase):
    def test_reset_credentials_warns_when_env_credentials_remain(self):
        with (
            patch("scripts.push_to_device._reset_credentials_file", return_value=False),
            patch("scripts.push_to_device.env_credentials_status", return_value=("OK", "")),
            patch("sys.stdout", new_callable=StringIO) as stdout,
        ):
            reset_credentials()

        self.assertIn("仍检测到环境变量凭证", stdout.getvalue())

    def test_reset_credentials_warns_when_env_credentials_are_partial(self):
        with (
            patch("scripts.push_to_device._reset_credentials_file", return_value=False),
            patch(
                "scripts.push_to_device.env_credentials_status",
                return_value=("INVALID", "环境变量 XTEINK_USERNAME/XTEINK_PASSWORD 必须同时设置"),
            ),
            patch("sys.stdout", new_callable=StringIO) as stdout,
        ):
            reset_credentials()

        self.assertIn("环境变量凭证不完整", stdout.getvalue())


class UploadFileTests(unittest.TestCase):
    def test_upload_signature_requires_oss_fields(self):
        session = FakeSession({"success": True, "host": "https://oss.example"})

        with (
            patch("sys.stdout", new_callable=StringIO),
            self.assertRaisesRegex(RuntimeError, "download_url"),
        ):
            upload_file(
                session,
                "token",
                {"id": "dev", "type": "ESP32C3"},
                b"data",
                "card.xth",
                "application/octet-stream",
                "md5",
                4,
                "uploads/image",
            )

    def test_oss_http_status_is_checked(self):
        session = FakeSession({
            "success": True,
            "host": "https://oss.example",
            "content_type": "application/octet-stream",
            "download_url": "https://download.example/card.xth",
        })
        oss_response = type(
            "OssResponse",
            (),
            {
                "text": "",
                "raise_for_status": lambda self: (_ for _ in ()).throw(RuntimeError("oss failed")),
            },
        )()

        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("scripts.push_to_device.requests.post", return_value=oss_response),
            self.assertRaisesRegex(RuntimeError, "oss failed"),
        ):
            upload_file(
                session,
                "token",
                {"id": "dev", "type": "ESP32C3"},
                b"data",
                "card.xth",
                "application/octet-stream",
                "md5",
                4,
                "uploads/image",
            )


if __name__ == "__main__":
    unittest.main()

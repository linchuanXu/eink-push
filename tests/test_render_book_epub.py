import tempfile
import unittest
from pathlib import Path

from ebooklib import epub
from PIL import Image

from scripts.epub.render_book_epub import (
    download_image,
    embed_images,
    split_chapters,
    strip_leading_heading,
    validate_epub_options,
)


class SplitChaptersTests(unittest.TestCase):
    def test_preserves_preface_before_first_h2(self):
        chapters = split_chapters("# 书名\n\n开场白\n\n## 第一章\n\n正文")

        self.assertEqual(chapters[0], ("书名", "开场白"))
        self.assertEqual(chapters[1], ("第一章", "正文"))

    def test_skips_standalone_h1_preface(self):
        chapters = split_chapters("# 书名\n\n## 第一章\n\n正文")

        self.assertEqual(chapters, [("第一章", "正文")])

    def test_ignores_h2_inside_fenced_code(self):
        chapters = split_chapters("```markdown\n## Not a chapter\n```\n\n## 正文\n内容")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0][0], "前言")
        self.assertEqual(chapters[1][0], "正文")

    def test_strip_leading_heading_removes_duplicate_title(self):
        self.assertEqual(strip_leading_heading("## 第一章\n\n正文", "第一章"), "正文")
        self.assertEqual(strip_leading_heading("## 另一章\n\n正文", "第一章"), "## 另一章\n\n正文")


class LocalImageTests(unittest.TestCase):
    def make_png(self, path: Path) -> None:
        img = Image.new("RGB", (10, 10), (255, 255, 255))
        img.save(path, format="PNG")

    def test_download_image_resolves_relative_to_markdown_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "images" / "cover.png"
            image_path.parent.mkdir()
            self.make_png(image_path)

            data = download_image("images/cover.png", base_dir=root)

        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

    def test_embed_images_uses_markdown_directory_for_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "images" / "cover.png"
            image_path.parent.mkdir()
            self.make_png(image_path)
            book = epub.EpubBook()

            markdown, count, total_bytes = embed_images(
                "![cover](images/cover.png)",
                book,
                base_dir=root,
            )

        self.assertEqual(count, 1)
        self.assertGreater(total_bytes, 0)
        self.assertIn("images/img_", markdown)


class EpubOptionValidationTests(unittest.TestCase):
    def test_valid_image_options_pass(self):
        self.assertEqual(validate_epub_options(88, 480), [])

    def test_invalid_image_options_are_reported(self):
        errors = validate_epub_options(0, 0)

        self.assertIn("--image-quality 必须在 1..100 之间", errors)
        self.assertIn("--image-width 必须大于 0", errors)


if __name__ == "__main__":
    unittest.main()

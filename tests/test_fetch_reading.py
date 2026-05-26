import unittest

from scripts.fetch_reading import apply_output_options, clean_book_name, compact_book, compact_bookmark


class CleanBookNameTests(unittest.TestCase):
    def test_removes_epub_extension(self):
        self.assertEqual(clean_book_name("悉达多.epub"), "悉达多")

    def test_removes_zlibrary_timestamp_watermark(self):
        self.assertEqual(
            clean_book_name("百年孤独_20260328-1726_2026-03-28.epub"),
            "百年孤独",
        )

    def test_removes_zlibrary_parenthetical_watermark(self):
        self.assertEqual(clean_book_name("人类简史 (Z-Library).txt"), "人类简史")


class CompactOutputTests(unittest.TestCase):
    def test_compact_book_keeps_display_fields(self):
        book = compact_book({
            "book_name": "百年孤独_20260328-1726.epub",
            "progress_percent": 82,
            "duration_seconds": 3600,
            "extra": "ignored",
        })

        self.assertEqual(book["clean_name"], "百年孤独")
        self.assertEqual(book["progress_percent"], 82)
        self.assertEqual(book["duration_seconds"], 3600)
        self.assertNotIn("extra", book)

    def test_compact_bookmark_keeps_display_fields(self):
        mark = compact_bookmark({
            "book_name": "悉达多.epub",
            "chapter_title": "河边",
            "chapter_index": 3,
            "content": "这是一条摘录",
            "extra": "ignored",
        })

        self.assertEqual(mark["clean_name"], "悉达多")
        self.assertEqual(mark["chapter_title"], "河边")
        self.assertEqual(mark["content"], "这是一条摘录")
        self.assertNotIn("extra", mark)

    def test_apply_output_options_limits_and_marks_truncated(self):
        result = {
            "success": True,
            "books": [
                {"book_name": "A.epub"},
                {"book_name": "B.epub"},
                {"book_name": "C.epub"},
            ],
        }

        out = apply_output_options(result, collection_key="books", compact=True, limit=2)

        self.assertEqual([book["clean_name"] for book in out["books"]], ["A", "B"])
        self.assertEqual(out["returned"], 2)
        self.assertEqual(out["available_in_response"], 3)
        self.assertTrue(out["truncated"])
        self.assertEqual(len(result["books"]), 3)

    def test_apply_output_options_unlimited_is_not_truncated(self):
        result = {"bookmarks": [{"book_name": "A.epub", "content": "x"}]}

        out = apply_output_options(result, collection_key="bookmarks", compact=True, limit=0)

        self.assertEqual(out["returned"], 1)
        self.assertFalse(out["truncated"])


if __name__ == "__main__":
    unittest.main()

import struct
import unittest
from io import BytesIO

from scripts.render_image import (
    _HEADER_SIZE,
    _INDEX_ENTRY,
    _META_SIZE,
    assess_html_layout,
    assess_rendered_png,
    encode_xtc,
    encode_xtch,
    HtmlLayoutWarning,
    should_block_push,
    validate_render_options,
    XtgXthParams,
)


def fake_page(width=10, height=8, payload=b"abc"):
    header = struct.pack("<IHHBBIII", 0x00475458, width, height, 0, 0, len(payload), 0, 0)
    return header + payload


class HtmlLayoutAssessmentTests(unittest.TestCase):
    def test_clean_layout_has_no_warnings(self):
        self.assertEqual(
            assess_html_layout(
                {
                    "scrollWidth": 480,
                    "scrollHeight": 800,
                    "textLength": 20,
                    "backgroundColor": "rgb(255, 255, 255)",
                    "minFontPx": 30,
                },
                480,
                800,
            ),
            [],
        )

    def test_detects_common_layout_issues(self):
        warnings = assess_html_layout(
            {
                "scrollWidth": 520,
                "scrollHeight": 1200,
                "textLength": 0,
                "backgroundColor": "rgba(0, 0, 0, 0)",
                "minFontPx": 20,
            },
            480,
            800,
        )

        self.assertEqual(
            [w.code for w in warnings],
            [
                "empty-text",
                "horizontal-overflow",
                "heavy-vertical-overflow",
                "transparent-background",
            ],
        )

    def test_detects_small_font_when_text_is_present(self):
        warnings = assess_html_layout(
            {
                "scrollWidth": 480,
                "scrollHeight": 800,
                "textLength": 20,
                "backgroundColor": "rgb(255, 255, 255)",
                "minFontPx": 18,
            },
            480,
            800,
        )

        self.assertEqual([w.code for w in warnings], ["small-font"])

    def test_push_gate_blocks_only_dangerous_layouts(self):
        self.assertFalse(should_block_push([]))
        self.assertFalse(
            should_block_push(
                [HtmlLayoutWarning("vertical-overflow", "minor overflow")]
            )
        )
        warnings = assess_html_layout(
            {
                "scrollWidth": 640,
                "scrollHeight": 800,
                "textLength": 20,
                "backgroundColor": "rgb(255, 255, 255)",
                "minFontPx": 30,
            },
            480,
            800,
        )
        self.assertTrue(should_block_push(warnings))
        self.assertTrue(
            should_block_push([HtmlLayoutWarning("small-font", "font too small")])
        )


class RenderedPngAssessmentTests(unittest.TestCase):
    def make_png(self, pixels, size=(10, 10)):
        from PIL import Image

        img = Image.new("L", size)
        img.putdata(pixels)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_detects_blank_white_render(self):
        warnings = assess_rendered_png(self.make_png([255] * 100))
        self.assertEqual([w.code for w in warnings], ["blank-render"])

    def test_detects_low_contrast_render(self):
        pixels = [128] * 95 + [130] * 5
        warnings = assess_rendered_png(self.make_png(pixels))
        self.assertEqual([w.code for w in warnings], ["low-contrast-render"])

    def test_readable_contrast_has_no_warnings(self):
        pixels = [0, 255] * 50
        self.assertEqual(assess_rendered_png(self.make_png(pixels)), [])


class RenderOptionValidationTests(unittest.TestCase):
    def test_valid_defaults_pass(self):
        self.assertEqual(validate_render_options(480, 800, XtgXthParams()), [])

    def test_rejects_values_that_would_render_badly_or_crash(self):
        errors = validate_render_options(
            0,
            -1,
            XtgXthParams(
                brightness=101,
                contrast=-101,
                gamma=0,
                sharpen=101,
                dither=-1,
                threshold=300,
            ),
        )

        self.assertIn("--width 必须大于 0", errors)
        self.assertIn("--height 必须大于 0", errors)
        self.assertIn("--gamma 必须在 0.4..2.5 之间", errors)
        self.assertIn("--threshold 必须在 0..255 之间", errors)


class ContainerEncodingTests(unittest.TestCase):
    def test_container_requires_at_least_one_page(self):
        with self.assertRaisesRegex(ValueError, "至少需要 1 个页面"):
            encode_xtc([])

    def test_xtc_header_and_index_offsets_without_metadata(self):
        page1 = fake_page(width=10, height=8, payload=b"abc")
        page2 = fake_page(width=12, height=9, payload=b"defg")

        data = encode_xtc([page1, page2])
        magic, version, page_count, _, has_meta, has_thumbs, has_chapters, current_page = struct.unpack_from(
            "<IHHBBBBI", data, 0
        )
        meta_offset, index_offset, data_offset = struct.unpack_from("<QQQ", data, 16)

        self.assertEqual(magic, 0x00435458)
        self.assertEqual(version, 0x0100)
        self.assertEqual(page_count, 2)
        self.assertEqual((has_meta, has_thumbs, has_chapters, current_page), (0, 0, 0, 1))
        self.assertEqual(meta_offset, 0)
        self.assertEqual(index_offset, _HEADER_SIZE)
        self.assertEqual(data_offset, _HEADER_SIZE + 2 * _INDEX_ENTRY)

        offset1, size1, width1, height1 = struct.unpack_from("<QIHH", data, index_offset)
        offset2, size2, width2, height2 = struct.unpack_from("<QIHH", data, index_offset + _INDEX_ENTRY)
        self.assertEqual((offset1, size1, width1, height1), (data_offset, len(page1), 10, 8))
        self.assertEqual((offset2, size2, width2, height2), (data_offset + len(page1), len(page2), 12, 9))

    def test_xtch_header_with_metadata(self):
        page = fake_page()

        data = encode_xtch([page], title="标题", author="作者")
        magic, _, page_count, _, has_meta = struct.unpack_from("<IHHBB", data, 0)
        meta_offset, index_offset, data_offset = struct.unpack_from("<QQQ", data, 16)

        self.assertEqual(magic, 0x48435458)
        self.assertEqual(page_count, 1)
        self.assertEqual(has_meta, 1)
        self.assertEqual(meta_offset, _HEADER_SIZE)
        self.assertEqual(index_offset, _HEADER_SIZE + _META_SIZE)
        self.assertEqual(data_offset, _HEADER_SIZE + _META_SIZE + _INDEX_ENTRY)

    def test_metadata_truncation_preserves_utf8_boundaries(self):
        page = fake_page()

        data = encode_xtch([page], title="标题" * 100, author="作者" * 100)
        meta = data[_HEADER_SIZE:_HEADER_SIZE + _META_SIZE]
        title = meta[:128].split(b"\x00", 1)[0]
        author = meta[128:192].split(b"\x00", 1)[0]

        title.decode("utf-8")
        author.decode("utf-8")


if __name__ == "__main__":
    unittest.main()

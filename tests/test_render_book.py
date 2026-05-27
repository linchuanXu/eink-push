import unittest

from scripts.render_book import (
    _parse_node_version,
    convert_markdown_tables_to_text,
    preprocess_markdown,
)


class NodeVersionTests(unittest.TestCase):
    def test_parse_node_version(self):
        self.assertEqual(_parse_node_version("v22.19.0"), (22, 19, 0))
        self.assertEqual(_parse_node_version("18"), (18, 0, 0))
        self.assertIsNone(_parse_node_version("not node"))


class PreprocessMarkdownTests(unittest.TestCase):
    def test_frontmatter_title_becomes_heading(self):
        md = "---\ntitle: 测试书\nsummary: 简短说明\n---\n正文"

        self.assertEqual(
            preprocess_markdown(md),
            "# 测试书\n\n简短说明\n\n正文",
        )

    def test_frontmatter_skips_style_and_keeps_colons(self):
        md = "---\ntitle: 测试\nstyle: compact\nsource: https://example.com/a:b\n---\n正文"

        self.assertEqual(
            preprocess_markdown(md),
            "# 测试\n\nhttps://example.com/a:b\n\n正文",
        )

    def test_gfm_table_converts_to_list(self):
        md = "| 名称 | 说明 |\n| --- | --- |\n| A | Alpha |\n| B | Beta |"

        self.assertEqual(
            preprocess_markdown(md),
            "- **名称**：A ｜ **说明**：Alpha\n- **名称**：B ｜ **说明**：Beta\n",
        )

    def test_fenced_code_block_table_is_unchanged(self):
        md = "```markdown\n| A | B |\n| --- | --- |\n| 1 | 2 |\n```"

        self.assertEqual(preprocess_markdown(md), md)

    def test_public_table_converter_matches_preprocess_table_step(self):
        md = "| 指标 | 数值 |\n| --- | --- |\n| 阅读 | 7h |"

        self.assertEqual(
            convert_markdown_tables_to_text(md),
            "- **指标**：阅读 ｜ **数值**：7h\n",
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from scripts.render_book import preprocess_markdown


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


if __name__ == "__main__":
    unittest.main()

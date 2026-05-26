# Agent 工作流细节

本文档供 `SKILL.md` 在需要具体执行步骤时读取。所有命令默认在 Skill 根目录执行。

---

## 推送卡片

适用于 ≤2000 字内容；≤200 字通常做单张卡片，200-2000 字做多张翻页卡片集。卡片是截图，不是文章排版；连续长文优先走 Markdown 电子书。

设计规范见 `references/design-guide.md`，样本见 `references/framework-samples/`。通常直接按规范写 HTML，用户明确指定风格时再查样本。

HTML 要点：

- 文件名：`output/{主题词}_{YYYYMMDD-HHMM}.html`。
- 多张：`output/{主题词}_p1_{时间戳}.html`、`_p2_`。
- `body` 建议：`width:100vw; height:100vh; overflow:hidden; margin:0; padding:0`。
- 起点模板：`assets/templates/base.html`。

推送命令：

```bash
# 单张
python scripts/render_image.py "output/文件名.html" --push

# 多张
python scripts/render_image.py "output/主题_p1_时间戳.html" "output/主题_p2_时间戳.html" --title "标题" --author "龙虾" --push
```

成功后告诉用户：已推送到阅星曈，设备上即可接收。

成功渲染会输出 `OUTPUT:<path>`，以该行作为生成产物路径。

预览策略：开发调试或排障时可加 `--preview` 生成 `.preview.png`；正式 Skill 推送命令默认不带 `--preview`，避免 `output/` 长期堆积预览图。

---

## 推送 Markdown 电子书

适用于 >2000 字、连续长文、多节论述。

Markdown 要点：

- 文件名：`output/{主题词}_{YYYYMMDD-HHMM}.md`，主题词 ≤10 字。
- 禁止主动写 GFM 表格；改用列表、加粗标签或缩进文本。
- `render_book.py` 会兜底把表格转为列表，但人工组织的列表更清晰。

命令：

```bash
python scripts/render_book.py "output/文件名.md" --title "标题" --author "龙虾" --push
```

成功渲染会输出 `OUTPUT:<path>`，以该行作为生成的 `.xtc` 路径。

---

## 推送 EPUB

仅当用户明确提到“EPUB / epub 格式 / 推 EPUB / 生成 EPUB”时使用。适合图文混排、需要封面、希望进入设备电子书阅读器的内容。

命令：

```bash
# 基础
python scripts/epub/render_book_epub.py "output/文件名.md" --title "标题" --author "龙虾" --push

# 推荐：带 SVG 封面
python scripts/epub/render_book_epub.py "output/文件名.md" --title "标题" --author "龙虾" --cover-svg --push

# 带副标题
python scripts/epub/render_book_epub.py "output/文件名.md" --title "标题" --subtitle "副标题" --author "龙虾" --cover-svg --push
```

成功生成会输出 `OUTPUT:<path>`，以该行作为生成的 `.epub` 路径。

封面主题：`tech`、`business`、`design`、`literature`、`science`、`personal`。封面布局：`minimal`、`classic`、`modern`。

---

## 查书架

```bash
python scripts/fetch_reading.py books [--keyword 关键词] [--format epub|txt] [--per-page 50] --compact --limit 50
```

解析 stdout JSON。展示时：

- 使用 `clean_name`，不要直接展示带水印的 `book_name`。
- 时长转为“X 分钟 / X 小时 Y 分钟”。
- 时间戳转为“M月D日”。
- 展示最近活跃书籍。

展示后可以询问是否生成：

- 书摘卡片。
- 阅读笔记电子书。
- 阅读看板卡片。

---

## 查书签

指定书：

```bash
python scripts/fetch_reading.py bookmarks --keyword "完整book_name原始值" --all --compact --limit 100
```

全部书签：

```bash
python scripts/fetch_reading.py bookmarks --all --compact --limit 100
```

注意：指定书时 `--keyword` 传原始 `book_name`，不是 `clean_name`。脚本已过滤“(本章结束)”占位符。
需要完整整理时可去掉 `--limit`；需要服务端原始字段时去掉 `--compact`。

---

## 书摘卡片

1. 拉取书签。
2. AI 选 3-8 条精彩摘录，跳过 <15 字或重复内容。
3. 每张卡片 1-3 条，大号引文 + 细体来源。
4. 写 HTML：`output/{clean_name}_摘录_p1_{YYYYMMDD-HHMM}.html`。
5. 推送：

```bash
python scripts/render_image.py "output/书名_摘录_p1_时间戳.html" "output/书名_摘录_p2_时间戳.html" --title "《书名》书摘" --author "龙虾" --push
```

---

## 阅读笔记电子书

1. 拉取书签。
2. 按 `chapter_index` 升序，同章归在同一 `##` 下。
3. `chapter_title` 为空时用“第 N 章”占位。
4. 写 Markdown：`output/{clean_name}_笔记_{YYYYMMDD-HHMM}.md`。
5. 推送：

```bash
python scripts/render_book.py "output/书名_笔记_时间戳.md" --title "《书名》阅读笔记" --author "龙虾" --push
```

---

## 阅读看板卡片

1. 拉取书架。
2. 统计：
   - 正在读：`progress_percent` 1-99。
   - 已读完：`progress_percent == 100`。
   - 总时长：所有书 `duration_seconds` 之和。
   - 最近活跃：按 `last_uploaded_at` 排序取前 3-5。
3. 写 HTML：`output/阅读看板_{YYYYMMDD-HHMM}.html`。
4. 推送：

```bash
python scripts/render_image.py "output/阅读看板_时间戳.html" --push
```

---

## 联网搜索调研

适用于阅星曈 Skill 场景中的实时资料查询，尤其是用户希望搜索结果继续做成卡片或电子书时。

```bash
python scripts/search_query.py "查询内容"
python scripts/search_query.py "查询内容" --system-prompt "用简洁中文回答，重点列出关键事实"
```

解析 stdout JSON，优先展示：

- 主体回答：`answer` / `content` / `result`。
- 引用来源：`citations` / `references` / `sources`。

如果字段结构不符预期，展示原始 JSON 并说明需要人工确认。

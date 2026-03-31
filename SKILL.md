---
name: eink_push
description: 将内容渲染并推送到阅星曈墨水屏设备（支持卡片和电子书），或从设备拉取阅读数据（书架 / 书签）。当用户说「发到阅星曈 / 推到设备 / 发到墨水屏 / 推一下 / 同步到设备 / 发给阅星曈 / 推送内容 / 发到阅读器」，或任务完成后要求推送、交付、发送到墨水屏时触发；当用户说「我的书架 / 我在读什么 / 阅读进度 / 书签 / 摘录 / 读书笔记 / 阅读报告 / 高亮」等阅读数据查询时也触发。
metadata: {"openclaw": {"emoji": "🖤", "requires": {"bins": ["python"]}}}
---

# 阅星曈推送 Skill

将任务产出推送到阅星曈墨水屏设备。支持单张卡片、多张卡片集、电子书三种格式，按内容字数自动分流。

> 首次使用或环境报错，见 `references/SETUP.md`。

---

## 分流规则

| 字数 | 格式 | 说明 |
|------|------|------|
| ≤200 字 | 单张卡片 `.xth` | 一屏 PPT / 仪表盘 / 资讯卡 |
| 200–2000 字 | 多张卡片集 `.xtch` | 每张一主题，宁多勿挤 |
| >2000 字 / 连续长文 | 电子书 `.epub` | 多节论述、报告体、适合滚屏读 |

**卡片是「截图」，不是文章排版。** 连续阅读的内容 → epub。卡片设计规范见 `references/design-guide.md`。

---

## 工作目录

以下所有命令以本 `SKILL.md` 所在目录为根目录执行（`{baseDir}`）。

---

## 凭证预检（每次推送前必做）

```bash
python {baseDir}/scripts/push_to_device.py --check-credentials
```

- 输出 `OK` → 继续
- 输出 `MISSING` → 询问用户手机号和密码，用 Write 工具写入 `{baseDir}/.credentials.json`：
  ```json
  { "username": "手机号", "password": "密码" }
  ```
- 推送返回 401 → `python {baseDir}/scripts/push_to_device.py --reset-credentials` 后重新询问

---

## 卡片路径（单张 ≤200 字 / 多张 200–2000 字）

**第 1 步：写 HTML**

| 项目 | 说明 |
|------|------|
| 单张文件名 | `output/{主题词}_{YYYYMMDD-HHMM}.html` |
| 多张文件名 | `output/{主题词}_p1_{时间戳}.html`、`_p2_`… |
| canvas 写法 | `body { width:100vw !important; height:100vh !important; max-width:none !important; min-height:0 !important; overflow:hidden !important; margin:0 !important; padding:0 !important; }` |
| 起点模板 | Read `{baseDir}/assets/templates/base.html` |
| 设计规范 | `{baseDir}/references/design-guide.md` |

**第 2 步：渲染**

```bash
# 单张
python {baseDir}/scripts/render_image.py "output/文件名.html"

# 多张（自动打包为 .xtch）
python {baseDir}/scripts/render_image.py "output/主题_p1_时间戳.html" "output/主题_p2_时间戳.html" --title "标题" --author "龙虾"
```

**第 3 步：推送**

```bash
python {baseDir}/scripts/push_to_device.py "output/文件名.xth"    # 单张
python {baseDir}/scripts/push_to_device.py "output/主题_时间戳.xtch"  # 多张
```

---

## 电子书路径（>2000 字 / 连续长文）

**第 1 步：整理为 Markdown**

文件命名：`output/{主题词}_{YYYYMMDD-HHMM}.md`，主题词 ≤10 字，跟随用户语言。

**第 2 步：生成电子书**

```bash
python {baseDir}/scripts/render_book.py "output/文件名.md" --title "标题" --author "龙虾"
```

**第 3 步：推送**

```bash
python {baseDir}/scripts/push_to_device.py "output/文件名.epub"
```

---

## 阅读器数据拉取

当用户说「我的书架 / 我在读什么 / 阅读进度 / 书签 / 摘录 / 读书笔记 / 阅读报告 / 高亮」等，或在书摘/笔记/看板相关请求中需要先获取设备数据时触发本节。

所有工作流均需先通过凭证预检（见上文）。

---

### D1 — 查书架

```bash
python {baseDir}/scripts/fetch_reading.py books [--keyword 关键词] [--format epub|txt]
```

- 解析 stdout JSON，使用每本书的 `clean_name` 字段作为展示书名
- `duration_seconds` 转换为分钟/小时后再呈现
- `progress_percent` 直接展示进度百分比
- 向用户自然语言回复书架内容，询问是否要生成阅读看板卡片（→ 工作流 C）

---

### D2 — 查书签

```bash
# 查单本书的全部书签（推荐传完整 book_name，如响应中的 book_name 字段原值）
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name" --all

# 查全部书签（不限书）
python {baseDir}/scripts/fetch_reading.py bookmarks --all
```

- 解析 stdout JSON，`bookmarks` 已自动过滤「(本章结束)」占位符
- 使用 `clean_name` 字段展示书名，`chapter_title` 展示章节
- 向用户自然语言呈现书签内容，询问是否要生成书摘卡片（→ 工作流 A）或阅读笔记 EPUB（→ 工作流 B）

---

### A — 书摘卡片

从书签生成精美引言卡片，推回设备。

**第 1 步：拉取书签**

```bash
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name" --all
```

**第 2 步：AI 挑选摘录，写 HTML**

- 从 `bookmarks` 中挑选精彩句子（通常 3–8 条）
- 每张卡片放 1–3 条摘录，引言排版：大号引文 + 细体来源（书名 / 章节）
- 文件命名：`output/{书名}_摘录_p1_{YYYYMMDD-HHMM}.html`、`_p2_`…
- 设计规范同卡片路径（见 `{baseDir}/references/design-guide.md`）

**第 3 步：渲染 + 推送**

```bash
python {baseDir}/scripts/render_image.py "output/书名_摘录_p1_时间戳.html" "output/书名_摘录_p2_时间戳.html" --title "《书名》书摘" --author "龙虾"
python {baseDir}/scripts/push_to_device.py "output/书名_摘录_时间戳.xtch"
```

---

### B — 阅读笔记 EPUB

将一本书的所有书签整理为带目录的 EPUB，推回设备。

**第 1 步：拉取书签**

```bash
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name" --all
```

**第 2 步：AI 整理为 Markdown**

- 按 `chapter_index` 升序排列，相同章节的摘录归在同一 `##` 标题下
- 文件格式：

```markdown
# 《书名》阅读笔记

## 章节标题（chapter_title）

> 摘录原文（content）

> 摘录原文

## 下一章节…
```

- 文件命名：`output/{书名}_笔记_{YYYYMMDD-HHMM}.md`

**第 3 步：生成 EPUB + 推送**

```bash
python {baseDir}/scripts/render_book.py "output/书名_笔记_时间戳.md" --title "《书名》阅读笔记" --author "龙虾"
python {baseDir}/scripts/push_to_device.py "output/书名_笔记_时间戳.epub"
```

---

### C — 阅读看板卡片

生成个人阅读状态一览卡，推回设备。

**第 1 步：拉取书架**

```bash
python {baseDir}/scripts/fetch_reading.py books --per-page 50
```

**第 2 步：AI 统计并写 HTML**

统计维度（按需选取，不必全用）：
- 正在读（`progress_percent` 在 1–99 之间）
- 已读完（`progress_percent == 100`）
- 总阅读时长（所有书 `duration_seconds` 之和，转小时）
- 最近活跃书目（按 `last_uploaded_at` 排序取前 3–5 本）

版式建议：仪表盘 / 多栏卡片，突出"正在读"和"总时长"，参考设计规范。文件命名：`output/阅读看板_{YYYYMMDD-HHMM}.html`

**第 3 步：渲染 + 推送**

```bash
python {baseDir}/scripts/render_image.py "output/阅读看板_时间戳.html"
python {baseDir}/scripts/push_to_device.py "output/阅读看板_时间戳.xth"
```

---

## 推送完成后

- 卡片：`已将「标题」渲染为卡片，推送到阅星曈，设备上即可接收。`
- 电子书：`已将《标题》打包为电子书，推送到阅星曈，设备上即可接收。`

失败时见 `references/TROUBLESHOOTING.md`。首次推送成功后，告知常用触发方式（见 `references/ONBOARDING-COPY.md`）。

---

## 主动询问规则

任务完成后，产出超过 100 字，无论用户是否提及阅星曈，都在回复末尾追加：

```
---
要把这份内容推送到阅星曈吗？
• 卡片（简报 / 仪表盘式版式，宜拆多张；不是长文章排版）
• 电子书（长文、多节论述 → Markdown 转 epub）
```

**阅读数据场景额外追问：** 展示完书签摘录或书架数据后，在回复末尾追加：

```
---
要根据这些数据生成内容推回阅星曈吗？
• 书摘卡片（精选摘录 → 引言排版卡片集）
• 阅读笔记 EPUB（所有书签按章节整理 → 电子书）
• 阅读看板卡片（书架统计 → 仪表盘卡片）
```

**不询问的情况：** 用户只是在问问题 / 已明确说不用推 / 本次任务本身就是在执行推送或拉取流程。

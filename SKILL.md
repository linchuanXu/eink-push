---
name: eink_push
description: 推送内容到阅星曈墨水屏（卡片 / 电子书），或拉取书架、书签等阅读数据。
metadata: {"openclaw": {"emoji": "🖤", "requires": {"bins": ["python"]}}}
---

# 阅星曈 Skill

推送内容到阅星曈墨水屏设备，或从设备拉取阅读数据。

**推送**：将任务产出渲染为单张卡片、多张卡片集或电子书，按内容字数自动分流后推送。  
**拉取**：查询书架（进度 / 时长）、书签摘录，并可进一步生成书摘卡片、阅读笔记 EPUB、阅读看板卡片推回设备。

以下所有命令以本 `SKILL.md` 所在目录为根目录执行（`{baseDir}`）。首次使用或环境报错，见 `references/SETUP.md`。

## 触发条件

**推送触发**：用户说「发到阅星曈 / 推到设备 / 发到墨水屏 / 推一下 / 同步到设备 / 发给阅星曈 / 推送内容 / 发到阅读器」，或任务完成后要求推送 / 交付 / 发送到墨水屏。

**拉取触发**：用户说「我的书架 / 我在读什么 / 阅读进度 / 读了哪些书 / 书签 / 摘录 / 读书笔记 / 阅读报告 / 高亮」等阅读数据查询。

---

## 凭证预检（每次操作前必做）

```bash
python {baseDir}/scripts/push_to_device.py --check-credentials
```

- 输出 `OK` → 继续
- 输出 `MISSING` → 询问用户手机号和密码，用 Write 工具写入 `{baseDir}/.credentials.json`：
  ```json
  { "username": "手机号", "password": "密码" }
  ```
- 操作返回 401 → `python {baseDir}/scripts/push_to_device.py --reset-credentials` 后重新询问

---

## 意图决策表

| 用户意图 | 工作流 | 说明 |
|----------|--------|------|
| 任务结束后说"发到阅星曈 / 推到设备 / 推一下" | 按字数分流 → 卡片或电子书 | 见推送「分流规则」 |
| 明确说"做成卡片 / 生成简报 / 卡片形式" | 推送：卡片路径 | 不看字数，直接走卡片 |
| 明确说"做成电子书 / 生成 epub / 电子书形式" | 推送：电子书路径 | 不看字数，直接走电子书 |
| "我的书架 / 我在读什么 / 阅读进度 / 读了哪些书" | D1 — 查书架 | |
| "书签 / 摘录 / 高亮 / 划线"（有指定书名） | D2 — 查书签 | 传完整 `book_name` 精确匹配 |
| "书签 / 摘录 / 高亮 / 划线"（未指定书名） | D1 → 用户选书 → D2 | 先查书架，让用户选目标书 |
| "把书签做成卡片 / 书摘卡片 / 精选摘录" | A — 书摘卡片 | |
| "整理阅读笔记 / 笔记 EPUB / 书签整理成书" | B — 阅读笔记 EPUB | |
| "阅读报告 / 阅读看板 / 阅读统计" | C — 阅读看板卡片 | |

### ⚠️ 易混淆场景

| 用户说的 | 可能意图 | 正确处理 |
|----------|----------|----------|
| "发到阅星曈"（对话中无明确内容产出） | 不明确推送什么 | 询问用户要推送什么内容 |
| "书签"（未指定书名） | 不明确是哪本书 | 先执行 D1 查书架，展示书目让用户选择 |
| "做个阅读笔记" | 可能是笔记 EPUB 或书摘卡片 | 询问："整理为电子书（按章节排列）还是卡片（精选摘录）？" |
| "把书签推到设备" | 格式未指定 | 询问："做成翻页卡片集还是 EPUB 电子书？" |
| "推送一下"（当前对话产出不足 50 字） | 内容极短，推送意义不大 | 确认是否仍要推送，或建议补充内容 |

**核心判断原则：**
- 能确定内容和格式 → 直接执行，不要过多询问
- 能确定内容，但格式不明确 → 询问格式（卡片 / 电子书）
- 内容不明确（如"书签"未指定书） → 先拉取数据让用户确认
- 什么都不明确 → 逐步引导，每次只问一个问题

---

## 推送：卡片路径

适用于 ≤200 字（单张）或 200–2000 字（多张卡片集）的内容。

**分流规则**

| 字数 | 格式 | 说明 |
|------|------|------|
| ≤200 字 | 单张卡片 `.xth` | 一屏 PPT / 仪表盘 / 资讯卡 |
| 200–2000 字 | 多张卡片集 `.xtch` | 每张一主题，宁多勿挤 |

**卡片是「截图」，不是文章排版。** 需要连续阅读的内容 → 走电子书路径。卡片设计规范见 `{baseDir}/references/design-guide.md`。

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
python {baseDir}/scripts/push_to_device.py "output/文件名.xth"       # 单张
python {baseDir}/scripts/push_to_device.py "output/主题_时间戳.xtch" # 多张
```

---

## 推送：电子书路径

适用于 >2000 字 / 连续长文 / 多节论述 / 报告体内容。

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

## 拉取：阅读器数据

当用户意图指向书架或书签数据时触发本节。所有工作流均需先通过凭证预检。

---

### D1 — 查书架

```bash
python {baseDir}/scripts/fetch_reading.py books [--keyword 关键词] [--format epub|txt] [--per-page 50]
```

解析 stdout JSON 后，按「用户体验规则」中的书架格式向用户展示。展示后主动追问（见「主动询问规则」）。

---

### D2 — 查书签

```bash
# 查单本书的全部书签（--keyword 传 book_name 字段的原始值，不是 clean_name）
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name原始值" --all

# 查全部书签（不限书）
python {baseDir}/scripts/fetch_reading.py bookmarks --all
```

`bookmarks` 已自动过滤「(本章结束)」占位符。解析后按「用户体验规则」中的书签格式展示，展示后主动追问。

---

### A — 书摘卡片

从书签生成精美引言卡片，推回设备。

**第 1 步：拉取书签**

```bash
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name原始值" --all
```

**第 2 步：AI 挑选摘录，写 HTML**

- 从 `bookmarks` 中挑选精彩句子（通常 3–8 条），跳过过短（<15 字）或重复的条目
- 每张卡片放 1–3 条摘录，引言排版：大号引文 + 细体来源（书名 / 章节名）
- 文件命名：`output/{clean_name}_摘录_p1_{YYYYMMDD-HHMM}.html`、`_p2_`…
- 设计规范见 `{baseDir}/references/design-guide.md`

**第 3 步：渲染 + 推送**

```bash
python {baseDir}/scripts/render_image.py "output/书名_摘录_p1_时间戳.html" "output/书名_摘录_p2_时间戳.html" --title "《书名》书摘" --author "龙虾"
python {baseDir}/scripts/push_to_device.py "output/书名_摘录_时间戳.xtch"
```

---

### B — 阅读笔记 EPUB

将一本书的所有书签按章节整理为带目录的 EPUB，推回设备。

**第 1 步：拉取书签**

```bash
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name原始值" --all
```

**第 2 步：AI 整理为 Markdown**

- 按 `chapter_index` 升序排列，同一章节的摘录归在同一 `##` 标题下
- `chapter_title` 为空时，用「第 N 章」占位

```markdown
# 《书名》阅读笔记

## 章节标题

> 摘录原文

> 摘录原文

## 下一章节…
```

文件命名：`output/{clean_name}_笔记_{YYYYMMDD-HHMM}.md`

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

| 维度 | 数据来源 | 说明 |
|------|----------|------|
| 正在读 | `progress_percent` 在 1–99 之间 | |
| 已读完 | `progress_percent == 100` | |
| 总阅读时长 | 所有书 `duration_seconds` 之和 | 转换为小时展示 |
| 最近活跃 | 按 `last_uploaded_at` 排序取前 3–5 本 | |

版式建议：仪表盘 / 多栏卡片，突出「正在读」和「总时长」，参考设计规范。  
文件命名：`output/阅读看板_{YYYYMMDD-HHMM}.html`

**第 3 步：渲染 + 推送**

```bash
python {baseDir}/scripts/render_image.py "output/阅读看板_时间戳.html"
python {baseDir}/scripts/push_to_device.py "output/阅读看板_时间戳.xth"
```

---

## 用户体验规则

### 精简进度

不向用户暴露内部步骤（"正在获取上传签名… 正在上传到 OSS…"），只报告用户关心的节点：

- 推送：`"正在推送「标题」…"` → `"已推送到阅星曈，设备上即可接收。"`
- 拉取：`"正在读取书架…"` → 直接展示结果，不逐步播报翻页进度

### 隐藏内部字段

面向用户的展示中**不暴露** `book_name`（原始文件名）、`device_id`、`user_id`、`chapter_path` 等内部字段。始终使用：
- 书名 → `clean_name`
- 阅读时长 → 转换为「X 分钟」或「X 小时 Y 分钟」
- 时间戳 → 转换为「M月D日」或「X天前」

### 书架展示格式

```
你的书架（共 N 本）：

1. 悉达多 — 进度 50%，已读 2 分钟
2. 百年孤独 — 进度 82%，已读 3.5 小时
3. 人类简史 — 进度 100%，已读 8 小时  ✓ 已读完

最近活跃：悉达多（3月30日同步）
```

### 书签展示格式

```
《百年孤独》的书签（共 12 条）：

家族谱系图（第 1 章）
  与情人蓄养的牲畜以惊人的速度繁殖，使其成为马孔多首富。

冰块的发明（第 2 章）
  世界如此新鲜，许多东西尚无名称，提到时不得不用手指点。

……（共 12 条）
```

---

## 错误处理

| 错误 | 处理方式 |
|------|----------|
|| `[CREDENTIALS_MISSING]` 或退出码 2 | 凭证文件缺失或字段不全，走凭证预检流程重新收集 |
|| `[CREDENTIALS_MISSING]` 或退出码 2 | 凭证文件缺失或字段不全，走凭证预检流程重新收集 |
|| HTTP 401 | 告知用户"账号或密码有误"，运行 `--reset-credentials`，重新收集 |
| 未找到绑定设备 | "未找到绑定设备，请先在阅星曈 App 中绑定设备" |
| `[ERROR] Playwright 未安装` | 引导用户执行 `pip install playwright && playwright install chromium` |
| `[ERROR] ebooklib 未安装` | 引导用户执行 `pip install ebooklib markdown Pillow` |
| 其他错误 | 将脚本完整报错原文展示给用户，说明需要手动排查 |

---

## 主动询问规则

**通用产出场景**：本次任务产出的是「可发布型」内容（报告、摘要、文章、创作、分析、计划），且用户未提及推送，在回复末尾追加：

```
---
要把这份内容推送到阅星曈吗？
• 卡片（简报 / 仪表盘版式，宜拆多张；不适合长文排版）
• 电子书（长文、多节论述 → Markdown 转 epub）
```

**阅读数据场景**：展示完书签或书架数据后，在回复末尾追加：

```
---
要根据这些数据生成内容推回阅星曈吗？
• 书摘卡片（精选摘录 → 引言排版卡片集）
• 阅读笔记 EPUB（所有书签按章节整理 → 电子书）
• 阅读看板卡片（书架统计 → 仪表盘卡片）
```

**不询问的情况：**
- 用户只是在问问题，没有产出内容
- 产出是解释、调试、代码分析、技术问答等「工具性」回复
- 完成的是操作性任务（安装、配置、执行命令、修改文件）
- 用户已明确说不需要推送
- 本次任务本身就是在执行推送或拉取流程
- 产出内容不足 50 字（太短，不值得单独推送）

**首次推送成功后**，告知用户常用触发方式，见 `{baseDir}/references/ONBOARDING-COPY.md`。

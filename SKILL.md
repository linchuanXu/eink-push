---
name: eink_push
description: 推送内容到阅星曈墨水屏（卡片 / 电子书），或拉取书架、书签等阅读数据。
metadata: {"openclaw": {"emoji": "🖤", "requires": {"bins": ["python"]}}}
---

# 阅星曈 Skill

推送内容到阅星曈墨水屏，或拉取书架 / 书签数据。

以下所有命令以本文件所在目录为根目录执行（`{baseDir}`）。

---

## 凭证预检（每次操作前必做）

```bash
python {baseDir}/scripts/push_to_device.py --check-credentials
```

| 输出 | 处理 |
|------|------|
| `OK`（凭证早已存在） | 直接继续 |
| `OK`（**本次刚写入**） | 继续；操作完成后 Read `{baseDir}/references/ONBOARDING-COPY.md`，以自然语言向用户展示 |
| `MISSING` | 询问用户手机号和密码，Write 写入 `{baseDir}/.credentials.json`：`{ "username": "手机号", "password": "密码" }` |
| HTTP 401 | 运行 `--reset-credentials`，重新收集凭证 |

---

## 意图路由

| 用户说的 | 走哪个流程 |
|----------|------------|
| 发到阅星曈 / 推到设备 / 推一下 / 发到墨水屏 | → 按字数分流：≤2000 字走**卡片**，>2000 字走**电子书** |
| 明确说"卡片 / 简报 / 仪表盘" | → **推送：卡片** |
| 明确说"电子书 / 长文 / 连续阅读" | → **推送：电子书** |
| 我的书架 / 阅读进度 / 读了哪些书 | → **D1 查书架** |
| 书签 / 摘录 / 高亮（指定书名） | → **D2 查书签** |
| 书签 / 摘录 / 高亮（未指定书） | → D1 → 用户选书 → D2 |
| 书摘卡片 / 精选摘录 | → **A 书摘卡片** |
| 整理笔记 / 书签整理成书 | → **B 阅读笔记电子书** |
| 阅读报告 / 阅读看板 | → **C 阅读看板卡片** |

### ⚠️ 易混淆

| 情况 | 处理 |
|------|------|
| "发到阅星曈"但对话无明确内容产出 | 询问要推送什么 |
| 提到书签但未指定书名 | 先 D1 查书架，让用户选书 |
| "做个阅读笔记" | 询问：整理为电子书还是书摘卡片？ |
| "推送一下"但内容不足 50 字 | 确认是否仍要推送 |

**判断原则**：能确定内容和形式 → 直接执行；格式不明 → 问一次；内容不明 → 先拉数据再确认。

---

## 推送：卡片

适用于 ≤2000 字的内容。

| 字数 | 形式 |
|------|------|
| ≤200 字 | 单张卡片：一屏资讯 / 仪表盘 |
| 200–2000 字 | 多张卡片集：每张一主题，宁多勿挤 |

**卡片是截图，不是文章排版。** 长文或连续阅读 → 走电子书。设计规范见 `{baseDir}/references/design-guide.md`。

**第 1 步：写 HTML**

| 项目 | 说明 |
|------|------|
| 单张文件名 | `output/{主题词}_{YYYYMMDD-HHMM}.html` |
| 多张文件名 | `output/{主题词}_p1_{时间戳}.html`、`_p2_`… |
| body 写法 | `width:100vw; height:100vh; overflow:hidden; margin:0; padding:0` |
| 起点模板 | Read `{baseDir}/assets/templates/base.html` |

**第 2 步：渲染**

```bash
# 单张
python {baseDir}/scripts/render_image.py "output/文件名.html"

# 多张（自动打包）
python {baseDir}/scripts/render_image.py "output/主题_p1_时间戳.html" "output/主题_p2_时间戳.html" --title "标题" --author "龙虾"
```

**第 3 步：推送**

→ 说：「正在推送「{标题}」…」

```bash
python {baseDir}/scripts/push_to_device.py "output/渲染结果文件"
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## 推送：电子书

适用于 >2000 字 / 连续长文 / 多节论述。

**第 1 步：整理为 Markdown**

文件命名：`output/{主题词}_{YYYYMMDD-HHMM}.md`，主题词 ≤10 字。

**第 2 步：生成并推送**

→ 说：「正在生成并推送「{标题}」…」

```bash
python {baseDir}/scripts/render_book.py "output/文件名.md" --title "标题" --author "龙虾"
python {baseDir}/scripts/push_to_device.py "output/文件名.xtc"
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## D1 — 查书架

```bash
python {baseDir}/scripts/fetch_reading.py books [--keyword 关键词] [--format epub|txt] [--per-page 50]
```

解析 stdout JSON，向用户展示（使用 `clean_name` 而非 `book_name`，时长转为「X 分钟 / X 小时 Y 分钟」，时间戳转为「M月D日」）：

```
你的书架（共 N 本）：

1. 悉达多 — 进度 50%，已读 2 分钟
2. 百年孤独 — 进度 82%，已读 3.5 小时
3. 人类简史 — 进度 100%，已读 8 小时  ✓ 已读完

最近活跃：悉达多（3月30日同步）
```

展示后追加：

```
---
要根据这些数据生成内容推回阅星曈吗？
• 书摘卡片（精选摘录 → 引言排版）
• 阅读笔记电子书（所有书签按章节整理）
• 阅读看板卡片（书架统计 → 仪表盘）
```

---

## D2 — 查书签

```bash
# 指定书（--keyword 传 book_name 原始值，非 clean_name）
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name原始值" --all

# 全部书签
python {baseDir}/scripts/fetch_reading.py bookmarks --all
```

已自动过滤「(本章结束)」占位符。向用户展示（字段处理同 D1）：

```
《百年孤独》的书签（共 12 条）：

家族谱系图（第 1 章）
  与情人蓄养的牲畜以惊人的速度繁殖，使其成为马孔多首富。

冰块的发明（第 2 章）
  世界如此新鲜，许多东西尚无名称，提到时不得不用手指点。

……（共 12 条）
```

展示后追加：

```
---
要根据这些书签生成内容推回阅星曈吗？
• 书摘卡片（精选摘录 → 引言排版）
• 阅读笔记电子书（所有书签按章节整理）
```

---

## A — 书摘卡片

**第 1 步：拉取书签**（同 D2）

**第 2 步：AI 挑选摘录，写 HTML**

- 挑选精彩句子 3–8 条，跳过 <15 字或重复的条目
- 每张卡片 1–3 条，大号引文 + 细体来源（书名 / 章节名）
- 文件命名：`output/{clean_name}_摘录_p1_{YYYYMMDD-HHMM}.html`、`_p2_`…
- 设计规范见 `{baseDir}/references/design-guide.md`

**第 3 步：渲染 + 推送**

→ 说：「正在生成《{书名}》书摘卡片并推送…」

```bash
python {baseDir}/scripts/render_image.py "output/书名_摘录_p1_时间戳.html" "output/书名_摘录_p2_时间戳.html" --title "《书名》书摘" --author "龙虾"
python {baseDir}/scripts/push_to_device.py "output/书名_摘录_时间戳.xtch"
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## B — 阅读笔记电子书

**第 1 步：拉取书签**（同 D2）

**第 2 步：AI 整理为 Markdown**

按 `chapter_index` 升序排列，同章归在同一 `##` 下，`chapter_title` 为空时用「第 N 章」占位：

```markdown
# 《书名》阅读笔记

## 章节标题

> 摘录原文

## 下一章节…
```

文件命名：`output/{clean_name}_笔记_{YYYYMMDD-HHMM}.md`

**第 3 步：生成并推送**

→ 说：「正在整理《{书名}》阅读笔记并推送…」

```bash
python {baseDir}/scripts/render_book.py "output/书名_笔记_时间戳.md" --title "《书名》阅读笔记" --author "龙虾"
python {baseDir}/scripts/push_to_device.py "output/书名_笔记_时间戳.xtc"
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## C — 阅读看板卡片

**第 1 步：拉取书架**（同 D1）

**第 2 步：AI 统计并写 HTML**

| 维度 | 来源字段 | 说明 |
|------|----------|------|
| 正在读 | `progress_percent` 1–99 | |
| 已读完 | `progress_percent == 100` | |
| 总时长 | 所有书 `duration_seconds` 之和 | 转为小时 |
| 最近活跃 | `last_uploaded_at` 排序取前 3–5 | |

版式：仪表盘 / 多栏，突出「正在读」和「总时长」。文件命名：`output/阅读看板_{YYYYMMDD-HHMM}.html`

**第 3 步：渲染 + 推送**

→ 说：「正在生成阅读看板并推送…」

```bash
python {baseDir}/scripts/render_image.py "output/阅读看板_时间戳.html"
python {baseDir}/scripts/push_to_device.py "output/阅读看板_时间戳.xth"
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## 主动询问

**当本次任务产出「可发布型」内容**（报告、摘要、文章、创作、分析）且用户未提推送时，在回复末尾追加：

```
---
要把这份内容推送到阅星曈吗？
• 卡片（写 HTML，适合短内容 / 仪表盘）
• 电子书（写 Markdown，适合长文连续阅读）
```

**不追加的情况**：纯问答 / 技术解释 / 操作性任务 / 已在执行推送 / 内容不足 50 字 / 用户已明确拒绝。

---

## 错误处理

| 错误 | 处理 |
|------|------|
| `[CREDENTIALS_MISSING]` 或退出码 2 | 走凭证预检流程重新收集 |
| 未找到绑定设备 | 告知用户在阅星曈 App 中绑定设备后重试 |
| 依赖缺失（`[ERROR]` 开头） | 告知用户按 `{baseDir}/references/SETUP.md` 安装对应依赖后重试 |
| `skia-canvas` native 模块报错 | 告知用户在 Skill 目录执行 `npm install marknative`；若仍失败见 `{baseDir}/references/SETUP.md` |
| 其他脚本报错 | 将完整报错原文展示给用户，说明需手动排查 |

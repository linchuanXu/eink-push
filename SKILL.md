---
name: eink-push
description: >
  将内容推送到阅星曈/Yue Xingtong 墨水屏设备；生成卡片、翻页图片集、
  Markdown/EPUB 电子书；查询书架、阅读进度、书签摘录；在阅星曈推送场景中调用联网搜索。
  用户提到发到墨水屏、阅星曈、书签、书架、阅读进度、EPUB 或把调研结果推送到设备时使用。
metadata:
  homepage: https://github.com/linchuanXu/eink-push
  compatibility: >
    Requires Python >= 3.10 (pip install -r requirements.txt; playwright install chromium)
    and Node.js ≥ 18 (npm install marknative). Windows/macOS/Linux supported.
  openclaw:
    emoji: '🖤'
    requires:
      bins: ['python']
    install:
      - id: npm-marknative
        kind: node
        package: marknative
        label: 安装 marknative（电子书路径，需 Node.js ≥ 18）
  security:
    credentials_usage: |
      This skill reads username/password from XTEINK_USERNAME/XTEINK_PASSWORD first,
      then falls back to .credentials.json (written by the user on first setup). It
      sends credentials ONLY to the official 阅星曈 API (api-prod.xteink.cn) for
      authentication. Credentials are never logged, stored elsewhere, or transmitted
      to any other domain.
    allowed_domains:
      - api-prod.xteink.cn
---

# 阅星曈 Skill

推送内容到阅星曈墨水屏，或拉取书架 / 书签数据。

以下所有命令以本文件所在目录为根目录执行（`{baseDir}`）。

---

## 环境准备

首次运行前，或遇到依赖缺失报错时，先运行：

```bash
python {baseDir}/scripts/check_environment.py
```

若输出 `MISSING` 或 `FAIL`，按脚本给出的 `fix:` 命令处理；需要展开说明时 Read `{baseDir}/references/SETUP.md`。

> **Windows 提示**：`python` 不存在时用 `py -3`；`pip` 不存在时用 `python -m pip`。

---

## 凭证预检（每次操作前必做）

优先读取环境变量 `XTEINK_USERNAME` / `XTEINK_PASSWORD`；未设置时读取 `{baseDir}/.credentials.json`。兼容别名：`YUEXINGTONG_USERNAME` / `YUEXINGTONG_PASSWORD`。

```bash
python {baseDir}/scripts/push_to_device.py --check-credentials
```

| 输出 | 处理 |
|------|------|
| `OK` | 直接继续 |
| `OK` + `AUTH_OK`（运行 `--check-credentials --auth` 时） | 结构和账号密码均有效 |
| `MISSING` | 询问用户手机号和密码，Write 写入 `{baseDir}/.credentials.json`：`{ "username": "手机号", "password": "密码" }` |
| `INVALID` | 若提示环境变量只配置一半，要求同时设置用户名和密码；否则告知凭证文件损坏或缺字段，重新收集后覆盖写入 |
| `AUTH_FAILED: ...` | 按报错处理；401 时运行 `--reset-credentials` 或更新环境变量后重新收集凭证 |
| HTTP 401 | 运行 `--reset-credentials` 或更新环境变量，重新收集凭证 |

首次写入或覆盖 `.credentials.json` 后，重新运行 `--check-credentials`。若输出 `OK`，Read `{baseDir}/references/ONBOARDING-COPY.md`，用自然语言向用户说明后续可做什么；若用户愿意联网校验，再运行 `--check-credentials --auth`。

---

## 意图路由

### 高价值话术

优先覆盖这些典型表达，不要继续堆同义词到 frontmatter：

- “把这段发到阅星曈”
- “做成墨水屏卡片”
- “生成 EPUB 发到设备”
- “看一下我的书架”
- “整理《书名》的书签”

| 用户说的 | 走哪个流程 |
|----------|------------|
| 发到阅星曈 / 推到设备 / 推一下 / 发到墨水屏 | → 按字数分流：≤2000 字走**卡片**，>2000 字走**电子书** |
| 明确说"卡片 / 简报 / 仪表盘" | → **推送：卡片** |
| 明确说"电子书 / 长文 / 连续阅读" | → **推送：电子书** |
| 明确说「epub / EPUB / epub格式」 | → **推送：EPUB 电子书** |
| 我的书架 / 阅读进度 / 读了哪些书 | → **D1 查书架** |
| 书签 / 摘录 / 高亮（指定书名） | → **D2 查书签** |
| 书签 / 摘录 / 高亮（未指定书） | → D1 → 用户选书 → D2 |
| 书摘卡片 / 精选摘录 | → **A 书摘卡片** |
| 整理笔记 / 书签整理成书 | → **B 阅读笔记电子书** |
| 阅读报告 / 阅读看板 | → **C 阅读看板卡片** |
| 帮我查一下 / 搜一下 / 最新资讯 / 现在什么情况 / 今天的 XX | → **E 联网搜索调研** |

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

适用于 ≤2000 字内容。详细 HTML 写法、拆页规则和设计规范见 `{baseDir}/references/AGENT-WORKFLOWS.md` 与 `{baseDir}/references/design-guide.md`。

→ 说：「正在推送「{标题}」…」

```bash
python {baseDir}/scripts/render_image.py "output/文件名.html" --push
python {baseDir}/scripts/render_image.py "output/主题_p1_时间戳.html" "output/主题_p2_时间戳.html" --title "标题" --author "龙虾" --push
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## 推送：电子书

适用于 >2000 字 / 连续长文 / 多节论述。先写 Markdown 到 `output/{主题词}_{YYYYMMDD-HHMM}.md`；不要主动使用表格。详细整理规范见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

→ 说：「正在生成并推送「{标题}」…」

```bash
python {baseDir}/scripts/render_book.py "output/文件名.md" --title "标题" --author "龙虾" --push
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## 推送：EPUB 电子书

仅当用户明确提到「生成 EPUB」「推 EPUB」「epub 格式」时使用。适用于图文混排、需要封面、希望在设备电子书阅读器中阅读的内容。

→ 说：「正在生成 EPUB 并推送「{标题}」…」

```bash
python {baseDir}/scripts/epub/render_book_epub.py "output/文件名.md" --title "标题" --author "龙虾" --push
python {baseDir}/scripts/epub/render_book_epub.py "output/文件名.md" --title "标题" --author "龙虾" --cover-svg --push
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## D1 — 查书架

```bash
python {baseDir}/scripts/fetch_reading.py books [--keyword 关键词] [--format epub|txt] [--per-page 50] [--compact] [--limit N]
```

默认加 `--compact --limit 50`，除非需要完整原始字段。解析 stdout JSON，向用户展示 `clean_name`、进度、已读时长和最近活跃。展示格式和后续生成选项见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

---

## D2 — 查书签

```bash
# 指定书（--keyword 传 book_name 原始值，非 clean_name）
python {baseDir}/scripts/fetch_reading.py bookmarks --keyword "完整book_name原始值" --all [--compact] [--limit N]

# 全部书签
python {baseDir}/scripts/fetch_reading.py bookmarks --all [--compact] [--limit N]
```

默认加 `--compact --limit 100`，除非要整理完整笔记。已自动过滤「(本章结束)」占位符。展示字段和后续生成选项见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

---

## A — 书摘卡片

拉取书签，挑选 3-8 条精彩摘录，写 HTML 卡片。详细挑选和排版规则见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

→ 说：「正在生成《{书名}》书摘卡片并推送…」

```bash
python {baseDir}/scripts/render_image.py "output/书名_摘录_p1_时间戳.html" "output/书名_摘录_p2_时间戳.html" --title "《书名》书摘" --author "龙虾" --push
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## B — 阅读笔记电子书

拉取书签，按 `chapter_index` 升序整理为 Markdown。详细规则见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

→ 说：「正在整理《{书名}》阅读笔记并推送…」

```bash
python {baseDir}/scripts/render_book.py "output/书名_笔记_时间戳.md" --title "《书名》阅读笔记" --author "龙虾" --push
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## C — 阅读看板卡片

拉取书架，统计正在读、已读完、总时长、最近活跃并写仪表盘 HTML。详细字段规则见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

→ 说：「正在生成阅读看板并推送…」

```bash
python {baseDir}/scripts/render_image.py "output/阅读看板_时间戳.html" --push
```

→ 成功后说：「已推送到阅星曈，设备上即可接收。」

---

## E — 联网搜索调研

适用于阅星曈场景中的实时资料查询，尤其是用户希望把结果继续推送到设备时。普通泛化搜索优先用通用搜索能力。

```bash
python {baseDir}/scripts/search_query.py "查询内容"
python {baseDir}/scripts/search_query.py "查询内容" --system-prompt "用简洁中文回答，重点列出关键事实"
```

解析 stdout JSON，展示主体回答和引用来源；字段细节见 `{baseDir}/references/AGENT-WORKFLOWS.md`。

展示后追加：

```
---
要把这份调研结果推送到阅星曈吗？
• 卡片（写 HTML，适合摘要 / 仪表盘）
• 电子书（写 Markdown，适合长篇报告）
```

---

## 主动询问

**当本次任务产出「可发布型」内容**（报告、摘要、文章、创作、分析）且用户未提推送时，在回复末尾追加：

```
---
要把这份内容推送到阅星曈吗？
• 卡片（写 HTML，适合短内容 / 仪表盘）
• 电子书（写 Markdown，适合长文连续阅读）
```

**不追加的情况**：纯问答 / 技术解释 / 操作性任务 / 已在执行推送 / 内容不足 50 字 / 用户已明确拒绝 / 联网搜索调研结果（E 章节已内置提示）。

---

## 错误处理

| 错误 | 处理 |
|------|------|
| `[CREDENTIALS_MISSING]` / `[CREDENTIALS_INVALID]` 或退出码 2 | 走凭证预检流程重新收集 |
| 未找到绑定设备 | 告知用户在阅星曈 App 中绑定设备后重试 |
| 依赖缺失（`[ERROR]` 开头） | **Read** `{baseDir}/references/SETUP.md`，在 `{baseDir}` 按「环境准备」与 SETUP 补全依赖后重试 |
| `skia-canvas` native 模块报错 | 告知用户在 Skill 目录执行 `npm install marknative`；若仍失败见 `{baseDir}/references/SETUP.md` |
| 网络超时 / 推送失败 | Read `{baseDir}/references/TROUBLESHOOTING.md`，按对应错误给出提示 |
| 其他脚本报错 | 将完整报错原文展示给用户，说明需手动排查 |

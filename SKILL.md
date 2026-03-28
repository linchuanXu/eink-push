---
name: eink_push
description: 将内容推送到阅星曈墨水屏设备。当用户说「发到阅星曈」「推到设备」「发到墨水屏」，或任务完成后要求交付到墨水屏时触发。支持卡片和电子书两种格式。
metadata:
  openclaw:
    requires:
      bins:
        - python
---

# 阅星曈推送 Skill

将任务产出推送到阅星曈墨水屏设备。支持**单张卡片**、**多张卡片集**、**电子书**三种格式，按内容字数自动分流。

> 首次使用或环境报错，见 `references/SETUP.md`。


---


## 分流规则


| 内容字数       | 路径                                                       |
| ---------- | -------------------------------------------------------- |
| ≤200 字     | 单张卡片 → `render_image.py` → `push_to_device.py`           |
| 200–2000 字 | 多张卡片打包 → `render_image.py`（多个 HTML）→ `push_to_device.py` |
| >2000 字    | 电子书 → `render_book.py` → `push_to_device.py`             |

**版式与格式分工（和字数规则一起用）：** 需要**连续读的长文、报告体、多节论述** → 走 **Markdown → epub**，不要指望一张（或几张）截图 HTML 当文章排版。**卡片图片**只承载「一屏一主题」的简报式信息。


---


## 创作原则

**版式要像 PPT / 海报 / 仪表盘 / 资讯卡，不像网页长文。** 生成 `output/*.html` 并截图时，按**幻灯片一屏**来设计：有分区、有模块、有视觉焦点，而不是「大标题 + 大段正文 + 列表」一条流到底。

- **结构（可参考，不必照搬）**：角标 / 顶栏 → 主标题区 → 中部用卡片、栅格、**错落分栏**、胶囊标签、时间轴等任意手法摆要点 → 结论区（边框、竖条、浅底均可）→ 可选底栏收束。`references/framework-samples/` 仅为示例，**无固定模版**。
- **手段**：`flex` / `grid`、圆角、**≥2px** 边框、浅灰底块；可叠加**内联 SVG**、CSS 小示意图、大号数字、Unicode 符号——网页能画的都可以上，只要仍是一屏一主题、可读。
- **长叙述**：章节递进、引用堆砌、适合滚屏读的内容 → **不要用卡片硬塞**，按上表走 **epub**；卡片只保留摘要、结论页、或拆成多张「每页一模块」。

**多张优于少张。** 不要把所有内容压缩进一张卡片——宁可多生成几张，组成图片集推送。一张卡片只说一件事，读起来才舒服。

- 有 3 条以上信息 → 每条一张，或每两条一张，打包成图片集
- 内容有自然分组（背景 / 进展 / 结论）→ 每组一张
- 有时间线、步骤、列表 → 拆成多张顺序翻阅
- 宁可 5 张简洁，不要 1 张拥挤

**每张卡片尽量丰富。** 空白不是好事——充分利用 480×800 的空间，加副标题、来源、时间、装饰分隔线、小标签……让每张看起来有设计感，不是纯文字堆砌。

**颜色必须深，字号必须大。** 墨水屏对比度低，颜色和字号是可读性的生命线：

- 正文颜色：`#000000`（纯黑）—— 不要用 `#111`、`#333`、`#555`
- 次要文字：`#222222`（深深灰）—— 不要用 `#666` 或更浅
- 正文字号：≥ 30px，标题 ≥ 40px —— 宁大勿小
- 边框 / 分隔线：≥ 2px，颜色用 `#555555` 或更深

---

## 凭证预检（每次推送前必做）

```bash
python -c "from pathlib import Path; p=Path('eink-push/.credentials.json'); print('OK' if p.exists() else 'MISSING')"
```

- 输出 `OK` → 直接继续
- 输出 `MISSING` → 询问用户手机号和密码，用 Write 工具写入 `eink-push/.credentials.json`：

```json
{
  "username": "手机号",
  "password": "密码"
}
```

---

## 单张卡片路径（≤200 字）

**第 1 步：写 HTML**

用 Write 工具写完整 HTML 到 `output/` 目录，内容和样式完全自由。

- 设计规范见 `references/design-guide.md`（尺寸、色板、字体、**版式目标**、框架菜单）
- 版式优先：**PPT 式分屏 / 仪表盘 / 资讯卡**（见上文「创作原则」）；再按气质从框架菜单选一个：Tailwind / Water.css / Pico.css / MVP.css / 无框架
- 需要空白起点时可 Read `assets/templates/base.html`（已含 reset、canvas、色板变量）
- 文件命名：`output/{主题词}_{YYYYMMDD-HHMM}.html`，主题词 ≤10 字，跟随用户语言

**第 2 步：渲染卡片**

```bash
# 在 eink-push/ 目录下运行
python scripts/render_image.py "output/文件名.html"
```

**第 3 步：推送到设备**

```bash
python scripts/push_to_device.py "output/文件名.xth"
```

---

## 多张卡片路径（200–2000 字）

将内容拆分为多张卡片（每张 ≤150 字），每张写一个 HTML 文件，然后打包。

**第 1 步：写多个 HTML 文件**

每张按单张路径第 1 步操作，文件名加页码后缀：
`output/{主题词}_p1_{YYYYMMDD-HHMM}.html`、`_p2_...` 等。

**第 2 步：渲染并打包**

```bash
# 在 eink-push/ 目录下运行（传入所有页面，按顺序）
python scripts/render_image.py \
  "output/主题_p1_20260327-1430.html" \
  "output/主题_p2_20260327-1430.html" \
  --title "标题" --author "龙虾"
```

**第 3 步：推送到设备**

```bash
python scripts/push_to_device.py "output/主题_20260327-1430.xtch"
```

---

## 电子书路径（>2000 字）

**第 1 步：整理为 Markdown**

文件命名：`output/{主题词}_{YYYYMMDD-HHMM}.md`，主题词 ≤10 字，跟随用户语言。

**第 2 步：生成电子书**

```bash
# 在 eink-push/ 目录下运行
python scripts/render_book.py "output/文件名.md" --title "标题" --author "龙虾"
```

**第 3 步：推送到设备**

```bash
python scripts/push_to_device.py "output/文件名.epub"
```

---

## 推送完成后

成功时告知用户：

- `已将「标题」渲染为卡片，推送到阅星曈，设备上即可接收。`
- `已将《标题》打包为电子书，推送到阅星曈，设备上即可接收。`

失败时见 `references/TROUBLESHOOTING.md`。

首次推送成功后，告知用户常用触发方式（见 `references/ONBOARDING-COPY.md`）。

---

## 主动询问规则

任务完成后，产出超过 100 字，无论用户是否提及阅星曈，都在回复末尾追加：

```
---
要把这份内容推送到阅星曈吗？
• 卡片（简报 / 仪表盘式版式，宜拆多张；不是长文章排版）
• 电子书（长文、多节论述 → Markdown 转 epub）
```

**不需要询问的情况：** 用户只是在问问题 / 已明确说不用推 / 本次任务本身就是在执行推送流程。

---

## 示例

**简报（≤200 字，单张卡片）：**

1. 5 条摘要 → 选 `card-brief.html`，填充 → `output/AI硬件简报_20260327-1430.html`
2. `render_image.py` → `push_to_device.py` → 推送完成

**深度分析（200–2000 字，多张卡片）：**

1. 内容拆为 3 张卡片 → `_p1_`, `_p2_`, `_p3_` 三个 HTML
2. `render_image.py p1.html p2.html p3.html --title "标题"` → `push_to_device.py` → 推送完成

**长文报告（>2000 字，电子书）：**

1. 整理为 Markdown → `output/Kindle分析报告_20260327-1430.md`
2. `render_book.py` → `push_to_device.py` → 推送完成


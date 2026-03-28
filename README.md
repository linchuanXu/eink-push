# eink-push · 阅星曈推送 Skill

[English below ↓](#english)

一个 [Cursor](https://cursor.sh) Agent Skill，让 AI 助手能将任何创作内容——简报、分析、长文——一键推送到**阅星曈**墨水屏设备。

支持三种格式，AI 根据字数自动选择：

| 内容长度 | 格式 | 说明 |
|---------|------|------|
| ≤ 200 字 | 单张卡片 | 单幅图片，即取即读 |
| 200–2000 字 | 图片集 | 多张卡片打包，顺序翻阅 |
| > 2000 字 | 电子书 | EPUB 格式，沉浸阅读 |

---

## 安装

### 前提条件

- [Cursor](https://cursor.sh) IDE
- Python 3.8+
- 阅星曈账号及已绑定的设备

### 步骤

**1. 克隆到 Cursor 的 skills 目录**

```bash
# macOS / Linux
git clone https://github.com/your-username/eink-push ~/.cursor/skills/eink-push

# Windows（PowerShell）
git clone https://github.com/your-username/eink-push "$env:USERPROFILE\.cursor\skills\eink-push"
```

**2. 安装 Python 依赖**

```bash
pip install playwright Pillow requests markdown ebooklib
playwright install chromium
```

**3. 下载字体（推荐，获得最佳渲染效果）**

```bash
cd ~/.cursor/skills/eink-push   # Windows: cd "$env:USERPROFILE\.cursor\skills\eink-push"
python scripts/setup_fonts.py
```

不执行此步骤也能运行——渲染脚本会自动从 Google Fonts CDN 拉取字体，或回退到系统字体。

---

## 使用方式

在 Cursor 对话中直接说：

- `发到阅星曈`
- `推到设备`
- `整理成电子书发过去`
- `把这次对话的结论整理成卡片推到墨水屏`

AI 会自动判断内容长度并选择合适格式。任务结束后，若产出超过 100 字，AI 也会主动询问是否推送。

**首次使用**时，AI 会引导你输入阅星曈账号和密码，保存到本地 `.credentials.json`（已加入 `.gitignore`，不会上传到仓库）。

---

## 文件结构

```
eink-push/
├── SKILL.md                    # Cursor Skill 主文件
├── assets/
│   ├── fonts/                  # 本地字体（通过 setup_fonts.py 下载，默认不随仓库分发）
│   └── templates/
│       └── base.html           # HTML 卡片起点模板
├── references/
│   ├── design-guide.md         # 卡片设计规范（画布、颜色、字体、CSS 框架）
│   ├── SETUP.md                # 首次安装指引
│   ├── TROUBLESHOOTING.md      # 故障排查
│   └── ONBOARDING-COPY.md      # 首次成功后的引导话术
├── scripts/
│   ├── render_image.py         # HTML → .xth / .xtc 截图打包
│   ├── render_book.py          # Markdown → .epub 电子书
│   ├── push_to_device.py       # 推送文件到阅星曈设备
│   └── setup_fonts.py          # 下载字体到 assets/fonts/
└── output/                     # 生成文件暂存目录（已加入 .gitignore）
```

---

## 故障排查

见 [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md)。

---

<a name="english"></a>

## English

A [Cursor](https://cursor.sh) Agent Skill that lets AI push any content—summaries, analyses, long-form articles—to **Yue Xingtong (阅星曈)** e-ink devices with a single command.

Three formats supported, selected automatically by content length:

| Length | Format | Description |
|--------|--------|-------------|
| ≤ 200 words | Single card | One image, instant read |
| 200–2000 words | Card set | Multiple cards bundled for paged reading |
| > 2000 words | E-book | EPUB format for immersive reading |

### Installation

**Prerequisites:** [Cursor](https://cursor.sh) IDE · Python 3.8+ · Yue Xingtong account with a bound device

**1. Clone to Cursor's skills directory**

```bash
# macOS / Linux
git clone https://github.com/your-username/eink-push ~/.cursor/skills/eink-push

# Windows (PowerShell)
git clone https://github.com/your-username/eink-push "$env:USERPROFILE\.cursor\skills\eink-push"
```

**2. Install Python dependencies**

```bash
pip install playwright Pillow requests markdown ebooklib
playwright install chromium
```

**3. Download fonts (recommended)**

```bash
cd ~/.cursor/skills/eink-push
python scripts/setup_fonts.py
```

This step is optional — the render script will fall back to Google Fonts CDN or system fonts if local fonts are absent.

### Usage

In any Cursor conversation, say:

- *"发到阅星曈"* — push to e-ink device
- *"推到设备"* — send to device
- *"整理成电子书发过去"* — package as an e-book and send

The AI picks the right format automatically. After tasks that produce more than ~100 words, it will also proactively ask if you'd like to push.

On first use, the AI will prompt for your account credentials, which are saved locally in `.credentials.json` (excluded from git).

### Troubleshooting

See [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md).

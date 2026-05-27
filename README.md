# eink-push · 阅星曈推送 Skill

[English below ↓](#english)

一个 [OpenClaw](https://openclaw.ai) Agent Skill，让 AI 助手能将任何创作内容——简报、分析、长文——一键推送到**阅星曈**墨水屏设备；也能反向拉取书架进度和书签，生成书摘卡片、阅读笔记等内容推回设备。

**推送**：AI 根据内容长度自动选择格式：

| 内容长度 | 格式 | 说明 |
|---------|------|------|
| ≤ 200 字 | 单张卡片 | 单幅图片，即取即读 |
| 200–2000 字 | 翻页卡片集 | 多张卡片打包，顺序翻阅 |
| > 2000 字 | 翻页电子书 | Markdown 渲染分页图片，沉浸阅读 |

**拉取**：查询书架进度、书签摘录，并可生成书摘卡片、阅读笔记电子书、阅读看板卡片推回设备。

---

## 安装

在 OpenClaw 中，直接告诉 AI：

🧑 **你：** 安装技能 `https://github.com/linchuanXu/eink-push`，并且引导我登录账号密码，教我怎么使用这个技能

🤖 **AI：** 好的，已安装 eink-push 技能！我会先检查本地是否已有凭证；如果没有，请提供你的**阅星曈手机号**和**密码**，我来帮你完成配置。

🧑 **你：** 手机号 138xxxxxxxx，密码 xxxxxx

🤖 **AI：** 已保存并通过结构检查！以后直接说"发到阅星曈"，我就会把当前内容推送到你的墨水屏设备。

---

## 更新

如果你是通过 OpenClaw / Codex 安装的普通用户，直接在对话里说：

> 更新技能 `https://github.com/linchuanXu/eink-push`

更新后让 AI 重新运行一次环境检查：

```powershell
python scripts/check_environment.py
```

也可以只检查 Skill 是否有新版本：

```powershell
python scripts/check_update.py
```

凭证文件 `.credentials.json`、环境变量和设备绑定不会因为更新仓库文件而被覆盖。

如果你本机有这个 Git 仓库，并且用 `scripts/install_skill.py` 同步到本地 Skill 目录，更新流程是：

```powershell
git pull
python scripts/install_skill.py
python scripts/install_skill.py --apply
python scripts/check_environment.py
```

`install_skill.py` 默认是 dry-run，会先显示哪些 runtime 文件将被复制或更新；确认无误后再加 `--apply`。如电子书路径提示 `marknative` 缺失，在实际安装目录运行：

```powershell
npm install marknative
```

版本检查机制类似微信读书 Skill：`SKILL.md` 声明 `version`，`check_update.py` 会读取本地版本并对比 GitHub 最新版本；`check_environment.py` 会把可用更新显示为非阻断的 `UPDATE` 提示。

---

## 配置账号

首次使用时，AI 会提示你输入阅星曈手机号和密码。正式安装环境推荐通过环境变量注入凭证；未设置环境变量时，会自动保存到本地 `.credentials.json`（不会上传到仓库）。

环境变量优先级最高：

```powershell
$env:XTEINK_USERNAME="你的手机号"
$env:XTEINK_PASSWORD="你的密码"
```

也可以提前手动创建：

```json
{
  "username": "你的手机号",
  "password": "你的密码"
}
```

保存后可运行：

```powershell
python scripts/push_to_device.py --check-credentials
```

输出 `OK` 表示凭证结构正常。需要实际登录校验时运行：

```powershell
python scripts/push_to_device.py --check-credentials --auth
```

输出 `AUTH_OK` 表示账号密码可登录。

---

## 使用方式

安装后，在 OpenClaw 对话中直接说：

**推送内容到设备：**
- `发到阅星曈`
- `推到设备`
- `整理成电子书发过去`
- `把这次对话的结论整理成卡片推到墨水屏`

AI 会自动判断内容长度，选择合适格式推送。任务结束后若产出超过 50 字，AI 也会主动询问是否推送。

**查询阅读数据：**
- `我的书架` / `我在读什么` / `阅读进度`
- `《悉达多》的书签` / `最近的摘录`
- `把书签做成卡片` / `整理阅读笔记` / `生成阅读看板`

---

## 故障排查

见 [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md)。

---

## 开发者快速验证

在仓库根目录安装依赖（Python 需 3.10+）：

```powershell
pip install -r requirements.txt
playwright install chromium
npm install marknative
```

先跑环境预检，缺什么会直接给出修复命令：

```powershell
python scripts/check_environment.py
```

检查本机是否存在重复或漂移的安装副本：

```powershell
python scripts/check_installation.py
python scripts/check_installation.py --require-installed
```

检查 git 跟踪 / 未忽略的发布候选内容是否混入凭证、生成产物或本地依赖：

```powershell
python scripts/check_package.py
```

预览会同步到本机 Skill 目录的运行文件；默认不会写文件：

```powershell
python scripts/install_skill.py
python scripts/install_skill.py --apply
```

自定义 `--target` 时必须指向名为 `eink-push` 的 Skill 目录，且不能位于当前源码目录内部。
真实安装副本只同步 runtime 文件；`check_package.py`、`install_skill.py`、
`smoke_test.py`、`verify.py` 等维护脚本保留在开发仓库中。安装后若电子书路径提示
`marknative` 缺失，请在实际安装目录运行 `npm install marknative`。

离线验证卡片渲染：

```powershell
python scripts/render_image.py assets/templates/base.html --preview
```

离线验证 Markdown 翻页电子书：

```powershell
"# 测试书`n`n## 第一章`n`n这是测试内容。" | Out-File -Encoding utf8 output/test.md
python scripts/render_book.py output/test.md --title "测试书" --author "龙虾"
```

离线验证 EPUB 生成：

```powershell
python scripts/epub/render_book_epub.py output/test.md --title "测试书" --author "龙虾" --cover-svg
```

一键运行离线 smoke test（不会推送设备；依赖缺失的路径会显示 SKIP）：

```powershell
python scripts/smoke_test.py
```

完整离线验证：

```powershell
python scripts/verify.py
```

只有带 `--push` 或直接运行 `scripts/push_to_device.py` 的命令会真实推送到设备。

---

<a name="english"></a>

## English

An [OpenClaw](https://openclaw.ai) Agent Skill that lets AI push any content—summaries, analyses, long-form articles—to **Yue Xingtong (阅星曈)** e-ink devices with a single command. It can also pull reading progress and bookmarks from the device, then generate highlight cards, reading notes, and dashboards to push back.

**Push**: Format is selected automatically by content length:

| Length | Format | Description |
|--------|--------|-------------|
| ≤ 200 words | Single card | One image, instant read |
| 200–2000 words | Card set | Multiple cards bundled for paged reading |
| > 2000 words | Paged e-book | Markdown rendered to paginated images |

**Pull**: Query reading progress and bookmarks, then generate highlight cards, reading-note e-books, or reading dashboards to push back to the device.

---

## Installation

In OpenClaw, just tell the AI:

🧑 **You:** Install skill `https://github.com/linchuanXu/eink-push` and guide me to log in, then show me how to use it

🤖 **AI:** Done! I will first check whether credentials already exist locally. If they do not, please share your **Yue Xingtong phone number** and **password** so I can finish setup.

🧑 **You:** Phone 138xxxxxxxx, password xxxxxx

🤖 **AI:** Saved and structure-checked! From now on, just say "发到阅星曈" and I'll push your content to the e-ink device.

---

## Update

If you installed the skill through OpenClaw / Codex, tell the AI:

> Update skill `https://github.com/linchuanXu/eink-push`

After updating, ask it to run the environment check again:

```powershell
python scripts/check_environment.py
```

You can also check only whether a newer Skill version is available:

```powershell
python scripts/check_update.py
```

Your `.credentials.json`, environment variables, and device binding are not overwritten by updating the repository files.

If you keep a local Git checkout and sync it into your local Skill directory with `scripts/install_skill.py`, update with:

```powershell
git pull
python scripts/install_skill.py
python scripts/install_skill.py --apply
python scripts/check_environment.py
```

`install_skill.py` is a dry-run by default and prints which runtime files would be copied or updated; rerun with `--apply` to sync them. If book rendering reports missing `marknative`, run this inside the actual installed Skill directory:

```powershell
npm install marknative
```

The update check follows the same idea as the WeRead Skill: `SKILL.md` declares a `version`, `check_update.py` reads the local version and compares it with the latest version on GitHub, and `check_environment.py` reports available updates as a non-blocking `UPDATE` notice.

---

## Credentials setup

On first use, the AI will prompt for your Yue Xingtong phone number and password. For installed environments, credentials are preferably injected through environment variables. If they are not set, the skill falls back to a local `.credentials.json` file (excluded from git).

Environment variables take precedence:

```powershell
$env:XTEINK_USERNAME="your_phone_number"
$env:XTEINK_PASSWORD="your_password"
```

You can also create the file manually in advance:

```json
{
  "username": "your_phone_number",
  "password": "your_password"
}
```

After saving it, run:

```powershell
python scripts/push_to_device.py --check-credentials
```

`OK` means the local credentials file is well-formed. To verify the account by logging in:

```powershell
python scripts/push_to_device.py --check-credentials --auth
```

`AUTH_OK` means the account can log in.

---

## Usage

**Push content to device:**
- *"发到阅星曈"* — push to e-ink device
- *"推到设备"* — send to device
- *"整理成电子书发过去"* — package as an e-book and send
- *"把这次对话的结论整理成卡片推到墨水屏"* — summarize and push as cards

The AI picks the right format automatically. After tasks that produce more than ~50 words, it will also proactively ask if you'd like to push.

**Pull reading data:**
- *"我的书架"* / *"阅读进度"* — view reading shelf and progress
- *"《书名》的书签"* — view bookmarks for a book
- *"把书签做成卡片"* / *"整理阅读笔记"* / *"生成阅读看板"* — generate and push derived content

---

## Troubleshooting

See [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md).

---

## Developer quick check

Install dependencies from the repository root. Python 3.10+ is required:

```powershell
pip install -r requirements.txt
playwright install chromium
npm install marknative
```

Run the environment preflight first. It prints fix commands for missing dependencies:

```powershell
python scripts/check_environment.py
```

Check for duplicate or drifted installed copies:

```powershell
python scripts/check_installation.py
python scripts/check_installation.py --require-installed
```

Check tracked and unignored package candidates for credentials, generated artifacts, or local dependencies:

```powershell
python scripts/check_package.py
```

Preview the runtime files that would be synced into the local Skill directory. This is dry-run by default:

```powershell
python scripts/install_skill.py
python scripts/install_skill.py --apply
```

When using a custom `--target`, point it at a Skill directory named `eink-push`; it must not live inside this source checkout.
Installed copies receive runtime files only; maintenance scripts such as `check_package.py`,
`install_skill.py`, `smoke_test.py`, and `verify.py` stay in the development checkout. If the
installed copy reports missing `marknative` for book rendering, run `npm install marknative`
inside the actual installed Skill directory.

Offline card render check:

```powershell
python scripts/render_image.py assets/templates/base.html --preview
```

Offline Markdown paged-book check:

```powershell
"# Test Book`n`n## Chapter One`n`nThis is a test." | Out-File -Encoding utf8 output/test.md
python scripts/render_book.py output/test.md --title "Test Book" --author "龙虾"
```

Offline EPUB check:

```powershell
python scripts/epub/render_book_epub.py output/test.md --title "Test Book" --author "龙虾" --cover-svg
```

Run the offline smoke test in one command. It never pushes to the device; paths with missing dependencies are shown as SKIP.

```powershell
python scripts/smoke_test.py
```

Full offline verification:

```powershell
python scripts/verify.py
```

Only commands with `--push`, or direct calls to `scripts/push_to_device.py`, send files to the device.

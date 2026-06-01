# eink-push

把 AI 生成的内容、阅读摘录和长文报告推送到阅星曈墨水屏设备的 Agent Skill。

它适合这些场景：

- 把一段回答、简报或研究结论做成墨水屏卡片
- 把长文、教程、调研报告整理成可连续阅读的电子书
- 查询阅星曈书架、阅读进度和书签摘录
- 把书签整理成书摘卡片、阅读笔记或阅读看板

> 当前仓库是 Skill 源码，不是一个需要部署的 Web 服务。用户通过 OpenClaw / Codex 安装这个 GitHub 仓库后，本地 Agent 会按 `SKILL.md` 调用其中的脚本。

## Quick Start

在 OpenClaw / Codex 里直接说：

```text
安装技能 https://github.com/linchuanXu/eink-push
```

安装后，继续让 AI 帮你完成登录配置：

```text
引导我登录阅星曈账号，并检查这个技能能不能用
```

如果是第一次使用，AI 会提示你提供阅星曈手机号和密码。配置完成后，你可以直接说：

```text
把这段发到阅星曈
整理成电子书发过去
看一下我的书架
把《悉达多》的书签做成卡片
```

## 能力一览

### 推送内容

Skill 会根据内容长度和你的表达自动选择格式：

| 内容 | 默认格式 | 适合 |
| --- | --- | --- |
| 200 字以内 | 单张卡片 | 短提醒、金句、结论 |
| 200-2000 字 | 翻页卡片集 | 简报、摘要、清单 |
| 2000 字以上 | 翻页电子书 | 长文、报告、教程 |
| 明确要求 EPUB | EPUB 文件 | 需要封面或电子书阅读器体验 |

典型说法：

```text
发到阅星曈
推到设备
做成墨水屏卡片
整理成电子书发过去
生成 EPUB 推到设备
```

### 查询阅读数据

支持查询书架、阅读进度和书签摘录：

```text
我的书架
我最近在读什么
《书名》的书签
最近的摘录
```

查询后还能继续生成内容：

```text
把书签做成卡片
整理成阅读笔记
生成阅读看板发到设备
```

## 凭证与安全

Skill 需要阅星曈账号才能推送和查询数据。凭证读取顺序：

1. 环境变量 `XTEINK_USERNAME` / `XTEINK_PASSWORD`
2. 兼容别名 `YUEXINGTONG_USERNAME` / `YUEXINGTONG_PASSWORD`
3. 本地 `.credentials.json`

`.credentials.json` 只保存在本地，已被仓库忽略，不会上传到 GitHub。凭证只会发送到阅星曈官方接口 `api-prod.xteink.cn` 用于登录。

手动配置环境变量：

```powershell
$env:XTEINK_USERNAME="你的手机号"
$env:XTEINK_PASSWORD="你的密码"
```

手动创建 `.credentials.json`：

```json
{
  "username": "你的手机号",
  "password": "你的密码"
}
```

检查凭证结构：

```powershell
python scripts/push_to_device.py --check-credentials
```

实际登录校验：

```powershell
python scripts/push_to_device.py --check-credentials --auth
```

输出 `AUTH_OK` 表示账号密码可登录。

## 哪些命令会真的推送

只有带 `--push` 的命令，或直接执行推送脚本，才会把文件发送到设备。

会真实推送：

```powershell
python scripts/render_image.py output/card.html --push
python scripts/render_book.py output/book.md --title "标题" --push
python scripts/epub/render_book_epub.py output/book.md --title "标题" --push
python scripts/push_to_device.py output/file.xtg
```

只做本地验证，不会推送：

```powershell
python scripts/check_environment.py
python scripts/check_installation.py
python scripts/check_package.py
python scripts/smoke_test.py
python scripts/verify.py
python scripts/render_image.py assets/templates/base.html --preview
```

## 更新

如果你是通过 OpenClaw / Codex 安装的普通用户，直接说：

```text
更新技能 https://github.com/linchuanXu/eink-push
```

更新后建议让 AI 再跑一次环境检查：

```powershell
python scripts/check_environment.py
```

如果你维护的是本地 Git 仓库，并用 `scripts/install_skill.py` 同步到 Skill 目录：

```powershell
git pull
python scripts/install_skill.py
python scripts/install_skill.py --apply
python scripts/check_environment.py
```

`install_skill.py` 默认 dry-run，会先显示即将复制或更新的 runtime 文件；确认无误后再加 `--apply`。

## 开发者

Python 3.10+ 是最低要求。在仓库根目录安装依赖：

```powershell
pip install -r requirements.txt
playwright install chromium
npm install marknative
```

环境预检：

```powershell
python scripts/check_environment.py
```

检查本机是否存在重复或漂移的安装副本：

```powershell
python scripts/check_installation.py
python scripts/check_installation.py --require-installed
```

检查发布候选内容是否混入凭证、生成产物或本地依赖：

```powershell
python scripts/check_package.py
```

预览将同步到本机 Skill 目录的 runtime 文件：

```powershell
python scripts/install_skill.py
```

实际同步：

```powershell
python scripts/install_skill.py --apply
```

自定义安装目录时使用 `--target`，目标目录必须名为 `eink-push`，且不能位于当前源码目录内部：

```powershell
python scripts/install_skill.py --target "C:\Users\you\.codex\skills\eink-push"
python scripts/install_skill.py --target "C:\Users\you\.codex\skills\eink-push" --apply
```

真实安装副本只同步 runtime 文件；`check_package.py`、`install_skill.py`、`smoke_test.py`、`verify.py` 等维护脚本保留在开发仓库中。

离线渲染卡片：

```powershell
python scripts/render_image.py assets/templates/base.html --preview
```

离线渲染 Markdown 翻页电子书：

```powershell
"# 测试书`n`n## 第一章`n`n这是测试内容。" | Out-File -Encoding utf8 output/test.md
python scripts/render_book.py output/test.md --title "测试书" --author "龙虾"
```

离线生成 EPUB：

```powershell
python scripts/epub/render_book_epub.py output/test.md --title "测试书" --author "龙虾" --cover-svg
```

一键离线 smoke test：

```powershell
python scripts/smoke_test.py
```

完整离线验证：

```powershell
python scripts/verify.py
```

## 项目文件

| 路径 | 说明 |
| --- | --- |
| `SKILL.md` | Agent 使用说明和意图路由 |
| `scripts/push_to_device.py` | 凭证检查与文件推送 |
| `scripts/render_image.py` | HTML 卡片渲染与卡片集打包 |
| `scripts/render_book.py` | Markdown 翻页电子书渲染 |
| `scripts/epub/render_book_epub.py` | EPUB 生成 |
| `scripts/fetch_reading.py` | 书架和书签查询 |
| `references/SETUP.md` | 环境安装细节 |
| `references/TROUBLESHOOTING.md` | 常见故障排查 |

## Troubleshooting

常见问题见 [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md)。

如果电子书路径提示 `marknative` 或 `skia-canvas` 缺失，请在实际运行 Skill 的目录执行：

```powershell
npm install marknative
```

如果仍失败，可继续参考 [`references/SETUP.md`](references/SETUP.md)。

## English

`eink-push` is an Agent Skill for sending AI-generated cards, paged books, EPUB files, reading notes, and dashboards to Yue Xingtong e-ink devices.

Install it in OpenClaw / Codex:

```text
Install skill https://github.com/linchuanXu/eink-push
```

Then ask the agent to configure your Yue Xingtong account and run the environment check.

Common prompts:

```text
Send this to Yue Xingtong
Turn this into an e-ink card
Package this as an e-book and send it
Show my reading shelf
Make highlight cards from this book's bookmarks
```

Only commands with `--push`, or direct calls to `scripts/push_to_device.py`, send files to the device. Validation commands such as `check_environment.py`, `smoke_test.py`, and `verify.py` are offline checks.

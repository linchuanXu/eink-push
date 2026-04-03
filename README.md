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

🤖 **AI：** 好的，已安装 eink-push 技能！请提供你的**阅星曈手机号**和**密码**，我来帮你完成配置。

🧑 **你：** 手机号 138xxxxxxxx，密码 xxxxxx

🤖 **AI：** 已保存！以后直接说"发到阅星曈"，我就会把当前内容推送到你的墨水屏设备。

---

## 配置账号

首次使用时，AI 会提示你输入阅星曈手机号和密码，自动保存到本地 `.credentials.json`（不会上传到仓库）。

也可以提前手动创建：

```json
{
  "username": "你的手机号",
  "password": "你的密码"
}
```

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

🤖 **AI:** Done! Please share your **Yue Xingtong phone number** and **password** so I can finish setup.

🧑 **You:** Phone 138xxxxxxxx, password xxxxxx

🤖 **AI:** Saved! From now on, just say "发到阅星曈" and I'll push your content to the e-ink device.

---

## Credentials setup

On first use, the AI will prompt for your Yue Xingtong phone number and password, and save them locally to `.credentials.json` (excluded from git).

You can also create the file manually in advance:

```json
{
  "username": "your_phone_number",
  "password": "your_password"
}
```

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

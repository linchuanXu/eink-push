# eink-push · 阅星曈推送 Skill

[English below ↓](#english)

一个 [OpenClaw](https://openclaw.ai) Agent Skill，让 AI 助手能将任何创作内容——简报、分析、长文——一键推送到**阅星曈**墨水屏设备。

支持三种格式，AI 根据字数自动选择：

| 内容长度 | 格式 | 说明 |
|---------|------|------|
| ≤ 200 字 | 单张卡片 | 单幅图片，即取即读 |
| 200–2000 字 | 图片集 | 多张卡片打包，顺序翻阅 |
| > 2000 字 | 电子书 | EPUB 格式，沉浸阅读 |

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

- `发到阅星曈`
- `推到设备`
- `整理成电子书发过去`
- `把这次对话的结论整理成卡片推到墨水屏`

AI 会自动判断内容长度，选择合适格式推送。任务结束后，若产出超过 100 字，AI 也会主动询问是否推送。

---

## 故障排查

见 [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md)。

---

<a name="english"></a>

## English

An [OpenClaw](https://openclaw.ai) Agent Skill that lets AI push any content—summaries, analyses, long-form articles—to **Yue Xingtong (阅星曈)** e-ink devices with a single command.

Three formats supported, selected automatically by content length:

| Length | Format | Description |
|--------|--------|-------------|
| ≤ 200 words | Single card | One image, instant read |
| 200–2000 words | Card set | Multiple cards bundled for paged reading |
| > 2000 words | E-book | EPUB format for immersive reading |

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

In any OpenClaw conversation, say:

- *"发到阅星曈"* — push to e-ink device
- *"推到设备"* — send to device
- *"整理成电子书发过去"* — package as an e-book and send
- *"把这次对话的结论整理成卡片推到墨水屏"* — summarize and push as cards

The AI picks the right format automatically. After tasks that produce more than ~100 words, it will also proactively ask if you'd like to push.

---

## Troubleshooting

See [`references/TROUBLESHOOTING.md`](references/TROUBLESHOOTING.md).

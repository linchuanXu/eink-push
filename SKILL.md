---
name: eink_push
description: 将内容渲染并推送到阅星曈墨水屏设备（支持卡片和电子书）。当用户说「发到阅星曈 / 推到设备 / 发到墨水屏 / 推一下 / 同步到设备 / 发给阅星曈 / 推送内容 / 发到阅读器」，或任务完成后要求推送、交付、发送到墨水屏时触发。
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

**不询问的情况：** 用户只是在问问题 / 已明确说不用推 / 本次任务本身就是在执行推送流程。

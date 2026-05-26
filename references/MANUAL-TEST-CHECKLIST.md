# 手动测试清单

本文档记录需要真实账号、网络或设备的测试。自动测试和 `scripts/smoke_test.py` 不会推送设备；本清单里的推送命令会真实创建设备任务。

---

## 前置条件

- 已安装 Python 依赖：`playwright`、`Pillow`、`requests`。
- 推荐用 `pip install -r requirements.txt` 安装 Python 依赖。
- 已安装 Playwright 浏览器：`playwright install chromium`。
- 已安装 Node.js >= 18。
- 已在 Skill 根目录运行：`npm install marknative`。
- 已配置 `XTEINK_USERNAME` / `XTEINK_PASSWORD` 环境变量，或 `.credentials.json` 存在且字段完整。
- 阅星曈 App 中已绑定设备，设备联网。

---

## 1. 凭证检查

本地结构检查：

```bash
python scripts/push_to_device.py --check-credentials
```

期望：输出 `OK`。

实际登录检查：

```bash
python scripts/push_to_device.py --check-credentials --auth
```

期望：先输出 `OK`，再输出 `AUTH_OK`。

失败处理：

- `MISSING`：重新收集账号密码并写入 `.credentials.json`。
- `INVALID`：覆盖写入合法 JSON。
- `AUTH_FAILED: 账号或密码错误（401）...`：重置凭证并重新收集。

---

## 2. 离线 smoke test

```bash
python scripts/smoke_test.py
```

期望：

- 依赖齐全时生成 `output/smoke/smoke-card.xth`、`output/smoke/smoke-card.preview.png`、`output/smoke/smoke-book.xtc`、`output/smoke/smoke-book.epub`。
- 依赖缺失或当前环境禁止启动浏览器时，对应路径显示 `SKIP`，整体不推送设备。

---

## 3. 真实推送：单张卡片

```bash
python scripts/render_image.py assets/templates/base.html --preview --push
```

期望：

- 生成 `.xth` 和 `.preview.png`。
- 输出 `OUTPUT:<path>`。
- 设备收到 `/Pushed Images/...` 中的卡片。

---

## 4. 真实推送：Markdown 翻页电子书

先创建测试 Markdown：

```powershell
"# 测试书`n`n## 第一章`n`n这是测试内容。" | Out-File -Encoding utf8 output/test.md
```

生成并推送：

```bash
python scripts/render_book.py output/test.md --title "测试书" --author "龙虾" --push
```

期望：

- 生成 `output/test.xtc`。
- 输出 `OUTPUT:<path>`。
- 设备收到 `/Pushed Images/test.xtc`。

---

## 5. 真实推送：EPUB

```bash
python scripts/epub/render_book_epub.py output/test.md --title "测试书" --author "龙虾" --cover-svg --push
```

期望：

- 生成 `output/test.epub`。
- 输出 `OUTPUT:<path>`。
- 设备收到 `/Pushed Books/test.epub`。
- EPUB 可在设备阅读器中打开。

---

## 6. 读取数据：书架 compact 输出

```bash
python scripts/fetch_reading.py books --compact --limit 10
```

期望：

- stdout 为 JSON。
- `books` 中只有展示常用字段。
- 包含 `returned`、`available_in_response`、`truncated`。

---

## 7. 读取数据：书签 compact 输出

```bash
python scripts/fetch_reading.py bookmarks --all --compact --limit 20
```

期望：

- stdout 为 JSON。
- 自动过滤 `(本章结束)`。
- `bookmarks` 中只有展示常用字段。

---

## 8. 回归确认

完成真实测试后，运行：

```bash
python -m unittest discover -s tests
python scripts/push_to_device.py --check-credentials
python scripts/smoke_test.py
python scripts/verify.py
```

期望：单测通过，凭证检查 `OK`，smoke test 无失败。

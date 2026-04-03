# 环境准备 · 首次使用指南

本文档供初次使用阅星曈推送 Skill 时参考。正常推送流程中无需查阅。

---

## 安装依赖

**Python 依赖**（卡片 + 推送路径）：

```bash
pip install playwright Pillow requests
playwright install chromium
```

**Node.js 依赖**（电子书路径）：

> 前提：已安装 Node.js >= 18（https://nodejs.org/）

```bash
# 在 eink-push/ 根目录执行一次
npm install marknative
```

## 字体（可选，推荐）

```bash
# 下载字体到 assets/fonts/（离线渲染，效果最佳）
python scripts/setup_fonts.py
```

render_image.py 按以下优先级自动选择字体：

1. `assets/fonts/` 有本地文件 → 直接注入（推荐，离线可用）
2. 无本地字体 → 自动从 Google Fonts CDN 拉取（需联网，约 +3s）
3. CDN 也失败 → Playwright 使用系统字体兜底（macOS：宋体-简 Songti SC；Windows：宋体 SimSun）

## 快速验证

所有命令均需在 `eink-push/` 目录下运行：

```powershell
# 1. 测试单张卡片渲染
python scripts/render_image.py assets/templates/base.html --preview

# 2. 测试电子书生成
"# 测试书`n`n## 第一章`n`n这是测试内容。" | Out-File -Encoding utf8 output/test.md
python scripts/render_book.py output/test.md --title "测试书" --author "龙虾"

# 3. 真实推送到设备（需网络 + 设备已绑定账号）
python scripts/push_to_device.py output/test-brief.xth
python scripts/push_to_device.py output/test.xtc
```

> macOS / Linux 用户：将 `Out-File` 替换为 `echo ... >`，其余命令相同。

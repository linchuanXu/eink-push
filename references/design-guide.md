# 阅星曈卡片设计规范

AI 写自由 HTML 时遵守本文档，确保在 480×800 墨水屏上正常渲染。

---

## 画布

- **固定尺寸**：480 × 800 px，`render_image.py` 截图时精确裁切，超出会被截掉
- **无需响应式**，直接写死像素或用 `vw/vh`
- 建议根元素加：`<html style="width:480px;height:800px;overflow:hidden">`

---

## 颜色

墨水屏只有灰阶，所有颜色最终被转成 4 级灰。写 HTML 时直接用黑白灰即可，不要用彩色（写了也能渲染，但颜色信息丢失）：

| 用途 | 建议值 |
|------|--------|
| 文字 / 主要内容 | `#000000` |
| 次要文字 / 标签 | `#444444` |
| 边框 / 分隔线 | `#888888` |
| 浅色背景 / 高亮区 | `#cccccc` |
| 页面背景 | `#ffffff` |

---

## 字体

- 优先使用本地字体（已内置 **MiSans** 和 **Noto Serif SC**），`render_image.py` 会自动注入
- 也可以用 Tailwind CDN / Google Fonts，Playwright 联网加载
- **最小字号 22px**，低于此在 e-ink 上偏小，阅读费力
- **正文 26–32px**（`base.html` 默认 28px），标题 36–48px
- 副标题 / 标签 / 元信息可用 20–24px，但不要再小
- 行高 1.6 以上，中文大字体也需要充足行距

```css
/* 推荐字体声明 */
font-family: 'MiSans', 'Noto Serif SC', serif;
```

---

## 布局注意事项

**可以用：**
- Flexbox / Grid — 完全支持
- `border`, `border-radius` — 支持
- `box-shadow` — 支持（灰度渲染，淡阴影效果不明显，加深一点）
- Tailwind CDN — 直接引入，Playwright 联网时正常工作

**避免：**
- CSS 动画 / transition（截图是静止画面，动画无意义）
- `background-image: url(http://...)` 外链图片（慢，可能失败）
- 渐变（`linear-gradient`）——墨水屏灰阶转换后效果差，改用纯色块
- 极细线（`1px` 有时在抖点后消失，建议 ≥ 2px）
- 大面积中灰（`#888888`）背景——抖点后变成噪点，用浅灰或白

---

## 框架菜单（随内容氛围选一个）

写卡片前先感受内容的气质，然后从下面选一个框架。以下框架均通过 CDN 引入，Playwright 联网时自动加载。也可选"无框架"离线使用。

---

### 1. Tailwind CSS — 现代、灵活、高密度信息
适合：数据卡、战情板、进度报告、结构化内容

```html
<script src="https://cdn.tailwindcss.com"></script>
```

常用灰阶 class：`text-black` `text-gray-600` `text-gray-400` `bg-white` `bg-gray-50` `bg-gray-100` `bg-gray-200` `border-gray-200` `border-gray-400`

---

### 2. Water.css — 无 class，素雅，阅读感强
适合：文章摘要、日记、语录、以段落为主的内容

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/light.css">
```

只需写语义 HTML（`<h1>` `<p>` `<blockquote>` `<ul>`），自动好看。

---

### 3. Pico.css — 简洁优雅，衬线感
适合：简报、阅读型卡片、知识摘要

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.classless.min.css">
```

同样写语义 HTML 即可，风格比 Water.css 更工整。

---

### 4. MVP.css — 极简主义，大字留白
适合：一句话金句、Today I Learned、单条重点

```html
<link rel="stylesheet" href="https://unpkg.com/mvp.css">
```

---

### 5. 无框架（离线，最快）
适合：需要完全掌控布局，或网络不可用时

直接在 `<style>` 里写 CSS，或从 `assets/templates/base.html` 读取起点（已含 reset + 色板变量 + 字体变量）。

---

## 起点文件

`assets/templates/base.html` — 极简空白画布，已包含 reset、canvas 尺寸、色板变量、字体变量。

Read 它作为起点，在 `<body>` 里自由写内容。也可以完全不用，直接写完整 HTML。

---

## 质量检查（写完 HTML 后自问）

- [ ] 内容是否超出 800px 高度？（加 `overflow:hidden` 强制裁切）
- [ ] 正文字号 ≥ 26px，标题 ≥ 36px？（墨水屏宜大不宜小）
- [ ] 没有用纯彩色作为主要信息载体？（颜色会丢失）
- [ ] 没有依赖外链图片？

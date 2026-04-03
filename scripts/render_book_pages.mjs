#!/usr/bin/env node
/**
 * render_book_pages.mjs — Markdown → 分页 PNG（供 render_book.py 调用）
 *
 * 用法：
 *   node render_book_pages.mjs <input.md> <output_dir>
 *
 * stdout：JSON { count: N, files: ["...page_0001.png", ...] }
 * stderr：错误信息
 *
 * 依赖：npm install marknative（在项目根目录）
 */

import { renderMarkdown, defaultTheme } from 'marknative';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// skia-canvas 是 marknative 的原生依赖，版本不匹配时降级，不影响渲染
let FontLibrary;
try {
  ({ FontLibrary } = await import('skia-canvas'));
} catch {
  /* 原生模块不可用，字体加载跳过，使用系统字体 */
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const FONT_DIR = join(PROJECT_ROOT, 'assets', 'fonts');

// ── 注册本地中文字体（FontLibrary 不可用时静默跳过）──────────────────────────
function loadFonts() {
  if (!FontLibrary) return;
  const fonts = [
    { alias: 'Noto Serif SC', files: ['NotoSerifSC-Regular.otf', 'NotoSerifSC-Bold.otf', 'NotoSerifSC-Black.otf'] },
    { alias: 'MiSans',        files: ['MiSans-Regular.otf', 'MiSans-Medium.otf', 'MiSans-Demibold.otf', 'MiSans-Bold.otf'] },
  ];
  for (const { alias, files } of fonts) {
    const paths = files.map(f => join(FONT_DIR, f)).filter(p => {
      try { readFileSync(p); return true; } catch { return false; }
    });
    if (paths.length > 0) {
      try { FontLibrary.use(alias, paths); } catch { /* 静默降级 */ }
    }
  }
}

// ── 配置阅星曈屏幕主题（480×800）──────────────────────────────────────────
function applyEinkTheme() {
  defaultTheme.page.width = 480;
  defaultTheme.page.height = 800;
  defaultTheme.page.margin = { top: 40, right: 36, bottom: 40, left: 36 };

  defaultTheme.typography.body.font       = '30px "Noto Serif SC", serif';
  defaultTheme.typography.body.lineHeight = 48;
  defaultTheme.typography.h1.font         = 'bold 44px "Noto Serif SC", serif';
  defaultTheme.typography.h1.lineHeight   = 64;
  defaultTheme.typography.h2.font         = 'bold 36px "Noto Serif SC", serif';
  defaultTheme.typography.h2.lineHeight   = 56;
  defaultTheme.typography.code.font       = '24px monospace';
  defaultTheme.typography.code.lineHeight = 36;

  defaultTheme.blocks.paragraph.marginBottom  = 24;
  defaultTheme.blocks.heading.marginTop       = 36;
  defaultTheme.blocks.heading.marginBottom    = 16;
  defaultTheme.blocks.list.marginBottom       = 24;
  defaultTheme.blocks.list.itemGap            = 8;
  defaultTheme.blocks.list.indent             = 36;
  defaultTheme.blocks.code.marginBottom       = 24;
  defaultTheme.blocks.code.padding            = 24;
  defaultTheme.blocks.quote.marginBottom      = 16;
  defaultTheme.blocks.quote.padding           = 16;
  defaultTheme.blocks.table.marginBottom      = 24;
  defaultTheme.blocks.table.cellPadding       = 16;
  defaultTheme.blocks.image.marginBottom      = 24;
}

// ── 主流程 ─────────────────────────────────────────────────────────────────
const mdPath  = process.argv[2];
const outDir  = process.argv[3];

if (!mdPath || !outDir) {
  process.stderr.write('Usage: render_book_pages.mjs <input.md> <output_dir>\n');
  process.exit(1);
}

let markdown;
try {
  markdown = readFileSync(resolve(mdPath), 'utf-8');
} catch (e) {
  process.stderr.write(`[ERROR] 无法读取文件：${mdPath}\n${e.message}\n`);
  process.exit(1);
}

loadFonts();
applyEinkTheme();

let pages;
try {
  pages = await renderMarkdown(markdown);
} catch (e) {
  process.stderr.write(`[ERROR] marknative 渲染失败：\n${e.message}\n${e.stack}\n`);
  process.exit(1);
}

mkdirSync(outDir, { recursive: true });

const files = [];
for (let i = 0; i < pages.length; i++) {
  const filename = join(outDir, `page_${String(i + 1).padStart(4, '0')}.png`);
  writeFileSync(filename, pages[i].data);
  files.push(filename);
}

process.stdout.write(JSON.stringify({ count: pages.length, files }) + '\n');

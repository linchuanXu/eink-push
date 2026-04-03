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
import { join, resolve } from 'path';

// ── 配置阅星曈屏幕主题（480×800）──────────────────────────────────────────
// 字体由 Skia 从系统中自动匹配（sans-serif / monospace）
function applyEinkTheme() {
  defaultTheme.page.width = 480;
  defaultTheme.page.height = 800;
  defaultTheme.page.margin = { top: 20, right: 18, bottom: 20, left: 18 };

  defaultTheme.typography.body.font       = '500 30px sans-serif';
  defaultTheme.typography.body.lineHeight = 48;
  defaultTheme.typography.h1.font         = 'bold 44px sans-serif';
  defaultTheme.typography.h1.lineHeight   = 64;
  defaultTheme.typography.h2.font         = 'bold 36px sans-serif';
  defaultTheme.typography.h2.lineHeight   = 56;
  defaultTheme.typography.code.font       = '500 24px monospace';
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

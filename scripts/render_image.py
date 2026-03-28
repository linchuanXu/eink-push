#!/usr/bin/env python3
"""
render_image.py — HTML 卡片模板 → 阅星曈设备图片

用法（单张）：
    python render_image.py <input.html> [options]

用法（多张，打包为翻页图片集）：
    python render_image.py <a.html> <b.html> <c.html> [options]

输出格式（--format，通常无需指定）：
    xth   高清图，4 灰阶（默认）
    xtg   快刷图，1bit 黑白

选项：
    --output, -o    输出文件路径（单张时有效；默认：第一个输入同目录同名换扩展名）
    --format        xth | xtg（默认 xth）
    --title         元数据：标题（写入 XTC/XTCH 容器）
    --author        元数据：作者（写入 XTC/XTCH 容器）
    --width         输出宽度（默认 480）
    --height        输出高度（默认 800）
    --preview       额外输出 PNG 预览图（仅单张有效）
    --no-fonts      跳过本地字体注入

图像调整（仅 xth/xtg 生效）：
    --brightness    亮度  -100..100（默认 0）
    --contrast      对比度 -100..100（默认 0）
    --gamma         伽马值 0.4..2.5（默认 1.0）
    --sharpen       锐化  0..100（默认 0）
    --dither-pct    抖点强度 0..100（默认 50）
    --invert        反色
    --threshold     XTG 二值阈值 0..255（默认 128）

依赖:
    pip install playwright Pillow
    playwright install chromium
"""

import argparse
import re
import struct
import sys
import time
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple


# ─── 常量 ────────────────────────────────────────────────────────────────────

SCREEN_W = 480
SCREEN_H = 800
FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"


# ═══════════════════════════════════════════════════════════════════════════════
# XTG / XTH 单帧编码
# ═══════════════════════════════════════════════════════════════════════════════

class XtgXthParams(NamedTuple):
    brightness: int = 0       # -100..100
    contrast: int = 0         # -100..100
    gamma: float = 1.0        # 0.4..2.5
    sharpen: int = 0          # 0..100
    dither: int = 50          # 0..100
    invert: bool = False
    threshold: int = 128      # XTG 二值阈值 0..255
    xthT1: int = 43           # XTH 三阈值
    xthT2: int = 128
    xthT3: int = 213


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _clamp_i(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _process_gray(rgb: bytes, width: int, height: int, p: XtgXthParams) -> List[int]:
    """RGB 字节 → 灰度列表（含亮度/对比度/Gamma/锐化/反色）"""
    n = width * height
    cv = _clamp_i(int(_clamp_i(p.contrast, -100, 100) * 2.55), -258, 258)
    cf = (259.0 * (cv + 255)) / (255.0 * (259 - cv))

    gray_float: List[float] = [0.0] * n
    for i in range(n):
        r, g, b = rgb[i * 3], rgb[i * 3 + 1], rgb[i * 3 + 2]
        v = 0.299 * r + 0.587 * g + 0.114 * b
        v += p.brightness * 2.55
        v = cf * (v - 128.0) + 128.0
        v = 255.0 * (_clamp(v / 255.0, 0.0, 1.0) ** (1.0 / p.gamma))
        if p.invert:
            v = 255.0 - v
        gray_float[i] = _clamp(v, 0.0, 255.0)

    if p.sharpen > 0:
        copy = gray_float[:]
        amt = _clamp_i(p.sharpen, 0, 100) / 100.0
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                idx = y * width + x
                c = copy[idx]
                edge = (c * 4.0
                        - copy[idx - 1] - copy[idx + 1]
                        - copy[idx - width] - copy[idx + width])
                gray_float[idx] = _clamp(c + edge * amt, 0.0, 255.0)

    return [int(round(g)) for g in gray_float]


def _floyd_steinberg_xtg(
    gray: List[int], width: int, height: int, dither_pct: int, threshold: int
) -> List[int]:
    work = [float(g) for g in gray]
    d = _clamp(dither_pct / 100.0, 0.0, 1.0)
    out: List[int] = [0] * len(gray)
    for y in range(height):
        for x in range(width):
            i = y * width + x
            old = _clamp(work[i], 0.0, 255.0)
            nv = 255 if old >= threshold else 0
            out[i] = nv
            if d <= 0:
                continue
            err = (old - nv) * d
            if x + 1 < width:
                work[i + 1] += err * (7.0 / 16.0)
            if y + 1 < height:
                dn = i + width
                if x > 0:
                    work[dn - 1] += err * (3.0 / 16.0)
                work[dn] += err * (5.0 / 16.0)
                if x + 1 < width:
                    work[dn + 1] += err * (1.0 / 16.0)
    return out


def _floyd_steinberg_xth(
    gray: List[int], width: int, height: int, dither_pct: int,
    t1: int, t2: int, t3: int
) -> List[int]:
    t1, t2, t3 = sorted([t1, t2, t3])
    work = [float(g) for g in gray]
    d = _clamp(dither_pct / 100.0, 0.0, 1.0)
    out: List[int] = [0] * len(gray)
    for y in range(height):
        for x in range(width):
            i = y * width + x
            old = _clamp(work[i], 0.0, 255.0)
            if old < t1:
                nv = 0
            elif old < t2:
                nv = 85
            elif old < t3:
                nv = 170
            else:
                nv = 255
            out[i] = nv
            if d <= 0:
                continue
            err = (old - nv) * d
            if x + 1 < width:
                work[i + 1] += err * (7.0 / 16.0)
            if y + 1 < height:
                dn = i + width
                if x > 0:
                    work[dn - 1] += err * (3.0 / 16.0)
                work[dn] += err * (5.0 / 16.0)
                if x + 1 < width:
                    work[dn + 1] += err * (1.0 / 16.0)
    return out


def _checksum64(body: bytes) -> int:
    h = 1469598103934665603
    p = 1099511628211
    for b in body:
        h ^= b
        h = (h * p) & ((1 << 64) - 1)
    return h


def _build_xt_header(
    magic: int, width: int, height: int,
    color_mode: int, compression: int, body: bytes
) -> bytes:
    """XTG/XTH 22字节文件头：magic + width + height + colorMode + compression + dataSize + checksum(8)"""
    cs = _checksum64(body)
    return struct.pack(
        "<IHHBBIII",
        magic,
        width & 0xFFFF,
        height & 0xFFFF,
        color_mode,
        compression,
        len(body) & 0xFFFFFFFF,
        cs & 0xFFFFFFFF,
        (cs >> 32) & 0xFFFFFFFF,
    )


def _encode_xtg(gray: List[int], width: int, height: int) -> bytes:
    """
    XTG: 1bit/像素，行优先，MSB = 最左像素。
    magic 0x00475458，colorMode 0（monochrome）。
    像素值 1=白，0=黑。
    """
    bpr = (width + 7) // 8
    body = bytearray(bpr * height)
    for y in range(height):
        for x in range(width):
            if gray[y * width + x] >= 128:
                body[y * bpr + (x >> 3)] |= 1 << (7 - (x & 7))
    body = bytes(body)
    return _build_xt_header(0x00475458, width, height, 0, 0, body) + body


def _encode_xth(gray: List[int], width: int, height: int) -> bytes:
    """
    XTH: 4灰阶 2bit/像素，两个位平面，列从右到左纵向扫描。
    magic 0x00485458，colorMode 1。
    LUT: pixelValue=(bit1<<1)|bit2, 0=白 1=深灰 2=浅灰 3=黑（中间值互换）。
    """
    bpc = (height + 7) // 8          # bytes per column per plane
    plane_len = width * bpc
    dtm1 = bytearray(plane_len)      # bit1 plane (cmd 0x24)
    dtm2 = bytearray(plane_len)      # bit2 plane (cmd 0x26)
    for x in range(width - 1, -1, -1):
        co = (width - 1 - x) * bpc
        for y in range(height):
            v = gray[y * width + x]
            # 映射到设备 LUT 的 0..3 档（0=白,1=深灰,2=浅灰,3=黑）
            tb = 0 if v <= 42 else (2 if v <= 127 else (1 if v <= 212 else 3))
            sv = 3 - tb              # 存储值（设备 LUT 映射）
            bi = 7 - (y & 7)
            by_ = co + (y >> 3)
            dtm1[by_] |= ((sv >> 1) & 1) << bi
            dtm2[by_] |= (sv & 1) << bi
    body = bytes(dtm1) + bytes(dtm2)
    return _build_xt_header(0x00485458, width, height, 1, 0, body) + body


def png_bytes_to_xtg_xth(
    png_bytes: bytes, params: XtgXthParams
) -> Tuple[bytes, bytes]:
    """PNG bytes → (xtg_bytes, xth_bytes)"""
    try:
        from PIL import Image
        import io
    except ImportError:
        print("[ERROR] Pillow 未安装。运行：pip install Pillow")
        sys.exit(1)

    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    width, height = img.size
    rgb = img.tobytes()

    gray = _process_gray(rgb, width, height, params)
    q_xtg = _floyd_steinberg_xtg(gray, width, height, params.dither, params.threshold)
    q_xth = _floyd_steinberg_xth(
        gray, width, height, params.dither,
        params.xthT1, params.xthT2, params.xthT3
    )
    return _encode_xtg(q_xtg, width, height), _encode_xth(q_xth, width, height)


# ═══════════════════════════════════════════════════════════════════════════════
# XTC / XTCH 多帧容器
# ═══════════════════════════════════════════════════════════════════════════════
#
# XTC  magic 0x00435458 — 存储多帧 XTG（快刷翻页）
# XTCH magic 0x48435458 — 存储多帧 XTH（高清翻页）
# 除 magic 外，两种格式结构完全相同。
#
# 文件布局（简化，不含缩略图/章节）：
#   [Header  56B]
#   [Metadata 256B]（可选，title/author 不为空时写入）
#   [Page Index  pageCount×16B]
#   [Data Area   所有 XTG/XTH 页面数据连续存储]

_XTC_MAGIC  = 0x00435458   # "XTC\0"
_XTCH_MAGIC = 0x48435458   # "XTCH"

_HEADER_SIZE = 56
_META_SIZE   = 256
_INDEX_ENTRY = 16


def _encode_xtc_xtch(
    pages: List[bytes],
    magic: int,
    title: str = "",
    author: str = "",
) -> bytes:
    """
    将多个 XTG（magic=XTC）或 XTH（magic=XTCH）页面打包为容器文件。

    pages  : 已编码的 XTG 或 XTH 字节列表
    magic  : _XTC_MAGIC 或 _XTCH_MAGIC
    title  : 容器元数据标题（可选）
    author : 容器元数据作者（可选）
    """
    page_count   = len(pages)
    has_metadata = 1 if (title or author) else 0

    # ── 计算各区段起始偏移 ──────────────────────────────────────────────────
    meta_offset  = _HEADER_SIZE if has_metadata else 0
    index_offset = _HEADER_SIZE + (_META_SIZE if has_metadata else 0)
    data_offset  = index_offset + page_count * _INDEX_ENTRY

    # ── 索引表 + 数据区 ─────────────────────────────────────────────────────
    index_data = bytearray()
    page_data  = bytearray()
    cur_offset = data_offset

    for page_bytes in pages:
        # 从 XTG/XTH 文件头读取宽高（偏移 4,6 各 uint16_t）
        pw = struct.unpack_from("<H", page_bytes, 4)[0]
        ph = struct.unpack_from("<H", page_bytes, 6)[0]
        ps = len(page_bytes)
        # 索引条目：offset(8) + size(4) + width(2) + height(2) = 16B
        index_data += struct.pack("<QIHH", cur_offset, ps, pw, ph)
        page_data  += page_bytes
        cur_offset += ps

    # ── 元数据块（256B）──────────────────────────────────────────────────────
    meta_bytes = b""
    if has_metadata:
        def _enc_str(s: str, size: int) -> bytes:
            b = s.encode("utf-8")[:size - 1]
            return b + b"\x00" * (size - len(b))

        meta_bytes = (
            _enc_str(title, 128)           # title
            + _enc_str(author, 64)         # author
            + _enc_str("", 32)             # publisher
            + _enc_str("", 16)             # language
            + struct.pack("<IHH",
                int(time.time()),          # createTime
                0xFFFF,                    # coverPage (none)
                0)                         # chapterCount
            + b"\x00" * 8                  # reserved
        )

    # ── 文件头（56B）────────────────────────────────────────────────────────
    # <I  H       H          B              B            B              B
    #  mark version pageCount readDirection hasMetadata  hasThumbnails  hasChapters
    # I           Q              Q            Q          Q             Q
    # currentPage metadataOffset indexOffset  dataOffset thumbOffset   chapterOffset
    header = struct.pack(
        "<IHHBBBBIQQQQQ",
        magic,
        0x0100,          # version 1.0
        page_count,
        0,               # readDirection: L→R
        has_metadata,
        0,               # hasThumbnails
        0,               # hasChapters
        1,               # currentPage (1-based, start at page 1)
        meta_offset,
        index_offset,
        data_offset,
        0,               # thumbOffset
        0,               # chapterOffset
    )

    return header + meta_bytes + bytes(index_data) + bytes(page_data)


def encode_xtc(pages_xtg: List[bytes], title: str = "", author: str = "") -> bytes:
    """多帧 XTG → XTC 容器（快刷翻页）"""
    return _encode_xtc_xtch(pages_xtg, _XTC_MAGIC, title, author)


def encode_xtch(pages_xth: List[bytes], title: str = "", author: str = "") -> bytes:
    """多帧 XTH → XTCH 容器（高清翻页）"""
    return _encode_xtc_xtch(pages_xth, _XTCH_MAGIC, title, author)


# ═══════════════════════════════════════════════════════════════════════════════
# Playwright：HTML → PNG
# ═══════════════════════════════════════════════════════════════════════════════

def _build_font_css(font_dir: Path) -> str:
    rules = []
    font_map = [
        ("Noto Serif SC", "400", "normal", "NotoSerifSC-Regular*"),
        ("Noto Serif SC", "700", "normal", "NotoSerifSC-Bold*"),
        ("Noto Serif SC", "900", "normal", "NotoSerifSC-Black*"),
        ("MiSans",        "400", "normal", "MiSans-Regular*"),
        ("MiSans",        "500", "normal", "MiSans-Medium*"),
        ("MiSans",        "600", "normal", "MiSans-Demibold*"),
        ("MiSans",        "700", "normal", "MiSans-Bold*"),
        ("Space Mono",    "400", "normal", "SpaceMono-Regular*"),
        ("Space Mono",    "700", "normal", "SpaceMono-Bold*"),
    ]
    for family, weight, style, pattern in font_map:
        matched = list(font_dir.glob(pattern))
        if not matched:
            continue
        font_path = matched[0].as_posix()
        rules.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
            f"font-style: {style}; src: url('file://{font_path}'); }}"
        )
    return "\n".join(rules)


def screenshot_html(html_path: Path, width: int, height: int, inject_fonts: bool) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright 未安装。运行：pip install playwright && playwright install chromium")
        sys.exit(1)

    html_url = f"file://{html_path.resolve().as_posix()}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.goto(html_url, wait_until="networkidle")

        if inject_fonts:
            font_css = _build_font_css(FONT_DIR) if FONT_DIR.exists() else ""
            if font_css:
                page.add_style_tag(content=font_css)
                page.evaluate("document.fonts.ready")
                print(f"[INFO] 使用本地字体：{html_path.name}")
            else:
                print(f"[INFO] 从 Google Fonts CDN 加载字体：{html_path.name}")
                page.add_style_tag(content="""
                    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900&family=Space+Mono:wght@400;700&display=swap');
                """)
                page.wait_for_load_state("networkidle", timeout=15000)
                page.evaluate("document.fonts.ready")

        png_bytes = page.screenshot(
            full_page=False,
            clip={"x": 0, "y": 0, "width": width, "height": height},
            type="png",
        )
        browser.close()
    return png_bytes


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="将 HTML 卡片模板渲染为阅星曈设备图片格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", help="输入 HTML 文件路径（可多个）")
    parser.add_argument("--output", "-o", default=None,
                        help="输出文件路径（默认：第一个输入同名换扩展名）")
    parser.add_argument("--format", choices=["xth", "xtg"], default=None,
                        help="输出格式：xth 高清图（默认）| xtg 快刷图")
    parser.add_argument("--title",  default="", help="容器元数据：标题（多帧时写入）")
    parser.add_argument("--author", default="", help="容器元数据：作者（多帧时写入）")
    parser.add_argument("--width",  type=int, default=SCREEN_W)
    parser.add_argument("--height", type=int, default=SCREEN_H)
    parser.add_argument("--preview", action="store_true",
                        help="额外输出 PNG 预览图（仅单张有效）")
    parser.add_argument("--no-fonts", action="store_true", help="跳过本地字体注入")

    # 图像调整
    parser.add_argument("--brightness", type=int,   default=0,   metavar="N")
    parser.add_argument("--contrast",   type=int,   default=0,   metavar="N")
    parser.add_argument("--gamma",      type=float, default=1.0, metavar="F")
    parser.add_argument("--sharpen",    type=int,   default=0,   metavar="N")
    parser.add_argument("--dither-pct", type=int,   default=50,  metavar="N")
    parser.add_argument("--invert",     action="store_true")
    parser.add_argument("--threshold",  type=int,   default=128, metavar="N")

    args = parser.parse_args()

    html_paths = [Path(p).resolve() for p in args.inputs]
    for hp in html_paths:
        if not hp.exists():
            print(f"[ERROR] 文件不存在：{hp}")
            sys.exit(1)

    multi = len(html_paths) > 1
    # 默认格式：xth 高清图；用户可用 --format xtg 切换快刷
    fmt = args.format if args.format is not None else "xth"

    params = XtgXthParams(
        brightness=args.brightness,
        contrast=args.contrast,
        gamma=args.gamma,
        sharpen=args.sharpen,
        dither=args.dither_pct,
        invert=args.invert,
        threshold=args.threshold,
    )

    # 确定输出路径
    if multi:
        out_ext = "xtch" if fmt == "xth" else "xtc"
    else:
        out_ext = fmt  # xth 或 xtg

    if args.output:
        output_path = Path(args.output).resolve()
    elif multi:
        # 多张模式：去掉第一个文件名中的 _pN 序号，作为容器文件名
        stem = re.sub(r"_p\d+", "", html_paths[0].stem)
        output_path = html_paths[0].parent / f"{stem}.{out_ext}"
    else:
        output_path = html_paths[0].with_suffix(f".{out_ext}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 渲染所有帧 ────────────────────────────────────────────────────────────
    frames_xtg: List[bytes] = []
    frames_xth: List[bytes] = []

    for i, html_path in enumerate(html_paths):
        label = f"[{i+1}/{len(html_paths)}] " if multi else ""
        print(f"[INFO] {label}渲染：{html_path.name}  尺寸：{args.width}×{args.height}  格式：{fmt.upper()}")

        png_bytes = screenshot_html(
            html_path=html_path,
            width=args.width,
            height=args.height,
            inject_fonts=not args.no_fonts,
        )
        print(f"[INFO] {label}截图完成，PNG {len(png_bytes) // 1024} KB")

        # 单张预览（仅第一张，仅单帧模式）
        if not multi and args.preview:
            preview_path = output_path.with_suffix(".preview.png")
            preview_path.write_bytes(png_bytes)
            print(f"[INFO] 预览已保存：{preview_path}")

        xtg_b, xth_b = png_bytes_to_xtg_xth(png_bytes, params)
        frames_xtg.append(xtg_b)
        frames_xth.append(xth_b)

    # ── 写出最终文件 ──────────────────────────────────────────────────────────
    if multi:
        if fmt == "xth":
            data = encode_xtch(frames_xth, title=args.title, author=args.author)
            label = "XTCH"
        else:
            data = encode_xtc(frames_xtg, title=args.title, author=args.author)
            label = "XTC"
        output_path.write_bytes(data)
        print(f"[OK] {label} 已生成：{output_path}  ({len(data) // 1024} KB，共 {len(html_paths)} 帧)")
    else:
        data = frames_xth[0] if fmt == "xth" else frames_xtg[0]
        output_path.write_bytes(data)
        print(f"[OK] {fmt.upper()} 已生成：{output_path}  ({len(data) // 1024} KB)")

    print(f"OUTPUT:{output_path}")


if __name__ == "__main__":
    main()

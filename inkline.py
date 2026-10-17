#!/usr/bin/env python3
"""inkline — Markdown → Kindle EPUB3，行内公式精确基线对齐。

核心：用 TeX 的真实 depth 值换算 CSS vertical-align，实现公式与正文的
像素级基线对齐。详见 PRINCIPLE.md。

用法:
    python3 inkline.py input.md output.epub --title "书名" --author "作者"
    python3 inkline.py src/ -o book.epub --title "书名" --recursive

依赖:
    python3 -m pip install mistune pygments pillow
    系统需 latex + dvisvgm（TeX Live / MacTeX）
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inkline_lib import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description='Markdown → Kindle EPUB3（公式精确对齐）')
    ap.add_argument('src', help='输入 .md 文件或目录')
    ap.add_argument('out', nargs='?', help='输出 .epub（或 -o）')
    ap.add_argument('-o', '--output', dest='out_opt')
    ap.add_argument('--title', default='Untitled')
    ap.add_argument('--author', default='')
    ap.add_argument('-r', '--recursive', action='store_true')
    ap.add_argument('-j', '--jobs', type=int, default=8)
    ap.add_argument('--kindle', action='store_true',
                        help='Kindle 版：公式走 PNG 外链（KF8 丢弃内联 SVG）')
    ap.add_argument('--kfx', metavar='OUT.kfx',
                        help='直出 KFX（EPUB→白底→boko→行内修复，需装 boko）')
    a = ap.parse_args()

    out = a.out or a.out_opt
    if not out and not a.kfx:
        sys.exit('need output path (-o out.epub or --kfx out.kfx)')
    epub_out = out or a.kfx + '.tmp.epub'
    epub_built = build(a.src, epub_out, a.title, a.author, a.recursive, a.jobs, True if a.kfx else a.kindle)
    if a.kfx:
        from inkline_lib.kfx_build import epub_to_kfx
        epub_to_kfx(epub_built, a.kfx)
        if not out:
            import os as _os
            _os.remove(epub_built)


if __name__ == '__main__':
    main()

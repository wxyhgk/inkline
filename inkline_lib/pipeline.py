"""构建主流程：扫描 → 预渲染 → 渲染 → 打包。"""
import os
import re
import shutil
import sys
import tempfile

import mistune
from pygments.formatters import HtmlFormatter

from .epub import write_epub
from .htmlrender import Renderer, bucket_css, display_math_html
from .mathrender import MathRenderer
from .styles import CSS
from .util import (anchor, clean_source, esc, extract_formulas, next_version,
                   read_sources, rewrite_md_links)


def build(src, out, title, author, recursive=False, jobs=8, kindle=False):
    """把 src（.md 文件或目录）构建成 out.epub。"""
    files = read_sources(src, recursive)
    if not files:
        sys.exit(f'no markdown found: {src}')
    print(f'sources: {len(files)} file(s)')

    tmp = tempfile.mkdtemp()
    try:
        # 公式渲染缓存持久化（跨次构建复用），否则每次全量都要重渲
        cachedir = os.path.join(os.path.expanduser('~'), '.cache', 'inkline')
        mr = MathRenderer(os.path.join(tmp, 'math'), jobs=jobs,
                          cache_dir=cachedir)
        mr.base_dir = os.path.dirname(os.path.abspath(files[0]))

        # 1) 读源 + 预处理 + 收集公式
        docs = []
        formulas = []
        for f in files:
            t = clean_source(open(f, encoding='utf-8').read())
            docs.append((f, t))
            formulas += extract_formulas(t)
        print(f'inline/display formulas: {len(formulas)} '
              f'(unique {len(set(formulas))})')

        # 2) 并行预渲染公式
        mr.render_all(formulas)
        print(f'rendered: {mr.ok_count()}/{len(mr._results)}')

        out = next_version(out)
        print(f'output: {out}')

        # 3) 渲染 Markdown
        renderer = Renderer(mr, kindle=kindle)
        md = mistune.create_markdown(renderer=renderer, plugins=['math', 'table'])
        parts = []
        for f, t in docs:
            parts.append(_render_doc(md, mr, t, f, files, kindle))
        defs = mr.glyphs.defs_block() if len(mr.glyphs) else ''
        html = ('<!DOCTYPE html>\n'
                '<html xmlns="http://www.w3.org/1999/xhtml" lang="zh">\n'
                f'<head><meta charset="utf-8"/><title>{esc(title)}</title>\n'
                '<link rel="stylesheet" href="style.css"/></head>\n'
                f'<body>' + defs + ''.join(parts) + '</body></html>')

        nav_entries = _nav_entries(docs)
        css = _full_css(mr, kindle)
        write_epub(out, html, css, os.path.join(tmp, 'math'), mr.imgdir,
                   nav_entries, title, author)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f'built {out} ({os.path.getsize(out) / 1024:.0f} KB)')
    return out


def _render_doc(md, mr, text, path, all_files, kindle=False):
    """渲染单个文档：公式占位 → 渲染 → 替换 → 注入锚点。"""
    text = rewrite_md_links(text, all_files)
    displays = []

    def grab(m):
        displays.append(m.group(1))
        return f'\n\n\x02DM{len(displays) - 1}\x02\n\n'

    text = re.sub(r'\$\$(.+?)\$\$', grab, text, flags=re.S)
    body = md(text)

    # 显示公式占位符是独立段落，替换时连 <p> 一起去掉，
    # 否则 <div> 嵌在 <p> 里会造成 EPUB 解析错乱
    for i, lx in enumerate(displays):
        ph = f'\x02DM{i}\x02'
        dm = display_math_html(lx.strip(), mr, kindle)
        body = body.replace(f'<p>{ph}</p>', dm).replace(ph, dm)

    # 首标题注入锚点 id（供 nav 与跨章链接跳转）
    return re.sub(r'<h([1-3])>',
                  lambda m: f'<h{m.group(1)} id="{anchor(path)}">', body, count=1)


def _nav_entries(docs):
    """从各文档首个 H1 生成 TOC 条目。"""
    entries = []
    for f, t in docs:
        m = re.search(r'^#\s+(.+)$', t, re.M)
        if m:
            title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            entries.append((anchor(f), title))
    return entries


def _full_css(mr, kindle=False):
    """基础 CSS + Pygments 高亮配色 + 公式分桶规则。"""
    hl_css = HtmlFormatter(style='friendly').get_style_defs('.hl')
    css = (CSS
           + '\n/* Pygments 语法高亮 */\n' + hl_css
           + '\n/* 行内公式分桶（剥离行内样式时仍随字号缩放） */\n'
           + bucket_css(mr.buckets) + '\n')
    if kindle:
        # KFX 背景渲染不可控：代码块去背景、无边框（靠等宽+换行区分）
        css += ('\n/* Kindle：代码块无背景 */\n'
                'pre.term, .hl pre, pre.term code, .hl code, code {background:none !important; border:0 !important;}\n')
    return css

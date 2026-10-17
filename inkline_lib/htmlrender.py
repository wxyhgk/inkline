"""Markdown → HTML：公式 HTML 生成、分桶 class、mistune 渲染器。

双轨输出公式尺寸：
  - 行内 style（em）→ Kindle / Apple Books 精确对齐
  - 分桶 class（em）→ 微信读书等剥离行内样式的阅读器仍随字号缩放
"""
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
import mistune

from .mathrender import PT2EM
from .util import esc
# 终端/纯文本语言不语法高亮，用等宽框
PLAIN_LANGS = {'text', 'console', 'output', 'shell-session', 'plain', ''}

# Kindle KFX(boko) 吃掉 pre 内空白：显式 br + nbsp，绕开 white-space 依赖
def kfx_pre(html):
    """pre/div.hl 块内：标签外文本换行→<br/>，缩进空格→nbsp。"""
    import re as _re
    def fix(m):
        tag, inner = m.group(1), m.group(2)
        parts = _re.split(r'(<[^>]+>)', inner)
        for i, p in enumerate(parts):
            if p.startswith('<') or not p:
                continue
            lines = p.split('\n')
            out = []
            for j, ln in enumerate(lines):
                # 行首空格→nbsp（缩进），行内连续2+空格→nbsp（对齐）
                k = 0
                while k < len(ln) and ln[k] == ' ':
                    k += 1
                ln = '&nbsp;' * k + ln[k:]
                ln = _re.sub(r'  +', lambda x: '&nbsp;' * len(x.group(0)), ln)
                out.append(ln)
            parts[i] = '<br/>'.join(out)
        return f'<{tag}>' + ''.join(parts) + f'</{tag.split()[0]}>'
    return _re.sub(r'<(pre[^>]*|div class="hl"[^>]*)>(.*?)</(pre|div)>', fix, html, flags=_re.S)

# ---------------------------------------------------------------- 分桶

def _bucket(x, step, lo, hi):
    """量化到 step 档，返回 (整数值 ×1000, 精确值)。"""
    x = max(lo, min(hi, x))
    d = int(round(x / step)) * step
    return int(round(d * 1000)), round(d, 4)


def bucket_class(w, h, v):
    """宽/高/偏移各自量化成独立 class，避免笛卡尔积爆炸。"""
    wi, _ = _bucket(w, 0.05, 0.20, 20.0)     # 宽 0.05em
    hi, _ = _bucket(h, 0.05, 0.50, 1.35)     # 高 0.05em
    vi, _ = _bucket(v, 0.025, -0.60, 0.0)    # 基线偏移 0.025em
    return f'iw{wi}', f'ih{hi}', f'iv{-vi}'


def bucket_css(buckets):
    """把分桶集合转成 CSS 规则。"""
    drops = []
    for c in sorted(buckets):
        if c == 'ivmid':
            drops.append('img.im.ivmid,svg.ivmid{vertical-align:middle}')
            continue
        n = int(c[2:]) / 1000
        if c.startswith('iw'):
            drops.append(f'img.im.{c},img.{c},svg.im.{c},svg.{c}{{width:{n:.4f}em}}')
        elif c.startswith('ih'):
            drops.append(f'img.im.{c},svg.im.{c}{{height:{n:.4f}em}}')
        elif c.startswith('iv'):
            drops.append(f'img.im.{c},svg.im.{c}{{vertical-align:-{n:.4f}em}}')
    return '\n'.join(drops)

# ---------------------------------------------------------------- 公式 HTML

def inline_math_html(latex, mr, kindle=False):
    """行内公式：默认内联 SVG；kindle 模式走 PNG 外链（KF8 丢弃内联 SVG）。"""
    from .svginline import parse_svg, emit_use
    import os
    r = mr.render(latex, display=False)
    if not r:
        return f'<code>${esc(latex)}$</code>'
    fname, w, ht, dp = r
    if kindle:
        return _png_img(mr, fname, w, ht, dp, latex)
    va = -dp * PT2EM
    he = (ht + dp) * PT2EM
    MAXH = 1.35
    if he > MAXH:
        sc = MAXH / he
        w, he, va = w * sc, he * sc, va * sc
    W, H, V = w * PT2EM, he, va
    cw, ch, cv = bucket_class(W, H, V)
    mr.buckets.update((cw, ch, cv))
    svg = open(os.path.join(mr.outdir, fname), encoding='utf-8').read()
    vb, uses, glyphs = parse_svg(svg)
    gid = {g: mr.glyphs.register(d) for g, d in glyphs.items()}
    return emit_use(vb, uses, gid, f'im {cw} {ch} {cv}',
                    f'width:{W:.4f}em;height:{H:.4f}em;vertical-align:{V:.4f}em',
                    esc(latex[:100]))

def svg_to_png(svg_path, png_path, dpi=None):
    """SVG → PNG。dpi 默认 300，可用 MWDPI 环境变量覆盖（KFX 尺寸测试）。"""
    import os as _os
    if dpi is None:
        dpi = int(_os.environ.get('MWDPI', '300'))
    import subprocess
    r = subprocess.run(['rsvg-convert', '-d', str(dpi), '-p', str(dpi),
                        '-o', png_path, svg_path],
                       capture_output=True, timeout=60)
    return r.returncode == 0 and __import__('os').path.exists(png_path)


def _png_img(mr, fname, w, ht, dp, latex):
    import os
    base = os.path.splitext(fname)[0] + '.png'
    png = os.path.join(mr.outdir, base)
    if not os.path.exists(png):
        svg_to_png(os.path.join(mr.outdir, fname), png)
    mr.pngs.add(base)
    va = -dp * PT2EM
    he = (ht + dp) * PT2EM
    if he > 1.35:
        sc = 1.35 / he
        w, he, va = w * sc, he * sc, va * sc
    W, H, V = w * PT2EM, he, va
    cw, ch, _ = bucket_class(W, H, V)
    mr.buckets.update((cw, ch, 'ivmid'))
    # Kindle KF8 对负 vertical-align 处理有 bug（图被推出可视区变空白），
    # 改用 middle 中线对齐：精度略降但保证可见
    return (f'<img class="im {cw} {ch} ivmid" src="math/{base}" '
            f'style="width:{W:.4f}em;height:{H:.4f}em;vertical-align:middle" '
            f'alt="{esc(latex[:100])}"/>')


def display_math_html(latex, mr, kindle=False):
    """显示公式：默认居中内联 SVG；kindle 模式走 PNG 外链。"""
    from .svginline import parse_svg, emit_use
    import os
    r = mr.render(latex, display=True)
    if not r:
        return f'<pre class="term"><code>$${esc(latex)}$$</code></pre>\n'
    fname, w, ht, dp = r
    if kindle:
        import os as _os
        base = _os.path.splitext(fname)[0] + '.png'
        png = _os.path.join(mr.outdir, base)
        if not _os.path.exists(png):
            svg_to_png(_os.path.join(mr.outdir, fname), png)
        mr.pngs.add(base)
        W = min(w * PT2EM, 92.0)
        cw, _, _ = bucket_class(W, 1.0, 0.0)
        mr.buckets.add(cw)
        return (f'<div class="dm"><img class="{cw}" src="math/{base}" '
                f'style="width:{W:.4f}em" alt="{esc(latex[:100])}"/></div>\n')
    W = min(w * PT2EM, 92.0)
    cw, _, _ = bucket_class(W, 1.0, 0.0)
    mr.buckets.add(cw)
    svg = open(os.path.join(mr.outdir, fname), encoding='utf-8').read()
    vb, uses, glyphs = parse_svg(svg)
    gid = {g: mr.glyphs.register(d) for g, d in glyphs.items()}
    return (f'<div class="dm">' +
            emit_use(vb, uses, gid, cw,
                     f'width:{W:.4f}em', esc(latex[:100])) + '</div>\n')


# ---------------------------------------------------------------- Renderer

class Renderer(mistune.HTMLRenderer):
    """mistune 渲染器：公式 → SVG，代码 → 高亮/等宽，表格/图片直通。"""

    def __init__(self, mr, style='friendly', kindle=False):
        super().__init__(escape=False)
        self.mr = mr
        self.kindle = kindle
        self.formatter = HtmlFormatter(style=style, nowrap=False)

    def inline_math(self, text):
        return inline_math_html(text, self.mr, self.kindle)

    def block_math(self, text):
        return display_math_html(text, self.mr, self.kindle)

    def block_code(self, code, info=None):
        lang = (info or '').strip().split()[0] if info else ''
        if not lang:
            lexer = self._guess(code)
            if lexer is None:
                return self._pre(f'<pre class="term"><code>{esc(code)}</code></pre>\n')
            return self._pre(f'<div class="hl">{highlight(code, lexer, self.formatter)}</div>\n')
        if lang.lower() in PLAIN_LANGS:
            return self._pre(f'<pre class="term"><code>{esc(code)}</code></pre>\n')
        try:
            lexer = get_lexer_by_name(lang)
        except Exception:
            return self._pre(f'<pre class="term"><code>{esc(code)}</code></pre>\n')
        return self._pre(f'<div class="hl">{highlight(code, lexer, self.formatter)}</div>\n')

    def _pre(self, html):
        return kfx_pre(html) if self.kindle else html

    @staticmethod
    def _guess(code):
        """无语言标注时猜测；太短或猜成纯文本则返回 None（走等宽框）。"""
        try:
            from pygments.lexers import guess_lexer
            if len(code.strip()) < 20:
                return None
            lexer = guess_lexer(code)
            return None if lexer.name in ('Text only',) else lexer
        except Exception:
            return None

    def codespan(self, text):
        return f'<code>{esc(text)}</code>'

    def image(self, text='', url='', title=None, **kw):
        """图片嵌入 EPUB 包（压缩 + 重命名），规避中文/相对路径问题。"""
        return self.mr.emit_image(url, text or '')

    def table_head(self, text):
        return f'<thead><tr>{text}</tr></thead>\n'

    def table_body(self, text):
        return f'<tbody>{text}</tbody>\n'

    def table_row(self, text):
        return f'<tr>{text}</tr>\n'

    def table_cell(self, text, align=None, head=False):
        tag = 'th' if head else 'td'
        a = f' style="text-align:{align}"' if align else ''
        return f'<{tag}{a}>{text}</{tag}>'

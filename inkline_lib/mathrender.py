"""LaTeX → SVG 渲染 + 图片打包（WebP 压缩）。

关键点：用 TeX 的 \\sbox 取得 (width, height, depth) 真实度量，
depth 决定行内公式的 CSS vertical-align —— 这是精确基线对齐的依据。
详见 PRINCIPLE.md。
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

PT2EM = 1 / 12.0        # 12pt 基准：TeX pt → CSS em

TEX_DOC = r'''\documentclass[12pt]{standalone}
\usepackage{amsmath,amssymb,bm}
\begin{document}
%s
\end{document}
'''


class MathRenderer:
    """LaTeX → SVG，附带 (width, height, depth) 度量，带磁盘缓存。

    Parameters
    ----------
    outdir : 输出目录（SVG 落 here）
    jobs : 并行渲染线程数
    cache_dir : 度量/SVG 缓存目录（跨次构建复用）；默认同 outdir
    img_max_px : 图片最长边上限，超出等比缩小
    img_quality : WebP 质量
    """

    def __init__(self, outdir, jobs=8, cache_dir=None,
                 img_max_px=1400, img_quality=82):
        self.outdir = outdir
        self.cache = cache_dir or outdir
        self.jobs = jobs
        self.img_max_px = img_max_px
        self.img_quality = img_quality
        os.makedirs(self.outdir, exist_ok=True)
        os.makedirs(self.cache, exist_ok=True)
        self._results = {}
        self.buckets = set()
        self.pngs = set()  # kindle 模式的 PNG 文件名        # 张量桶 class 集合（供生成 CSS）
        from .svginline import GlyphRegistry
        self.glyphs = GlyphRegistry()  # 全局字形表（内联 SVG 去重）
        self.base_dir = None   # 源 md 目录（解析相对图片路径）
        self.images = {}       # 源路径 → 包内文件名
        self.imgdir = os.path.join(outdir, 'pic')
        os.makedirs(self.imgdir, exist_ok=True)

    @staticmethod
    def _key(latex, display):
        return hashlib.md5((('D' if display else 'I') + latex).encode()).hexdigest()[:16]

    def render(self, latex, display=False):
        """→ (svg_filename, width_pt, height_pt, depth_pt) | None"""
        k = self._key(latex, display)
        if k in self._results:
            return self._results[k]
        name = f'm{k}.svg'
        cached = os.path.join(self.cache, name)
        met = os.path.join(self.cache, f'm{k}.met')
        if os.path.exists(cached) and os.path.exists(met):
            w, ht, dp = (float(x) for x in open(met).read().split(':'))
            # 缓存命中也要把 SVG 放进本轮 outdir（打包只扫 outdir）
            live = os.path.join(self.outdir, name)
            if not os.path.exists(live):
                shutil.copy(cached, live)
            self._results[k] = (name, w, ht, dp)
            return self._results[k]
        self._results[k] = self._compile(latex, display, cached, met)
        return self._results[k]
    def _compile(self, latex, display, svg, met):
        body = (f'$\\displaystyle {latex.strip()}$' if display
                else f'${latex.strip()}$')
        tmp = tempfile.mkdtemp()
        try:
            tex = os.path.join(tmp, 'a.tex')
            open(tex, 'w', encoding='utf-8').write(TEX_DOC % (
                f'\\sbox0{{{body}}}%\n'
                f'\\typeout{{MD2K:\\the\\wd0:\\the\\ht0:\\the\\dp0}}%\n'
                f'\\usebox0'))
            r = subprocess.run(
                ['latex', '-interaction=nonstopmode', '-halt-on-error',
                 '-output-directory', tmp, tex],
                capture_output=True, timeout=60)
            if r.returncode != 0:
                return None
            log = open(os.path.join(tmp, 'a.log'),
                       encoding='utf-8', errors='ignore').read()
            m = re.search(r'MD2K:([\d.]+)pt:([\d.]+)pt:([\d.]+)pt', log)
            if not m:
                return None
            w, ht, dp = (float(x) for x in m.groups())
            out = os.path.join(self.outdir, os.path.basename(svg))
            r2 = subprocess.run(
                ['dvisvgm', '--no-fonts', '--exact', '--bbox=min',
                 '-o', out, os.path.join(tmp, 'a.dvi')],
                capture_output=True, timeout=60)
            if r2.returncode != 0 or not os.path.exists(out):
                return None
            if self.cache != self.outdir:
                shutil.copy(out, svg)
            open(met, 'w').write(f'{w}:{ht}:{dp}')
            return (os.path.basename(svg), w, ht, dp)
        except Exception:
            return None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def render_all(self, items):
        """items: [(latex, is_display)] → 并行预渲染（自动去重）。"""
        tasks = list(dict.fromkeys(items))
        with ThreadPoolExecutor(max_workers=self.jobs) as ex:
            list(ex.map(lambda t: self.render(t[0], t[1]), tasks))

    def ok_count(self):
        return sum(1 for v in self._results.values() if v)

    # ---------------------------------------------------------- 图片打包

    def emit_image(self, src, alt=''):
        """把图片压缩进包，返回 <img> 标签。"""
        p = src
        if self.base_dir and not os.path.isabs(p):
            cand = os.path.normpath(os.path.join(self.base_dir, p))
            if os.path.exists(cand):
                p = cand
        if not os.path.exists(p):
            return ''                       # 图缺失静默跳过，不留破图
        if p in self.images:
            name = self.images[p]
        else:
            ok, name = self._pack_image(p)
            self.images[p] = name
        a = f' alt="{alt}"' if alt else ' alt=""'
        return f'<img class="pic" src="pic/{name}"{a}/>'

    def _pack_image(self, src):
        """转 WebP（失败则原样保留真实扩展名），返回 (ok, 包内文件名)。"""
        idx = len(self.images)
        try:
            from PIL import Image
            im = Image.open(src)
            if im.mode in ('RGBA', 'LA', 'P'):
                im = im.convert('RGBA').convert('RGB')
            w, h = im.size
            if max(w, h) > self.img_max_px:
                r = self.img_max_px / max(w, h)
                im = im.resize((max(1, int(w * r)), max(1, int(h * r))),
                               Image.LANCZOS)
            name = f'img{idx:04d}.webp'
            im.save(os.path.join(self.imgdir, name), 'WEBP',
                    quality=self.img_quality, method=6)
            return True, name
        except Exception:
            ext = os.path.splitext(src)[1].lower() or '.png'
            name = f'img{idx:04d}{ext}'
            shutil.copy(src, os.path.join(self.imgdir, name))
            return False, name

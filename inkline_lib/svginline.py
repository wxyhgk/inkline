"""SVG 内联发射：glyph 级共享 defs + id 命名空间。

背景：dvisvgm 每个 SVG 自带全套字形 defs（占85%体积），且 id
全局重名（g0-0 等）。直接内联会导致体积爆炸5.3x + 静默错字形。

方案（经评审确认唯一可行）：
  - 全局 glyph 表：按 path 的 d 串去重（518 unique，冗余度95%）
  - 每个公式只发射 <svg viewBox><use href="#gN"/></svg> 桩（约150B/处）
  - 文档头部放一个隐藏 <svg><defs> 存全量 glyph
  - id 命名空间化，防止跨公式碰撞
"""
import re

NS_SVG = 'http://www.w3.org/2000/svg'
NS_XLINK = 'http://www.w3.org/1999/xlink'

_re_path = re.compile(r"<path\s+id='([^']+)'\s+d='([^']+)'")
_re_path2 = re.compile(r'<path\s+id="([^"]+)"\s+d="([^"]+)"')
_re_use = re.compile(r"<use\s+x='([^']+)'\s+y='([^']+)'\s+xlink:href='#([^']+)'")
_re_use2 = re.compile(r'<use\s+x="([^"]+)"\s+y="([^"]+)"\s+xlink:href="#([^"]+)"')
_re_viewbox = re.compile(r"viewBox='([^']+)'")
_re_viewbox2 = re.compile(r'viewBox="([^"]+)"')


def parse_svg(svg_text):
    """解析 dvisvgm SVG → (viewBox, [(x, y, glyph_id)], {glyph_id: d})。

    只认 <defs><path id d> + <use x y xlink:href> 结构，
    其他元素（渐变/clip/注释/prolog）全部丢弃。
    """
    vb = _re_viewbox.search(svg_text) or _re_viewbox2.search(svg_text)
    viewbox = vb.group(1) if vb else '0 0 100 100'
    glyphs = {}
    for pat in (_re_path, _re_path2):
        for m in pat.finditer(svg_text):
            glyphs[m.group(1)] = m.group(2)
    uses = []
    for pat in (_re_use, _re_use2):
        for m in pat.finditer(svg_text):
            uses.append((m.group(1), m.group(2), m.group(3)))
    return viewbox, uses, glyphs


class GlyphRegistry:
    """全局字形表：d 串去重，分配 g0/g1/... 稳定 id。"""
    def __init__(self):
        self._d2id = {}
        self._order = []

    def register(self, d):
        """返回全局 glyph id，已存在则复用。"""
        gid = self._d2id.get(d)
        if gid is None:
            gid = f'g{len(self._order)}'
            self._d2id[d] = gid
            self._order.append(d)
        return gid
    def defs_block(self):
        """隐藏 defs 块：<svg style="display:none"><defs>..."""
        parts = ['<svg xmlns="{}" xmlns:xlink="{}" style="display:none" '
                 'aria-hidden="true"><defs>'.format(NS_SVG, NS_XLINK)]
        for i, d in enumerate(self._order):
            parts.append(f"<path id='g{i}' d='{d}'/>")
        parts.append('</defs></svg>')
        return ''.join(parts)

    def __len__(self):
        return len(self._order)


def emit_use(viewbox, uses, gid_map, cls, style, title):
    """发射一个公式引用桩。

    viewBox 保留（等比缩放依据），width/height 丢弃（用 em，由调用方给）。
    href 与 xlink:href 双写：旧 Kindle 只认 xlink，SVG2 阅读器认 href。
    <title> 满足无障碍（替代原 img alt）。
    """
    parts = [f'<svg class="{cls}" style="{style}" viewBox="{viewbox}" '
             f'xmlns="{NS_SVG}" xmlns:xlink="{NS_XLINK}" '
             f'role="img" aria-label="{title}">']
    if title:
        parts.append(f'<title>{title}</title>')
    for x, y, old_id in uses:
        gid = gid_map.get(old_id, old_id)
        parts.append(f'<use x="{x}" y="{y}" xlink:href="#{gid}" href="#{gid}"/>')
    parts.append('</svg>')
    return ''.join(parts)

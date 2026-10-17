"""EPUB3 打包。

Apple Books 比 Kindle 严格，以下缺一不可：
  - nav.xhtml（EPUB3 强制导航文档，properties="nav"）
  - 所有资源都要在 manifest 登记（漏登记整包被拒）
  - dc:title / dc:identifier / dcterms:modified
  - mimetype 必须首项、STORED 无压缩
"""
import glob
import os
import uuid
import zipfile

from .util import esc

# 扩展名 → media-type
MEDIA_TYPES = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'webp': 'image/webp', 'svg': 'image/svg+xml',
}


def _media_type(path):
    return MEDIA_TYPES.get(os.path.splitext(path)[1].lstrip('.').lower(),
                           'application/octet-stream')


def build_nav(nav_entries):
    """生成 nav.xhtml（TOC）。nav_entries: [(anchor_id, title)]"""
    lis = []
    for aid, title in nav_entries:
        lis.append(f'<li><a href="content.xhtml#{aid}">{esc(title)}</a></li>')
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" lang="zh" xml:lang="zh">\n'
            '<head><meta charset="utf-8"/><title>目录</title></head>\n'
            '<body><nav epub:type="toc" id="toc"><h1>目录</h1>\n'
            f'<ol>{"".join(lis)}</ol></nav></body></html>')


def build_opf(opf_uuid, title, author, svgs, pics, pngs=None):
    """生成 content.opf（manifest 必须登记每个资源）。"""
    items = [
        '<item id="c" href="content.xhtml" media-type="application/xhtml+xml" properties="svg"/>',
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
        'properties="nav"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
    ]
    for i, p in enumerate(pics):
        items.append(f'<item id="p{i}" href="pic/{os.path.basename(p)}" '
                     f'media-type="{_media_type(p)}"/>')
    for i, g in enumerate(pngs or []):
        items.append(f'<item id="g{i}" href="math/{os.path.basename(g)}" '
                     f'media-type="image/png"/>')

    creator_meta = ('\n<meta refines="#creator" property="role" '
                    'scheme="marc:relators">aut</meta>') if author else ''
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
            'unique-identifier="id" xml:lang="zh">\n'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f'<dc:identifier id="id">urn:uuid:{opf_uuid}</dc:identifier>\n'
            f'<dc:title>{esc(title)}</dc:title>\n'
            '<dc:language>zh</dc:language>\n'
            f'<dc:creator id="creator">{esc(author or "Anonymous")}</dc:creator>'
            f'{creator_meta}\n'
            '<meta property="dcterms:modified">2026-01-01T00:00:00Z</meta>\n'
            '</metadata>\n'
            '<manifest>\n' + '\n'.join(items) + '\n</manifest>\n'
           '<spine><itemref idref="c"/></spine>\n'
            '</package>')


CONTAINER_XML = ('<?xml version="1.0" encoding="utf-8"?>'
                 '<container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/>'
                 '</rootfiles></container>')


def write_epub(out, html, css, mathdir, picdir, nav_entries, title, author, inline=True):
    """写出 EPUB3 压缩包。"""
    svgs = sorted(glob.glob(os.path.join(mathdir, '*.svg')))
    pics = sorted(glob.glob(os.path.join(picdir, '*'))) if picdir else []
    nav = build_nav(nav_entries)
    opf = build_opf(str(uuid.uuid4()), title, author, svgs, pics)

    with zipfile.ZipFile(out, 'w') as z:
        zi = zipfile.ZipInfo('mimetype')          # 必须首项 + STORED
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, 'application/epub+zip')
        z.writestr('META-INF/container.xml', CONTAINER_XML, zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/content.xhtml', html, zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/nav.xhtml', nav, zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/style.css', css, zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/content.opf', opf, zipfile.ZIP_DEFLATED)
        for p in pics:
            z.write(p, f'OEBPS/pic/{os.path.basename(p)}')
        for g in sorted(glob.glob(os.path.join(mathdir, '*.png'))):
            z.write(g, f'OEBPS/math/{os.path.basename(g)}')

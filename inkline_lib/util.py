"""杂项工具：转义、版本号、源文件发现、文本预处理。"""
import glob
import os
import re


def esc(s):
    """HTML 转义。"""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))


def next_version(out):
    """输出文件已存在则递增版本号，绝不覆盖。

    book.epub -> book-v1.epub -> book-v2.epub ...
    已是 book-vN.epub 则从 N+1 续。
    """
    if not os.path.exists(out):
        return out
    base, ext = os.path.splitext(out)
    m = re.match(r'^(.*)-v(\d+)$', base)
    if m:
        base, start = m.group(1), int(m.group(2)) + 1
    else:
        start = 1
    n = start
    while os.path.exists(f'{base}-v{n}{ext}'):
        n += 1
    return f'{base}-v{n}{ext}'


def read_sources(src, recursive=False):
    """返回待处理的 .md 文件列表。"""
    if os.path.isfile(src):
        return [src]
    pat = '**/*.md' if recursive else '*.md'
    return sorted(glob.glob(os.path.join(src, pat), recursive=recursive))


def anchor(path):
    """源文件路径 → 稳定的章节锚点 id（用于 nav 与跨章跳转）。"""
    stem = os.path.splitext(os.path.basename(path))[0]
    return 'sec-' + re.sub(r'[^A-Za-z0-9]+', '-', stem).strip('-').lower()


def clean_source(text):
    """源 Markdown 预处理：去 front matter、转义会被误判为标签/链接的字符。

    修正的都是转换链路的坑，不改正文语义：
      - @<TRIPOS>CRYSIN 之类的字面尖括号 → 转义（否则 EPUB 解析失败）
      - OCR 残渣 )]( → 转义（否则被当成链接）
    """
    t = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S)   # YAML front matter
    t = re.sub(r'@<([A-Z][A-Z0-9]*)>', r'@&lt;\1&gt;', t)
    t = re.sub(r'(?<![a-zA-Z0-9])<([a-z]\d+)>', r'&lt;\1&gt;', t)
    t = re.sub(r'\]\((?!https?://|mailto:|#|\./|/|imgs/'
               r'|[^()\s]*\.(?:png|jpg|jpeg|gif|svg|webp))', ']\\(', t)
    return t


def rewrite_md_links(text, all_files):
    """把 ./xxx.md 链接改写为同文档锚点，使合并后的单文档内部可跳转。

    含嵌套方括号的标签（如 [(超)极化率分析[..]]）也要支持。
    """
    def rep(m):
        label, target = m.group(1), m.group(2)
        base = target.split('#')[0].lstrip('./')
        if not base.endswith('.md'):
            return m.group(0)
        for f in all_files:
            if os.path.basename(f) == base:
                return f'[{label}](#{anchor(f)})'
        return label
    return re.sub(r'\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(([^)\s]*\.md(?:#[^)]*)?)\)',
                  rep, text)


def extract_formulas(text):
    """返回 [(latex, is_display)]，display 前置优先。"""
    out = []
    for m in re.finditer(r'\$\$(.+?)\$\$', text, re.S):
        out.append((m.group(1).strip(), True))
    masked = re.sub(r'\$\$.+?\$\$', lambda m: '\x00' * len(m.group(0)),
                    text, flags=re.S)
    for m in re.finditer(r'\$([^$\n]{1,400})\$', masked):
        out.append((m.group(1).strip(), False))
    return out

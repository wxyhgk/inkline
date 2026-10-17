# inkline

Markdown → Kindle（EPUB3 / KFX），行内公式精确对齐。

## 效果

<img src="docs/imgs/scribe.png" width="400" alt="Kindle Scribe 真机：行内公式齐平、显示公式居中"/>

<img src="docs/imgs/layout.png" width="600" alt="桌面端渲染：行内不断行、超宽等比、表格"/>

数学公式进 Kindle 有三道坎：

1. KF8 丢弃内联 SVG，行内公式变空白
2. 通用转换器（Calibre）丢图片引用，小图撑破行
3. KFX 行内图默认块级渲染，每个公式独占一行

inkline 全解了：公式预渲染高清 PNG（白底），直出 KFX，并把行内图改写成 Kindle 原生行内结构（逆向 Send-to-Kindle 官方格式得出）。

## 安装

```bash
pip install -r requirements.txt   # mistune pygments Pillow
cargo install boko                # EPUB → KFX（需 Rust）
```

## 用法

```bash
# EPUB（通用阅读器）
python3 inkline.py input.md -o book.epub --title "书名" --kindle

# KFX（Kindle 直传，行内公式不断行）
python3 inkline.py input.md --title "书名" --kfx book.kfx

# 整本手册
python3 build_kfx.py -o 手册.kfx   # 在 Multiwfn_office 下
```

整目录：`python3 inkline.py docs/ --title T --kfx book.kfx -r`

## 链路

```
md → EPUB（kindle 模式：公式 PNG 外链 + 白底 + 代码块 br/nbsp）
   → boko convert（EPUB → KFX 原生 Ion）
   → kfx_patch（行内修复，见下）
```

## kfx_patch 原理（逆向官方 KFX）

对照 Send-to-Kindle 下发的官方 KFX，boko 生成的差三处，patch 全补：

| | 官方 | boko 原 | patch 后 |
|---|---|---|---|
| 嵌套 | image 在 text 的 content_list 内 | 同级 sibling（块） | 内嵌 |
| 标记 | `render: inline` | 无 | 加 |
| 样式 | `width/height(em)+baseline_shift` | 空（yj.vertical_align Kindle 不认） | 按每图 em 重写 |

基线公式：`bs = -(h/2 - 0.25) + 0.2`（Scribe 真机调定，0.2 为经验偏移）。

只改 storyline/style entity 内容，不增删 entity（新增 entity 会导致 Kindle 拒开）。

## 结构

```
inkline_lib/
  pipeline.py    构建主流程
  htmlrender.py  公式/代码块 HTML（含 kindle 适配）
  mathrender.py  公式预渲染（SVG→PNG 300dpi）
  epub.py        EPUB 打包
  kfx_build.py   EPUB→KFX 一键（白底+boko+patch）
  kfx_patch.py   KFX 行内修复
  kfx_ion.py     最小 Ion 编解码
  kfx_symbols.py YJ 符号表（852）
```

## 手写

USB 侧载的 KFX 在 Scribe 上可手写（真机验证）。

## 局限

- 超宽行内公式（>30em）按 max-width 等比缩小，可能偏小。

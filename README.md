# inkline

手里有一份带公式的中文手册（比如量子化学软件说明书），想放到 Kindle Scribe 上看，顺手拿笔批注。就这么个简单的想法，折腾了整整一周。

先试了官方推荐的路：把文件发到 Send to Kindle，云端转好再下发。慢，一本几百页的手册传上去等半天；而且每次改完都要重走一遍。等不起。

那就 USB 直拷。拷进去一看：公式全是空白框。换个方式转：公式出来了，但每个都独占一行，好好的一段话被切得稀碎。修好了不断行，公式又大得撑破页面。再修好尺寸，公式和文字不在一条线上，忽上忽下。调齐了基线，代码又挤成一团。

整整五个坑，一个接一个。没有现成工具一次走通——转换软件丢图、排版引擎不认行内公式、电子书格式的对齐规则和网页完全两样。只能一层层剥开 Kindle 的文件格式，对着官方转出来的文件逐字节比对，把每个环节亲手修好。

现在：一行命令，手册进去，Kindle 电子书出来。公式和文字齐平，代码换行分明，拷进 Scribe 拿起笔就能写。

## 效果

<img src="docs/imgs/scribe.png" width="400" alt="Kindle Scribe 真机"/>

<img src="docs/imgs/layout.png" width="600" alt="桌面端渲染"/>

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

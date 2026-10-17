# inkline

手里有一份带公式的中文手册，想放到 Kindle Scribe 上看，顺手拿笔批注。多简单的事，对吧？妈的，折腾了整整一周。

一开始走的官方路：Send to Kindle。传上去，等，半天没动静。一本几百页的手册，转完下发跟挤牙膏似的。改个错别字？重新传，重新等。艹，等不起。

行，USB 直拷总行了吧。拷进去打开一看——公式全是空白框，一页页全空着。当时人都傻了。

查了一圈，换了个开源转换器。这回公式出来了，心里一喜。再一看：每个公式独占一行啊！好好的一段话，"电子密度[换行]公式[换行]是波函数的基础"，切得稀碎。这能看？

咬牙修。把行内结构对着官方文件逐字节啃，终于不断行了。结果公式巨大，一个顶五个字大，把页面撑得七零八落。又调尺寸，调完公式和文字不在一条线，忽上忽下跟波浪似的。

调齐基线那天，真机上三档来回传，以为稳了。翻到代码章节——全挤成一团了，一页的终端输出变成一行天书。转换器把代码里的换行全吃了。

五个坑，踩完一个下一个，踩得想砸电脑。但每踩完一个，离"拷进去就能看"近一步。

现在：一行命令，手册进去，Kindle 电子书出来。公式贴着文字走，代码行行分明，拷进 Scribe 拿起笔就能写。值了。

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

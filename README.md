# inkline

手里有一份带公式的中文手册，想放到 Kindle Scribe 上看，顺手拿笔批注。多简单的事，对吧？妈的，从 10 月 15 号那天开始，折腾了整整三天。

一开始走的官方路：Send to Kindle。传上去，等，半天没动静。一本几百页的手册，转完下发跟挤牙膏似的。后来发现改个错别字都得重新传、重新等。艹，这谁等得起。当天晚上就死心了——这条路再官方，也救不了急。

第二天一早，行，USB 直拷总行了吧。先拿 Calibre 转 AZW3，拷进去打开一看——公式全是空白框，一页页翻过去，29 张图只出来 1 张。后来才查明白，这是 Calibre 8 的 KF8 writer 有 bug，图片引用全丢了，小文件连正文都保不住。那一刻坐在电脑前面，人都傻了，半天没说出话。Calibre，弃。

不信邪，当天夜里换了个 Rust 写的开源工具 boko，直接写 KFX。这回公式全出来了，29/29，心里一喜，赶紧往下翻。然后笑容就凝固了：每个公式独占一行啊！好好的一段话，"电子密度[换行]公式[换行]是波函数的基础"，切得稀碎。这他妈能看？boko 把所有图片都当成了块，跟行内两个字。

没办法，咬牙修。翻出之前 Send to Kindle 下发的一个官方文件——亚马逊自家转的，行内好好的——跟 boko 生成的逐字节比对。啃到凌晨两点，定位到三处差异：官方把图嵌在文字流里面，还带个行内标记，尺寸和基线都写在样式里；而 boko 全没写，代码里符号倒是有，就是没用上。当晚写出第一版补丁，不断行了。长出一口气，往 Scribe 上一传——公式巨大，一个顶五个字大，页面撑得七零八落。刚下去的火腾一下又上来了，那晚没睡好。

第三天，调尺寸。Kindle 按图片像素显示，没有网页那套缩放，300dpi 的高清图直接显示成 5.7 倍。只能把每张图的尺寸反推进样式里，一张一张对。调完一看，公式和文字不在一条线上，忽上忽下，整页跟波浪似的。得，继续调基线，真机上三档来回传，传一次等一次，传到第五遍的时候终于齐了。那天晚上多吃了一碗饭。

以为稳了，往后翻到代码章节，当场又凉了：一页的终端输出挤成了一行天书。boko 把代码里的换行全吃了。坐在那儿愣了半天，差点把杯子捏碎。回头在源头把换行写死，背景去掉，才算过去。

连着三个晚上，五个坑，踩完一个来下一个。好几次想砸电脑，想着"算了别搞了"，但都走到这儿了，差这一步，咬咬牙又坐回去了。中间还翻了 KOReader（要越狱，太野）、DeDRM 那套（只管脱壳不管生成）、亚马逊官方的 Ion 库（解不开 Kindle 的私有符号表，只能手写解码）——全是参考书，没有一个开箱即用。底座是 boko，缺的肉全是自己长的。

17 号晚上，一行命令跑通，手册进去，Kindle 电子书出来。公式贴着文字走，代码行行分明，拷进 Scribe 拿起笔就能写。回头看这三天，值了。



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

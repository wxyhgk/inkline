# inkline

手里有一份带公式的中文手册，想放到 Kindle Scribe 上看，顺手拿笔批注。多简单的事，对吧？妈的，折腾了整整一周。

一开始走的官方路：Send to Kindle。传上去，等，半天没动静。一本几百页的手册，转完下发跟挤牙膏似的。后来发现改个错别字都得重新传、重新等。艹，这谁等得起。死心了。

行，USB 直拷总行了吧，文件往里一拖，打开——公式全是空白框。一页页翻过去，全空着。那一刻坐在电脑前面，人都傻了，半天没说出话。

不信邪，查了一圈换了个开源转换器。这回公式出来了，心里一喜，赶紧往下翻。然后笑容就凝固了：每个公式独占一行啊！好好的一段话，"电子密度[换行]公式[换行]是波函数的基础"，切得稀碎。这他妈能看？

没办法，咬牙修。把官方转出来的文件和自己的逐字节比对，啃了两天，终于不断行了。长出一口气，往 Scribe 上一传——公式巨大，一个顶五个字大，页面撑得七零八落。刚下去的火腾一下又上来了。

调尺寸。调完一看，公式和文字不在一条线上，忽上忽下，整页跟波浪似的。得，继续调基线，真机上三档来回传，传一次等一次，传到第五遍的时候终于齐了。那天晚上多吃了一碗饭。

以为稳了，往后翻到代码章节，当场又凉了：一页的终端输出挤成了一行天书。转换器把代码里的换行全吃了。坐在那儿愣了半天，差点把杯子捏碎。

五个坑，踩完一个来下一个。好几次想砸电脑，想着"算了别搞了"，但都走到这儿了，差这一步，咬咬牙又坐回去了。

现在：一行命令，手册进去，Kindle 电子书出来。公式贴着文字走，代码行行分明，拷进 Scribe 拿起笔就能写。回头看那一周，值了。

## 效果

<img src="docs/imgs/scribe.png" width="400" alt="Kindle Scribe 真机"/>

<img src="docs/imgs/layout.png" width="600" alt="桌面端渲染"/>

## 踩过的开源项目

这一周几乎把 Kindle 生态的开源工具翻了个遍：

- **boko**（Rust，EPUB→KFX 原生写入）：唯一不依赖 Kindle Previewer 的开源 KFX 写入实现。成了我们的底座。但它行内图当块渲染、CSS 对齐全丢——我们写了 Ion 级后处理补上。
- **Calibre**（ebook-convert EPUB→AZW3）：第一版用的它。后来发现 8.x 的 KF8 writer 丢图片引用（29 张进包只引用 1 张），小文件连正文都丢。弃用，只留它做调试回转。
- **Kindle Previewer**（Amazon 官方）：转换质量标杆，我们逆向对标的对象。但它是黑盒 GUI，没法进自动化链路；而且它转的行内图一样要调。
- **KOReader**（越狱阅读器）：功能全，但要越狱 Scribe，丢官方同步。路子太野，没走。
- **DeDRM_tools / kfxlib（jhowell）**：只管脱壳和校验，不管生成。拿来读 KFX 结构当参考书。
- **amazon-ion**（Python）：官方 Ion 库，但解不了 KFX 的自定义符号表。只好照着 boko 的 ion.rs 手写了个最小编解码。

结论：没有一个开箱即用。boko 做骨架，缺的肉我们自己长——这就是 inkline。


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

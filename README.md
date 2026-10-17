# inkline

手里有一份带公式的中文手册，想放到 Kindle Scribe 上看，顺手拿笔批注。多简单的事，对吧？妈的，折腾了整整一周。

一开始走的官方路：Send to Kindle。传上去，等，半天没动静。一本几百页的手册，转完下发跟挤牙膏似的。后来发现改个错别字都得重新传、重新等。艹，这谁等得起。死心了。

行，USB 直拷总行了吧，文件往里一拖，打开——公式全是空白框。一页页翻过去，全空着。那一刻坐在电脑前面，人都傻了，半天没说出话。

不信邪，查了一圈换了个开源转换器。这回公式出来了，心里一喜，赶紧往下翻。然后笑容就凝固了：每个公式独占一行啊！好好的一段话，"电子密度[换行]公式[换行]是波函数的基础"，切得稀碎。这他妈能看？

没办法，咬牙修。把官方转出来的文件和自己的逐字节比对，啃了两天，终于不断行了。长出一口气，往 Scribe 上一传——公式巨大，一个顶五个字大，页面撑得七零八落。刚下去的火腾一下又上来了。

调尺寸。调完一看，公式和文字不在一条线上，忽上忽下，整页跟波浪似的。得，继续调基线，真机上三档来回传，传一次等一次，传到第五遍的时候终于齐了。那天晚上多吃了一碗饭。

以为稳了，往后翻到代码章节，当场又凉了：一页的终端输出挤成了一行天书。转换器把代码里的换行全吃了。坐在那儿愣了半天，差点把杯子捏碎。

五个坑，踩完一个来下一个。好几次想砸电脑，想着"算了别搞了"，但都走到这儿了，差这一步，咬咬牙又坐回去了。

## 时间线

- **Day 1（10-15）：空白框。** 试 Calibre 转 AZW3，发现丢图弃用；换 boko 直写 KFX，图全了但行内独占行。
- **Day 1 夜：逆向。** 拿 Send-to-Kindle 下发的官方 KFX 逐字节比对，定位三处差异（嵌套/render/样式），写出 kfx_patch 第一版，不断行了。
- **Day 2（10-16）：尺寸与基线。** 公式 5.7 倍大→按图反推 em；基线真机三档盲测，定下 +0.2；超宽去 height 等比；多尺寸按图分 style（新增 entity 拒开→改零新增）。
- **Day 2 夜：代码块。** pre 换行被吃→显式 br/nbsp；去背景。sec-3-21（329 图）全链跑通。
- **Day 3（10-17）：改名 inkline，写 README，建库推送。**

## 踩过的开源项目

（按踩的顺序）

- **Calibre**：第一个用的，KF8 writer 丢引用，弃。
- **boko**：底座，行内/对齐缺的肉自己长。
- **Kindle Previewer**：对标对象，黑盒进不了链路。
- **KOReader / DeDRM / kfxlib / amazon-ion**：路子野/只管一半/解不了，拿来当参考书。



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

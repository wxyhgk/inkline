# inkline 原理

Markdown → Kindle EPUB3，重点是**让行内公式和正文文字精确基线对齐**。

现有工具（pandoc、Kappan 等）在这一步都做得不好：公式要么浮高、要么下沉、要么大小错位。原因和我们的解法如下。

---

## 1. 问题：图片天然不会对齐

把公式渲染成图（PNG/SVG）插进 HTML，最容易踩的坑是 `<img>` 的默认对齐方式。

HTML 中 `<img>` 默认 `vertical-align: baseline`，含义是 **"图片的底边对齐文字的基线"**：

```
   文字文字   ┌──────┐
              │ 公式  │   ← 图整体浮在基线上方
   ───────────└──────┘──────────  ← 文字基线 = 图片底边
```

问题是：数学公式**真正的基线不在它的底边**。像 `ρ(r)` 里 `ρ` 的尾巴、分式 `a/b` 的分母、下标 `orb` 都伸到基线**以下**。

一个公式盒子有三个垂直度量（TeX 的术语）：

```
        ┌──────────┐  ← 盒子顶
        │          │
   ht   │   内容    │   ht = height，基线以上部分
（高）  │          │
        └──────────┘  ← ★ 公式基线
        │  ρ 的尾巴 │
   dp   │          │   dp = depth，基线以下部分
（深）  └──────────┘  ← 盒子底

   总高 = ht + dp
```

因为底边在基线下方 `dp` 处，一旦把**底边**贴到文字基线，公式的真实基线就被抬高了 `dp` —— 这就是"浮高"的来源。

---

## 2. 解法：用真实 depth 反推偏移

CSS 的 `vertical-align: <length>` 表示"把元素基线相对父级基线抬起多少"，负值即**降低**。所以只要：

```css
vertical-align: -dp;
```

把公式**底边下移 `dp`**，公式内部的真实基线就正好落在文字基线上：

```
        ┌──────┐
   文字  │ 公式  │ 文字      ← 公式基线与文字基线重合
   ─────┴──┬───┴─────────
           │ρ尾巴│  ← 尾巴自然垂到基线下方（正确）
           └─────┘
```

### 关键：`dp` 每个公式都不同

不能写死一个偏移量：

| 公式 | depth `dp` | `vertical-align` |
| --- | --- | --- |
| `ρ(r)` | 3.00 pt | −0.250 em |
| `E_orb` | 1.80 pt | −0.150 em |
| `a/b` | 4.14 pt | −0.345 em |

- 分式很深（分母下探）→ 需要明显下移
- 纯字母公式浅 → 只需微移

**对所有公式用同一个偏移（或 `middle`），必然是一部分浮高、一部分下沉。** 这就是现有工具的盲区。

---

## 3. 怎么拿到 `dp`：问 TeX 要

字形度量是 TeX 的看家本领，它算得绝对准。做法是把公式塞进 `\sbox`（一个"不排版只测量"的盒子），然后 `\typeout` 打印三个量：

```latex
\sbox0{$\rho(\mathbf{r})$}%
\typeout{MD2K:\the\wd0:\the\ht0:\the\dp0}%
\usebox0
```

输出：

```
MD2K:20.71306pt:9.0pt:3.0pt
      宽        高    深
```

代码从 `.log` 里正则取出来：

```python
m = re.search(r'MD2K:([\d.]+)pt:([\d.]+)pt:([\d.]+)pt', log)
w, ht, dp = map(float, m.groups())
```

对应实现：`MathRenderer._compile()`。

---

## 4. 尺寸也要换算：pt → em

TeX 的度量单位是 pt，但 EPUB 里要用相对单位 em，公式才能随正文字号缩放（用户在 Kindle 上调字号，公式得跟着变，不能大小错位）。

工具以 **12pt 基准**（`\documentclass[12pt]`）换算：

```python
PT2EM = 1 / 12.0

w_em  = w  * PT2EM          # 宽度
h_em  = (ht + dp) * PT2EM   # 总高
va_em = -dp * PT2EM         # 基线偏移
```

生成的 HTML：

```html
<img class="im" src="math/m3254faa8dde2f102.svg"
     style="width:1.7261em;height:1.0000em;vertical-align:-0.2500em"
     alt="\rho(\mathbf{r})"/>
```

对应实现：`inline_math_html()`。

---

## 5. 为什么要 SVG 而不是 PNG

| | PNG | SVG |
| --- | --- | --- |
| 缩放 | 放大糊 | 真矢量，无限清晰 |
| 体积 | 每个公式一张位图 | 字形转 `<path>` 轮廓，通常更小 |
| 显示一致性 | 依赖渲染时的 dpi | 任何设备一致 |

`dvisvgm --no-fonts` 把字形转成路径，**不依赖设备装了什么字体**，任何阅读器渲染出来都一样。Kindle 原生支持 SVG，不支持 MathML/KaTeX，所以 SVG 是唯一可靠方案。

---

## 6. 完整管线

```
Markdown
   │
   ├─ 扫描所有 $...$ / $$...$$ （去重）
   │
   ├─ 并行渲染（ThreadPoolExecutor）
   │     latex → dvi → dvisvgm → SVG
   │     同时从 .log 取 wd / ht / dp
   │     磁盘缓存（md5 命名，重复公式不重渲）
   │
   ├─ mistune 解析 Markdown → HTML
   │     行内公式 → <img style="vertical-align:-dp">
   │     显示公式 → <div class="dm"> 独立居中块
   │     代码块 → Pygments 高亮 / 终端等宽框
   │
   └─ 打包 EPUB3（mimetype / container.xml / content.opf / XHTML / CSS / SVG）
```

**显示公式的坑**：HTML 不允许块级元素嵌套在 `<p>` 内。若把 `<div>` 放进段落，阅读器解析时会拆错标签，公式退化成 LaTeX 源码文本。

解法：显示公式在 Markdown 预处理阶段换成带空行的占位符 → mistune 生成独立段落 → 渲染后把整个 `<p>占位符</p>` 替换为 `<div class="dm">`。

---

## 7. 验证结果

在渲染引擎（Chromium）里逐公式测量，30 个行内公式的基线偏差：

```
baseline offset: min = -5.02px, max = -5.00px, 差值 0.02px
              （-5px 是文字字降部的固定基线-底边差，非误差）
```

**亚像素级对齐**，即数学上精确对齐。

对照实验（同一公式三种 `vertical-align`）：`baseline` 浮高、`middle` 偏高或偏低、`-depth` 准确。
运行 `python3 inkline.py test_sample.md test.epub` 后打开 `test.epub` 第 1 节可自行比对。

---

## 8. 依赖

```bash
python3 -m pip install mistune pygments
# 系统：
#   macOS:  brew install --cask mactex   （或 BasicTeX）
#   Linux:  apt install texlive-latex-base texlive-latex-extra dvisvgm
```

`latex` 与 `dvisvgm` 是硬依赖（公式渲染），mistune/pygments 是纯 Python 依赖。

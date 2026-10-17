"""EPUB 样式表（Claude Design System 风格）。

表面色阶梯 / 陶土橙 / 发丝边框 / 精密圆角，取自逆向还原的 CDS token。
页面背景交给阅读器（不写死 body background），避免与深色模式冲突。
"""

CSS = """/* inkline — Claude Design System (CDS) 风格 */

:root {
  --surface-0:#f5f5f3; --surface-1:#fcfcfb; --surface-2:#ffffff;
  --clay:#d97757; --clay-light:#fbf3ef;
  --text-1:#151515; --text-2:#525252; --text-3:#8a8a8a;
  --alpha-1:hsla(0,0%,8%,.05); --alpha-2:hsla(0,0%,8%,.10);
  --border:hsla(0,0%,8%,.10);
  --code-bg:hsla(0,0%,8%,.035); --code-border:hsla(0,0%,8%,.12);
}
@media (prefers-color-scheme:dark) {
  :root {
    --surface-0:#0b0b0a; --surface-1:#151515; --surface-2:#1a1a19;
    --text-1:#e8e8e6; --text-2:#a8a8a6; --text-3:#7a7a78;
    --alpha-1:hsla(0,0%,100%,.05); --alpha-2:hsla(0,0%,100%,.09);
    --border:hsla(0,0%,100%,.09);
    --code-bg:hsla(0,0%,100%,.045); --code-border:hsla(0,0%,100%,.10);
  }
}

html,body {
  color:#151515;color:var(--text-1);
  font-family:"宋体",STSong,"Songti SC",SimSun,"Noto Serif CJK SC",Georgia,serif;
  line-height:1.8; margin:0; padding:1.1em 1em;
  text-align:justify; word-wrap:break-word;
  -webkit-font-smoothing:antialiased;
}

h1,h2,h3,h4 {
  font-family:"Anthropic Sans",-apple-system,"PingFang SC","Noto Sans CJK SC",sans-serif;
  line-height:1.35; color:#151515;color:var(--text-1);
  margin:1.4em 0 .6em; text-align:left;
}
h1 { font-size:1.45em; font-weight:600; margin-top:.4em }
h1::after {
  content:""; display:block; width:2.2em; height:3px;
  background:#d97757;background:var(--clay); border-radius:2px; margin-top:.5em;
}
h2 { font-size:1.2em; font-weight:600 }
h3 { font-size:1.06em; font-weight:600; color:#525252;color:var(--text-2) }

p { margin:.75em 0 }
a { color:#d97757;color:var(--clay); text-decoration:none }

/* 行内公式：基线由 vertical-align 精确控制 */
img { max-width:100%; height:auto }
svg.im { vertical-align:baseline; height:auto; fill:currentColor }
div.dm svg { fill:currentColor; max-width:96%; height:auto }



/* 显示公式：居中，无边框 */
div.dm {
  text-align:center; margin:1.3em 0;
}
div.dm img { max-width:96%; height:auto }

/* 终端输出块 */
pre.term {
  background:rgba(20,20,20,0.035);background:var(--code-bg);
  border:1px solid var(--code-border);
  border-radius:10px;
  padding:.75em .9em;
  font-family:"Anthropic Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.8em; line-height:1.6;
  overflow-x:auto; white-space:pre-wrap; word-break:break-all;
  color:#151515;color:var(--text-1); margin:.9em 0;
}
pre.term code { background:none; border:0; padding:0 }

/* 语法高亮块 */
.hl {
  background:rgba(20,20,20,0.035);background:var(--code-bg);
  border:1px solid var(--code-border);
  border-radius:10px;
  padding:.75em .9em; margin:.9em 0;
  font-size:.8em; overflow-x:auto;
}
.hl pre {
  margin:0; background:none; border:0; padding:0;
  font-family:"Anthropic Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  line-height:1.6;
}
.hl code { background:none; border:0; padding:0 }

/* 行内代码 */
code {
  font-family:"Anthropic Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  background:rgba(20,20,20,0.05);background:var(--alpha-1);
  border-radius:4px; padding:.08em .32em;
  font-size:.88em; color:#151515;color:var(--text-1);
}

/* 表格 */
table { border-collapse:collapse; margin:1.1em 0; font-size:.88em; width:100% }
th,td { border:1px solid var(--border); padding:.4em .65em; text-align:left }
th {
  background:rgba(20,20,20,0.05);background:var(--alpha-1);
  font-family:"Anthropic Sans",-apple-system,"PingFang SC",sans-serif;
  font-weight:600;
}

/* 引用块：陶土色左边线 */
blockquote {
  border-left:3px solid var(--clay);
  background:#fbf3ef;background:var(--clay-light);
  margin:1em 0; padding:.6em 1em;
  border-radius:0 8px 8px 0;
  color:#525252;color:var(--text-2);
}
@media (prefers-color-scheme:dark) {
  blockquote { background:rgba(20,20,20,0.05);background:var(--alpha-1) }
}

hr { border:0; border-top:1px solid var(--border); margin:1.6em 0 }

ul,ol { padding-left:1.4em; margin:.75em 0 }
li { margin:.3em 0 }

/* 图片：圆角 + 发丝边 */
p > img:only-child {
  display:block; margin:1em auto; border-radius:8px;
  border:1px solid var(--border);
}
"""

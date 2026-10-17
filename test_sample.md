# Multiwfn 手册 · 排版测试样张

本文用于检验 EPUB 排版效果，内容取自 Multiwfn 官方手册 2.6 节。

## 1 行内公式：基线对齐检验

行内公式是排版最难的部分。下面的段落密集穿插公式，用来检验**基线是否精确对齐**。

电子密度 $\rho(\mathbf{r})$ 是波函数分析的基础。它的梯度 $\nabla\rho(\mathbf{r})$ 的模长 $|\nabla\rho|$ 反映密度变化快慢；而拉普拉斯量 $\nabla^2\rho(\mathbf{r})$ 的符号，则指示局部电子是**富集**还是**耗散**。对任意实空间函数 $f(\mathbf{r})$，其积分 $\int f(\mathbf{r})\,\mathrm{d}\mathbf{r}$ 给出总贡献。

行内**分式** $\frac{1}{2}\rho(\mathbf{r})$ 与**上下标** $C_{\mu i}^{2}$、**希腊字母** $\alpha,\beta,\gamma,\varepsilon$ 应与其他文字等高。带**根号** $\sqrt{\rho}$ 和**求和** $\sum_{i}\eta_{i}\varphi_{i}$ 时，公式会自然超出文字高度，但主体仍应贴在基线上。

复杂一点：动能密度 $\tau(\mathbf{r})=\frac{1}{2}\sum_{i}\eta_{i}|\nabla\varphi_{i}(\mathbf{r})|^{2}$，以及信息熵 $P(x)=\rho(\mathbf{r})/N$。再看矩阵元 $F_{\mu\nu}$ 与 $\langle\phi_{\mu}|\hat{H}|\phi_{\nu}\rangle$ 的关系。

## 2 显示公式

电子密度的严格定义：

$$\rho(\mathbf{r})=\sum_{i}\eta_{i}\,|\varphi_{i}(\mathbf{r})|^{2}=\sum_{i}\eta_{i}\left|\sum_{\mu}C_{\mu i}\chi_{\mu}(\mathbf{r})\right|^{2}$$

梯度模长：

$$|\nabla\rho(\mathbf{r})|=\sqrt{\left(\frac{\partial\rho(\mathbf{r})}{\partial x}\right)^{2}+\left(\frac{\partial\rho(\mathbf{r})}{\partial y}\right)^{2}+\left(\frac{\partial\rho(\mathbf{r})}{\partial z}\right)^{2}}$$

拉普拉斯量：

$$\nabla^{2}\rho(\mathbf{r})=\frac{\partial^{2}\rho(\mathbf{r})}{\partial x^{2}}+\frac{\partial^{2}\rho(\mathbf{r})}{\partial y^{2}}+\frac{\partial^{2}\rho(\mathbf{r})}{\partial z^{2}}$$

## 3 终端输出（等宽块）

Multiwfn 的交互记录，应保留等宽与缩进：

```
Boot up Multiwfn and input below commands
examples\H2O.fch     // Load geometry
3                    // Plot real space function along a line
5                    // Spin density
1                    // Define line by two nuclei
1,6                  // Indices of the two atoms
-1                   // Replot
```

## 4 代码块（语法高亮）

```bash
#!/bin/bash
for f in *.fch; do
    base=$(basename "$f" .fch)
    echo "=== $base ==="
    multiwfn "$f" < input.txt > "${base}.out" 2>&1
done
```

```python
import numpy as np

def radial_density(rho, r):
    """Compute spherically averaged density."""
    return np.trapz(rho * r**2, r) * 4 * np.pi
```

## 5 表格

| 实空间函数 | 编号 | 单位 | 说明 |
| --- | --- | --- | --- |
| Electron density | 1 | a.u. | 电子密度 $\rho$ |
| Gradient norm | 2 | a.u. | 梯度模长 $\|\nabla\rho\|$ |
| Laplacian | 3 | a.u. | 拉普拉斯量 $\nabla^2\rho$ |
| ELF | 8 | — | 电子定域函数 |
| LOL | 9 | — | 定域化轨道指示函数 |

## 6 列表与引用

- 第一项：电子密度 $\rho(\mathbf{r})$
- 第二项：自旋密度 $\rho^{\alpha}-\rho^{\beta}$
- 第三项：动能密度 $\tau$，含分式 $\frac{1}{2}\sum_{i}\eta_{i}|\nabla\varphi_{i}|^{2}$

> **Usage** — 若 "laplfac" 在 `settings.ini` 中被设为其他值，则 $\nabla^2\rho$ 会乘以该值。

## 7 理论描述段（长段落混排）

The positive and negative values of this function correspond to electron density is locally depleted and locally concentrated, respectively. The relationships between $\nabla^2\rho$ and valence shell electron pair repulsion (VSEPR) model, chemical bond type, electron localization and chemical reactivity have been built by Bader and many other researchers.

Notice that in some other codes, such as AIMALL and AIM2000, Laplacian of electron density is defined as $-\frac{1}{4}\nabla^2\rho$, which differs from the value given by Multiwfn by a factor of $-1/4$. The $\nabla^2\rho$ outputted by Multiwfn is in atomic unit, which can be explicitly written as $1\ \mathrm{Bohr}^{-5}$ (corresponding to $24.09874\ \text{Å}^{-5}$, since $1\ \mathrm{Bohr}=0.529177\ \text{Å}$).

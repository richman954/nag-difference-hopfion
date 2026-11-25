# An energy-scale check that cancels an unknown energy offset

Chen et al. describe the hopfion as a local energy minimum and compute collapse and escape paths to a helical state at zero external field in a 105 nm FeGe plate. Compare the **initial-to-terminal drop** on each path. Any shared additive energy offset cancels. This tests the consistency of the proposed density units with the continuum model. The measured activation barrier is a different subtraction, saddle minus initial minimum. [Paper, Fig. 5 and Methods, Eqs. 3 and 8](https://juser.fz-juelich.de/record/1057547/files/s41567-026-03236-0.pdf) · [Barrier measurements](../data/processed/EXTRACTION_STATUS.md)

| Loss route | Density cells on Sheet1 | Drop assuming J/m³ | Drop assuming kJ/m³, expressed in J/m³ |
|---|---|---:|---:|
| Collapse | L2 − L37 | 1,141.44140625 | 1,141,441.40625 |
| Escape | S2 − S26 | 1,141.470703125 | 1,141,470.703125 |

Under the conditions below, the maximum allowed drop is approximately **169,316 J/m³**. The kJ/m³ interpretation exceeds it by a factor of **6.74** on each path. Reading the density column as J/m³ gives a drop within the bound for each path. The two paths share physical endpoint types, so this is one consistency check with two numerical realizations. Given the worksheet's volume formula, kJ/m³ corresponds to taking its printed pJ label literally, and J/m³ corresponds to a plotted number in fJ.

## Upper bound at the starting hopfion

Write $e$ for the sample-volume-averaged energy in the reference convention of the Hamiltonian. Suppose the initial state has $|m|=1$ everywhere, hence zero fourth component, and is locally stable in the full regularized model of Eq. 8. Its pointwise order parameter belongs to $S^3$. The variation

$$
\nu_t(r) = (\cos(t)\,m(r),\sin(t))
$$

preserves unit length and lateral periodicity. It must be permissible at every site, including both surfaces and the damaged layers. The fourth component is spatially constant. The exchange, DMI and zero-applied-field magnetic energies therefore scale as $\cos^2(t)$. In particular, the magnetostatic field is a linear response to the magnetization. After eliminating that field, the magnetostatic energy is quadratic, so it has the same scaling. The remaining fourth-component penalty contributes $\bar\kappa\sin^2(t)$ with $\bar\kappa$ the sample-average penalty.

$$
e(t)=e(0)\cos^2(t)+\bar\kappa\sin^2(t).
$$

Local stability requires $e''(0)=2(\bar\kappa-e(0))\ge0$. Thus $e_{\rm start}\le\bar\kappa$. Use the paper's approximate $\kappa=76.54$ J/m³ as the constant or upper bound in all layers. This step requires the starting configuration to admit fourth-component motion. The cited solver's historical default `MinimizeEndPoints = 0` holds endpoints fixed. The same revision can initialize the fourth component to a nonzero multiple of the first. The workbooks do not supply Chen's run settings or endpoint fields. A one-sided minimum on a discrete path, or convergence with a fixed endpoint, gives no test of the required transverse stability. [Solver endpoint options](https://github.com/kuchkin/mumax3-gneb/blob/b15ee29d1999a1bc63ee92d4f7e1884895f3bbb2/engine/gneb_minimizer.go#L40-L48) · [Initialization path](https://github.com/kuchkin/mumax3-gneb/blob/b15ee29d1999a1bc63ee92d4f7e1884895f3bbb2/engine/vpo_minimizer.go#L73-L85) · [Fourth-component assignment](https://github.com/kuchkin/mumax3-gneb/blob/b15ee29d1999a1bc63ee92d4f7e1884895f3bbb2/cuda/random.cu#L7-L16)

## Lower bound at the terminal state

Let $A$ denote the exchange stiffness and $D$ the bulk DMI coefficient. In each coordinate direction complete the square in the gradient of $m$. The identity $\sum_j |m\times e_j|^2=2|m|^2$ and the model's $|m|\le1$ imply

$$
A\sum_j|\partial_j m|^2 + D m\cdot(\nabla\times m)
\ge -\frac{D^2}{2A}|m|^2 \ge -\frac{D^2}{2A}.
$$

The extra fourth-component gradient and penalty in Eq. 8 are nonnegative. For the vector-potential convention in Eq. 3, extend the magnetization $M$ by zero outside the sample. With periodic lateral boundaries and decay in the free direction, the integrated squared gradient of the magnetic vector potential bounds its integrated squared curl. For $b=\nabla\times A_d$, completing a second square in $|b|^2/(2\mu_0)-M\cdot b$ gives a conservative magnetostatic density floor of $-\mu_0 M_s^2/2$ after integrating and dividing by sample volume. Use the same energy convention in this floor, the starting-state variation, and the workbook comparison. The conventional positive stray-field energy also satisfies this conservative floor and scales quadratically on the variation. Switching conventions along the variation can introduce a term proportional to the integral of $|M|^2$, which changes during the tilt and cannot be absorbed into a constant.

Use $A=4.75$ pJ/m, $D=0.853$ mJ/m² and $M_s=384$ kA/m as in the paper. Across any surface layers, assume $D(r)^2/(2A(r))$ and $M_s(r)^2$ are no larger than their bulk values, and that no additional energy terms invalidate the bounds. Combining the limits gives

$$
e_{\rm start}-e_{\rm end}
\le \bar\kappa + \frac{D^2}{2A}+\frac{\mu_0 M_s^2}{2}
\approx 76.54+76{,}590.42+92{,}649.34
=169{,}316.30\;\mathrm{J/m^3}.
$$

If the workbook stores $a e+c$ on a given path, its endpoint difference equals $a(e_{\rm start}-e_{\rm end})$. This removes the freedom to rescue a discrepant scale by choosing a shared offset $c$. The test still assumes a common linear scale and a common reference along each path. The exact endpoint fields, allowed surface variations, material distribution, discrete stencil and import transformation remain unverified. The physical barriers therefore retain their provisional status.

## Reproduce

From the repository root, run the following commands. The script calls the pinned publisher audit before reading any endpoint. Its JSON reports the original cells and SHA-256 digests, each conditional drop and the ratio to the bound.

```sh
python -m scripts.check_endpoint_scale
python -m pytest tests/test_endpoint_scale.py
```

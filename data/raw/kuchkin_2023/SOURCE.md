# Kuchkin et al. Figure 4B

The figure crop is adapted from V. M. Kuchkin, N. S. Kiselev, F. N. Rybakov, I. S. Lobanov, S. Blügel and V. M. Uzdin, “Heliknoton in a film of cubic chiral magnet,” *Frontiers in Physics* 11 (2023), Figure 4B. © 2023 the authors, distributed under CC BY 4.0. The only modifications are cropping panel B and lossless PNG encoding of the decoded RGB pixels. [Article and figure caption](https://doi.org/10.3389/fphy.2023.1201018) · [Publisher PDF](https://public-pages-files-2025.frontiersin.org/journals/physics/articles/10.3389/fphy.2023.1201018/pdf) · [License](https://creativecommons.org/licenses/by/4.0/)

| Asset | SHA-256 |
|---|---|
| Publisher PDF | `7a245489a9f8b89fb41ffe4f20a87381699175ffa9ca316104740de5912d9a02` |
| Original 1700 × 1467 JPEG, PDF page 6, image object 591 | `e2f27be3a9fba3c76ac7b69fb668d5976cd7c99a93d29a91c03df16cacc67b46` |
| Distributed `fig4b.png` | `cfb062e3bc730349dbd793f8c97d514bdc368b71e9d2669ec91dafdf578cd06f` |
| Decoded crop, 860 × 754 interleaved 8-bit RGB | `1817fe8333506f273ed6293c28a49a9a9c8f603f2f6b38c25e89f6bdb4576725` |

Extract object 591 from the publisher PDF, decode it to RGB and crop the box (840, 0, 1700, 754) in original pixel coordinates, with the right and bottom edges exclusive. For example, with a local `source.pdf`, PyMuPDF and Pillow:

```python
from io import BytesIO
import pymupdf
from PIL import Image

with pymupdf.open("source.pdf") as pdf:
    jpeg = pdf.extract_image(591)["image"]
with Image.open(BytesIO(jpeg)) as image:
    image.convert("RGB").crop((840, 0, 1700, 754)).save("fig4b.png")
```

## Readout at reduced temperature 0.8

From the repository root run `python scripts/check_kuchkin_rates.py` with Pillow installed. The main plot uses the blue and red dashed inverse transition rates and the black total lifetime. The upper-right inset supplies the inverse Arrhenius exponential for each route. Both temperature axes use units of J/kB, where J is the model exchange coupling. The authors give a zero-field domain of 5 × 5 × 2 spiral periods with 24 lattice sites per period for the transition-rate calculation. The stochastic runs described separately in §3.5 use 4 × 4 × 2 periods and 32 sites per period.

| Quantity | Readout | Pixel sensitivity |
|---|---:|---:|
| Escape/decay rate from the main plot | 0.446 | 0.415–0.479 |
| Escape/decay rate from the barrier exponential alone | 0.242 | 0.209–0.280 |
| Effective escape/decay prefactor ratio | 1.84 | 1.48–2.29 |

In a given plot the ratio of escape to decay rates equals the red inverse-rate reading divided by the blue one. Dividing the full main-panel ratio by the inset ratio gives the effective prefactor ratio at this temperature. The source does not separate any two-face multiplicity in these plotted rates. We use them as published. In reduced time units the two colored curves give 4,024 (inverse escape rate) and 1,795 (inverse decay rate). Summing their reciprocal rates gives a total lifetime of 1,241. The independent black trace reads 1,245, a difference of 0.09 vertical pixel.

The script fits the local centers of each trace over 27 columns around its 0.8 gridline to interpolate across the dashed gaps. The derivative of this fit accounts for a one-pixel horizontal reading error. Sensitivity extrema vary both curves’ vertical centers independently by one pixel and the two vertical-axis grid anchors by half a pixel each. These are graphical resolution ranges. They do not estimate uncertainty in the simulated Hamiltonian, rate model or dynamics.

These are model-derived curves in a separate material parameterization. They demonstrate how a prefactor changes the relative rate even when the ordering stays the same. They supply neither observed route counts nor a calibration of the Chen et al. energy scale.

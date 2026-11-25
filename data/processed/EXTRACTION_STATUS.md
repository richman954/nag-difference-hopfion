# Barrier extraction status

**Three numeric differences reproduced. Zero barriers promoted to validated pJ.** The two XLSX links in the publisher's source-data section return one byte-identical payload, 23,482 bytes per download. Both SHA-256 digests are `134949b49338512245559e0110a809cb29482978639227e4b5b10e594c88c7cc`. Distinct links document the two figure assignments. They represent one set of simulation curves. [Publisher](https://doi.org/10.1038/s41567-026-03236-0) · [Download receipt](../raw/nature_source_data/source_receipt.json)

| Directed path | Images | Sampled saddle minus initial minimum, Sheet1 | Difference on printed pJ scale | Conditional pJ if input density is J/m³ |
|---|---:|---|---:|---:|
| Skyrmion–antiskyrmion merger to hopfion | 29 | F7 − F2 | 0.00022388286621094 | 2.238828662109375 × 10⁻⁷ |
| Hopfion collapse | 36 | M13 − M2 | 0.00028564396875000 | 2.8564396875 × 10⁻⁷ |
| Hopfion escape through the free surface | 25 | T18 − T2 | 0.00073163708789062 | 7.31637087890625 × 10⁻⁷ |

The extractor checks the unique highest sampled interior image and its directed starting minimum on each trajectory. Image indices start at zero. The peaks are images 5, 11 and 16. An independent digitization of Extended Data Figure 9 found the same images and differences of about 0.0002224, 0.0002870 and 0.0007271 on the published scale, each within one vertical pixel of the workbook result. The exact cell values and ranges accompany each record. [Processed artifact](extracted_barriers.json) · [Plot check](../../scripts/check_fig9_plot.py)

The energy formulas multiply the density by the simulated volume (`Sheet1!A2`, 4.6305 × 10⁻²¹ m³) and divide by 10⁻¹⁵. Energy headers and figure axes say pJ. The density headers omit units. If the inputs are in J/m³, the formula gives a number in fJ. That interpretation gives physical pJ barriers 1,000 times smaller than a literal reading of the axes. At the precision of the seed table the plotted differences reproduce all three placeholders.

Historical solver code computes a binary32 image energy density and writes it unscaled. All 90 workbook densities are exactly representable in binary32. Only 1 of 90 matches simple division by 1,000 of a binary32 source followed by binary64 storage. Those checks favor the direct SI reading. The exact paper-specific build and preprocessing record are unknown. [Source-code fingerprint replay](../../scripts/check_solver_export.py) · [Historical writer](https://github.com/kuchkin/mumax3-gneb/blob/b15ee29d1999a1bc63ee92d4f7e1884895f3bbb2/engine/vpo_minimizer.go)

The ratios cancel the common scale. Collapse/merger is 1.27586, escape/merger is 3.26795 and **escape/collapse is 2.56136**. The last ratio directly compares the two routes out of a hopfion. These are discrete path-energy results. Relative event frequencies require observations or a separately specified rate model.

## Promotion criteria

A paper-specific simulation export with documented units and import steps, or an equivalent publisher or author clarification, must resolve the thousandfold discrepancy. Review the scale and provenance for all three paths together and replay the full test suite before enabling promotion. Until then, the artifact reports `physical_unit_unresolved`, and the active table retains the three provisional `raw_moesm_verification_pending` seeds.

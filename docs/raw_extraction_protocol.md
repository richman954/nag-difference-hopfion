# Reproducing the workbook audit

From the repository root, run the following commands.

```sh
python -m nagdiff.extraction
python -m nagdiff.chen2026_audit data/raw/nature_source_data > publisher_audit.json
python -m pytest
```

The first command writes the full JSON snapshot to `data/processed/extracted_barriers.json` using atomic replacement. Use `--out PATH` for a different destination. The second emits the publisher-specific audit directly, and exits with code 2 on a missing or untrusted attachment. The normal extraction command explicitly records the fallback reason when input cannot be used.

1. Resolve the figure-labeled links in the article. Preserve each original filename, download URL, size, retrieval date and SHA-256. Both URLs currently return the same bytes. [Article](https://doi.org/10.1038/s41567-026-03236-0) · [Receipt](../data/raw/nature_source_data/source_receipt.json)
2. Verify both digests before interpreting either workbook. Read worksheet A1 addresses, original formula text, cached decimal values, image IDs, reaction coordinates and chart ranges. Coordinates use columns D, K and R. The paths occupy F2:F30, M2:M37 and T2:T26 on Sheet1.
3. Replay the volume, energy and normalized-coordinate formulas and compare with cached values. For each branch verify the unique highest sampled energy lies in the interior and the start is a one-sided minimum. Subtract that starting energy from the peak. Escape and collapse each have their own starting cell.
4. Record both conditional absolute scales while the density units are unresolved. The tests exercise declared J, pJ and fJ values, genuine sparse spreadsheet addresses, invalid units, ambiguous extrema, malformed input, mismatched checksums and complete fallback. The active table always switches as a whole. [Differences and release criteria](../data/processed/EXTRACTION_STATUS.md)
5. To cross-check the plot independently, download the original Extended Data Figure 9 JPEG from the URL in the plot script and run the commands below. The plot check uses NumPy and Pillow. The solver check uses the Python standard library. Its optional `--solver-checkout` argument accepts a Git checkout containing the two historical revisions.

```sh
python scripts/check_fig9_plot.py 41567_2026_3236_Fig15_ESM.jpg
python scripts/check_solver_export.py
```

The conversion regression maps 2.24 × 10⁻¹⁶ J, 2.24 × 10⁻⁴ pJ and 0.224 fJ to the same value of 0.000224 pJ. The previous magnitude-based function returned 2.24 × 10⁻¹⁶ and 0.000224 for the first two inputs. That trillionfold software defect is distinct from the thousandfold physical-scale question in the publisher workbook.

For a separately reviewed literal-numeric workbook layout, the candidate CLI accepts an explicit manifest with pinned digests, unit and header coordinates, branch rows and both extrema. An untrusted mapping may produce a `candidate_only` artifact. Approval is package-controlled and cannot be granted by a locally supplied manifest. Formula-bearing publisher files use the dedicated audited code path above. [Candidate examples in tests](../tests/test_barrier_workbooks.py)

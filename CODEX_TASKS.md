# CODEX_TASKS

## Completed foundation

- [x] Initialize repository scaffold for NAG Difference Hopfion Benchmark.
- [x] Implement pairwise antisymmetric difference utilities.
- [x] Implement scoring terms and soft selection weights.
- [x] Add seeded hopfion barrier data with explicit provenance metadata.
- [x] Add tests for antisymmetry, diagonal zeros, and seeded comparison outcomes.
- [x] Add CI workflow running pytest.
- [x] Add raw extraction protocol and JSON extraction artifact CLI path.
- [x] Add explicit progress checkpoints and pipeline visuals with test gates.
- [x] Add second track: cancellation identity helpers and chain-certificate utilities.
- [x] Add docs/tests/formal starter files for chain-certificate track.

## Current priority — authoritative barrier data

The paper used by this benchmark is:

> Chen et al., "Laser-induced nucleation of magnetic hopfions," Nature Physics 22, 736–744 (2026). DOI: 10.1038/s41567-026-03236-0.

The article exposes the MEP simulation datasets as **Source Data Fig. 5** and
**Source Data Extended Data Fig. 9** XLSX files. The repository's existing
`MOESM13` / `MOESM16` assumptions are not established as the publisher's
source-data names and must not be used as provenance shortcuts.

- [ ] Obtain the publisher-provided Source Data Fig. 5 and Source Data Extended Data Fig. 9 XLSX files.
- [ ] Record original filenames, source URL/DOI context, retrieval date, and SHA-256 checksums.
- [ ] Inspect workbook sheet names, units, reaction-coordinate columns, and energy columns before defining any fixed mapping.
- [ ] Replace the `MOESM13` / `MOESM16` routing assumptions in `nagdiff/extraction.py` with mappings derived from the actual workbooks.
- [ ] Extract and independently recompute the three target barriers: skyrmion–antiskyrmion merger → hopfion, hopfion collapse/shrinking, and hopfion escape through the free surface.
- [ ] Add regression fixtures/tests that prove the mapping, units, checksums, and atomic fallback behavior.
- [ ] Compare extracted values against the plotted MEPs in Fig. 5 / Extended Data Fig. 9 and document any discrepancy with the seeded placeholders.
- [ ] Promote seeded placeholders to validated values only after the complete provenance/test gate passes.

## After data validation

- [ ] Feed validated barriers through pairwise/scoring sensitivity analyses.
- [ ] Replace Lean starter `sorry` statements incrementally with proved lemmas tied to stable APIs.

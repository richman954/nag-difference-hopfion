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

- [x] Acquire the publisher's Figure 5 and Extended Data Figure 9 workbooks with independent URLs, original filenames, dates and SHA-256 receipts.
- [x] Map all 90 images and reproduce the energy and reaction-coordinate formulas and chart caches for each branch.
- [x] Calculate all three directed saddle-minus-initial-minimum differences and cross-check the saddle images against the published Extended Data Figure 9.
- [x] Test explicit units, original spreadsheet addresses, checksums, malformed inputs and atomic fallback.
- [x] Test whether the scoring template responds to permuting or removing the barriers and whether coarse sampling recovers the known discrete saddles.
- [x] Implement a two-stage route prediction comparison with an independently recorded prediction digest and a complete enrolled roster.

## Open scientific and formalization tasks

- [ ] Establish the density unit and any scaling between the original simulation export and the spreadsheet. Record primary evidence and re-review all three physical barriers before promotion.
- [ ] Evaluate the full score and barrier-only baseline on future independently enrolled, route-labeled runs at matched conditions. Freeze model settings and inputs before observing outcomes.
- [ ] Replace Lean starter `sorry` statements incrementally with proved lemmas tied to stable APIs.

[Workbook evidence](data/processed/EXTRACTION_STATUS.md) · [Benchmark results](docs/benchmark_validation.md)

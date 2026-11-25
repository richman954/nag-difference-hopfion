# NAG-Difference Hopfion Benchmark Checkpoints

This file tracks forward progress with explicit checkpoints and test gates.

## Checkpoint 1 — Scaffold baseline (completed)
- Core package modules in place (`pairwise`, `scoring`, `hopfion_terms`, `extraction`).
- Baseline CI (`pytest`) configured.
- Seeded barriers explicitly marked as provisional.

## Checkpoint 2 — Extraction infrastructure (completed)
- Extraction CLI and JSON artifact generation implemented.
- Provenance fields required for extracted records.
- Raw-file SHA-256 checksums supported in extraction artifacts.
- Atomic fallback prevents incomplete extracted data from replacing the full seeded table.

## Checkpoint 3 — Reporting + progress visibility (completed)
- Compact pipeline visual exists in `docs/progress_visuals.md`.
- Comparison/reporting utilities and recurring test gates are present.

## Checkpoint 4 — Filename-based ingestion (superseded)

The authoritative figures resolve to filenames that contain MOESM13 and MOESM16. Publisher figure labels, download URLs, original byte digests and reviewed worksheet ranges establish the mapping. Filename matches alone cannot authorize extraction.

## Checkpoint 5 — Publisher data ingested, physical energy scale open

Both original workbooks are present, with separate source receipts and identical content. The extractor reproduces all three directed barriers, their minimum and saddle addresses and their plot ordering. The regression suite exercises failed-source, invalid-record and all-or-nothing fallback behavior. The remaining requirement for physical promotion is evidence of the simulation density unit and any preprocessing before spreadsheet import. [Status and release criteria](data/processed/EXTRACTION_STATUS.md)

## Checkpoint 6 — Discrimination checks and prospective evaluation

The scoring and grid-sampling controls replay on the publisher data. A two-stage evaluator freezes model predictions before receiving a cohort's route outcomes. An eligible external cohort and its independent enrollment record are still needed to measure predictive performance. Chain-certificate extensions and replacement of Lean starter `sorry` statements remain open. [Methods and results](docs/benchmark_validation.md)

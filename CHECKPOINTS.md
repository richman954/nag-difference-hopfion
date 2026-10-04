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

## Checkpoint 4 — Legacy MOESM mapping attempt (superseded)
- Earlier work assumed barrier inputs would arrive as `MOESM13` / `MOESM16`.
- That naming assumption is not established by the cited Nature Physics article.
- Do not promote data merely because a file has been renamed to match the legacy convention.

## Checkpoint 5 — Authoritative Nature source-data ingestion (current)
- Acquire the publisher's **Source Data Fig. 5** and **Source Data Extended Data Fig. 9** XLSX files for DOI `10.1038/s41567-026-03236-0`.
- Preserve original filenames and SHA-256 checksums.
- Inspect workbook structure before writing deterministic sheet/cell mappings.
- Extract all three target barrier paths and verify units/reaction-coordinate interpretation.
- Require a complete provenance record and passing tests before replacing seeded placeholders.

### Checkpoint 5 gate
All must pass:
1. Original source-data files identified from the article.
2. SHA-256 checksums recorded.
3. Deterministic mapping documented.
4. Three target barriers extracted from the authoritative workbooks.
5. Regression tests and full `pytest` pass.
6. Extracted values reconciled against Fig. 5 / Extended Data Fig. 9.
7. No fallback value is mislabeled as validated.

## Checkpoint 6 — Scientific analysis + formalization (next)
- Run parameter/sensitivity analysis with validated barriers.
- Extend chain-certificate results beyond toy examples.
- Replace Lean starter `sorry` statements with proved lemmas against stable definitions.

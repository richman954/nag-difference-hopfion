# NAG-Difference Hopfion Benchmark Checkpoints

This file tracks forward progress with explicit checkpoints and test gates.

## Checkpoint 1 — Scaffold baseline (completed)
- Core package modules in place (`pairwise`, `scoring`, `hopfion_terms`, `extraction`).
- Baseline CI (`pytest`) configured.
- Seeded barriers remain marked `raw_moesm_verification_pending`.

## Checkpoint 2 — Extraction reproducibility (completed)
- Extraction CLI and JSON artifact generation implemented.
- Provenance fields required for extracted records.
- Raw-file SHA256 checksums included in extraction artifacts.

## Checkpoint 3 — Reporting + visual progress (current)
- Add state of pipeline in a compact visual map.
- Keep a recurring “tests checkpoint” at each iteration.

## Checkpoint 4 — MOESM mapping hardening (next)
- Replace keyword-scan with explicit sheet/cell mapping once raw sheet structure is finalized.
- Add regression fixtures from curated sample files.
- Promote status from provisional only after validated extraction protocol review.

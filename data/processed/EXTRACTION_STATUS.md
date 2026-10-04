# Extraction Status

## Current status

**Authoritative source-data extraction has not yet been completed.**

The seeded barrier values currently in this repository remain provisional
placeholders and must continue to be labeled:

- `raw_moesm_verification_pending`

That legacy label is retained for compatibility, but the repository's previous
assumption that the relevant publisher data would be named `MOESM13` and
`MOESM16` is not established by the cited article.

For Chen et al., *Laser-induced nucleation of magnetic hopfions*, Nature Physics
22, 736–744 (2026), DOI `10.1038/s41567-026-03236-0`, the article identifies the
relevant MEP datasets as:

- **Source Data Fig. 5** — simulation data for the main minimum-energy paths.
- **Source Data Extended Data Fig. 9** — simulation data for the extended MEPs,
  including the separate shrinking/collapse and free-surface escape paths.

Until those publisher-provided XLSX files are ingested, checksummed, mapped,
and validated, no seeded barrier value should be described as directly
extracted from the paper.

## Promotion rule

Seeded placeholders may be replaced only when all three target barriers are
derived from the authoritative source-data workbooks with complete provenance,
unit handling, checksums, deterministic mapping, and passing regression tests.

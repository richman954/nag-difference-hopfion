# Raw Extraction Protocol — Nature Physics Source Data

## Authoritative publication

Chen et al., *Laser-induced nucleation of magnetic hopfions*, Nature Physics
22, 736–744 (2026). DOI: `10.1038/s41567-026-03236-0`.

The article publishes the relevant minimum-energy-path simulation datasets as:

1. **Source Data Fig. 5** (XLSX)
2. **Source Data Extended Data Fig. 9** (XLSX)

These are the primary inputs for validating the three barrier quantities used
by this benchmark.

## Intake procedure

1. Download the two XLSX files from the article's Source data section.
2. Preserve the publisher filenames. Do **not** rename files to `MOESM13` or
   `MOESM16` merely to satisfy the legacy extractor.
3. Store them under a clearly named raw-data directory such as
   `data/raw/nature_source_data/`.
4. Record for each file:
   - article DOI
   - source-data label (Fig. 5 or Extended Data Fig. 9)
   - original filename
   - retrieval date
   - SHA-256 checksum
5. Inspect workbook sheet names, headers, units, reaction-coordinate columns,
   energy columns, and any normalization before writing fixed extraction
   mappings.
6. Derive the three benchmark targets from the MEP curves:
   - skyrmion–antiskyrmion merger → hopfion
   - hopfion collapse by shrinking
   - hopfion escape through the free surface
7. Verify each barrier as a difference between the relevant local minimum and
   saddle point rather than blindly copying an isolated numeric cell.
8. Add regression fixtures and tests for workbook mapping, units, provenance,
   checksums, and complete/atomic promotion.
9. Run the full test suite.
10. Only after all three records validate should the active table switch from
    seeded fallback to extracted values.

## Legacy extractor warning

The current `nagdiff.extraction` implementation still contains hard-coded
`MOESM13` / `MOESM16` discovery and routing assumptions. Treat that path as
legacy scaffolding until it is replaced with mappings derived from the actual
publisher workbooks.

The repository snapshot ZIP files are not substitutes for the publisher source
data. Seeded values remain available for audit comparison and must not be
silently relabeled as extracted.

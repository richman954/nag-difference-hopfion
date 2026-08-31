# Raw Extraction Protocol (MOESM)

1. Place raw supplementary CSV or XLSX files under `data/raw/MOESM13/` and
   `data/raw/MOESM16/` (direct filenames beginning with `MOESM13` or `MOESM16`
   are also accepted). Do not substitute the repository snapshot ZIP uploads;
   an archive-content audit found no MOESM13 or MOESM16 source tables in them.
2. Run extraction:
   - `python -m nagdiff.extraction --raw data/raw --out data/processed/extracted_barriers.json`
3. Verify output includes all required provenance fields:
   - `source_file`, `sheet_name`, `row`, `column`, `unit`, `extraction_method`, `notes`
4. Keep seeded fallback values for audit comparison even when extraction succeeds.

The extractor records the source file, worksheet, one-based row and column,
normalized unit, method, and notes. It uses deterministic mappings for the
known flat CSV layout and a keyword-row scan for CSV/XLSX tables. Extracted
values become active only when all three target processes validate; otherwise
the complete seeded table remains active and **raw MOESM verification pending**.

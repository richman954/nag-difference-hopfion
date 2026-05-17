# Raw Extraction Protocol (MOESM)

1. Place raw supplementary files under `data/raw/` with names matching `MOESM13*.csv` and `MOESM16*.csv` (or folders `MOESM13/`, `MOESM16/` containing CSVs).
2. Run extraction:
   - `python -m nagdiff.extraction --raw data/raw --out data/processed/extracted_barriers.json`
3. Verify output includes all required provenance fields:
   - `source_file`, `sheet_name`, `row`, `column`, `unit`, `extraction_method`, `notes`
4. Keep seeded fallback values for audit comparison even when extraction succeeds.

The current extractor is CSV keyword-row scan based and remains a scaffold until finalized raw-sheet mappings are locked.

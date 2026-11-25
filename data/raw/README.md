# Raw barrier data

The original Figure 5 and Extended Data Figure 9 XLSX attachments from Chen et al. are in [nature_source_data](nature_source_data/). The [receipt](nature_source_data/source_receipt.json) records the publisher labels, URLs, original filenames, retrieval times, lengths and SHA-256 digests. Each link returned the same workbook bytes.

From the repository root, `python -m nagdiff.extraction` audits both attachments. An explicit `--raw` accepts the parent directory or the directory containing the pair. Competing or split layouts trigger fallback. Repository snapshot ZIPs and filename-matched CSVs cannot supply publisher provenance. [Protocol](../../docs/raw_extraction_protocol.md)

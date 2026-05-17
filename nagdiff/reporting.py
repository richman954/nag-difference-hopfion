from __future__ import annotations

import csv
from pathlib import Path

from nagdiff.hopfion_terms import load_barrier_table


def write_extraction_comparison_csv(out_csv: str | Path, raw_dir: str = "data/raw", extraction_mode: str = "auto") -> Path:
    table = load_barrier_table(raw_dir=raw_dir, extraction_mode=extraction_mode)
    seeded = {r["state"]: r for r in table["seeded_records"]}
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "state",
            "seeded_barrier_pj",
            "active_barrier_pj",
            "delta_pj",
            "provenance_status",
            "replacement_applied",
            "source_file",
            "sheet_name",
            "row",
            "column",
        ])
        for record in table["records"]:
            s = seeded[record["state"]]
            delta = float(record["barrier_pj"]) - float(s["barrier_pj"])
            replacement = record["provenance_status"] == "extracted_from_raw_moesm"
            writer.writerow([
                record["state"],
                s["barrier_pj"],
                record["barrier_pj"],
                delta,
                record["provenance_status"],
                str(replacement).lower(),
                record.get("source_file"),
                record.get("sheet_name"),
                record.get("row"),
                record.get("column"),
            ])
    return out_path

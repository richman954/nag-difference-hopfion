"""Seeded and extracted hopfion barrier terms with explicit provenance status."""

from __future__ import annotations

from pathlib import Path


REQUIRED_PROVENANCE_FIELDS = [
    "source_file",
    "sheet_name",
    "row",
    "column",
    "unit",
    "extraction_method",
    "notes",
]

SEEDED_BARRIER_DATA = [
    {
        "state": "skyrmion_antiskyrmion_merge_to_hopfion",
        "barrier_pj": 2.24e-4,
        "unit": "pJ",
        "provenance_note": "provisional placeholder from prior notes",
        "provenance_status": "raw_moesm_verification_pending",
        "source_target": "Source Data Fig. 5",
    },
    {
        "state": "hopfion_collapse",
        "barrier_pj": 2.86e-4,
        "unit": "pJ",
        "provenance_note": "provisional placeholder from prior notes",
        "provenance_status": "raw_moesm_verification_pending",
        "source_target": "Source Data Fig. 5",
    },
    {
        "state": "hopfion_escape",
        "barrier_pj": 7.32e-4,
        "unit": "pJ",
        "provenance_note": "provisional placeholder from prior notes",
        "provenance_status": "raw_moesm_verification_pending",
        "source_target": "Source Data Extended Data Fig. 9",
    },
]


def load_barrier_table(raw_dir: str | Path = "data/raw", extraction_mode: str = "auto") -> dict:
    from nagdiff.extraction import VALIDATED_STATUS, extraction_payload

    result = extraction_payload(raw_dir, extraction_mode)
    seeds = [dict(row) for row in SEEDED_BARRIER_DATA]
    if result["status"] == VALIDATED_STATUS and result["extracted_count"] == len(seeds):
        rows = [{**r, "provenance_status": result["status"]} for r in result["records"]]
        return {"mode": "extracted", "records": rows, "seeded_records": seeds,
                "extracted_count": len(rows), "checksums": result["checksums"]}
    rows = [{**s, "source_file": None, "sheet_name": None, "row": None,
             "column": None, "extraction_method": "seeded_fallback",
             "notes": "Provisional placeholder. " + result["reason"]} for s in seeds]
    return {"mode": "fallback", "status": result["status"], "reason": result["reason"],
            "records": rows, "seeded_records": seeds, "extracted_count": 0,
            "checksums": result["checksums"]}

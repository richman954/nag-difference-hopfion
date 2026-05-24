"""Seeded and extracted hopfion barrier terms with explicit provenance status."""

from __future__ import annotations

from dataclasses import asdict
from nagdiff.extraction import extract_barriers_and_checksums, is_extraction_validated

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
        "source_target": "MOESM13/MOESM16",
    },
    {
        "state": "hopfion_collapse",
        "barrier_pj": 2.86e-4,
        "unit": "pJ",
        "provenance_note": "provisional placeholder from prior notes",
        "provenance_status": "raw_moesm_verification_pending",
        "source_target": "MOESM13/MOESM16",
    },
    {
        "state": "hopfion_escape",
        "barrier_pj": 7.32e-4,
        "unit": "pJ",
        "provenance_note": "provisional placeholder from prior notes",
        "provenance_status": "raw_moesm_verification_pending",
        "source_target": "MOESM13/MOESM16",
    },
]


def _validate_provenance(record: dict[str, object]) -> None:
    for field in REQUIRED_PROVENANCE_FIELDS:
        if field not in record or record[field] in (None, ""):
            raise ValueError(f"missing required provenance field: {field}")


def load_barrier_table(raw_dir: str = "data/raw", extraction_mode: str = "auto") -> dict[str, object]:
    extracted, checksums = extract_barriers_and_checksums(raw_dir, mode=extraction_mode)

    payload = {
        "raw_dir": str(raw_dir),
        "mode": extraction_mode,
        "extracted_count": len(extracted),
        "checksums": checksums,
        "records": [asdict(row) for row in extracted],
    }

    if is_extraction_validated(payload):
        extracted_by_state = {row.state: row for row in extracted}
        combined = []
        for seeded in SEEDED_BARRIER_DATA:
            state = seeded["state"]
            ex = extracted_by_state[state]
            record = {
                "state": state,
                "barrier_pj": ex.barrier_pj,
                "unit": ex.unit,
                "source_file": ex.source_file,
                "sheet_name": ex.sheet_name,
                "row": ex.row,
                "column": ex.column,
                "extraction_method": ex.extraction_method,
                "notes": ex.notes,
                "provenance_status": "extracted_from_raw_moesm",
            }
            _validate_provenance(record)
            combined.append(record)
        return {
            "mode": "extracted",
            "records": combined,
            "seeded_records": SEEDED_BARRIER_DATA,
            "extracted_count": len(extracted_by_state),
        }

    combined = []
    for seeded in SEEDED_BARRIER_DATA:
        combined.append(
            {
                **seeded,
                "source_file": None,
                "sheet_name": None,
                "row": None,
                "column": None,
                "extraction_method": "seeded_fallback",
                "notes": "Extraction not found; using provisional seeded fallback.",
            }
        )

    return {
        "mode": "fallback",
        "records": combined,
        "seeded_records": SEEDED_BARRIER_DATA,
        "extracted_count": 0,
    }

"""Guardrails for scientific caution wording around seeded barriers."""

from pathlib import Path

from nagdiff.hopfion_terms import SEEDED_BARRIER_DATA


REQUIRED_LABEL = "raw_moesm_verification_pending"
REQUIRED_HUMAN_PHRASE = "raw MOESM verification pending"


def test_seeded_barrier_records_keep_required_provisional_status() -> None:
    statuses = {record["provenance_status"] for record in SEEDED_BARRIER_DATA}
    assert statuses == {REQUIRED_LABEL}


def test_readme_explicitly_marks_seeded_values_as_pending() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert REQUIRED_HUMAN_PHRASE in readme


def test_extraction_status_marks_seeded_values_as_pending() -> None:
    status_doc = Path("data/processed/EXTRACTION_STATUS.md").read_text(encoding="utf-8")
    assert REQUIRED_HUMAN_PHRASE in status_doc

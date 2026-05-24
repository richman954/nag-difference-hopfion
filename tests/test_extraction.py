import json

from nagdiff.extraction import write_extraction_artifact
from nagdiff.hopfion_terms import REQUIRED_PROVENANCE_FIELDS, load_barrier_table


import pytest

def test_write_extraction_artifact(tmp_path):
    (tmp_path / "MOESM13.csv").write_text(
        "label,value\n"
        "skyrmion antiskyrmion merge hopfion barrier,2.24e-4\n"
        "hopfion collapse barrier,2.86e-4\n",
        encoding="utf-8",
    )
    (tmp_path / "MOESM16.csv").write_text(
        "label,value\n"
        "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    out = tmp_path / "artifact.json"
    payload = write_extraction_artifact(tmp_path, out, base_dir=tmp_path)
    assert payload["extracted_count"] == 3
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["checksums"]) == 2
    assert len(data["records"]) == 3


def test_extracted_records_have_required_provenance(tmp_path):
    (tmp_path / "MOESM13.csv").write_text(
        "label,value\n"
        "skyrmion antiskyrmion merge hopfion barrier,2.24e-4\n"
        "hopfion collapse barrier,2.86e-4\n",
        encoding="utf-8",
    )
    (tmp_path / "MOESM16.csv").write_text(
        "label,value\n"
        "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)
    extracted = [r for r in table["records"] if r["provenance_status"] == "extracted_from_raw_moesm"]
    assert len(extracted) == 3
    for record in extracted:
        for field in REQUIRED_PROVENANCE_FIELDS:
            assert record[field] not in (None, "")


def test_is_extraction_validated_success(tmp_path):
    from nagdiff.extraction import is_extraction_validated
    payload = {
        "extracted_count": 3,
        "records": [
            {
                "state": "skyrmion_antiskyrmion_merge_to_hopfion",
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n"
            },
            {
                "state": "hopfion_collapse",
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n"
            },
            {
                "state": "hopfion_escape",
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n"
            }
        ],
        "checksums": {"f": "c"}
    }
    assert is_extraction_validated(payload) is True


def test_is_extraction_validated_fails_on_empty(tmp_path):
    from nagdiff.extraction import is_extraction_validated
    out = tmp_path / "artifact.json"
    payload = write_extraction_artifact(tmp_path, out, base_dir=tmp_path)
    assert is_extraction_validated(payload) is False

def test_write_extraction_artifact_path_traversal(tmp_path):
    out = tmp_path / "artifact.json"
    malicious_out = tmp_path / "../../artifact.json"
    malicious_raw = tmp_path / "../../raw"

    with pytest.raises(ValueError, match="Path traversal detected"):
        write_extraction_artifact(tmp_path, malicious_out, base_dir=tmp_path)

    with pytest.raises(ValueError, match="Path traversal detected"):
        write_extraction_artifact(malicious_raw, out, base_dir=tmp_path)


def test_fallback_values_marked_raw_moesm_verification_pending(tmp_path):
    table = load_barrier_table(raw_dir=tmp_path)
    for record in table["records"]:
        assert record["provenance_status"] == "raw_moesm_verification_pending"

import json

import pytest

from nagdiff.extraction import write_extraction_artifact
from nagdiff.hopfion_terms import (
    REQUIRED_PROVENANCE_FIELDS,
    _validate_provenance,
    load_barrier_table,
)


def test_write_extraction_artifact(tmp_path):
    (tmp_path / "MOESM13.csv").write_text(
        "label,value\n"
        "skyrmion antiskyrmion merge hopfion barrier,2.24e-4\n"
        "hopfion collapse barrier,2.86e-4\n",
        encoding="utf-8",
    )
    (tmp_path / "MOESM16.csv").write_text(
        "label,value\n" "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    out = tmp_path / "artifact.json"
    payload = write_extraction_artifact(tmp_path, out)
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
        "label,value\n" "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)
    extracted = [
        r
        for r in table["records"]
        if r["provenance_status"] == "extracted_from_raw_moesm"
    ]
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
                "barrier_pj": 1.0,
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n",
            },
            {
                "state": "hopfion_collapse",
                "barrier_pj": 1.0,
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n",
            },
            {
                "state": "hopfion_escape",
                "barrier_pj": 1.0,
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n",
            },
        ],
        "checksums": {"f": "c"},
    }
    assert is_extraction_validated(payload) is True


def test_is_extraction_validated_fails_on_empty(tmp_path):
    from nagdiff.extraction import is_extraction_validated

    out = tmp_path / "artifact.json"
    payload = write_extraction_artifact(tmp_path, out)
    assert is_extraction_validated(payload) is False


def test_fallback_values_marked_raw_moesm_verification_pending(tmp_path):
    table = load_barrier_table(raw_dir=tmp_path)
    for record in table["records"]:
        assert record["provenance_status"] == "raw_moesm_verification_pending"


def test_extracts_from_named_moesm_directories_and_keeps_seeded_comparison(tmp_path):
    moesm13 = tmp_path / "MOESM13"
    moesm16 = tmp_path / "MOESM16"
    moesm13.mkdir()
    moesm16.mkdir()
    (moesm13 / "barriers.csv").write_text(
        "process,barrier\n"
        "skyrmion antiskyrmion merge hopfion,1.11e-4\n"
        "hopfion collapse,2.22e-4\n",
        encoding="utf-8",
    )
    (moesm16 / "barriers.csv").write_text(
        "process,barrier\nhopfion escape,3.33e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)

    assert table["mode"] == "extracted"
    assert [record["barrier_pj"] for record in table["records"]] == [
        1.11e-4,
        2.22e-4,
        3.33e-4,
    ]
    assert table["seeded_records"][0]["barrier_pj"] == 2.24e-4
    for record in table["records"]:
        assert record["source_file"].endswith("barriers.csv")
        assert record["sheet_name"] == "barriers"
        assert record["row"] > 0
        assert record["column"] > 0
        assert record["unit"] == "pJ"
        assert record["extraction_method"] == "keyword_row_scan_csv"
        assert record["notes"]


def test_partial_extraction_does_not_replace_any_seeded_values(tmp_path):
    moesm13 = tmp_path / "MOESM13"
    moesm13.mkdir()
    (moesm13 / "barriers.csv").write_text(
        "process,barrier\nhopfion collapse,9.99e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)

    assert table["mode"] == "fallback"
    assert [record["barrier_pj"] for record in table["records"]] == [
        2.24e-4,
        2.86e-4,
        7.32e-4,
    ]
    assert all(
        record["extraction_method"] == "seeded_fallback" for record in table["records"]
    )


def test_validate_provenance_raises_value_error_on_missing_field():
    record = {
        "source_file": "file.csv",
        "sheet_name": "Sheet1",
        "row": 1,
        "column": 1,
        "unit": "pJ",
        "extraction_method": "method",
        "notes": "some notes",
    }

    # Assert valid record passes
    _validate_provenance(record)

    # Test missing field
    invalid_record = record.copy()
    del invalid_record["notes"]
    with pytest.raises(ValueError):
        _validate_provenance(invalid_record)

    # Test empty string
    empty_record = record.copy()
    empty_record["notes"] = ""
    with pytest.raises(ValueError):
        _validate_provenance(empty_record)

    # Test None
    none_record = record.copy()
    none_record["notes"] = None
    with pytest.raises(ValueError):
        _validate_provenance(none_record)

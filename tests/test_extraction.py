import json

from nagdiff.extraction import write_extraction_artifact
from nagdiff.hopfion_terms import REQUIRED_PROVENANCE_FIELDS, load_barrier_table


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


def test_strict_mode_uses_mapping_file(tmp_path):
    (tmp_path / "MOESM13.csv").write_text("h,v\na,2.24e-4\nb,2.86e-4\n", encoding="utf-8")
    (tmp_path / "MOESM16.csv").write_text("h,v\na,7.32e-4\n", encoding="utf-8")
    mapping = tmp_path / "map.json"
    mapping.write_text(
        """{
  "states": {
    "skyrmion_antiskyrmion_merge_to_hopfion": {"file": "MOESM13.csv", "row": 2, "column": 2, "unit": "pJ"},
    "hopfion_collapse": {"file": "MOESM13.csv", "row": 3, "column": 2, "unit": "pJ"},
    "hopfion_escape": {"file": "MOESM16.csv", "row": 2, "column": 2, "unit": "pJ"}
  }
}""",
        encoding="utf-8",
    )
    from nagdiff.extraction import extract_barriers_from_raw
    recs = extract_barriers_from_raw(tmp_path, mode="strict", mapping_path=mapping)
    assert len(recs) == 3

def test_default_mode_is_strict(tmp_path):
    (tmp_path / "MOESM13.csv").write_text("h,v\na,2.24e-4\nb,2.86e-4\n", encoding="utf-8")
    (tmp_path / "MOESM16.csv").write_text("h,v\na,7.32e-4\n", encoding="utf-8")
    mapping = tmp_path / "map.json"
    mapping.write_text(
        """{
  "states": {
    "skyrmion_antiskyrmion_merge_to_hopfion": {"file": "MOESM13.csv", "row": 2, "column": 2, "unit": "pJ"},
    "hopfion_collapse": {"file": "MOESM13.csv", "row": 3, "column": 2, "unit": "pJ"},
    "hopfion_escape": {"file": "MOESM16.csv", "row": 2, "column": 2, "unit": "pJ"}
  }
}""",
        encoding="utf-8",
    )
    from nagdiff.extraction import extract_barriers_from_raw
    recs = extract_barriers_from_raw(tmp_path, mapping_path=mapping)
    assert len(recs) == 3
    assert all(r.extraction_method == "strict_csv_mapping" for r in recs)


def test_load_strict_mapping_rejects_invalid_state_specs(tmp_path):
    bad = tmp_path / "bad_map.json"
    bad.write_text(
        '{"states": {"hopfion_escape": {"file": "MOESM16.csv", "row": 0, "column": 2, "unit": "pJ"}}}',
        encoding="utf-8",
    )
    from nagdiff.extraction import load_strict_mapping

    try:
        load_strict_mapping(bad)
    except ValueError as exc:
        assert "row must be a 1-indexed positive integer" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid row index")


def test_extract_rejects_unknown_mode(tmp_path):
    from nagdiff.extraction import extract_barriers_from_raw

    try:
        extract_barriers_from_raw(tmp_path, mode="nonsense")
    except ValueError as exc:
        assert "mode must be one of" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported extraction mode")


def test_strict_mode_respects_declared_units(tmp_path):
    (tmp_path / "MOESM13.csv").write_text("h,v\na,224\nb,286\n", encoding="utf-8")
    (tmp_path / "MOESM16.csv").write_text("h,v\na,732\n", encoding="utf-8")
    mapping = tmp_path / "map_units.json"
    mapping.write_text(
        """{\n  "states": {\n    "skyrmion_antiskyrmion_merge_to_hopfion": {"file": "MOESM13.csv", "row": 2, "column": 2, "unit": "fJ"},\n    "hopfion_collapse": {"file": "MOESM13.csv", "row": 3, "column": 2, "unit": "fJ"},\n    "hopfion_escape": {"file": "MOESM16.csv", "row": 2, "column": 2, "unit": "fJ"}\n  }\n}""",
        encoding="utf-8",
    )
    from nagdiff.extraction import extract_barriers_from_raw

    recs = extract_barriers_from_raw(tmp_path, mode="strict", mapping_path=mapping)
    values = {r.state: r.barrier_pj for r in recs}
    import pytest

    assert values["skyrmion_antiskyrmion_merge_to_hopfion"] == pytest.approx(224e-3)
    assert values["hopfion_collapse"] == pytest.approx(286e-3)
    assert values["hopfion_escape"] == pytest.approx(732e-3)


def test_collect_checksums_is_deterministically_sorted(tmp_path):
    (tmp_path / "MOESM16.csv").write_text("h,v\na,7.32e-4\n", encoding="utf-8")
    (tmp_path / "MOESM13.csv").write_text("h,v\na,2.24e-4\n", encoding="utf-8")

    from nagdiff.extraction import collect_raw_file_checksums

    checksums = collect_raw_file_checksums(tmp_path)
    keys = list(checksums.keys())
    assert keys == sorted(keys)

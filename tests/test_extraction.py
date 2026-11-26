"""Entry-point tests for the proposed all-three-or-fallback contract."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

from nagdiff import extraction
from nagdiff.hopfion_terms import load_barrier_table
from nagdiff.reporting import write_extraction_comparison_csv
from test_barrier_workbooks import BARRIERS_PJ, ESCAPE, FILES, make_example

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "nature_source_data"
SEED = [2.24e-4, 2.86e-4, 7.32e-4]


@pytest.fixture
def reviewed_fixture(tmp_path, monkeypatch):
    manifest = make_example(tmp_path)
    # Simulate a future reviewed release *inside this test process only*.
    monkeypatch.setattr(extraction, "_APPROVED_MANIFEST_JSON", json.dumps(manifest))
    return manifest


def assert_all_fallback(table):
    assert table["mode"] == "fallback"
    assert table["extracted_count"] == 0
    assert table["reason"]
    assert [r["barrier_pj"] for r in table["records"]] == SEED
    assert {r["provenance_status"] for r in table["records"]} == {"raw_moesm_verification_pending"}
    assert {r["extraction_method"] for r in table["records"]} == {"seeded_fallback"}
    assert all(r["source_file"] is None for r in table["records"])


@pytest.mark.parametrize("layout", ["flat", "directories"])
def test_unitless_legacy_csv_is_fallback_only(tmp_path, layout):
    inputs = {"MOESM13": "skyrmion antiskyrmion merge hopfion,2.24e-4\nhopfion collapse,2.86e-4",
              "MOESM16": "hopfion escape,7.32e-4"}
    for label, rows in inputs.items():
        path = tmp_path / (label + ".csv") if layout == "flat" else tmp_path / label / "barriers.csv"
        path.parent.mkdir(exist_ok=True)
        path.write_text("label,value\n" + rows, encoding="utf-8")
    assert_all_fallback(load_barrier_table(tmp_path))


def test_empty_fallback_and_reason(tmp_path):
    assert_all_fallback(load_barrier_table(tmp_path))


@pytest.mark.parametrize("corruption", ["missing", "bytes", "partial", "wrong_saddle", "bad_unit"])
def test_atomic_fallback_even_after_valid_first_file(reviewed_fixture, tmp_path, monkeypatch, corruption):
    path = tmp_path / FILES["ed9"]
    if corruption == "missing":
        path.unlink()
    elif corruption == "bytes":
        with path.open("ab") as fh:
            fh.write(b"altered")
    elif corruption == "partial":
        del reviewed_fixture["paths"][ESCAPE]
    elif corruption == "wrong_saddle":
        reviewed_fixture["paths"][ESCAPE]["saddle_row"] = 19
    else:
        reviewed_fixture["paths"][ESCAPE]["unit"] = "a.u."
    monkeypatch.setattr(extraction, "_APPROVED_MANIFEST_JSON", json.dumps(reviewed_fixture))
    assert_all_fallback(load_barrier_table(tmp_path))
    payload = extraction.write_extraction_artifact(tmp_path, tmp_path / "extraction.json", mode="strict")
    assert payload["records"] == []
    assert not extraction.is_extraction_validated(payload)


def test_reviewed_test_pair_all_three_or_none_and_report(reviewed_fixture, tmp_path):
    table = load_barrier_table(tmp_path)
    assert table["mode"] == "extracted"
    assert [r["barrier_pj"] for r in table["records"]] == list(map(float, BARRIERS_PJ.values()))
    assert [r["barrier_pj"] for r in table["seeded_records"]] == SEED
    artifact = tmp_path / "artifact.json"
    payload = extraction.write_extraction_artifact(tmp_path, artifact)
    assert extraction.is_extraction_validated(json.loads(artifact.read_text()))
    assert len(payload["checksums"]) == 2
    objects = extraction.extract_barriers_from_raw(tmp_path)
    assert objects[1].minimum == table["records"][1]["minimum"]
    with write_extraction_comparison_csv(tmp_path / "comparison.csv", tmp_path).open() as stream:
        rows = list(csv.DictReader(stream))
    assert [r["replacement_applied"] for r in rows] == ["true"] * 3
    assert rows[1]["minimum_energy_cell"] == "AD18" and rows[1]["saddle_energy_cell"] == "AD20"


def test_arbitrary_dictionaries_cannot_promote(tmp_path):
    for payload in (None, 3, [], {"extracted_count": 3, "records": [1, 2, 3], "checksums": {"f": "c"}}):
        assert not extraction.is_extraction_validated(payload)
    assert not extraction.is_extraction_validated(
        {"status": extraction.VALIDATED_STATUS, "mode": "strict", "raw_dir": chr(0)}
    )
    assert_all_fallback(load_barrier_table(tmp_path))


@pytest.mark.parametrize("tampering", ["duplicate", "extra", "wrong_hash", "wrong_cell", "wrong_value",
                                       "boolean_row", "unknown_field", "missing_state", "stale_bytes"])
def test_saved_payload_is_replayed_against_sources(reviewed_fixture, tmp_path, tampering):
    payload = extraction.extraction_payload(tmp_path)
    assert extraction.is_extraction_validated(payload)
    r = payload["records"][0]
    if tampering == "duplicate":
        payload["records"][1] = copy.deepcopy(r)
    elif tampering == "extra":
        payload["records"].append(copy.deepcopy(r))
    elif tampering == "wrong_hash":
        payload["checksums"][r["source_file"]] = "a" * 64
    elif tampering == "wrong_cell":
        r["minimum"]["energy_cell"] = "B9"
    elif tampering == "wrong_value":
        r["barrier_pj"] = float("nan")
    elif tampering == "boolean_row":
        r["row"] = True
    elif tampering == "unknown_field":
        r["additional"] = "unreviewed"
    elif tampering == "missing_state":
        del r["state"]
    else:
        (tmp_path / FILES["ed9"]).unlink()
    assert not extraction.is_extraction_validated(payload)


def test_candidate_manifest_never_promotes_itself(tmp_path, monkeypatch):
    manifest = make_example(tmp_path)
    source = tmp_path / "manifest.json"
    source.write_text(json.dumps(manifest))
    artifact = tmp_path / "candidate.json"
    monkeypatch.setattr("sys.argv", ["extraction", "--raw", str(tmp_path), "--candidate-manifest",
                                   str(source), "--out", str(artifact)])
    extraction.main()
    data = json.loads(artifact.read_text())
    assert data["status"] == "candidate_only" and len(data["candidate_records"]) == 3
    assert data["records"] == [] and not extraction.is_extraction_validated(data)
    assert_all_fallback(load_barrier_table(tmp_path))


def test_actual_publisher_files_do_not_promote_ambiguous_physical_units(tmp_path):
    payload = extraction.write_extraction_artifact(RAW, tmp_path / "actual.json")
    assert payload["status"] == "physical_unit_unresolved"
    assert payload["extracted_count"] == 0 and len(payload["checksums"]) == 2
    assert len(set(payload["checksums"].values())) == 1
    assert not extraction.is_extraction_validated(payload)
    assert_all_fallback(load_barrier_table(RAW))
    with write_extraction_comparison_csv(tmp_path / "report.csv", RAW).open() as stream:
        assert {row["replacement_applied"] for row in csv.DictReader(stream)} == {"false"}


def test_default_cli_finds_bundled_publisher_pair(tmp_path, monkeypatch):
    output = tmp_path / "extraction.json"
    monkeypatch.chdir(RAW.parents[2])
    monkeypatch.setattr("sys.argv", ["extraction", "--out", str(output)])
    extraction.main()
    payload = json.loads(output.read_text())
    assert payload["raw_dir"] == "data/raw"
    assert payload["status"] == "physical_unit_unresolved"
    assert payload["records"] == [] and payload["extracted_count"] == 0
    assert len(payload["checksums"]) == 2
    assert payload["source_audit"] == extraction.extraction_payload(RAW)["source_audit"]
    assert load_barrier_table()["status"] == payload["status"]
    assert_all_fallback(load_barrier_table())


def test_reviewed_pair_accepts_raw_root_or_attachment_directory(tmp_path, monkeypatch):
    directory = tmp_path / "nature_source_data"
    manifest = make_example(directory)
    monkeypatch.setattr(extraction, "_APPROVED_MANIFEST_JSON", json.dumps(manifest))
    nested = extraction.extraction_payload(tmp_path)
    direct = extraction.extraction_payload(directory)
    assert nested["extracted_count"] == 3
    assert nested["records"] == direct["records"]
    assert extraction.collect_raw_file_checksums(tmp_path) == extraction.collect_raw_file_checksums(directory)

    (tmp_path / FILES["ed9"]).write_bytes(b"competing copy")
    assert not extraction.is_extraction_validated(nested)
    assert extraction.is_extraction_validated(direct)
    assert_all_fallback(load_barrier_table(tmp_path))
    assert "Ambiguous" in extraction.extraction_payload(tmp_path)["reason"]
    assert extraction.extraction_payload(tmp_path)["checksums"] == {}


@pytest.mark.parametrize("layout", ["split", "competing"])
def test_ambiguous_publisher_layout_never_returns_a_partial_audit(tmp_path, layout):
    directory = tmp_path / "nature_source_data"
    directory.mkdir()
    for slot, filename in FILES.items():
        dest = tmp_path if layout == "split" and slot == "fig5" else directory
        (dest / filename).write_bytes((RAW / filename).read_bytes())
    if layout == "competing":
        (tmp_path / FILES["fig5"]).write_bytes(b"competing copy")
    payload = extraction.extraction_payload(tmp_path)
    assert payload["status"] == "pending"
    assert "Ambiguous" in payload["reason"]
    assert payload["checksums"] == {} and payload["records"] == []
    assert "source_audit" not in payload


def test_diagnostic_checksums_are_atomic_for_missing_second_file(tmp_path):
    (tmp_path / FILES["fig5"]).write_bytes(b"source")
    assert extraction.collect_raw_file_checksums(tmp_path) == {}


def test_invalid_write_preserves_last_complete_json(tmp_path, monkeypatch):
    dest = tmp_path / "result.json"
    dest.write_bytes(b'{"old":true}')
    def fail(*args, **kwargs):
        raise OSError("injected failure before rename")
    monkeypatch.setattr(extraction.os, "replace", fail)
    with pytest.raises(OSError):
        extraction.write_extraction_artifact(tmp_path, dest)
    assert dest.read_bytes() == b'{"old":true}'
    assert list(tmp_path.iterdir()) == [dest]

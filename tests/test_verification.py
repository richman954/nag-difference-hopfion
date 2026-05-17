from nagdiff.verification import evaluate_extraction_gate, write_extraction_status


def test_gate_fails_without_raw_files(tmp_path):
    status = evaluate_extraction_gate(raw_dir=tmp_path)
    assert status["gate_passed"] is False
    assert status["table_mode"] == "fallback"


def test_gate_passes_with_complete_strict_inputs(tmp_path):
    (tmp_path / "MOESM13.csv").write_text("h,v\na,2.24e-4\nb,2.86e-4\n", encoding="utf-8")
    (tmp_path / "MOESM16.csv").write_text("h,v\na,7.32e-4\n", encoding="utf-8")
    (tmp_path / "moesm_strict_mapping.json").write_text(
        """{
  "states": {
    "skyrmion_antiskyrmion_merge_to_hopfion": {"file": "MOESM13.csv", "row": 2, "column": 2},
    "hopfion_collapse": {"file": "MOESM13.csv", "row": 3, "column": 2},
    "hopfion_escape": {"file": "MOESM16.csv", "row": 2, "column": 2}
  }
}""",
        encoding="utf-8",
    )
    status = evaluate_extraction_gate(raw_dir=tmp_path)
    assert status["gate_passed"] is True
    assert status["extracted_count"] == 3


def test_write_extraction_status_file(tmp_path):
    out = tmp_path / "EXTRACTION_STATUS.md"
    write_extraction_status(raw_dir=tmp_path, out_path=out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "gate_passed" in text

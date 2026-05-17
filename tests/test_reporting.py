from nagdiff.reporting import write_extraction_comparison_csv


def test_write_extraction_comparison_csv(tmp_path):
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
    out = tmp_path / "comparison.csv"
    write_extraction_comparison_csv(out, raw_dir=tmp_path, extraction_mode="strict")
    text = out.read_text(encoding="utf-8")
    assert "replacement_applied" in text
    assert "skyrmion_antiskyrmion_merge_to_hopfion" in text


def test_write_extraction_comparison_csv_uses_mapping_path(tmp_path):
    (tmp_path / "MOESM13.csv").write_text("h,v\na,2.24e-4\nb,2.86e-4\n", encoding="utf-8")
    (tmp_path / "MOESM16.csv").write_text("h,v\na,7.32e-4\n", encoding="utf-8")
    mapping = tmp_path / "custom_map.json"
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

    out = tmp_path / "comparison.csv"
    write_extraction_comparison_csv(out, raw_dir=tmp_path, extraction_mode="strict", mapping_path=mapping)
    text = out.read_text(encoding="utf-8")
    assert "extracted_from_raw_moesm" in text
    assert "true" in text

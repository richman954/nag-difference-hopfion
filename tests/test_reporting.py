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


def test_write_extraction_comparison_csv_injection_mitigation(tmp_path, monkeypatch):
    import nagdiff.hopfion_terms

    def mock_load_barrier_table(*args, **kwargs):
        return {
            "mode": "extracted",
            "seeded_records": [
                {"state": "state_1", "barrier_pj": 1.0},
            ],
            "records": [
                {
                    "state": "state_1",
                    "barrier_pj": 1.5,
                    "provenance_status": "extracted_from_raw_moesm",
                    "source_file": "=cmd|' /C calc'!A0",
                    "sheet_name": "+malicious",
                    "row": "-1",
                    "column": "@evil",
                }
            ],
            "extracted_count": 1,
        }

    import nagdiff.reporting
    monkeypatch.setattr(nagdiff.reporting, "load_barrier_table", mock_load_barrier_table)

    out = tmp_path / "comparison_safe.csv"
    write_extraction_comparison_csv(out, raw_dir=tmp_path, extraction_mode="strict")
    text = out.read_text(encoding="utf-8")

    assert "'=cmd|' /C calc'!A0" in text
    assert "'+malicious" in text
    assert "'-1" in text
    assert "'@evil" in text

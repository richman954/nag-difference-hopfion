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
    write_extraction_comparison_csv(out, raw_dir=tmp_path, extraction_mode="heuristic")
    text = out.read_text(encoding="utf-8")
    assert "replacement_applied" in text
    assert "skyrmion_antiskyrmion_merge_to_hopfion" in text

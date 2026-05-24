from nagdiff.reporting import prepare_extraction_comparison_rows, write_extraction_comparison_csv


def test_prepare_extraction_comparison_rows(tmp_path):
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
    rows = prepare_extraction_comparison_rows(raw_dir=tmp_path, extraction_mode="strict")
    # Verify the header is correct
    assert rows[0] == [
        "state",
        "seeded_barrier_pj",
        "active_barrier_pj",
        "delta_pj",
        "provenance_status",
        "replacement_applied",
        "source_file",
        "sheet_name",
        "row",
        "column",
    ]
    # Check that at least one row was processed
    assert len(rows) > 1
    # Check some properties of the processed rows
    found = False
    for row in rows[1:]:
        if row[0] == "skyrmion_antiskyrmion_merge_to_hopfion":
            found = True
            break
    assert found

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

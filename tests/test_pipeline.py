from nagdiff.pipeline import run_checkpoint_pipeline


def test_run_checkpoint_pipeline_outputs_artifacts(tmp_path):
    (tmp_path / "MOESM13.csv").write_text("h,v\na,2.24e-4\nb,2.86e-4\n", encoding="utf-8")
    (tmp_path / "MOESM16.csv").write_text("h,v\na,7.32e-4\n", encoding="utf-8")
    mapping = tmp_path / "map.json"
    mapping.write_text(
        """{
  "states": {
    "skyrmion_antiskyrmion_merge_to_hopfion": {"file": "MOESM13.csv", "row": 2, "column": 2},
    "hopfion_collapse": {"file": "MOESM13.csv", "row": 3, "column": 2},
    "hopfion_escape": {"file": "MOESM16.csv", "row": 2, "column": 2}
  }
}""",
        encoding="utf-8",
    )

    artifact = tmp_path / "extracted_barriers.json"
    comparison = tmp_path / "extraction_comparison.csv"
    result = run_checkpoint_pipeline(
        raw_dir=tmp_path,
        extraction_mode="strict",
        mapping_path=mapping,
        artifact_out=artifact,
        comparison_out=comparison,
    )

    assert result["extracted_count"] == 3
    assert result["table_mode"] == "extracted"
    assert artifact.exists()
    assert comparison.exists()

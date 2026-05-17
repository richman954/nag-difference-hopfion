from __future__ import annotations

from pathlib import Path

from nagdiff.extraction import write_extraction_artifact
from nagdiff.hopfion_terms import load_barrier_table
from nagdiff.reporting import write_extraction_comparison_csv


def run_checkpoint_pipeline(
    raw_dir: str | Path = "data/raw",
    extraction_mode: str = "strict",
    mapping_path: str | Path = "data/raw/moesm_strict_mapping.json",
    artifact_out: str | Path = "data/processed/extracted_barriers.json",
    comparison_out: str | Path = "data/processed/extraction_comparison.csv",
) -> dict[str, object]:
    artifact = write_extraction_artifact(
        raw_dir=raw_dir,
        out_path=artifact_out,
        mode=extraction_mode,
        mapping_path=mapping_path,
    )
    comparison_path = write_extraction_comparison_csv(
        out_csv=comparison_out,
        raw_dir=raw_dir,
        extraction_mode=extraction_mode,
    )
    table = load_barrier_table(raw_dir=raw_dir, extraction_mode=extraction_mode)
    return {
        "mode": extraction_mode,
        "artifact_path": str(artifact_out),
        "comparison_path": str(comparison_path),
        "extracted_count": table["extracted_count"],
        "table_mode": table["mode"],
        "checksums_count": len(artifact.get("checksums", {})),
    }

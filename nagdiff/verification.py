from __future__ import annotations

from pathlib import Path

from nagdiff.pipeline import run_checkpoint_pipeline


def evaluate_extraction_gate(
    raw_dir: str | Path = "data/raw",
    mapping_path: str | Path = "data/raw/moesm_strict_mapping.json",
) -> dict[str, object]:
    result = run_checkpoint_pipeline(raw_dir=raw_dir, mapping_path=mapping_path)
    passed = result["table_mode"] == "extracted" and result["extracted_count"] == 3
    return {
        **result,
        "gate_passed": passed,
        "gate_reason": "all three target barriers extracted in strict mode" if passed else "incomplete strict extraction; seeded fallback still active",
    }


def write_extraction_status(
    raw_dir: str | Path = "data/raw",
    out_path: str | Path = "data/processed/EXTRACTION_STATUS.md",
    mapping_path: str | Path = "data/raw/moesm_strict_mapping.json",
) -> Path:
    status = evaluate_extraction_gate(raw_dir=raw_dir, mapping_path=mapping_path)
    lines = [
        "# Extraction Status",
        "",
        "## Current status",
        "",
    ]
    if status["gate_passed"]:
        lines += [
            "**Strict extraction completed for all target barriers; verification review pending.**",
            "",
            "Seeded fallback table is retained for audit comparison.",
        ]
    else:
        lines += [
            "**Raw MOESM spreadsheet extraction is still pending/incomplete in strict mode.**",
            "",
            "Seeded barrier values remain provisional and are **raw MOESM verification pending** (`raw_moesm_verification_pending`).",
        ]
    lines += [
        "",
        "## Gate report",
        "",
        f"- mode: `{status['mode']}`",
        f"- extracted_count: `{status['extracted_count']}`",
        f"- table_mode: `{status['table_mode']}`",
        f"- checksums_count: `{status['checksums_count']}`",
        f"- gate_passed: `{str(status['gate_passed']).lower()}`",
        f"- gate_reason: {status['gate_reason']}",
        "",
        "## Notes",
        "",
        "Do not treat extracted values as final publication values until manual source-level verification is complete.",
    ]
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p

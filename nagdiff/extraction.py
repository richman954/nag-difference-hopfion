"""Atomic barrier extraction and replay for the Chen et al. benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, fields
from pathlib import Path

from .barrier_workbooks import (
    FILES, WorkbookError, extract_workbooks, load_manifest, normalize_to_pj, resolve_workbook_directory,
)


# A future reviewed release can pin a literal mapping here after its dimensions
# and MEP assignments have been reconciled with the publisher. This trust data
# belongs to the package. A manifest in the input directory cannot set it.
_APPROVED_MANIFEST_JSON: str | None = None
VALIDATED_STATUS = "validated_publisher_workbooks"
TARGETS = (
    "skyrmion_antiskyrmion_merge_to_hopfion", "hopfion_collapse", "hopfion_escape",
)


@dataclass
class ExtractedBarrier:
    state: str
    barrier_pj: float
    source_file: str
    sheet_name: str
    row: int
    column: int
    unit: str
    extraction_method: str
    notes: str
    doi: str
    figure: str
    source_url: str
    retrieved_on: str
    sha256: str
    source_unit: str
    energy_header: dict
    coordinate_header: dict
    branch_rows: list
    minimum: dict
    saddle: dict
    barrier_pj_decimal: str


def _normalize_to_pj(val, unit):
    """Conversion requires a declared unit, including for zero or negative energies."""
    return normalize_to_pj(val, unit)


def extraction_payload(raw_dir: str | Path, mode: str = "auto") -> dict:
    """Build a complete comparison snapshot. Never release a partial table."""
    if mode not in ("auto", "strict", "heuristic"):
        raise ValueError(f"unknown extraction mode: {mode!r}")
    payload = {
        "raw_dir": str(raw_dir), "mode": mode, "status": "pending",
        "extracted_count": 0, "checksums": {}, "records": [],
    }
    if mode == "heuristic":
        payload["reason"] = "A keyword match does not establish a physical barrier."
        return payload
    if _APPROVED_MANIFEST_JSON is None:
        from .chen2026_audit import AuditError, audit_publisher_pair

        try:
            audit = audit_publisher_pair(Path(raw_dir))
        except AuditError as exc:
            payload["reason"] = str(exc)
            return payload
        payload.update(status=audit["status"], source_audit=audit,
                       checksums={s["filename"]: s["sha256"] for s in audit["sources"]},
                       reason="Energy headers and figure axes say pJ. The density unit is missing "
                              "and the volume-based worksheet formula divides by 1e-15.")
        return payload

    manifest = json.loads(_APPROVED_MANIFEST_JSON)
    try:
        records = extract_workbooks(Path(raw_dir), manifest)
    except WorkbookError as exc:
        payload["reason"] = str(exc)
        return payload
    payload.update(status=VALIDATED_STATUS, extracted_count=len(records), records=records,
                   checksums={r["source_file"]: r["sha256"] for r in records})
    return payload


def collect_raw_file_checksums(raw_dir: str | Path = "data/raw") -> dict[str, str]:
    """Diagnostic hashes for a complete publisher-named pair. A digest alone grants no trust."""
    directory = resolve_workbook_directory(raw_dir)
    checksums = {}
    for filename in FILES.values():
        path = directory / filename
        try:
            data = path.read_bytes()
        except (FileNotFoundError, NotADirectoryError):
            return {}
        checksums[str(path)] = hashlib.sha256(data).hexdigest()
    return checksums


def extract_barriers_from_raw(raw_dir: str | Path = "data/raw", mode: str = "auto") -> list[ExtractedBarrier]:
    records = extraction_payload(raw_dir, mode)["records"]
    keys = [f.name for f in fields(ExtractedBarrier)]
    return [ExtractedBarrier(**{key: row[key] for key in keys}) for row in records]


def is_extraction_validated(payload: object) -> bool:
    """Reproduce an exported artifact from pinned source bytes before trusting it."""
    if not isinstance(payload, dict) or payload.get("status") != VALIDATED_STATUS:
        return False
    if not isinstance(payload.get("raw_dir"), str) or payload.get("mode") not in ("auto", "strict"):
        return False
    canonical = extraction_payload(payload["raw_dir"], payload["mode"])
    if canonical["status"] != VALIDATED_STATUS:
        return False
    try:
        # JSON comparison distinguishes true from 1, rejects NaN, and checks
        # every endpoint and hash as well as array cardinality and order.
        return json.dumps(payload, sort_keys=True, allow_nan=False) == json.dumps(
            canonical, sort_keys=True, allow_nan=False
        )
    except (TypeError, ValueError):
        return False


def _write_json(out_path: str | Path, data: dict) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=out.parent, delete=False) as tmp:
            tmp_name = tmp.name
            json.dump(data, tmp, indent=2, allow_nan=False)
            tmp.write("\n")
        os.replace(tmp_name, out)
    finally:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)


def write_extraction_artifact(raw_dir: str | Path, out_path: str | Path, mode: str = "auto") -> dict:
    payload = extraction_payload(raw_dir, mode)
    _write_json(out_path, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract benchmark barriers from reviewed workbooks.")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--out", default="data/processed/extracted_barriers.json")
    parser.add_argument("--mode", default="auto", choices=["auto", "strict", "heuristic"])
    parser.add_argument("--candidate-manifest", help="Check a proposed literal-cell mapping offline.")
    args = parser.parse_args()
    if args.candidate_manifest:
        if args.mode == "heuristic":
            parser.error("candidate review requires explicit mappings")
        try:
            records = extract_workbooks(Path(args.raw), load_manifest(Path(args.candidate_manifest)))
        except WorkbookError as exc:
            parser.exit(2, f"Candidate rejected: {exc}\n")
        payload = {"status": "candidate_only", "extracted_count": 0, "records": [],
                   "candidate_records": records}
        _write_json(args.out, payload)
    else:
        payload = write_extraction_artifact(args.raw, args.out, args.mode)
    print(f"{payload['status']}: {payload['extracted_count']} validated records; {args.out}")


if __name__ == "__main__":
    main()

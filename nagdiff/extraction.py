from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

TARGETS = {
    "skyrmion_antiskyrmion_merge_to_hopfion": ["skyrmion", "antiskyrmion", "merge", "hopfion"],
    "hopfion_collapse": ["hopfion", "collapse"],
    "hopfion_escape": ["hopfion", "escape"],
}

STRICT_CSV_MAPPING = {
    "skyrmion_antiskyrmion_merge_to_hopfion": {"file": "MOESM13.csv", "row": 2, "column": 2},
    "hopfion_collapse": {"file": "MOESM13.csv", "row": 3, "column": 2},
    "hopfion_escape": {"file": "MOESM16.csv", "row": 2, "column": 2},
}

NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


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


def _iter_moesm_files(raw_dir: Path) -> Iterable[Path]:
    patterns = ["MOESM13*.csv", "MOESM16*.csv", "MOESM13/*.csv", "MOESM16/*.csv"]
    seen: set[Path] = set()
    for pattern in patterns:
        for p in raw_dir.glob(pattern):
            if p.is_file() and p not in seen:
                seen.add(p)
                yield p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _normalize_to_pj(val: float) -> float:
    if val > 1e-2:
        return val * 1e-12
    return val


def collect_raw_file_checksums(raw_dir: str | Path = "data/raw") -> dict[str, str]:
    raw_path = Path(raw_dir)
    return {str(file): _sha256(file) for file in _iter_moesm_files(raw_path)}


def _extract_strict_csv(raw_dir: Path, file_contents: dict[Path, str]) -> list[ExtractedBarrier]:
    results: list[ExtractedBarrier] = []
    parsed_files = {}
    for state, spec in STRICT_CSV_MAPPING.items():
        file = raw_dir / spec["file"]
        if file not in file_contents:
            continue
        if file not in parsed_files:
            parsed_files[file] = list(csv.reader(io.StringIO(file_contents[file], newline="")))
        rows = parsed_files[file]
        r = spec["row"] - 1
        c = spec["column"] - 1
        if r >= len(rows) or c >= len(rows[r]):
            continue
        match = NUM_RE.search(rows[r][c])
        if not match:
            continue
        val = _normalize_to_pj(float(match.group(0)))
        results.append(
            ExtractedBarrier(
                state=state,
                barrier_pj=val,
                source_file=str(file),
                sheet_name=file.stem,
                row=spec["row"],
                column=spec["column"],
                unit="pJ",
                extraction_method="strict_csv_mapping",
                notes="Extracted via deterministic file/row/column mapping.",
            )
        )
    return results


def _extract_keyword_csv(raw_dir: Path, file_contents: dict[Path, str]) -> list[ExtractedBarrier]:
    results: dict[str, ExtractedBarrier] = {}
    for file, text_content in file_contents.items():
        with io.StringIO(text_content, newline="") as fh:
            reader = csv.reader(fh)
            for r_idx, row in enumerate(reader, start=1):
                for c_idx, cell in enumerate(row, start=1):
                    text = (cell or "").strip().lower()
                    if not text:
                        continue
                    for state, keywords in TARGETS.items():
                        if state in results:
                            continue
                        if all(k in text for k in keywords):
                            for scan_c in range(c_idx, min(c_idx + 6, len(row) + 1)):
                                m = NUM_RE.search(row[scan_c - 1])
                                if not m:
                                    continue
                                val = _normalize_to_pj(float(m.group(0)))
                                results[state] = ExtractedBarrier(
                                    state=state,
                                    barrier_pj=val,
                                    source_file=str(file),
                                    sheet_name=file.stem,
                                    row=r_idx,
                                    column=scan_c,
                                    unit="pJ",
                                    extraction_method="keyword_row_scan_csv",
                                    notes="Extracted from MOESM raw CSV by keyword and nearest numeric cell.",
                                )
                                break
    return [results[s] for s in TARGETS if s in results]


def extract_barriers_and_checksums(raw_dir: str | Path = "data/raw", mode: str = "auto") -> tuple[list[ExtractedBarrier], dict[str, str]]:
    raw_path = Path(raw_dir)
    checksums: dict[str, str] = {}
    file_contents: dict[Path, str] = {}

    for file in _iter_moesm_files(raw_path):
        data = file.read_bytes()
        checksums[str(file)] = hashlib.sha256(data).hexdigest()
        file_contents[file] = data.decode("utf-8")

    if mode == "strict":
        return _extract_strict_csv(raw_path, file_contents), checksums
    if mode == "heuristic":
        return _extract_keyword_csv(raw_path, file_contents), checksums

    strict_records = _extract_strict_csv(raw_path, file_contents)
    if len(strict_records) == len(TARGETS):
        return strict_records, checksums
    return _extract_keyword_csv(raw_path, file_contents), checksums


def extract_barriers_from_raw(raw_dir: str | Path = "data/raw", mode: str = "auto") -> list[ExtractedBarrier]:
    records, _ = extract_barriers_and_checksums(raw_dir, mode)
    return records


def is_extraction_validated(payload: dict[str, object]) -> bool:
    if payload.get("extracted_count", 0) != len(TARGETS):
        return False
    records = payload.get("records", [])
    if not records:
        return False
    if not payload.get("checksums"):
        return False

    expected_states = set(TARGETS.keys())
    found_states = set()

    required_fields = ["source_file", "sheet_name", "row", "column", "unit", "extraction_method", "notes"]

    for record in records:
        if record.get("extraction_method") == "seeded_fallback":
            return False
        for field in required_fields:
            if field not in record or record[field] in (None, ""):
                return False
        found_states.add(record.get("state"))

    if expected_states != found_states:
        return False

    return True


def write_extraction_artifact(raw_dir: str | Path, out_path: str | Path, mode: str = "auto") -> dict[str, object]:
    extracted, checksums = extract_barriers_and_checksums(raw_dir, mode=mode)
    payload = {
        "raw_dir": str(raw_dir),
        "mode": mode,
        "extracted_count": len(extracted),
        "checksums": checksums,
        "records": [asdict(row) for row in extracted],
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract hopfion barriers from raw MOESM CSV files.")
    parser.add_argument("--raw", default="data/raw", help="Raw data directory")
    parser.add_argument("--out", default="data/processed/extracted_barriers.json", help="Output JSON artifact path")
    parser.add_argument("--mode", default="auto", choices=["auto", "strict", "heuristic"], help="Extraction mode")
    args = parser.parse_args()
    payload = write_extraction_artifact(args.raw, args.out, mode=args.mode)
    print(f"wrote {args.out} with {payload['extracted_count']} extracted records (mode={args.mode})")


if __name__ == "__main__":
    main()

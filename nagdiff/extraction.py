from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

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


def _extract_strict_csv(raw_dir: Path) -> list[ExtractedBarrier]:
    results: list[ExtractedBarrier] = []
    for state, spec in STRICT_CSV_MAPPING.items():
        file = raw_dir / spec["file"]
        if not file.exists():
            continue
        rows = list(csv.reader(file.open("r", encoding="utf-8", newline="")))
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


def extract_barriers_from_raw(raw_dir: str | Path = "data/raw") -> list[ExtractedBarrier]:
    raw_path = Path(raw_dir)
    return _extract_strict_csv(raw_path)


def write_extraction_artifact(raw_dir: str | Path, out_path: str | Path) -> dict[str, object]:
    extracted = extract_barriers_from_raw(raw_dir)
    payload = {
        "raw_dir": str(raw_dir),
        "mode": "strict",
        "extracted_count": len(extracted),
        "checksums": collect_raw_file_checksums(raw_dir),
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
    args = parser.parse_args()
    payload = write_extraction_artifact(args.raw, args.out)
    print(f"wrote {args.out} with {payload['extracted_count']} extracted records (mode=strict)")


if __name__ == "__main__":
    main()

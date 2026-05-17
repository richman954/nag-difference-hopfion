from __future__ import annotations

import argparse
import csv
import hashlib
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
    patterns = [
        "MOESM13*.csv",
        "MOESM16*.csv",
        "MOESM13/*.csv",
        "MOESM16/*.csv",
    ]
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


def collect_raw_file_checksums(raw_dir: str | Path = "data/raw") -> dict[str, str]:
    raw_path = Path(raw_dir)
    checksums: dict[str, str] = {}
    for file in _iter_moesm_files(raw_path):
        checksums[str(file)] = _sha256(file)
    return checksums


def extract_barriers_from_raw(raw_dir: str | Path = "data/raw") -> list[ExtractedBarrier]:
    raw_path = Path(raw_dir)
    results: dict[str, ExtractedBarrier] = {}

    for file in _iter_moesm_files(raw_path):
        with file.open("r", encoding="utf-8", newline="") as fh:
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
                                candidate = row[scan_c - 1]
                                m = NUM_RE.search(candidate)
                                if not m:
                                    continue
                                val = float(m.group(0))
                                if val > 1e-2:
                                    val = val * 1e-12
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


def write_extraction_artifact(raw_dir: str | Path, out_path: str | Path) -> dict[str, object]:
    extracted = extract_barriers_from_raw(raw_dir)
    payload = {
        "raw_dir": str(raw_dir),
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
    parser.add_argument(
        "--out",
        default="data/processed/extracted_barriers.json",
        help="Output JSON artifact path",
    )
    args = parser.parse_args()
    payload = write_extraction_artifact(args.raw, args.out)
    print(f"wrote {args.out} with {payload['extracted_count']} extracted records")


if __name__ == "__main__":
    main()

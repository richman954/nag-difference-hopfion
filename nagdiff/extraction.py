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

DEFAULT_STRICT_MAPPING_PATH = Path("data/raw/moesm_strict_mapping.json")

NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _validate_mapping_state_spec(state: str, spec: object) -> dict[str, object]:
    if not isinstance(spec, dict):
        raise ValueError(f"invalid mapping for state '{state}': expected object spec")

    required = {"file", "row", "column"}
    missing = required.difference(spec.keys())
    if missing:
        missing_txt = ", ".join(sorted(missing))
        raise ValueError(f"invalid mapping for state '{state}': missing fields: {missing_txt}")

    file = spec["file"]
    row = spec["row"]
    column = spec["column"]
    unit = spec.get("unit", "pJ")
    if not isinstance(file, str) or not file.strip():
        raise ValueError(f"invalid mapping for state '{state}': file must be a non-empty string")
    if not isinstance(row, int) or row < 1:
        raise ValueError(f"invalid mapping for state '{state}': row must be a 1-indexed positive integer")
    if not isinstance(column, int) or column < 1:
        raise ValueError(f"invalid mapping for state '{state}': column must be a 1-indexed positive integer")
    if not isinstance(unit, str) or unit not in {"pJ", "fJ", "aJ"}:
        raise ValueError(f"invalid mapping for state '{state}': unit must be one of pJ, fJ, aJ")

    return {"file": file, "row": row, "column": column, "unit": unit}


def load_strict_mapping(path: str | Path = DEFAULT_STRICT_MAPPING_PATH) -> dict[str, dict[str, object]]:
    p = Path(path)
    if not p.exists():
        return {}

    payload = json.loads(p.read_text(encoding="utf-8"))
    states = payload.get("states", {})
    if not isinstance(states, dict):
        raise ValueError("invalid strict mapping: top-level 'states' must be an object")

    validated: dict[str, dict[str, object]] = {}
    for state, spec in states.items():
        if state not in TARGETS:
            continue
        validated[state] = _validate_mapping_state_spec(state, spec)

    return validated


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


def _normalize_to_pj(val: float, unit: str = "pJ") -> float:
    if unit == "pJ":
        return val
    if unit == "fJ":
        return val * 1e-3
    if unit == "aJ":
        return val * 1e-6
    raise ValueError(f"unsupported unit: {unit}")


def collect_raw_file_checksums(raw_dir: str | Path = "data/raw") -> dict[str, str]:
    raw_path = Path(raw_dir)
    files = sorted(_iter_moesm_files(raw_path), key=lambda p: str(p))
    return {str(file): _sha256(file) for file in files}


def _extract_strict_csv(raw_dir: Path, mapping_path: str | Path = DEFAULT_STRICT_MAPPING_PATH) -> list[ExtractedBarrier]:
    results: list[ExtractedBarrier] = []
    strict_mapping = load_strict_mapping(mapping_path)
    for state, spec in strict_mapping.items():
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
        val = _normalize_to_pj(float(match.group(0)), unit=spec["unit"])
        results.append(
            ExtractedBarrier(
                state=state,
                barrier_pj=val,
                source_file=str(file),
                sheet_name=file.stem,
                row=spec["row"],
                column=spec["column"],
                unit=spec["unit"],
                extraction_method="strict_csv_mapping",
                notes="Extracted via deterministic file/row/column mapping.",
            )
        )
    return results


def _extract_keyword_csv(raw_dir: Path) -> list[ExtractedBarrier]:
    results: dict[str, ExtractedBarrier] = {}
    for file in _iter_moesm_files(raw_dir):
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
                                m = NUM_RE.search(row[scan_c - 1])
                                if not m:
                                    continue
                                val = _normalize_to_pj(float(m.group(0)), unit="pJ")
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


def extract_barriers_from_raw(raw_dir: str | Path = "data/raw", mode: str = "strict", mapping_path: str | Path = DEFAULT_STRICT_MAPPING_PATH) -> list[ExtractedBarrier]:
    raw_path = Path(raw_dir)
    if mode == "strict":
        return _extract_strict_csv(raw_path, mapping_path=mapping_path)
    if mode == "heuristic":
        return _extract_keyword_csv(raw_path)
    if mode != "auto":
        raise ValueError("mode must be one of: strict, heuristic, auto")

    strict_records = _extract_strict_csv(raw_path, mapping_path=mapping_path)
    if len(strict_records) == len(TARGETS):
        return strict_records
    return _extract_keyword_csv(raw_path)


def write_extraction_artifact(raw_dir: str | Path, out_path: str | Path, mode: str = "strict", mapping_path: str | Path = DEFAULT_STRICT_MAPPING_PATH) -> dict[str, object]:
    extracted = extract_barriers_from_raw(raw_dir, mode=mode, mapping_path=mapping_path)
    payload = {
        "raw_dir": str(Path(raw_dir)),
        "mode": mode,
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
    parser.add_argument("--mode", default="strict", choices=["auto", "strict", "heuristic"], help="Extraction mode (strict recommended)")
    parser.add_argument("--mapping", default=str(DEFAULT_STRICT_MAPPING_PATH), help="Strict mapping JSON path")
    args = parser.parse_args()
    payload = write_extraction_artifact(args.raw, args.out, mode=args.mode, mapping_path=args.mapping)
    print(f"wrote {args.out} with {payload['extracted_count']} extracted records (mode={args.mode})")


if __name__ == "__main__":
    main()

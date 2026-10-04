from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

TARGETS = {
    "skyrmion_antiskyrmion_merge_to_hopfion": [
        "skyrmion",
        "antiskyrmion",
        "merge",
        "hopfion",
    ],
    "hopfion_collapse": ["hopfion", "collapse"],
    "hopfion_escape": ["hopfion", "escape"],
}

TARGET_SOURCE = {
    "skyrmion_antiskyrmion_merge_to_hopfion": "MOESM13",
    "hopfion_collapse": "MOESM13",
    "hopfion_escape": "MOESM16",
}

STRICT_CSV_MAPPING = {
    "skyrmion_antiskyrmion_merge_to_hopfion": {
        "file": "MOESM13.csv",
        "row": 2,
        "column": 2,
    },
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
    patterns = [
        "MOESM13*.csv",
        "MOESM16*.csv",
        "MOESM13/*.csv",
        "MOESM16/*.csv",
        "MOESM13*.xlsx",
        "MOESM16*.xlsx",
        "MOESM13/*.xlsx",
        "MOESM16/*.xlsx",
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


def _normalize_to_pj(val: float) -> float:
    if val > 1e-2:
        return val * 1e-12
    return val


def _xlsx_rows(path: Path) -> Iterable[tuple[str, list[tuple[int, str]]]]:
    """Yield worksheet rows without requiring a heavyweight spreadsheet dependency."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    pkg_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"

    query_row = f".//{ns}row"
    query_c = f"{ns}c"
    query_v = f"{ns}v"
    query_is = f"{ns}is"
    col_re = re.compile(r"[A-Z]+")

    with zipfile.ZipFile(path) as book:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall(f"{ns}si")]

        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        relationships = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall(f"{pkg_ns}Relationship")
        }

        sheets_node = workbook.find(f"{ns}sheets")
        for sheet in (sheets_node if sheets_node is not None else []):
            sheet_name = sheet.attrib["name"]
            target = targets[sheet.attrib[f"{rel_ns}id"]].lstrip("/")
            member = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(book.read(member))
            for row in root.findall(query_row):
                cells: list[tuple[int, str]] = []
                for cell in row.findall(query_c):
                    letters = col_re.match(cell.attrib.get("r", "A"))
                    column = 0
                    for char in letters.group(0) if letters else "A":
                        column = column * 26 + ord(char) - 64
                    value = cell.find(query_v)
                    inline = cell.find(query_is)
                    text = "" if value is None else (value.text or "")
                    if cell.attrib.get("t") == "s" and text:
                        text = shared[int(text)]
                    elif inline is not None:
                        text = "".join(inline.itertext())
                    cells.append((column, text))
                yield sheet_name, cells


def _tabular_rows(path: Path) -> Iterable[tuple[str, int, list[tuple[int, str]]]]:
    if path.suffix.lower() == ".xlsx":
        counters: dict[str, int] = {}
        for sheet, cells in _xlsx_rows(path):
            counters[sheet] = counters.get(sheet, 0) + 1
            yield sheet, counters[sheet], cells
        return
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row_number, row in enumerate(csv.reader(fh), start=1):
            yield path.stem, row_number, list(enumerate(row, start=1))


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


def _extract_keyword_tables(raw_dir: Path) -> list[ExtractedBarrier]:
    results: dict[str, ExtractedBarrier] = {}
    for file in _iter_moesm_files(raw_dir):
        source_group = "MOESM13" if "moesm13" in str(file).lower() else "MOESM16"
        for sheet_name, r_idx, row in _tabular_rows(file):
            for position, (c_idx, cell) in enumerate(row):
                cell_text = (cell or "").strip().lower()
                if not cell_text:
                    continue
                for state, keywords in TARGETS.items():
                    if state in results or TARGET_SOURCE[state] != source_group:
                        continue
                    if all(keyword in cell_text for keyword in keywords):
                        for scan_c, candidate in row[position : position + 6]:
                            match = NUM_RE.search(candidate)
                            if not match:
                                continue
                            val = _normalize_to_pj(float(match.group(0)))
                            results[state] = ExtractedBarrier(
                                state=state,
                                barrier_pj=val,
                                source_file=str(file),
                                sheet_name=sheet_name,
                                row=r_idx,
                                column=scan_c,
                                unit="pJ",
                                extraction_method=f"keyword_row_scan_{file.suffix.lower().lstrip('.')}",
                                notes=(
                                    f"Extracted from raw {source_group} table by target keywords "
                                    "and nearest numeric cell; numeric value normalized to pJ."
                                ),
                            )
                            break
    return [results[s] for s in TARGETS if s in results]


def extract_barriers_from_raw(
    raw_dir: str | Path = "data/raw", mode: str = "auto"
) -> list[ExtractedBarrier]:
    raw_path = Path(raw_dir)
    if mode == "strict":
        return _extract_strict_csv(raw_path)
    if mode == "heuristic":
        return _extract_keyword_tables(raw_path)
    strict_records = _extract_strict_csv(raw_path)
    if len(strict_records) == len(TARGETS):
        return strict_records
    return _extract_keyword_tables(raw_path)


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

    required_fields = [
        "source_file",
        "sheet_name",
        "row",
        "column",
        "unit",
        "extraction_method",
        "notes",
    ]

    for record in records:
        if record.get("extraction_method") == "seeded_fallback":
            return False
        barrier = record.get("barrier_pj")
        if (
            not isinstance(barrier, (int, float))
            or not math.isfinite(barrier)
            or barrier <= 0
        ):
            return False
        for field in required_fields:
            if field not in record or record[field] in (None, ""):
                return False
        found_states.add(record.get("state"))

    if expected_states != found_states:
        return False

    return True


def write_extraction_artifact(
    raw_dir: str | Path, out_path: str | Path, mode: str = "auto"
) -> dict[str, object]:
    extracted = extract_barriers_from_raw(raw_dir, mode=mode)
    payload = {
        "raw_dir": str(raw_dir),
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
    parser = argparse.ArgumentParser(
        description="Extract hopfion barriers from raw MOESM CSV/XLSX tables."
    )
    parser.add_argument("--raw", default="data/raw", help="Raw data directory")
    parser.add_argument(
        "--out",
        default="data/processed/extracted_barriers.json",
        help="Output JSON artifact path",
    )
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "strict", "heuristic"],
        help="Extraction mode",
    )
    args = parser.parse_args()
    payload = write_extraction_artifact(args.raw, args.out, mode=args.mode)
    print(
        f"wrote {args.out} with {payload['extracted_count']} extracted records (mode={args.mode})"
    )


if __name__ == "__main__":
    main()

"""Read reviewed literal-numeric MEP paths. Callers decide which manifest is trusted.

Only the supported OOXML subset is accepted. In particular a formula cache is
never a substitute for checking its formula and physical dimensional scale.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import posixpath
import re
import zipfile
import zlib
from datetime import date
from decimal import Decimal, DecimalException, localcontext
from pathlib import Path
from xml.etree import ElementTree as ET

DOI = "10.1038/s41567-026-03236-0"
ROUTING = {
    "skyrmion_antiskyrmion_merge_to_hopfion": "fig5",
    "hopfion_collapse": "fig5",
    "hopfion_escape": "ed9",
}
FIGURES = {"fig5": "Source Data Fig. 5", "ed9": "Source Data Extended Data Fig. 9"}
# Original filenames resolved from the publisher's *labelled* article links.
PREFIX = "https://static-content.springer.com/esm/art%3A10.1038%2Fs41567-026-03236-0/MediaObjects/"
FILES = {"fig5": "41567_2026_3236_MOESM13_ESM.xlsx", "ed9": "41567_2026_3236_MOESM16_ESM.xlsx"}

PJ = {symbol: Decimal(1).scaleb(power) for symbol, power in
      {"J": 12, "mJ": 9, "uJ": 6, "nJ": 3, "pJ": 0, "fJ": -3, "aJ": -6, "zJ": -9, "yJ": -12}.items()}
PJ.update(eV=Decimal("1.602176634E-7"), meV=Decimal("1.602176634E-10"))
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?")
A1 = re.compile(r"([A-Z]{1,3})([1-9][0-9]{0,6})")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class WorkbookError(ValueError):
    """The input cannot support a complete, unambiguous barrier calculation."""


def resolve_workbook_directory(raw_dir: str | Path) -> Path:
    """Accept either the repository raw directory or a directory containing the pair."""
    root = Path(raw_dir)
    locations = []
    for directory in (root, root / "nature_source_data"):
        for filename in FILES.values():
            try:
                (directory / filename).lstat()
            except (FileNotFoundError, NotADirectoryError):
                continue
            except (OSError, ValueError) as exc:
                raise WorkbookError(f"Cannot inspect {directory / filename}: {exc}") from exc
            locations.append(directory)
            break
    if len(locations) > 1:
        raise WorkbookError(f"Ambiguous publisher workbook locations: {locations[0]} and {locations[1]}")
    return locations[0] if locations else root


def require(condition, message):
    if not condition:
        raise WorkbookError(message)


def _keys(obj, names, where):
    require(isinstance(obj, dict) and set(obj) == set(names), f"Wrong or missing keys in {where}")


def load_manifest(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate manifest key: {key}")
            result[key] = value
        return result
    try:
        data = json.loads(Path(path).read_text(encoding="utf8"), object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkbookError(f"Cannot read manifest: {exc}") from exc
    require(isinstance(data, dict), "Manifest must be an object")
    return data


def _decimal(value):
    require(type(value) in (str, int, float, Decimal), "Expected a finite number")
    text = str(value)
    require(len(text) <= 80 and NUMBER.fullmatch(text), f"Invalid numeric value: {text[:80]}")
    try:
        result = Decimal(text)
    except DecimalException as exc:
        raise WorkbookError("Invalid decimal") from exc
    require(-400 <= result.as_tuple().exponent <= 400, "Numerical exponent out of supported range")
    return result


def _unit_scale(unit):
    require(isinstance(unit, str), "An explicit energy unit is required")
    unit = unit.strip().replace("µ", "u").replace("μ", "u").replace("−", "-")
    pattern = r"(?:(?:×\s*)?10\^([+-]?[0-9]{1,2})\s*\*?\s*)?(" + "|".join(PJ) + r")"
    match = re.fullmatch(pattern, unit)
    require(match, f"Unknown or ambiguous energy unit: {unit!r}")
    return PJ[match[2]].scaleb(int(match[1] or 0))


def normalize_to_pj(value, unit):
    """Convert a finite explicit source magnitude to pJ. Never infer a unit."""
    with localcontext() as ctx:
        ctx.prec = 1100
        return _decimal(value) * _unit_scale(unit)


def _address(value):
    m = A1.fullmatch(value) if isinstance(value, str) else None
    require(m, f"Invalid A1 address: {value!r}")
    column = 0
    for letter in m[1]:
        column = 26 * column + ord(letter) - ord("A") + 1
    row = int(m[2])
    require(column <= 16384 and row <= 1048576, "Address outside Excel limits")
    return m[1], row, column


def _formula_bounds(formula, address):
    ref = formula.get("ref")
    if ref is None:
        require(formula.get("t") not in {"array", "dataTable"}, f"Missing formula range at {address}")
        return None
    first, separator, last = ref.partition(":")
    _, top, left = _address(first)
    _, bottom, right = _address(last if separator else first)
    _, row, column = _address(address)
    require(top <= row <= bottom and left <= column <= right, f"Invalid formula range at {address}")
    return top, bottom, left, right


def _workbook_cells(data, required_sheets):
    """Use stored A1 addresses and raw OOXML numeric strings, including sparse rows."""
    def strings(node):
        if node is None:
            return ""
        # Only text and rich-text runs are visible. Ignore phonetic annotations.
        parts = []
        for child in node:
            if child.tag == NS + "t":
                parts.append(child.text or "")
            elif child.tag == NS + "r":
                parts.append(child.findtext(NS + "t", ""))
        return "".join(parts)

    cells = {}
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        names = book.namelist()
        require(len(names) == len(set(names)), "Duplicate XLSX ZIP member")

        def xml(member):
            return ET.fromstring(book.read(member))

        shared = []
        if "xl/sharedStrings.xml" in names:
            shared = [strings(si) for si in xml("xl/sharedStrings.xml").findall(NS+"si")]
        styles = [0]
        if "xl/styles.xml" in names:
            formats = xml("xl/styles.xml").find(NS+"cellXfs")
            if formats is not None:
                styles = [int(x.get("numFmtId", "0")) for x in formats.findall(NS+"xf")]
        rels = {}
        for rel in xml("xl/_rels/workbook.xml.rels").findall(PKG+"Relationship"):
            rid = rel.attrib["Id"]
            require(rid not in rels, "Duplicate XLSX relationship")
            rels[rid] = rel
        all_names = set()
        for sheet in xml("xl/workbook.xml").findall(f"{NS}sheets/{NS}sheet"):
            title = sheet.attrib["name"]
            require(title.casefold() not in all_names, "Duplicate worksheet names")
            all_names.add(title.casefold())
            if title not in required_sheets:
                continue
            rel = rels[sheet.attrib[REL+"id"]]
            require(rel.get("Type", "").endswith("/worksheet") and rel.get("TargetMode", "Internal") == "Internal",
                    "Unsupported worksheet relationship")
            member = posixpath.normpath(posixpath.join("xl", rel.attrib["Target"])).lstrip("/")
            require(member.startswith("xl/"), "Invalid worksheet target")
            table = cells[title] = {}
            formula_ranges = []
            for row in xml(member).findall(f"{NS}sheetData/{NS}row"):
                for c in row.findall(NS+"c"):
                    addr = c.attrib["r"]
                    require(addr not in table and _address(addr)[1] == int(row.attrib["r"]),
                            f"Duplicate or inconsistent address {title}!{addr}")
                    kind = c.get("t", "n")
                    require(kind in {"b", "d", "e", "inlineStr", "n", "s", "str"},
                            f"Unknown cell type in {title}!{addr}")
                    require(len(c.findall(NS + "v")) <= 1 and len(c.findall(NS + "is")) <= 1
                            and not (c.find(NS + "v") is not None and c.find(NS + "is") is not None),
                            f"Conflicting cell values in {title}!{addr}")
                    raw = c.findtext(NS+"v", "")
                    formulas = c.findall(NS + "f")
                    if formulas:
                        require(len(formulas) == 1, f"Conflicting formulas in {title}!{addr}")
                        bounds = _formula_bounds(formulas[0], addr)
                        if bounds:
                            formula_ranges.append(bounds)
                        kind = "formula"
                    elif kind == "s":
                        require(raw.isascii() and raw.isdigit() and int(raw) < len(shared), "Invalid shared string")
                        kind, raw = "text", shared[int(raw)]
                    elif kind == "inlineStr":
                        kind, raw = "text", strings(c.find(NS+"is"))
                    elif kind == "n":
                        style = int(c.get("s", "0"))
                        require(0 <= style < len(styles), "Invalid numeric cell style")
                        # Numeric/date storage is identical. Only unscaled, numeric
                        # built-in formats are supported for measurement cells.
                        if styles[style] not in {0, 1, 2, 3, 4, 11, 37, 38, 39, 40, 48}:
                            kind = "unsupported numeric display format"
                    table[addr] = (kind, raw)
            # An array or data-table output may store only a cache at a mapped
            # cell, with the formula and its output range on another cell.
            if formula_ranges:
                for addr in table:
                    _, row, column = _address(addr)
                    if any(top <= row <= bottom and left <= column <= right
                           for top, bottom, left, right in formula_ranges):
                        table[addr] = ("formula", "")
        require(set(cells) == required_sheets, "Mapped worksheet missing")
    return cells


def _header(table, header):
    _keys(header, ("cell", "text"), "header")
    letters, row, number = _address(header["cell"])
    text = header["text"]
    require(isinstance(text, str) and text.strip() and table.get(header["cell"]) == ("text", text),
            f"Header mismatch at {header['cell']}")
    return letters, row, number


def _energy_unit(header, unit, state):
    # Require a single declared energy unit, either alone or attached to an
    # energy label. Dimensional qualifiers and mixed units require manual review.
    text = header.strip()
    if text == unit:
        return _unit_scale(unit)
    match = re.fullmatch(
        r"(?:energy|e)\s*(?:\[([^\[\]()]+)\]|\(([^\[\]()]+)\)|/\s*(.+?))"
        r"(?:\s+(merge|merger|collapse|collapce|escape))?", text, re.I)
    require(match, f"Unrecognized or ambiguous energy header: {header}")
    label = match[4]
    labels = {
        "skyrmion_antiskyrmion_merge_to_hopfion": {"merger", "merge"},
        "hopfion_collapse": {"collapse", "collapce"},
        "hopfion_escape": {"escape"},
    }
    require(label is None or label.lower() in labels[state], f"Header describes a different transition: {header}")
    declared = next(s for s in match.groups()[:3] if s is not None)
    scale = _unit_scale(declared)
    require(scale == _unit_scale(unit), f"Header unit {declared} differs from manifest {unit}")
    return scale


def _record(state, path, table, source):
    energy, erow, column = _header(table, path["energy_header"])
    coord, crow, _ = _header(table, path["coordinate_header"])
    require(energy != coord, "Coordinate and energy columns coincide")
    require(path["coordinate_header"]["text"].strip().lower() in {
        "coordinate", "reaction coordinate", "normalized reaction coordinate", "path coordinate",
    }, "Unrecognized reaction-coordinate header")
    scale = _energy_unit(path["energy_header"]["text"], path["unit"], state)
    bounds = path["branch_rows"]
    require(isinstance(bounds, list) and len(bounds) == 2, "Expected two branch rows")
    lo, hi = bounds
    start, top = path["minimum_row"], path["saddle_row"]
    require(all(type(i) is int and 1 <= i <= 1048576 for i in (lo, hi, start, top)), "Invalid physical row number")
    require(max(erow, crow) < lo <= start <= hi and lo < top < hi and start != top,
            "Invalid minimum, saddle or branch bounds")

    def number(cell):
        data = table.get(cell)
        require(data and data[0] == "n", f"{path['sheet']}!{cell} requires a literal numeric cell")
        return _decimal(data[1])

    xs = [number(f"{coord}{i}") for i in range(lo, hi+1)]
    ys = {i: number(f"{energy}{i}") for i in range(lo, hi+1)}
    require(all(a < b for a,b in zip(xs, xs[1:])) or all(a > b for a,b in zip(xs, xs[1:])),
            "Reaction coordinates must be strictly monotone within the branch")
    require(all(y < ys[top] for i,y in ys.items() if i != top), "Saddle must be unique maximum on reviewed branch")
    require(all(ys[start] < ys[i] for i in (start-1, start+1) if i in ys), "Minimum is not locally unique")
    step = 1 if top > start else -1
    require(all(ys[start] < ys[i] for i in range(start+step, top+step, step)), "Ambiguous starting well")

    def point(i):
        e, x = f"{energy}{i}", f"{coord}{i}"
        return {"energy_cell": e, "coordinate_cell": x, "energy_raw": table[e][1], "coordinate_raw": table[x][1],
                "energy_pj_decimal": str(ys[i] * scale)}

    with localcontext() as ctx:
        ctx.prec = 1100
        barrier = (ys[top] - ys[start]) * scale
        converted = float(barrier)
        require(math.isfinite(converted) and converted > 0, "Barrier outside representable positive pJ range")
        return {
            "state": state, "barrier_pj": converted, "barrier_pj_decimal": str(barrier),
            "source_file": source["filename"], "sha256": source["sha256"], "source_url": source["url"],
            "doi": DOI, "figure": FIGURES[path["workbook"]], "retrieved_on": source["retrieved_on"],
            "sheet_name": path["sheet"], "energy_header": dict(path["energy_header"]),
            "coordinate_header": dict(path["coordinate_header"]), "source_unit": path["unit"],
            "branch_rows": list(bounds), "minimum": point(start), "saddle": point(top),
            "row": top, "column": column, "unit": "pJ", "extraction_method": "saddle_minus_local_minimum",
            "notes": "Energy at the mapped branch saddle minus energy at the mapped starting well.",
        }


def extract_workbooks(raw_dir, manifest):
    """Return all three audited differences or raise WorkbookError with no partial result.

    A caller-supplied manifest and matching hashes establish reproducibility
    only. Promotion requires a separate, independently reviewed manifest.
    """
    try:
        _keys(manifest, ("schema_version", "doi", "workbooks", "paths"), "manifest")
        require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1
                and manifest["doi"] == DOI, "Unsupported schema or DOI")
        sources, paths = manifest["workbooks"], manifest["paths"]
        _keys(sources, FILES, "workbooks")
        _keys(paths, ROUTING, "paths")
        for state, slot in ROUTING.items():
            p = paths[state]
            _keys(p, ("workbook", "sheet", "energy_header", "coordinate_header", "unit",
                      "minimum_row", "saddle_row", "branch_rows"), state)
            require(p["workbook"] == slot and isinstance(p["sheet"], str) and p["sheet"].strip(),
                    "Invalid figure assignment or worksheet name")
        directory = resolve_workbook_directory(raw_dir)
        snapshots = {}
        for slot, filename in FILES.items():
            source = sources[slot]
            _keys(source, ("filename", "url", "retrieved_on", "sha256"), slot)
            require(source["filename"] == filename and source["url"] == PREFIX+filename, "Unexpected publisher file or URL")
            retrieved = source["retrieved_on"]
            require(isinstance(retrieved, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", retrieved)
                    and date(2026, 4, 21) <= date.fromisoformat(retrieved) <= date.today(), "Invalid retrieval date")
            digest = source["sha256"]
            require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "Expected lowercase SHA-256")
            data = (directory / filename).read_bytes()
            require(hashlib.sha256(data).hexdigest() == digest, f"SHA-256 mismatch for {filename}")
            snapshots[slot] = data
        sheets = {slot: _workbook_cells(data, {p["sheet"] for p in paths.values() if p["workbook"] == slot})
                  for slot, data in snapshots.items()}
        records, used = [], set()
        for state, slot in ROUTING.items():
            p = paths[state]
            record = _record(state, p, sheets[slot][p["sheet"]], sources[slot])
            key = (record["sha256"], record["sheet_name"], record["minimum"]["energy_cell"], record["saddle"]["energy_cell"])
            require(key not in used, "Duplicate energy path for different states")
            used.add(key)
            records.append(record)
        return records
    except WorkbookError:
        raise
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError, OverflowError,
            RuntimeError, EOFError, zlib.error, zipfile.BadZipFile, ET.ParseError, DecimalException) as exc:
        raise WorkbookError(f"Invalid workbook or manifest: {exc}") from exc

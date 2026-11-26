"""Reproduce numeric differences in two pinned Chen et al. publisher attachments.

Only these exact OOXML bytes are recognized. Replay of their documented formulas
is reported separately from validation of their physical energy scale.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, localcontext
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .barrier_workbooks import WorkbookError, resolve_workbook_directory

DOI = "10.1038/s41567-026-03236-0"
ISSUE = "https://github.com/richman954/nag-difference-hopfion/issues/69"
ARTICLE = "https://www.nature.com/articles/s41567-026-03236-0"
ASSET_BASE = "https://static-content.springer.com/esm/art%3A10.1038%2Fs41567-026-03236-0/MediaObjects/"
DIGEST = "134949b49338512245559e0110a809cb29482978639227e4b5b10e594c88c7cc"
SIZE = 23482
FIG5 = "Source Data Fig. 5"
ED9 = "Source Data Extended Data Fig. 9"
FILES = {FIG5: "41567_2026_3236_MOESM13_ESM.xlsx", ED9: "41567_2026_3236_MOESM16_ESM.xlsx"}
STATUS = "physical_unit_unresolved"
D = Decimal
DIVISOR = D("1e-15")
TOLERANCE = D("1e-15")  # absolute in the cached column's printed units


class AuditError(ValueError):
    """An expected source, pinned byte sequence or mapped data invariant failed."""


@dataclass(frozen=True)
class Branch:
    name: str
    source: str
    energy_header: str
    end: int
    offset: int
    image: str
    distance: str
    coordinate: str
    density: str
    energy: str


BRANCHES = (
    Branch("merger", FIG5, "E[pJ] merge", 30, 0, "B", "C", "D", "E", "F"),
    Branch("collapse", FIG5, "E[pJ] collapce", 37, 1, "I", "J", "K", "L", "M"),
    Branch("escape", ED9, "E[pJ] escape", 26, 1, "P", "Q", "R", "S", "T"),
)


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _decimal(text: str, address: str) -> Decimal:
    try:
        number = D(text)
    except ArithmeticError as exc:
        raise AuditError(f"Non-numeric {address}: {text!r}") from exc
    _check(number.is_finite(), f"Non-finite {address}")
    return number


def _check_formula_column(cells, column: str, end: int, expression: str) -> None:
    """OOXML shared formulas have one expression followed by group references."""
    start = f"{column}2"
    formula = cells[start].find("{*}f")
    _check(formula is not None and formula.text == expression, f"Unexpected formula at {start}")
    group = formula.get("si")
    _check(formula.get("t") == "shared" and group is not None and
           formula.get("ref") == f"{start}:{column}{end}", f"Invalid shared range at {start}")
    for row in range(3, end + 1):
        address = f"{column}{row}"
        child = cells[address].find("{*}f")
        _check(child is not None and child.get("t") == "shared" and child.get("si") == group
               and child.text is None, f"Invalid shared formula at {address}")


def _peak(energies: list[Decimal]) -> int:
    """Return the zero-based index of the unique maximum along a directed path."""
    _check(len(energies) >= 3, "Path needs two endpoints and an interior sample")
    highest = max(energies)
    index = energies.index(highest)
    _check(0 < index < len(energies) - 1 and energies.count(highest) == 1,
           "Ambiguous or endpoint saddle")
    # The escape path starts with two equal samples. The first departure from
    # such a plateau must point uphill for the starting image to be a minimum.
    first_change = next(value for value in energies[1:] if value != energies[0])
    _check(first_change > energies[0], "Invalid starting minimum")
    return index


def _read_cells(data: bytes):
    # The caller authenticates these bytes before opening the ZIP. The named
    # worksheet and chart paths below are specific to this pinned package.
    with ZipFile(BytesIO(data)) as archive:
        def read_xml(path):
            return ET.fromstring(archive.read(path))
        workbook = read_xml("xl/workbook.xml")
        sheets = workbook.findall(".//{*}sheets/{*}sheet")
        _check(len(sheets) == 1 and sheets[0].get("name") == "Sheet1", "Unexpected sheet mapping")
        root = read_xml("xl/worksheets/sheet1.xml")
        cells = {c.attrib["r"]: c for c in root.findall(".//{*}sheetData/{*}row/{*}c")}
        strings = ["".join(item.itertext()) for item in read_xml("xl/sharedStrings.xml")]
        chart = read_xml("xl/charts/chart1.xml")
        series = chart.findall(".//{*}scatterChart/{*}ser")
    return cells, strings, series


def _read_branch(branch, cells, strings, chart_series, volume, include_profiles):
    b = branch

    def value(address):
        cell = cells[address]
        raw = cell.findtext("{*}v")
        _check(raw is not None and cell.get("t", "n") == "n", f"Missing number at {address}")
        return _decimal(raw, address)

    for col, label in [(b.image, "Image"), (b.distance, "Distance"), (b.coordinate, "Coordinate"),
                       (b.density, "energy dens"), (b.energy, b.energy_header)]:
        c = cells[col + "1"]
        _check(c.get("t") == "s" and strings[int(c.findtext("{*}v"))] == label,
               f"Unexpected header at {col}1")
    chart_ranges = [f.text for f in chart_series.findall(".//{*}f")]
    _check(chart_ranges == [
        f"Sheet1!${b.energy}$1:${b.energy}$1",
        f"Sheet1!${b.coordinate}$2:${b.coordinate}${b.end}",
        f"Sheet1!${b.energy}$2:${b.energy}${b.end}"], f"Unexpected chart series for {b.name}")
    distance = b.distance
    normalized = f"({distance}2-${distance}$2)/(${distance}${b.end}-${distance}$2)"
    if b.offset:
        normalized += "+1"
    _check_formula_column(cells, b.coordinate, b.end, normalized)
    energy_expression = f"{b.density}2*$A$2/0.000000000000001"
    _check_formula_column(cells, b.energy, b.end, energy_expression)

    xmin, xmax = value(distance + "2"), value(distance + str(b.end))
    _check(xmax > xmin, f"Invalid distance range for {b.name}")
    energies = []
    prior_distance = None
    energy_error = coordinate_error = D(0)
    for row in range(2, b.end + 1):
        _check(value(b.image + str(row)) == row - 2, f"Unexpected image at row {row}")
        x = value(distance + str(row))
        _check(prior_distance is None or x > prior_distance, f"Unordered path at {distance}{row}")
        prior_distance = x
        energy = value(b.energy + str(row))
        energies.append(energy)
        ep = value(b.density + str(row)) * volume / DIVISOR
        xp = (x - xmin) / (xmax - xmin) + b.offset
        energy_error = max(energy_error, abs(energy - ep))
        coordinate_error = max(coordinate_error, abs(value(b.coordinate + str(row)) - xp))
    _check(max(energy_error, coordinate_error) <= TOLERANCE, f"Cached formula replay failed for {b.name}")

    # Compare the separately stored plot cache against the worksheet values.
    for axis, column in (("xVal", b.coordinate), ("yVal", b.energy)):
        cache = chart_series.find(f"{{*}}{axis}/{{*}}numRef/{{*}}numCache")
        _check(cache is not None, f"Missing chart cache for {axis}")
        points = cache.findall("{*}pt")
        _check(len(points) == len(energies), f"Invalid chart length for {axis}")
        for index, point in enumerate(points):
            address = column + str(index + 2)
            _check(point.get("idx") == str(index) and
                   _decimal(point.findtext("{*}v"), address) == value(address),
                   f"Chart data differ from the worksheet at {address}")

    peak_row = 2 + _peak(energies)
    numeric_delta = energies[peak_row - 2] - energies[0]
    change_density = value(b.density + str(peak_row)) - value(b.density + "2")
    delta_J_if_SI = change_density * volume

    def point(row):
        result = {}
        for field in ("image", "distance", "coordinate", "density", "energy"):
            coordinate = getattr(b, field) + str(row)
            result[field] = {"cell": coordinate, "raw": cells[coordinate].findtext("{*}v")}
        return result

    result = {
        "path": b.name, "source": b.source, "filename": FILES[b.source], "sheet": "Sheet1",
        "energy_header_cell": b.energy + "1", "energy_header": b.energy_header,
        "energy_range": f"{b.energy}2:{b.energy}{b.end}",
        "coordinate_range": f"{b.coordinate}2:{b.coordinate}{b.end}",
        "doi": DOI, "source_url": ASSET_BASE + FILES[b.source], "source_sha256": DIGEST,
        "retrieved_utc_date": "2026-11-25", "source_unit_label": "pJ",
        "coordinate_header_cell": b.coordinate + "1", "coordinate_header": "Coordinate",
        "density_header_cell": b.density + "1", "density_header": "energy dens",
        "density_unit": None, "physical_unit_status": STATUS,
        "energy_formula_at_first_row": "=" + energy_expression,
        "coordinate_formula_at_first_row": "=" + normalized, "chart_series_ranges": chart_ranges,
        "chart_cache_values_matched": 2 * len(energies),
        "images": len(energies), "initial_minimum": point(2), "saddle": point(peak_row),
        "final_image": point(b.end),
        "barrier_in_column_units": str(numeric_delta),
        "conditional_pJ_if_header_scale": str(numeric_delta),
        "conditional_J_if_SI_density_and_volume": str(delta_J_if_SI),
        "conditional_pJ_if_SI_density_and_volume": str(delta_J_if_SI * D("1e12")),
        "max_abs_energy_cache_error": str(energy_error),
        "max_abs_coordinate_cache_error": str(coordinate_error),
    }
    if include_profiles:
        result["density_profile"] = [cells[f"{b.density}{row}"].findtext("{*}v")
                                     for row in range(2, b.end + 1)]
    return result


def audit_publisher_pair(raw_dir: Path, *, include_profiles: bool = False) -> dict:
    """Verify both attachments, replay every mapped path and return qualified results."""
    try:
        directory = resolve_workbook_directory(raw_dir)
    except WorkbookError as exc:
        raise AuditError(str(exc)) from exc
    buffers, sources = {}, []
    for label, filename in FILES.items():
        path = directory / filename
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise AuditError(f"Cannot read {label} ({filename}): {exc}") from exc
        digest = hashlib.sha256(data).hexdigest()
        _check(digest == DIGEST and len(data) == SIZE, f"Checksum or size mismatch for {label}: {digest}")
        buffers[label] = data
        sources.append({"publisher_label": label, "source_url": ASSET_BASE + filename,
                        "filename": filename, "sha256": digest, "size_bytes": len(data),
                        "retrieved_utc_date": "2026-11-25"})
    _check(buffers[FIG5] == buffers[ED9], "Pinned source payloads differ")
    cells, strings, charts = _read_cells(buffers[FIG5])
    _check(len(charts) == 3, "Unexpected chart series count")
    _check(strings[int(cells["A1"].findtext("{*}v"))] == "Volume", "Unexpected A1 header")
    volume_formula = cells["A2"].findtext("{*}f")
    _check(volume_formula == "3*70*3*70*1.5*70*1E-27", "Unknown volume formula")
    with localcontext() as context:
        context.prec = 50
        volume = D(210) * D(210) * D(105) * D("1e-27")
        _check(_decimal(cells["A2"].findtext("{*}v"), "A2") == volume, "Invalid volume cache")
        branches = [_read_branch(b, cells, strings, chart, volume, include_profiles)
                    for b, chart in zip(BRANCHES, charts)]
    return {
        "doi": DOI, "article": ARTICLE, "benchmark_source_discovery_issue": ISSUE,
        "sources": sources, "byte_identical": True, "unique_workbook_payloads": 1,
        "status": STATUS, "validated_count": 0, "numeric_barrier_count": len(branches),
        "method": "Unique highest sampled energy minus the directed starting image on each branch.",
        "physical_unit_caveat": (
            "The source headers and the published Fig. 5 and Extended Data Fig. 9 axes say pJ. Each plotted column is energy "
            "density times Sheet1!A2 divided by 1e-15. If density is in J/m^3 and volume in m^3, "
            "the resulting plotted unit is fJ. The density columns do not state their unit. "
            "The two pJ interpretations differ by a factor of 1000."
        ),
        "volume": {"sheet": "Sheet1", "cell": "A2", "formula": "=" + volume_formula,
                   "raw": cells["A2"].findtext("{*}v")},
        "cache_replay_absolute_tolerance": str(TOLERANCE), "paths": branches,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path, help="Directory with both original XLSX attachments")
    args = parser.parse_args(argv)
    try:
        result = audit_publisher_pair(args.raw_dir)
    except AuditError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

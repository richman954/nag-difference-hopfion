"""Regression cases use generated workbooks only. No fixture is a measurement."""

from __future__ import annotations

import hashlib
import json
import zipfile
from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.formula import ArrayFormula

from nagdiff.barrier_workbooks import (
    WorkbookError,
    extract_workbooks,
    load_manifest,
    normalize_to_pj,
)


MERGER = "skyrmion_antiskyrmion_merge_to_hopfion"
COLLAPSE = "hopfion_collapse"
ESCAPE = "hopfion_escape"
DOI = "10.1038/s41567-026-03236-0"
SHEET = "MEP data"
FILES = {
    "fig5": "41567_2026_3236_MOESM13_ESM.xlsx",
    "ed9": "41567_2026_3236_MOESM16_ESM.xlsx",
}
BASE_URL = "https://static-content.springer.com/esm/art%3A10.1038%2Fs41567-026-03236-0/MediaObjects/"
# Each barrier is between a local minimum and its saddle on one series.
# The three distinct values make swapped tracks and reused source cells visible.
BARRIERS_PJ = {
    MERGER: Decimal("0.000224"),
    COLLAPSE: Decimal("0.00036"),
    ESCAPE: Decimal("0.00084"),
}
PJ_PER_UNIT = {
    "J": Decimal("1e12"),
    "pJ": Decimal("1"),
    "fJ": Decimal("1e-3"),
    "10^-18 J": Decimal("1e-6"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_example(raw_dir, unit="pJ"):
    """Build independent synthetic data in the layout expected by a reviewed mapping."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    workbooks = {}
    paths = {}
    for figure, states in (("fig5", (MERGER, COLLAPSE)), ("ed9", (ESCAPE,))):
        book = Workbook()
        # A decoy first worksheet and large unpopulated area catch sheet-index and
        # compacted-row errors. The mapped worksheet also contains a decoy column.
        book.active.title = "Contents"
        book.active["AA20"] = 1100
        sheet = book.create_sheet(SHEET)
        sheet["A1"] = "Synthetic regression fixture"
        for state, (coordinate, energy) in zip(states, (("Z", "AA"), ("AC", "AD"))):
            header = f"E ({unit})"
            sheet[f"{coordinate}4"] = "Reaction coordinate"
            sheet[f"{energy}4"] = header
            # Both endpoints are interior extrema: energy falls into the minimum,
            # rises through the saddle, and falls on its other side.
            for row, level in enumerate(("-0.25", "-0.5", "0", "0.5", "0.25"), start=17):
                sheet[f"{coordinate}{row}"] = row - 17
                sheet[f"{energy}{row}"] = float(Decimal(level) * BARRIERS_PJ[state] / PJ_PER_UNIT[unit])
            paths[state] = {
                "workbook": figure,
                "sheet": SHEET,
                "coordinate_header": {"cell": f"{coordinate}4", "text": "Reaction coordinate"},
                "energy_header": {"cell": f"{energy}4", "text": header},
                "unit": unit,
                "branch_rows": [17, 21],
                "minimum_row": 18,
                "saddle_row": 20,
            }
        path = raw_dir / FILES[figure]
        book.save(path)
        book.close()
        workbooks[figure] = {
            "filename": path.name,
            "url": BASE_URL + path.name,
            "retrieved_on": "2026-04-21",
            "sha256": digest(path),
        }
    return {"schema_version": 1, "doi": DOI, "workbooks": workbooks, "paths": paths}


@pytest.fixture
def example(tmp_path):
    return make_example(tmp_path)


def change_cell(raw_dir, manifest, address, value):
    """Change bytes *and* refresh fixture hash, so semantic tests reach parsing."""
    spec = manifest["workbooks"]["fig5"]
    path = raw_dir / spec["filename"]
    book = load_workbook(path)
    book[SHEET][address].value = value
    book.save(path)
    book.close()
    spec["sha256"] = digest(path)


@pytest.mark.parametrize(
    ("value", "unit"),
    [(2.24e-16, "J"), (2.24e-4, "pJ"), (0.224, "fJ")],
)
def test_same_energy_in_different_units(value, unit):
    assert normalize_to_pj(value, unit) == Decimal("0.000224")


@pytest.mark.parametrize("value", [-3, 0, 0.0099, 0.01, 0.0101, 100])
def test_unit_conversion_is_independent_of_magnitude(value):
    assert normalize_to_pj(value, "pJ") == Decimal(str(value))
    assert normalize_to_pj(value, "J") == Decimal(str(value)) * Decimal("1e12")


@pytest.mark.parametrize("unit", [None, "", "pj", "PJ", "pJ/nm", "a.u."])
def test_ambiguous_or_unsupported_unit_rejected(unit):
    with pytest.raises(WorkbookError):
        normalize_to_pj(2.24e-4, unit)


@pytest.mark.parametrize("value", [True, None, float("nan"), float("inf"), float("-inf"), "curve 2: 0.5"])
def test_invalid_energy_rejected(value):
    with pytest.raises(WorkbookError):
        normalize_to_pj(value, "pJ")


@pytest.mark.parametrize("unit", ["pJ", "J", "fJ", "10^-18 J"])
def test_xlsx_differences_and_both_physical_cell_addresses(tmp_path, unit):
    manifest = make_example(tmp_path, unit)
    records = extract_workbooks(tmp_path, manifest)
    assert [r["state"] for r in records] == [MERGER, COLLAPSE, ESCAPE]
    for record in records:
        state = record["state"]
        assert Decimal(record["barrier_pj_decimal"]) == BARRIERS_PJ[state]
        assert record["barrier_pj"] == float(BARRIERS_PJ[state])
        coordinate, energy = ("AC", "AD") if state == COLLAPSE else ("Z", "AA")
        assert record["sheet_name"] == SHEET
        spec = manifest["workbooks"]["ed9" if state == ESCAPE else "fig5"]
        assert record["sha256"] == digest(tmp_path / spec["filename"])
        assert record["source_file"] == spec["filename"]
        assert record["source_url"] == spec["url"]
        assert record["retrieved_on"] == spec["retrieved_on"]
        assert record["doi"] == DOI
        assert record["source_unit"] == unit
        assert record["unit"] == "pJ"
        assert record["coordinate_header"] == {"cell": f"{coordinate}4", "text": "Reaction coordinate"}
        assert record["energy_header"] == {"cell": f"{energy}4", "text": f"E ({unit})"}
        for role, row, level in (("minimum", 18, "-0.5"), ("saddle", 20, "0.5")):
            source = record[role]
            assert source["energy_cell"] == f"{energy}{row}"
            assert source["coordinate_cell"] == f"{coordinate}{row}"
            assert Decimal(source["energy_raw"]) == Decimal(level) * BARRIERS_PJ[state] / PJ_PER_UNIT[unit]
            assert Decimal(source["coordinate_raw"]) == row - 17


@pytest.mark.parametrize("figure", ["fig5", "ed9"])
def test_checksum_recomputed_from_workbook_bytes(tmp_path, example, figure):
    spec = example["workbooks"][figure]
    # ZIP parsers tolerate trailing bytes, leaving exactly the original cells.
    with (tmp_path / spec["filename"]).open("ab") as stream:
        stream.write(b"changed after digest was pinned")
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize("field", ["sha256", "filename", "retrieved_on", "url"])
def test_missing_source_identity_rejected(tmp_path, example, field):
    del example["workbooks"]["ed9"][field]
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("sha256", "not a sha256"),
        ("retrieved_on", "2026-02-30"),
        ("url", "https://example.org/unrelated.xlsx"),
        ("filename", "../outside.xlsx"),
    ],
)
def test_invalid_source_identity_rejected(tmp_path, example, field, invalid):
    example["workbooks"]["ed9"][field] = invalid
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("sheet", "Contents"),
        ("sheet", "missing"),
        ("unit", "J"),
        ("workbook", "ed9"),
        ("minimum_row", True),
        ("saddle_row", 18),
        ("saddle_row", 16),
    ],
)
def test_invalid_series_mapping_rejected(tmp_path, example, field, invalid):
    example["paths"][MERGER][field] = invalid
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize(
    ("address", "value"),
    [
        ("AA4", "E"),
        ("Z4", "sample number"),
        ("AA20", None),
        ("AA20", True),
        ("AA20", "curve 2; 0.000112 pJ"),
        ("AA20", "#DIV/0!"),
        ("AA20", "=1/100"),
        ("AA19", -1),
        ("AA19", 1),
        ("Z19", 1),
        ("Z19", None),
        ("AA20", 0.0),
    ],
)
def test_rehashed_but_malformed_workbook_rejected(tmp_path, example, address, value):
    change_cell(tmp_path, example, address, value)
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


def test_two_scenarios_cannot_reuse_same_endpoints(tmp_path, example):
    example["paths"][COLLAPSE] = example["paths"][MERGER].copy()
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


def test_missing_state_is_never_partial_success(tmp_path, example):
    del example["paths"][ESCAPE]
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


def test_confirmed_checksum_on_invalid_xlsx_is_insufficient(tmp_path, example):
    spec = example["workbooks"]["ed9"]
    path = tmp_path / spec["filename"]
    path.write_bytes(b"<html>download unavailable</html>")
    spec["sha256"] = digest(path)
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


def test_duplicate_json_key_rejected_without_overwriting_first_value(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text('{"workbooks":{"fig5":{}, "fig5":{}}}', encoding="utf-8")
    with pytest.raises(WorkbookError):
        load_manifest(path)


def test_serialized_manifest_round_trip(tmp_path, example):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(example), encoding="utf-8")
    assert load_manifest(path) == example


def test_downhill_product_is_not_the_reference_minimum(tmp_path, example):
    # End of the branch is more stable than the reactant local minimum.
    change_cell(tmp_path, example, "AA21", -0.001)
    record = extract_workbooks(tmp_path, example)[0]
    assert Decimal(record["barrier_pj_decimal"]) == BARRIERS_PJ[MERGER]
    assert record["minimum"]["energy_cell"] == "AA18"


def test_an_unrelated_peak_outside_mapped_branch_is_ignored(tmp_path, example):
    change_cell(tmp_path, example, "AA35", 1000)
    record = extract_workbooks(tmp_path, example)[0]
    assert Decimal(record["barrier_pj_decimal"]) == BARRIERS_PJ[MERGER]


@pytest.mark.parametrize("level", [-0.000112, 0.000112])
def test_tied_extremum_is_ambiguous(tmp_path, example, level):
    change_cell(tmp_path, example, "AA19", level)
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize("label", ["E", "E (pJ/nm)", "E (pJ) or E (J)", "E (pJ), scaled by unknown factor"])
def test_manifest_cannot_declare_units_absent_or_ambiguous_on_sheet(tmp_path, example, label):
    change_cell(tmp_path, example, "AA4", label)
    example["paths"][MERGER]["energy_header"]["text"] = label
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


def test_figures_must_be_distinct_workbooks(tmp_path, example):
    example["workbooks"]["ed9"] = example["workbooks"]["fig5"].copy()
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


def test_barrier_invariant_under_common_energy_offset(tmp_path, example):
    spec = example["workbooks"]["fig5"]
    path = tmp_path / spec["filename"]
    book = load_workbook(path)
    sheet = book[SHEET]
    # Compare a large absolute baseline with the identical near-zero profile.
    for row in range(17, 22):
        cell = sheet[f"AA{row}"]
        cell.value = float(Decimal(str(cell.value)) + Decimal("2000"))
    book.save(path)
    book.close()
    spec["sha256"] = digest(path)
    assert Decimal(extract_workbooks(tmp_path, example)[0]["barrier_pj_decimal"]) == BARRIERS_PJ[MERGER]


def test_distinct_publisher_links_can_serve_identical_bytes(tmp_path, example):
    # Reproduce the publisher's arrangement: two independently named files with
    # one shared byte sequence and three physically separate reaction paths.
    spec5, spec9 = (example["workbooks"][key] for key in ("fig5", "ed9"))
    path5 = tmp_path / spec5["filename"]
    book = load_workbook(path5)
    sheet = book[SHEET]
    sheet["AF4"] = "Reaction coordinate"
    sheet["AG4"] = "E (pJ)"
    for row, level in enumerate(("-0.25", "-0.5", "0", "0.5", "0.25"), start=17):
        sheet[f"AF{row}"] = row - 17
        sheet[f"AG{row}"] = float(Decimal(level) * BARRIERS_PJ[ESCAPE])
    book.save(path5)
    book.close()
    (tmp_path / spec9["filename"]).write_bytes(path5.read_bytes())
    spec5["sha256"] = spec9["sha256"] = digest(path5)
    example["paths"][ESCAPE]["coordinate_header"]["cell"] = "AF4"
    example["paths"][ESCAPE]["energy_header"]["cell"] = "AG4"
    records = extract_workbooks(tmp_path, example)
    assert [Decimal(record["barrier_pj_decimal"]) for record in records] == list(BARRIERS_PJ.values())


def test_explicit_process_label_cannot_contradict_mapped_state(tmp_path, example):
    label = "E[pJ] collapce"  # This is the spelling used in the publisher file.
    change_cell(tmp_path, example, "AA4", label)
    example["paths"][MERGER]["energy_header"]["text"] = label
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize("row", [4, 20])
def test_array_output_with_formula_anchor_outside_mapped_columns(tmp_path, example, row):
    # Only Y has a formula element in OOXML. The mapped Z and AA cells retain
    # their plausible text or numeric caches from the fixture.
    change_cell(tmp_path, example, f"Y{row}", ArrayFormula(f"Y{row}:AA{row}", "=ROW()"))
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)


@pytest.mark.parametrize("malformation", ["formula_cache", "unknown_header_type"])
def test_literal_series_rejects_formulas_and_unknown_cell_types(tmp_path, example, malformation):
    if malformation == "formula_cache":
        change_cell(tmp_path, example, "AA20", "=999")
    spec = example["workbooks"]["fig5"]
    path = tmp_path / spec["filename"]
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(BytesIO(path.read_bytes())) as original, zipfile.ZipFile(path, "w") as changed:
        for member in original.infolist():
            data = original.read(member)
            if member.filename == "xl/worksheets/sheet2.xml":
                root = ET.fromstring(data)
                if malformation == "formula_cache":
                    value = root.find(f".//{ns}c[@r='AA20']/{ns}v")
                    assert value is not None
                    value.text = "0.000112"  # Expected saddle as a stale formula cache.
                else:
                    cell = root.find(f".//{ns}c[@r='AA4']")
                    cell.clear()
                    cell.set("r", "AA4")
                    cell.set("t", "text")
                    ET.SubElement(cell, ns + "v").text = "E (pJ)"
                data = ET.tostring(root, encoding="utf-8")
            changed.writestr(member, data)
    spec["sha256"] = digest(path)
    with pytest.raises(WorkbookError):
        extract_workbooks(tmp_path, example)

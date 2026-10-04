import json

from nagdiff.extraction import write_extraction_artifact
from nagdiff.hopfion_terms import REQUIRED_PROVENANCE_FIELDS, load_barrier_table


def test_write_extraction_artifact(tmp_path):
    (tmp_path / "MOESM13.csv").write_text(
        "label,value\n"
        "skyrmion antiskyrmion merge hopfion barrier,2.24e-4\n"
        "hopfion collapse barrier,2.86e-4\n",
        encoding="utf-8",
    )
    (tmp_path / "MOESM16.csv").write_text(
        "label,value\n"
        "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    out = tmp_path / "artifact.json"
    payload = write_extraction_artifact(tmp_path, out)
    assert payload["extracted_count"] == 3
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["checksums"]) == 2
    assert len(data["records"]) == 3


def test_extracted_records_have_required_provenance(tmp_path):
    (tmp_path / "MOESM13.csv").write_text(
        "label,value\n"
        "skyrmion antiskyrmion merge hopfion barrier,2.24e-4\n"
        "hopfion collapse barrier,2.86e-4\n",
        encoding="utf-8",
    )
    (tmp_path / "MOESM16.csv").write_text(
        "label,value\n"
        "hopfion escape barrier,7.32e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)
    extracted = [r for r in table["records"] if r["provenance_status"] == "extracted_from_raw_moesm"]
    assert len(extracted) == 3
    for record in extracted:
        for field in REQUIRED_PROVENANCE_FIELDS:
            assert record[field] not in (None, "")


def test_is_extraction_validated_success(tmp_path):
    from nagdiff.extraction import is_extraction_validated
    payload = {
        "extracted_count": 3,
        "records": [
            {
                "state": "skyrmion_antiskyrmion_merge_to_hopfion",
                "barrier_pj": 1.0,
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n"
            },
            {
                "state": "hopfion_collapse",
                "barrier_pj": 1.0,
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n"
            },
            {
                "state": "hopfion_escape",
                "barrier_pj": 1.0,
                "source_file": "f",
                "sheet_name": "s",
                "row": 1,
                "column": 1,
                "unit": "pJ",
                "extraction_method": "f",
                "notes": "n"
            }
        ],
        "checksums": {"f": "c"}
    }
    assert is_extraction_validated(payload) is True


def test_is_extraction_validated_fails_on_empty(tmp_path):
    from nagdiff.extraction import is_extraction_validated
    out = tmp_path / "artifact.json"
    payload = write_extraction_artifact(tmp_path, out)
    assert is_extraction_validated(payload) is False


def test_fallback_values_marked_raw_moesm_verification_pending(tmp_path):
    table = load_barrier_table(raw_dir=tmp_path)
    for record in table["records"]:
        assert record["provenance_status"] == "raw_moesm_verification_pending"


def test_extracts_from_named_moesm_directories_and_keeps_seeded_comparison(tmp_path):
    moesm13 = tmp_path / "MOESM13"
    moesm16 = tmp_path / "MOESM16"
    moesm13.mkdir()
    moesm16.mkdir()
    (moesm13 / "barriers.csv").write_text(
        "process,barrier\n"
        "skyrmion antiskyrmion merge hopfion,1.11e-4\n"
        "hopfion collapse,2.22e-4\n",
        encoding="utf-8",
    )
    (moesm16 / "barriers.csv").write_text(
        "process,barrier\nhopfion escape,3.33e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)

    assert table["mode"] == "extracted"
    assert [record["barrier_pj"] for record in table["records"]] == [1.11e-4, 2.22e-4, 3.33e-4]
    assert table["seeded_records"][0]["barrier_pj"] == 2.24e-4
    for record in table["records"]:
        assert record["source_file"].endswith("barriers.csv")
        assert record["sheet_name"] == "barriers"
        assert record["row"] > 0
        assert record["column"] > 0
        assert record["unit"] == "pJ"
        assert record["extraction_method"] == "keyword_row_scan_csv"
        assert record["notes"]


def test_partial_extraction_does_not_replace_any_seeded_values(tmp_path):
    moesm13 = tmp_path / "MOESM13"
    moesm13.mkdir()
    (moesm13 / "barriers.csv").write_text(
        "process,barrier\nhopfion collapse,9.99e-4\n",
        encoding="utf-8",
    )

    table = load_barrier_table(raw_dir=tmp_path)

    assert table["mode"] == "fallback"
    assert [record["barrier_pj"] for record in table["records"]] == [2.24e-4, 2.86e-4, 7.32e-4]
    assert all(record["extraction_method"] == "seeded_fallback" for record in table["records"])

def test_xlsx_rows_extraction(tmp_path):
    import zipfile
    from nagdiff.extraction import _xlsx_rows

    xlsx_path = tmp_path / "test.xlsx"
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    pkg_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'

    with zipfile.ZipFile(xlsx_path, 'w') as zf:
        zf.writestr('xl/workbook.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{ns}" xmlns:r="{rel_ns}">
    <sheets>
        <sheet name="Sheet1" r:id="rId1"/>
        <sheet name="Sheet2" r:id="rId2"/>
    </sheets>
</workbook>''')

        zf.writestr('xl/_rels/workbook.xml.rels', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{pkg_ns}">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet2.xml"/>
</Relationships>''')

        zf.writestr('xl/sharedStrings.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="{ns}">
    <si><t>Shared string 1</t></si>
    <si><t>Shared string 2</t></si>
</sst>''')

        zf.writestr('xl/worksheets/sheet1.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{ns}">
    <sheetData>
        <row r="1">
            <c r="A1" t="s"><v>0</v></c>
            <c r="B1"><is><t>Inline string</t></is></c>
            <c r="C1"><v>123.45</v></c>
            <c r="AA1"><v>0.001</v></c>
            <c r="AB1" t="s"><v></v></c>
            <c r="AC1" t="s"></c>
            <c r="Z1"/>
        </row>
    </sheetData>
</worksheet>''')

        zf.writestr('xl/worksheets/sheet2.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{ns}">
    <sheetData>
        <row r="1">
            <c r="A1" t="s"><v>1</v></c>
        </row>
    </sheetData>
</worksheet>''')

    rows = list(_xlsx_rows(xlsx_path))

    assert len(rows) == 2

    sheet1_name, sheet1_cells = rows[0]
    assert sheet1_name == "Sheet1"
    assert sheet1_cells == [
        (1, 'Shared string 1'),
        (2, 'Inline string'),
        (3, '123.45'),
        (27, '0.001'),
        (28, ''),
        (29, ''),
        (26, '')
    ]

    sheet2_name, sheet2_cells = rows[1]
    assert sheet2_name == "Sheet2"
    assert sheet2_cells == [(1, 'Shared string 2')]


def test_xlsx_rows_no_shared_strings(tmp_path):
    import zipfile
    from nagdiff.extraction import _xlsx_rows

    xlsx_path = tmp_path / "test_no_shared.xlsx"
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    pkg_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'

    with zipfile.ZipFile(xlsx_path, 'w') as zf:
        zf.writestr('xl/workbook.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{ns}" xmlns:r="{rel_ns}">
    <sheets>
        <sheet name="Sheet1" r:id="rId1"/>
    </sheets>
</workbook>''')

        zf.writestr('xl/_rels/workbook.xml.rels', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{pkg_ns}">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>''')

        zf.writestr('xl/worksheets/sheet1.xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{ns}">
    <sheetData>
        <row r="1">
            <c r="A1"><v>123</v></c>
        </row>
    </sheetData>
</worksheet>''')

    rows = list(_xlsx_rows(xlsx_path))
    assert len(rows) == 1
    assert rows[0][0] == "Sheet1"
    assert rows[0][1] == [(1, '123')]

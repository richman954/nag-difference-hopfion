from decimal import Decimal
import json
from pathlib import Path
from shutil import copyfile
from xml.etree import ElementTree as ET

import pytest

from nagdiff import chen2026_audit as audit


BUNDLED = Path(__file__).resolve().parents[1] / "data/raw/nature_source_data"


def test_verified_workbooks_preserve_both_roles_and_unresolved_scale(capsys):
    assert audit.main([str(BUNDLED)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert [item["filename"] for item in result["sources"]] == list(audit.FILES.values())
    assert len({item["source_url"] for item in result["sources"]}) == 2
    assert {item["sha256"] for item in result["sources"]} == {audit.DIGEST}
    assert result["unique_workbook_payloads"] == 1
    assert result["status"] == "physical_unit_unresolved"
    assert result["validated_count"] == 0
    assert result["volume"]["raw"] == "4.6305E-21"
    assert [path["source"] for path in result["paths"]] == [audit.FIG5, audit.FIG5, audit.ED9]
    expected = [
        ("merger", 29, "F2", "F7",  "F30", "0.00022388286621094", "2.238828662109375e-7"),
        ("collapse", 36, "M2", "M13", "M37", "0.00028564396875000", "2.8564396875e-7"),
        ("escape", 25, "T2", "T18", "T26", "0.00073163708789062", "7.31637087890625e-7"),
    ]
    for path, (name, count, first, highest, last, delta, si_pJ) in zip(result["paths"], expected):
        assert (path["path"], path["images"]) == (name, count)
        assert [path[p]["energy"]["cell"] for p in ("initial_minimum", "saddle", "final_image")] == [
            first, highest, last
        ]
        assert path["barrier_in_column_units"] == delta
        assert Decimal(path["conditional_pJ_if_SI_density_and_volume"]) == Decimal(si_pJ)
        assert Decimal(path["max_abs_energy_cache_error"]) < Decimal("1e-15")
        assert Decimal(path["max_abs_coordinate_cache_error"]) < Decimal("1e-15")


def test_optional_density_profiles_match_mapped_source_cells():
    standard = audit.audit_publisher_pair(BUNDLED)
    profiled = audit.audit_publisher_pair(BUNDLED.parent, include_profiles=True)
    for path in profiled["paths"]:
        profile = path.pop("density_profile")
        assert len(profile) == path["images"]
        for endpoint in ("initial_minimum", "saddle", "final_image"):
            image = int(path[endpoint]["image"]["raw"])
            assert profile[image] == path[endpoint]["density"]["raw"]
    assert profiled == standard


@pytest.mark.parametrize("fault", ["missing", "altered"])
def test_second_attachment_failure_is_atomic(tmp_path, capsys, fault):
    first, second = audit.FILES.values()
    copyfile(BUNDLED / first, tmp_path / first)
    if fault == "altered":
        (tmp_path / second).write_bytes((BUNDLED / second).read_bytes() + b"!")
    assert audit.main([str(tmp_path)]) == 2
    streams = capsys.readouterr()
    assert streams.out == ""
    assert audit.ED9 in streams.err


@pytest.mark.parametrize("values", [
    [1, 1], [1, 2, 3], [3, 2, 0], [0, 5, 5, -1], [0, -1, 6, -2], [0, 0, -1, 6, -2],
])
def test_directed_saddle_rejects_malformed_or_ambiguous_paths(values):
    with pytest.raises(audit.AuditError):
        audit._peak([Decimal(v) for v in values])


def test_starting_plateau_and_lower_local_peak():
    assert audit._peak([Decimal(v) for v in [0, 0, 2, 1, 4, -1]]) == 4


@pytest.mark.parametrize("bad", [
    '<f t="shared" si="1"/>', '<f t="shared" si="0">OTHER()</f>', '<v>0</v>',
])
def test_changed_shared_formula_cannot_supply_cache(bad):
    cells = {
        "F2": ET.fromstring('<c><f t="shared" si="0" ref="F2:F3">E2*$A$2/1e-15</f></c>'),
        "F3": ET.fromstring("<c>" + bad + "</c>"),
    }
    with pytest.raises(audit.AuditError, match="Invalid shared formula at F3"):
        audit._check_formula_column(cells, "F", 3, "E2*$A$2/1e-15")

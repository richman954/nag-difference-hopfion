from decimal import Decimal
from pathlib import Path

import pytest

from nagdiff.chen2026_audit import AuditError
from scripts.check_endpoint_scale import compare, continuum_limits, endpoint_drop


RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_model_limits_from_reported_parameters():
    result = continuum_limits()
    assert result["exchange_DMI_floor_J_m3"] == pytest.approx(-76590.4210526)
    assert result["magnetostatic_floor_J_m3"] == pytest.approx(-92649.3372655)
    assert result["conditional_drop_ceiling_J_m3"] == pytest.approx(169316.2983)


def test_measured_endpoint_spreads_and_publication_gate():
    result = compare(RAW)
    assert result["physical_unit_status"] == "physical_unit_unresolved"
    assert result["validated_barriers"] == 0
    assert set(result["endpoints"]) == {"collapse", "escape"}
    for name, first, last, drop in (
        ("collapse", "L2", "L37", "1141.44140625"),
        ("escape", "S2", "S26", "1141.470703125"),
    ):
        branch = result["endpoints"][name]
        assert branch["sheet"] == "Sheet1"
        assert (branch["initial_density"]["cell"], branch["terminal_density"]["cell"]) == (first, last)
        si = branch["readings"]["density_in_J_m3"]
        assert Decimal(si["start_minus_end_J_m3"]) == Decimal(drop)
        assert not si["exceeds_conditional_ceiling"]
        scaled = branch["readings"]["density_in_kJ_m3"]
        assert Decimal(scaled["start_minus_end_J_m3"]) == 1000 * Decimal(drop)
        assert scaled["drop_divided_by_ceiling"] == pytest.approx(6.742, abs=0.001)
        assert scaled["exceeds_conditional_ceiling"]


def test_constant_offset_cancels_for_both_hypotheses():
    start, end = Decimal("-31552.22265625"), Decimal("-32693.6640625")
    ceiling = continuum_limits()["conditional_drop_ceiling_J_m3"]
    result = endpoint_drop(start, end, ceiling)
    offset = Decimal("238050.125")
    assert endpoint_drop(start + offset, end + offset, ceiling) == result
    # This is the directed drop. An increase between endpoints cannot violate its upper bound.
    assert not endpoint_drop(end, start, ceiling)["density_in_kJ_m3"]["exceeds_conditional_ceiling"]


def test_untrusted_sources_cannot_supply_endpoints(tmp_path):
    with pytest.raises(AuditError):
        compare(tmp_path)

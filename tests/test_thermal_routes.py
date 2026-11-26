from decimal import Decimal
import json
from pathlib import Path

import pytest

from nagdiff.chen2026_audit import AuditError, FILES
from nagdiff.thermal_routes import BARRIER_FIELDS, main, run_sensitivity, thermal_log_odds


RAW = Path(__file__).resolve().parents[1] / "data/raw"
RATE = "assumed_prefactor_log10_escape_over_collapse_rate"
TIE = "log10_escape_over_collapse_prefactor_for_equal_rates"


def test_two_source_scales_and_prefactor_crossover():
    result = run_sensitivity(RAW)
    assert result["physical_unit_status"] == "physical_unit_unresolved"
    assert len(result["source_sha256"]) == 2
    plotted, si = (result["scenarios"][key] for key in BARRIER_FIELDS)
    # The publisher's plotted caches have rounded values. The conditional SI
    # calculation instead starts from the stored density and volume.
    assert float(plotted[RATE]) == pytest.approx(-70145.39923238666, rel=1e-12)
    assert float(si[RATE]) == pytest.approx(-70.14539923238745, rel=1e-12)
    assert float(plotted[TIE]) / float(si[TIE]) == pytest.approx(1000, rel=1e-12)
    assert Decimal(si["barrier_gap_escape_minus_collapse_J"]) == Decimal("4.45993119140625e-19")

    for scenario in [plotted, si]:
        args = (scenario["collapse_barrier_pJ"], scenario["escape_barrier_pJ"], 200)
        assert Decimal(thermal_log_odds(*args, scenario[TIE])[RATE]) == 0
        assert Decimal(thermal_log_odds(*args, float(scenario[TIE]) + 1)[RATE]) > 0


def test_temperature_scaling_sign_and_symmetry():
    a = thermal_log_odds(1, 2, 160)
    b = thermal_log_odds(2, 1, 160)
    warmer = thermal_log_odds(1, 2, 320)
    assert float(a[RATE]) == pytest.approx(2 * float(warmer[RATE]))
    assert float(a[RATE]) == -float(b[RATE])
    tie = thermal_log_odds("0e-12", 0, 1, -4)
    assert Decimal(tie[TIE]).is_zero()
    assert Decimal(tie[RATE]) == -4


def test_log_domain_handles_extreme_rate_suppression():
    result = thermal_log_odds(0, 1, "1e-400")
    assert Decimal(result[RATE]).is_finite()
    assert Decimal(result[RATE]) < Decimal("-1e400")


@pytest.mark.parametrize("collapse,escape,temp,prefactor", [
    (-1, 0, 200, 0), (0, "NaN", 200, 0), (0, 1, 0, 0),
    (0, 1, -2, 0), (0, 1, "1 K", 0), (0, 1, 200, "Infinity"),
    (0, 1, "1e-9999999", 0),
])
def test_rejects_invalid_physical_or_numerical_inputs(collapse, escape, temp, prefactor):
    with pytest.raises(ValueError):
        thermal_log_odds(collapse, escape, temp, prefactor)


def test_cli_honors_inputs_and_refuses_unpinned_workbook(tmp_path, capsys):
    main(["--raw", str(RAW), "--temperature-k", "300", "--log10-prefactor-ratio", "2"])
    report = json.loads(capsys.readouterr().out)
    assert (report["temperature_K"], report["assumed_log10_escape_over_collapse_prefactor"]) == ("300", "2")
    for scenario in report["scenarios"].values():
        assert float(scenario[RATE]) == pytest.approx(2 - float(scenario[TIE]))

    for filename in FILES.values():
        (tmp_path / filename).write_bytes((RAW / "nature_source_data" / filename).read_bytes())
    path = tmp_path / list(FILES.values())[1]
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(AuditError, match="Checksum"):
        run_sensitivity(tmp_path)

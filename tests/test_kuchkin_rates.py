"""Independent visual landmarks and a rate-sum identity for the external figure."""
import pytest

from scripts.check_kuchkin_rates import measure


def test_route_ratio_and_total_trace_in_external_htst_figure():
    result = measure()
    times = result["inverse_rates_and_total_lifetime_reduced_units"]
    # Direct visual estimates from logarithmic grid lines and curve positions.
    assert times["escape"] == pytest.approx(4000, rel=0.02)
    assert times["decay"] == pytest.approx(1800, rel=0.02)
    assert times["total"] == pytest.approx(1250, rel=0.02)
    assert result["escape_over_decay_rate"] == pytest.approx(times["decay"] / times["escape"])
    assert result["total_line_residual_px"] < 1

    main = result["escape_over_decay_pixel_range"]
    inset = result["barrier_exponential_only_pixel_range"]
    assert inset[0] < result["barrier_exponential_only_escape_over_decay_rate"] < inset[1]
    assert main[0] < result["escape_over_decay_rate"] < main[1]
    assert inset[1] < main[0] < main[1] < 1
    assert result["inferred_escape_over_decay_prefactor"] == pytest.approx(1.84, rel=0.02)
    assert result["prefactor_pixel_range"][0] > 1


def test_figure_hash_rejected_before_measurement(tmp_path):
    path = tmp_path / "unverified.png"
    path.write_bytes(b"different figure")
    with pytest.raises(ValueError, match="SHA-256"):
        measure(path)

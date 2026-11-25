"""Thermal rate sensitivity for two competing exits from a hopfion.

For two stationary activated routes, k_i = nu_i * exp(-B_i / (k_B T)).
This reports log10(k_escape / k_collapse) under each of the publisher workbook's
possible physical energy scales. All temperatures and prefactors are model inputs.
The illustration holds the barriers fixed as T varies.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, DecimalException, Underflow, localcontext
import json
from pathlib import Path

from .chen2026_audit import AuditError, audit_publisher_pair


# The SI defines this value exactly. https://physics.nist.gov/cuu/Constants/Value/k.html
BOLTZMANN_J_PER_K = Decimal("1.380649e-23")
JOULES_PER_PJ = Decimal("1e-12")
BARRIER_FIELDS = ("conditional_pJ_if_header_scale", "conditional_pJ_if_SI_density_and_volume")


def _decimal(value, name):
    try:
        number = Decimal(str(value))
    except DecimalException as exc:
        raise ValueError(f"{name} must be a finite decimal number") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be a finite decimal number")
    return number


def thermal_log_odds(collapse_pj, escape_pj, temperature_k, log10_prefactor_ratio=0):
    """Return decimal strings to preserve logarithms outside binary64 range.

    The optional prefactor ratio is supplied as log10(nu_escape / nu_collapse).
    A positive output log rate ratio favors escape. A zero gives equal rates.
    """
    collapse = _decimal(collapse_pj, "collapse barrier")
    escape = _decimal(escape_pj, "escape barrier")
    temperature = _decimal(temperature_k, "temperature")
    prefactor_log = _decimal(log10_prefactor_ratio, "log10 prefactor ratio")
    if min(collapse, escape) < 0 or temperature <= 0:
        raise ValueError("barriers must be nonnegative and temperature in kelvin must be positive")
    try:
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.traps[Underflow] = True
            gap_j = (escape - collapse) * JOULES_PER_PJ
            gap_in_kbt = gap_j / (BOLTZMANN_J_PER_K * temperature)
            crossover = gap_in_kbt / Decimal(10).ln()
            actual_log = prefactor_log - crossover
            return {
                "barrier_gap_escape_minus_collapse_J": str(gap_j),
                "barrier_gap_in_kBT": str(gap_in_kbt),
                "equal_prefactor_log10_escape_over_collapse_rate": str(-crossover),
                "log10_escape_over_collapse_prefactor_for_equal_rates": str(crossover),
                "assumed_prefactor_log10_escape_over_collapse_rate": str(actual_log),
            }
    except DecimalException as exc:
        raise ValueError("thermal calculation exceeds the supported decimal range") from exc


def run_sensitivity(raw_dir, temperature_k=200, log10_prefactor_ratio=0):
    """Verify the publisher pair before evaluating the two unit interpretations."""
    audit = audit_publisher_pair(Path(raw_dir))
    paths = {p["path"]: p for p in audit["paths"]}
    scenarios = {}
    for field in BARRIER_FIELDS:
        collapse = paths["collapse"][field]
        escape = paths["escape"][field]
        scenarios[field] = {
            "collapse_barrier_pJ": collapse,
            "escape_barrier_pJ": escape,
            **thermal_log_odds(collapse, escape, temperature_k, log10_prefactor_ratio),
        }
    return {
        "status": "conditional_thermal_sensitivity",
        "physical_unit_status": audit["status"],
        "source_sha256": {s["filename"]: s["sha256"] for s in audit["sources"]},
        "temperature_K": str(temperature_k),
        "assumed_log10_escape_over_collapse_prefactor": str(log10_prefactor_ratio),
        "boltzmann_J_per_K": str(BOLTZMANN_J_PER_K),
        "scenarios": scenarios,
        "scope": "Stationary, isothermal two-route model with fixed barriers and supplied "
                 "effective prefactors. The output is a conditional rate ratio. Absolute "
                 "lifetimes and route frequencies for a laser pulse require additional data.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--temperature-k", default="200", help="positive temperature, in kelvin (default: 200)")
    parser.add_argument("--log10-prefactor-ratio", default="0", help="log10(nu_escape / nu_collapse), default 0")
    args = parser.parse_args(argv)
    try:
        report = run_sensitivity(args.raw, args.temperature_k, args.log10_prefactor_ratio)
    except (AuditError, ValueError) as exc:
        parser.exit(2, f"thermal routes: {exc}\n")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

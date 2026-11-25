"""Test the two conditional density scales against an offset-independent endpoint bound.

From the repository root: python -m scripts.check_endpoint_scale
The bound concerns the drop from the initial hopfion to the terminal helical
state. See docs/endpoint_energy_bound.md for the continuum-model assumptions.
"""
import argparse
from decimal import Decimal
import json
import math
from pathlib import Path

from nagdiff.chen2026_audit import AuditError, audit_publisher_pair


def continuum_limits():
    """Energy densities in J/m³ for Chen et al. Eqs. 3 and 8 at zero applied field."""
    stiffness = 4.75e-12  # J/m
    dmi = 0.853e-3  # J/m²
    saturation = 384e3  # A/m
    mu0 = 4 * math.pi * 1e-7  # H/m, at the precision of the material parameters
    kappa = 76.54  # J/m³, approximate value quoted in the paper
    exchange_dmi_floor = -dmi**2 / (2 * stiffness)
    magnetic_floor = -mu0 * saturation**2 / 2
    lower = exchange_dmi_floor + magnetic_floor
    return {
        "exchange_DMI_floor_J_m3": exchange_dmi_floor,
        "magnetostatic_floor_J_m3": magnetic_floor,
        "terminal_floor_J_m3": lower,
        "conditional_initial_ceiling_J_m3": kappa,
        "conditional_drop_ceiling_J_m3": kappa - lower,
    }


def endpoint_drop(start, end, ceiling):
    raw_drop = Decimal(start) - Decimal(end)
    readings = {}
    for scale, multiplier in (("density_in_J_m3", 1), ("density_in_kJ_m3", 1000)):
        value = raw_drop * multiplier
        readings[scale] = {
            "start_minus_end_J_m3": str(value),
            "drop_divided_by_ceiling": float(value) / ceiling,
            "exceeds_conditional_ceiling": float(value) > ceiling,
        }
    return readings


def compare(raw_dir):
    audit = audit_publisher_pair(Path(raw_dir))
    limits = continuum_limits()
    endpoints = {}
    for branch in audit["paths"]:
        if branch["path"] in ("collapse", "escape"):
            initial = branch["initial_minimum"]["density"]
            terminal = branch["final_image"]["density"]
            endpoints[branch["path"]] = {
                "sheet": branch["sheet"], "filename": branch["filename"],
                "source_sha256": branch["source_sha256"],
                "initial_density": initial, "terminal_density": terminal,
                "readings": endpoint_drop(initial["raw"], terminal["raw"], limits["conditional_drop_ceiling_J_m3"]),
            }

    return {
        "publication_doi": audit["doi"], "comparison": "loss_route_start_minus_terminal_density",
        "physical_unit_status": audit["status"], "validated_barriers": audit["validated_count"],
        "limits": limits, "endpoints": endpoints,
        "assumptions": [
            "Initial state has zero fourth component everywhere and is a local minimum against its uniform S³ variation.",
            "Zero external field, free faces, allowed variation in all layers, bulk-bounded material scales, and no extra surface energy.",
            "Eqs. 3 and 8 describe the energy differences, with consistent normalization and a common additive offset per path.",
            "The continuum bound applies to the implementation at the accuracy needed for this comparison.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)
    try:
        result = compare(args.raw)
    except AuditError as exc:
        parser.exit(2, f"Source audit failed: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()

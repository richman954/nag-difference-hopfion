"""Compare the publisher's stored inputs with a historically dated RGNEB writer.

Run from any directory. The optional workbook argument defaults to Source Data
Fig. 5 bundled with this repository. Use --solver-checkout with a clone of
https://github.com/kuchkin/mumax3-gneb to verify the two historical versions
of the writer. The command requires only the Python standard library.
"""

import argparse
from decimal import Decimal as D
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import struct
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile


XLSX_SHA = "134949b49338512245559e0110a809cb29482978639227e4b5b10e594c88c7cc"
DEFAULT_WORKBOOK = (Path(__file__).resolve().parents[1] / "data" / "raw" / "nature_source_data"
                    / "41567_2026_3236_MOESM13_ESM.xlsx")
SUBMITTED = "ce2ba57ba23d1e982cff20ef4643c770424617cb"
WORKBOOK_ERA = "b15ee29d1999a1bc63ee92d4f7e1884895f3bbb2"
SOLVER_FILE = "engine/vpo_minimizer.go"
SOLVER_FILE_SHA = "c90c7d4c2307f8d5d236402c9671403cc46384ec26426c4eee85362ff69306b7"
BRANCHES = {
    "merger": ("B", "C", "E", "G", 30),
    "collapse": ("I", "J", "L", "N", 37),
    "escape": ("P", "Q", "S", "U", 26),
}


def binary32(value):
    return struct.unpack(">f", struct.pack(">f", float(value)))[0]


def neighbors(value):
    """Both bracketing floats and the nearest one for these finite nonzero inputs."""
    bits, = struct.unpack(">I", struct.pack(">f", value))
    return [struct.unpack(">f", struct.pack(">I", n))[0] for n in (bits - 1, bits, bits + 1)]


def matching_export(raw, divisor, transform):
    """Compare alternative unit pipelines at the resolution of the stored density."""
    # The transforms are monotone. Only candidates bracketing the inverse
    # image can produce the closest rounded output; a wider search adds none.
    candidates = neighbors(float(raw) * divisor)
    return any(D.from_float(transform(v)) == raw for v in candidates)


def fmt_compatible(raw):
    """Writer's %.15f, 15-significant-digit input rounding, binary64 XML roundtrip."""
    value = binary32(raw)
    printed = D(f"{value:.15f}")
    decimal_quantum = D(1).scaleb(printed.adjusted() - 14)
    serialization_error = D.from_float(math.ulp(float(printed)))
    return abs(raw - printed) <= decimal_quantum / 2 + serialization_error


def verify_solver(checkout):
    digests = {}
    for ref in (SUBMITTED, WORKBOOK_ERA):
        data = subprocess.check_output(["git", "-C", str(checkout), "show", f"{ref}:{SOLVER_FILE}"])
        digest = sha256(data).hexdigest()
        if digest != SOLVER_FILE_SHA:
            raise ValueError(f"Unexpected solver file at {ref}")
        digests[ref] = digest
    return digests


def audit(path):
    data = path.read_bytes()
    if sha256(data).hexdigest() != XLSX_SHA:
        raise ValueError("Publisher workbook SHA-256 mismatch")
    with ZipFile(BytesIO(data)) as workbook:
        root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        props = ET.fromstring(workbook.read("docProps/core.xml"))
    cells = {
        c.attrib["r"]: c.findtext("{*}v")
        for c in root.findall(".//{*}sheetData/{*}row/{*}c")
    }
    missing = {name: [] for name in ("float64_div1000", "float32_div1000", "float32_reciprocal_mul")}
    result = {}
    for name, (image_col, distance_col, density_col, diagnostic_col, stop) in BRANCHES.items():
        matches = {"consecutive_image_id": 0, "density_exact_binary32": 0,
                   "field_compatible_printf_and_sheet": 0, "distance_compatible_printf_and_sheet": 0}
        distances = []
        for r in range(2, stop + 1):
            key = density_col + str(r)
            density = D(cells[key])
            matches["consecutive_image_id"] += D(cells[image_col + str(r)]) == r - 2
            matches["density_exact_binary32"] += D.from_float(binary32(density)) == density
            matches["field_compatible_printf_and_sheet"] += fmt_compatible(D(cells[diagnostic_col + str(r)]))
            distance = D(cells[distance_col + str(r)])
            matches["distance_compatible_printf_and_sheet"] += fmt_compatible(distance)
            distances.append(binary32(distance))
            # If workbook energies really denote pJ with SI volume, its raw density
            # is 1/1000 of native J/m^3. Check specific ways of doing that rescale.
            tests = [
                ("float64_div1000", 1000, lambda x: x / 1000),
                ("float32_div1000", 1000, lambda x: binary32(x / 1000)),
                ("float32_reciprocal_mul", 1 / binary32(0.001),
                 lambda x: binary32(x * binary32(0.001))),
            ]
            for mode, inverse_scale, transform in tests:
                if not matching_export(density, inverse_scale, transform):
                    missing[mode].append(key)
        tail = [distances[-2] - distances[-3], distances[-1] - distances[-2]]
        result[name] = {"points":stop-1, **matches, "last_two_distance_increments":tail,
                        "nonzero_first_cumulative_distance":distances[0]}
    return {"source_sha256": XLSX_SHA, "source_sheet": "Sheet1",
            "metadata_created":props.findtext("{*}created"), "metadata_modified":props.findtext("{*}modified"),
            "paths":result, "unreachable_density_cells_under_1000_scaling":missing,
            "interpretation":"The export units and numerical signatures favor direct native SI densities. "
                             "A solver build, simulation inputs and original unedited run outputs would "
                             "establish the missing publication-specific provenance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, nargs="?", default=DEFAULT_WORKBOOK)
    parser.add_argument("--solver-checkout", type=Path, help="Path to the solver Git repository")
    args = parser.parse_args()
    try:
        result = audit(args.workbook)
        if args.solver_checkout:
            result["solver_file_sha256_at_two_revisions"] = verify_solver(args.solver_checkout)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

"""Read the two route rates at T/(J/k_B)=0.8 in Kuchkin et al. Fig. 4B.

The main panel gives inverse HTST rates. The inset gives the inverse
Arrhenius exponential alone. These are model curves for a chiral film.
"""
import argparse
from hashlib import sha256
from io import BytesIO
from itertools import product
import json
import math
from pathlib import Path
from statistics import linear_regression, median


DEFAULT_CROP = Path(__file__).resolve().parents[1] / 'data/raw/kuchkin_2023/fig4b.png'
CROP_SHA256 = 'cfb062e3bc730349dbd793f8c97d514bdc368b71e9d2669ec91dafdf578cd06f'


def _line_fit(pixels, center_x, rows, color):
    """Fit per-column stroke centers across one full dash period on either side."""
    xs, ys = [], []
    for x in range(round(center_x) - 13, round(center_x) + 14):
        matches = []
        for y in rows:
            r, g, b = pixels[x, y]
            if color == "red":
                on_line = r - g > 55 and r - b > 60
            elif color == "blue":
                on_line = b - r > 30 and b - g > 12
            else:
                on_line = max(r, g, b) < 100 and max(r, g, b) - min(r, g, b) < 18
            if on_line:
                matches.append(y)
        if matches:
            xs.append(x - center_x)
            ys.append(median(matches))
    if len(xs) < 8 or min(xs) >= 0 or max(xs) <= 0:
        raise ValueError(f"Insufficient {color} stroke on both sides of the sampling column")
    return linear_regression(xs, ys)


def _odds(escape_line, decay_line, pixels_per_decade, grid_decades):
    # k_escape / k_decay = (1/k_decay)/(1/k_escape). Row increases downward.
    gap = escape_line.intercept - decay_line.intercept
    nom = 10 ** (gap / pixels_per_decade)
    # Independent one-pixel center errors for the two curves, common ±1 px
    # horizontal error, and ±0.5 px errors at each of the two gridline anchors.
    bounds = []
    for dx, dg, dp in product((-1, 1), (-2, 2), (-1, 1)):
        total_gap = gap + dx * (escape_line.slope - decay_line.slope) + dg
        bounds.append(10 ** (total_gap / (pixels_per_decade + dp / grid_decades)))
    return nom, [min(bounds), max(bounds)]


def measure(path=DEFAULT_CROP):
    data = Path(path).read_bytes()
    if sha256(data).hexdigest() != CROP_SHA256:
        raise ValueError("Figure 4B crop SHA-256 does not match")
    from PIL import Image
    from PIL import Image
    with Image.open(BytesIO(data)) as image:
        rgb = image.convert("RGB")
    pixels = rgb.load()
    # Native RGB crop coordinates. The 0.8 tick has its own gridline in each
    # panel. Main 10^3 and 10^9 gridlines at y=627.5 and 217.0, respectively.
    # Inset 10^2 and 10^9 gridlines at y=317.75 and 78.0.
    main_x, inset_x = 707.5, 756.5
    main_step = (627.5 - 217.0) / 6
    inset_step = (317.75 - 78.0) / 7
    main = {k: _line_fit(pixels, main_x, range(572, 626), color)
            for k, color in [('escape', 'blue'), ('decay', 'red'), ('total', 'black')]}
    inset = {k: _line_fit(pixels, inset_x, range(326, 363), color)
             for k, color in [('escape', 'blue'), ('decay', 'red')]}
    main_vals = {k: 10 ** (3 + (627.5 - line.intercept) / main_step)
                 for k, line in main.items()}
    main_odds, main_bounds = _odds(main['escape'], main['decay'], main_step, 6)
    exp_odds, exp_bounds = _odds(inset['escape'], inset['decay'], inset_step, 7)
    summed_tau = 1 / (1 / main_vals['escape'] + 1 / main_vals['decay'])
    return {
        'doi': '10.3389/fphy.2023.1201018', 'figure': '4B', 'reduced_temperature': 0.8,
        'crop_sha256': CROP_SHA256, 'source_type': 'external theoretical HTST curves',
        'main_stroke_centers_px': {k: line.intercept for k, line in main.items()},
        'inset_stroke_centers_px': {k: line.intercept for k, line in inset.items()},
        'inverse_rates_and_total_lifetime_reduced_units': main_vals,
        'total_lifetime_from_sum_of_rates': summed_tau,
        'total_line_residual_px': main_step * abs(math.log10(summed_tau / main_vals['total'])),
        'escape_over_decay_rate': main_odds, 'escape_over_decay_pixel_range': main_bounds,
        'barrier_exponential_only_escape_over_decay_rate': exp_odds,
        'barrier_exponential_only_pixel_range': exp_bounds,
        'inferred_escape_over_decay_prefactor': main_odds / exp_odds,
        'prefactor_pixel_range': [main_bounds[0] / exp_bounds[1], main_bounds[1] / exp_bounds[0]],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('crop', nargs='?', type=Path, default=DEFAULT_CROP)
    args = parser.parse_args()
    try:
        print(json.dumps(measure(args.crop), indent=2))
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(2, f"Figure 4B check: {exc}\n")

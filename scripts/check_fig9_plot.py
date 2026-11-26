"""Digitize the three MEP plots in Chen et al., Extended Data Fig. 9 (2026).

Usage: python scripts/check_fig9_plot.py 41567_2026_3236_Fig15_ESM.jpg
Dependencies: NumPy and Pillow. This check reads only the original plotted JPEG.
Source: https://media.springernature.com/full/springer-static/esm/art%3A10.1038%2Fs41567-026-03236-0/MediaObjects/41567_2026_3236_Fig15_ESM.jpg
"""
import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path


FIGURE_SHA256 = "43d18dc628ffc3a700a38bd105609daab3a3451596f8e03c071f1790e0fd258d"


def measure(image_path):
    import numpy as np
    from PIL import Image, ImageFilter

    contents = Path(image_path).read_bytes()
    if sha256(contents).hexdigest() != FIGURE_SHA256:
        raise ValueError("Expected the publisher's original Extended Data Fig. 9 JPEG.")
    with Image.open(BytesIO(contents)) as image:
        rgb_image = image.convert("RGB")

    # Grid centers in original pixel coordinates. Each panel spans seven 0.001-pJ
    # ticks on the published scale. Each pair gives the top and bottom grid center.
    panels = [
        ("merger", (37, 77, 138), 30.5, 1541.5, 29),
        ("collapse", (252, 65, 22), 1851.5, 3363.5, 36),
        ("escape", (235, 209, 52), 3693.0, 5204.5, 25),
    ]
    for name, color, top, bottom, count in panels:
        left, right = 310, 1580
        region = np.asarray(rgb_image.crop((left, int(top), right, int(bottom) + 1)), dtype=np.int16)
        colored = np.abs(region - np.array(color, dtype=np.int16)).max(axis=2) < 50
        # Erode away narrow connecting lines. Each filled marker retains a center.
        binary_image = Image.fromarray(colored).convert("L")
        centers = np.asarray(binary_image.filter(ImageFilter.MinFilter(15))) > 0
        columns = np.flatnonzero(centers.any(axis=0))
        marker_groups = np.split(columns, np.where(np.diff(columns) != 1)[0] + 1)
        points = []
        for group in marker_groups:
            if len(group) < 3:
                continue
            rows = np.where(centers[:, group])[0]
            points.append((float(np.median(group)) + left, float(np.median(rows)) + int(top)))
        if len(points) != count:
            raise ValueError(f"{name}: recovered {len(points)} of {count} visible markers")
        # Pixel y increases down the image, so the highest plotted energy has least y.
        peak = min(range(count), key=lambda i: points[i][1])
        rise_pixels = points[0][1] - points[peak][1]
        rise_pj_on_plot = rise_pixels * 0.007 / (bottom - top)
        print(f"{name}: {count} markers, apex image {peak}, rise {rise_pixels:g} px, "
              f"printed-axis rise {rise_pj_on_plot:.7f} pJ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jpeg", type=Path)
    path = parser.parse_args().jpeg
    try:
        measure(path)
    except ModuleNotFoundError:
        parser.exit(2, "Install numpy and Pillow to run this optional plot check.\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    main()

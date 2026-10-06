#!/usr/bin/env python3
"""
Trims a band's (k, E) data down to a window around its extremum (minimum for
conduction bands, maximum for valence bands) and overwrites the file in place
with that window.

Mode is inferred from the filename prefix produced by Kohn-Sham-States-Extraction.py
("CB..." -> minimum, "VB..." -> maximum), or can be forced with --mode.
The half-window size (points kept on each side of the extremum) comes from
material_config.json's settings.points_around_extremum (default 25), which
the web app's parameter form calls "fitting window (points around
extremum)" and applies identically whether the direction was auto-detected
or manually configured.

Unmodified from the validated one-off toolkit.
"""

import sys
import os
import json
import numpy as np


def infer_mode(filename):
    base = os.path.basename(filename)
    if base.startswith("CB"):
        return "min"
    if base.startswith("VB"):
        return "max"
    raise ValueError(
        f"Cannot infer min/max mode from filename '{filename}' "
        "(expected it to start with 'CB' or 'VB'); pass --mode min|max explicitly."
    )


def process_file(filename, mode, half_window):
    try:
        data = np.loadtxt(filename)
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return

    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] < 2:
        print(f"Error: File {filename} must contain at least 2 columns")
        return

    extreme_value = np.min(data[:, 1]) if mode == "min" else np.max(data[:, 1])
    idx = np.where(data[:, 1] == extreme_value)[0]
    first_idx, last_idx = idx[0], idx[-1]
    k_at_extreme = data[idx, 0]

    start = max(0, first_idx - half_window)
    end = min(len(data), last_idx + half_window + 1)
    extracted = data[start:end]

    np.savetxt(filename, extracted, fmt="%.5f")

    with open("Extracted-max-min-values-with-kpoint.txt", "a") as f:
        f.write(f"File: {filename}\n")
        label = "Minimum" if mode == "min" else "Maximum"
        f.write(f"{label} energy value: {extreme_value}\n")
        f.write(f"Number of successive occurrences: {len(idx)}\n")
        f.write("Corresponding wave vector(s): " + ", ".join(f"{v}" for v in k_at_extreme) + "\n")
        f.write(f"Extracted data range: rows {start} to {end - 1}\n")
        f.write("---\n\n")

    print(f"[{mode}] {filename}: extremum = {extreme_value:.6f} eV, kept rows {start}-{end - 1}")


def load_half_window():
    if os.path.exists("material_config.json"):
        with open("material_config.json") as f:
            return json.load(f)["settings"].get("points_around_extremum", 25)
    return 25


def main():
    args = sys.argv[1:]
    mode_override = None
    if "--mode" in args:
        i = args.index("--mode")
        mode_override = args[i + 1]
        del args[i:i + 2]

    if not args:
        print("Usage: python3 Extract-Extremum.py file1 [file2 ...] [--mode min|max]")
        sys.exit(1)

    half_window = load_half_window()

    for filename in args:
        mode = mode_override or infer_mode(filename)
        process_file(filename, mode, half_window)


if __name__ == "__main__":
    main()

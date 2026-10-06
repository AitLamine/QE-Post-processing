#!/usr/bin/env python3
"""
"Manual mode" counterpart to Detect-Configuration.py.

Auto mode (Detect-Configuration.py) parses the lattice constant and VBM/CBM
band indices from a full set of raw QE input/output files. Manual mode skips
that upload: the student instead types the lattice constant (Angstrom) and
the VBM band index directly, and uploads only the band-structure data file
(a full multi-band bands.x `.dat.gnu`, or a single already-extracted band
file with just one blank-line-delimited block).

This script writes material_config.json in EXACTLY the same schema that
Detect-Configuration.py produces (same top-level keys, same "lattice" and
"band_edges" sub-schemas), so every later pipeline step
(Kohn-Sham-States-Extraction.py onward) runs identically regardless of which
of the two scripts produced the file. Fields that auto mode derives from QE
files but manual mode has no source for (ibrav, celldm, nelec, noncolin) are
set to null and the source_file fields say "manually entered" instead of a
path, so provenance is still honest in the final README/info files.

Usage:
    python3 Manual-Configuration.py <band_data_file> <direction_label> \\
        <lattice_constant_angstrom> <vbm_band_index> \\
        [n_bands_below_vbm] [n_bands_above_cbm] [points_around_extremum] \\
        [material_label]

n_bands_below_vbm/n_bands_above_cbm/points_around_extremum/material_label are
optional and default the same way Detect-Configuration.py's
DEFAULT_SETTINGS/Pipeline-Settings.json do. Plot settings (axis range,
legend, figure format) are read from Pipeline-Settings.json if present in the
current directory, same as Detect-Configuration.py, so a single settings
payload from the API layer covers both modes.
"""

import sys
import os
import json

# Kept in sync with Detect-Configuration.py's DEFAULT_PLOT_SETTINGS. Duplicated
# (rather than imported) because "Detect-Configuration.py" is not a valid
# Python module name (hyphens) to import from without importlib gymnastics,
# and this dict is small and rarely changed.
DEFAULT_PLOT_SETTINGS = {
    "x_range": "",
    "y_range": "",
    "legend_show": True,
    "legend_label_data": "DFT data points",
    "legend_label_fit": "Fitted parabola",
    "legend_position": "best",
    "figure_format": "png",
    "template_path": None,
}


def main():
    if len(sys.argv) < 5:
        print(
            "Usage: python3 Manual-Configuration.py <band_data_file> <direction_label> "
            "<lattice_constant_angstrom> <vbm_band_index> "
            "[n_bands_below_vbm] [n_bands_above_cbm] [points_around_extremum] [material_label]"
        )
        sys.exit(1)

    band_data_file = sys.argv[1]
    direction_label = sys.argv[2]
    lattice_constant_angstrom = float(sys.argv[3])
    vbm_band_index = int(sys.argv[4])
    n_below = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    n_above = int(sys.argv[6]) if len(sys.argv) > 6 else 3
    points_around_extremum = int(sys.argv[7]) if len(sys.argv) > 7 else 25
    material_label = sys.argv[8] if len(sys.argv) > 8 else ""

    if not os.path.exists(band_data_file):
        print(f"ERROR: band data file not found: {band_data_file}")
        sys.exit(1)

    plot_settings = dict(DEFAULT_PLOT_SETTINGS)
    settings = {
        "n_bands_below_vbm": n_below,
        "n_bands_above_cbm": n_above,
        "points_around_extremum": points_around_extremum,
        "material_label": material_label,
        "plot": plot_settings,
    }
    if os.path.exists("Pipeline-Settings.json"):
        with open("Pipeline-Settings.json") as f:
            raw = json.load(f)
        raw.pop("direction_overrides", None)
        plot_override = raw.pop("plot", None)
        settings.update(raw)
        if plot_override:
            plot_settings.update(plot_override)
        settings["plot"] = plot_settings
        # CLI args still win over Pipeline-Settings.json for the values a
        # student actually typed into the manual-mode form.
        settings["n_bands_below_vbm"] = n_below
        settings["n_bands_above_cbm"] = n_above
        settings["points_around_extremum"] = points_around_extremum
        if material_label:
            settings["material_label"] = material_label

    vbm_index = vbm_band_index
    cbm_index = vbm_index + 1
    valence_indices = [vbm_index - k for k in range(n_below)]
    conduction_indices = [cbm_index + k for k in range(n_above)]

    if min(valence_indices) < 1:
        print(
            f"ERROR: Requested {n_below} valence bands below the typed VBM index "
            f"(band #{vbm_index}) but that goes below band 1. Reduce "
            "n_bands_below_vbm or increase the VBM index."
        )
        sys.exit(1)

    lattice = {
        "lattice_axis_used": "manual",
        "ibrav": None,
        "celldm1_bohr": None,
        "celldm3_ratio": None,
        "a_angstrom": None,
        "c_angstrom": None,
        "lattice_constant_angstrom": lattice_constant_angstrom,
        "source_file": "manually entered",
        "kpath_source_file": "manually entered",
        "manual_entry": True,
    }

    band_edges = {
        "nelec": None,
        "noncolin": None,
        "vbm_index": vbm_index,
        "cbm_index": cbm_index,
        "valence_band_indices": valence_indices,
        "conduction_band_indices": conduction_indices,
        "source_file": "manually entered",
        "manual_entry": True,
    }

    resolved_material_label = settings.get("material_label") or ""

    config = {
        "direction_dir": os.path.dirname(band_data_file) or ".",
        "direction_label": direction_label,
        "material_label": resolved_material_label,
        "band_gnu_file": band_data_file,
        "settings": settings,
        "lattice": lattice,
        "band_edges": band_edges,
        "detection_mode": "manual",
    }

    with open("material_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("=" * 70)
    print(f"Manually-entered configuration: {direction_label}")
    print("=" * 70)
    print(f"Settings used         : n_bands_below_vbm={n_below} "
          f"n_bands_above_cbm={n_above} points_around_extremum={points_around_extremum}")
    print(f"Material label        : {resolved_material_label or '(none)'}")
    print(f"Band data file        : {band_data_file}")
    print(f"Lattice constant (typed, Ang): {lattice_constant_angstrom:.6f}")
    print(f"VBM band index (typed) : {vbm_index}   CBM band index: {cbm_index}")
    print(f"Valence bands (top->down)    : {valence_indices}")
    print(f"Conduction bands (bottom->up): {conduction_indices}")
    print("Saved to material_config.json")


if __name__ == "__main__":
    main()

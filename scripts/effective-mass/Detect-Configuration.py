#!/usr/bin/env python3
"""
Auto-discovers, for a given direction folder, everything the rest of the
pipeline needs: the band .dat.gnu file, the lattice constant to use for the
effective-mass conversion (a or c, depending on the k-path direction), and
which band indices are the VBM/CBM neighborhood.

Writes material_config.json into the current working directory, consumed by
every later step (Kohn-Sham-States-Extraction.py onward). This is the "Auto
mode" entry point of the GUI pipeline (see Manual-Configuration.py for the
"Manual mode" entry point that produces the same material_config.json schema
from typed values instead).

Ported from Detect-Configuration.py in the validated one-off toolkit, with one
addition: DEFAULT_SETTINGS now carries a "plot" sub-dict (figure axis
range/legend/format settings for the new GUI plotting options) so it always
ends up embedded in material_config.json's "settings" key, exactly like every
other pipeline setting, for Kohn-Sham-States-Polynomial-Fitting-Script.py to
read later.
"""

import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qe_parsing_utils import (
    find_band_gnu_file,
    resolve_lattice_constant_angstrom,
    resolve_band_edge_indices,
    ConfigError,
)

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

DEFAULT_SETTINGS = {
    "n_bands_below_vbm": 3,
    "n_bands_above_cbm": 3,
    "points_around_extremum": 25,
    "material_label": "",
    "plot": dict(DEFAULT_PLOT_SETTINGS),
}


def guess_material_label(band_gnu_file):
    """
    Best-effort guess of the material name from the QE prefix, e.g.
    'Bulk-ZnTe-Wurtzite-PBESOL-Bands.dat.gnu' -> 'ZnTe'. Only used when
    material_label is left blank in Pipeline-Settings.json.
    """
    base = os.path.basename(band_gnu_file)
    m = re.search(r"Bulk-([A-Za-z0-9]+)-Wurtzite", base)
    return m.group(1) if m else None


def load_settings(direction_label):
    """
    Loads Pipeline-Settings.json and applies any per-direction override for
    this direction_label. Top-level keys (n_bands_below_vbm,
    n_bands_above_cbm, points_around_extremum, plot) set the default for
    every direction; "direction_overrides"."<Direction-Label>" overrides just
    that one direction - e.g. to use a narrower/wider fitting window for a
    single k-path without changing the others.
    """
    settings = dict(DEFAULT_SETTINGS)
    settings["plot"] = dict(DEFAULT_PLOT_SETTINGS)

    if os.path.exists("Pipeline-Settings.json"):
        with open("Pipeline-Settings.json") as f:
            raw = json.load(f)

        overrides = raw.pop("direction_overrides", {})
        plot_override = raw.pop("plot", None)
        settings.update(raw)
        if plot_override:
            settings["plot"].update(plot_override)

        direction_specific = overrides.get(direction_label, {})
        direction_plot = direction_specific.pop("plot", None)
        settings.update(direction_specific)
        if direction_plot:
            settings["plot"].update(direction_plot)

    return settings


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 Detect-Configuration.py <direction_dir> <direction_label>")
        print("Example: python3 Detect-Configuration.py "
              "Calculations-Results-All-Directions/Calculations-Results-First-Direction First-Direction")
        sys.exit(1)

    direction_dir, direction_label = sys.argv[1], sys.argv[2]
    settings = load_settings(direction_label)

    try:
        band_gnu = find_band_gnu_file(direction_dir)
        lattice = resolve_lattice_constant_angstrom(direction_dir)
        edges = resolve_band_edge_indices(
            direction_dir, settings["n_bands_below_vbm"], settings["n_bands_above_cbm"]
        )
    except ConfigError as e:
        print(f"ERROR while auto-detecting configuration for {direction_dir}:")
        print(f"  {e}")
        sys.exit(1)

    material_label = settings.get("material_label") or guess_material_label(band_gnu) or ""

    config = {
        "direction_dir": direction_dir,
        "direction_label": direction_label,
        "material_label": material_label,
        "band_gnu_file": band_gnu,
        "settings": settings,
        "lattice": lattice,
        "band_edges": edges,
    }

    with open("material_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("=" * 70)
    print(f"Auto-detected configuration: {direction_label}")
    print("=" * 70)
    print(f"Settings used         : n_bands_below_vbm={settings['n_bands_below_vbm']} "
          f"n_bands_above_cbm={settings['n_bands_above_cbm']} "
          f"points_around_extremum={settings['points_around_extremum']}")
    label_note = "" if settings.get("material_label") else " (guessed from band file name)"
    print(f"Material label        : {material_label or '(none)'}{label_note}")
    print(f"Band data file        : {band_gnu}")
    print(f"ibrav                 : {lattice['ibrav']}")
    axis_note = "in-plane (a)" if lattice["lattice_axis_used"] == "a" else "c-axis (Gamma-A path)"
    print(f"K-path axis detected  : {lattice['lattice_axis_used']}  [{axis_note}]")
    a_line = f"a = {lattice['a_angstrom']:.6f} Ang"
    c_line = f"  c = {lattice['c_angstrom']:.6f} Ang" if lattice["c_angstrom"] else ""
    print(a_line + c_line)
    print(f"-> lattice constant used for m*: {lattice['lattice_constant_angstrom']:.6f} Ang "
          f"(from {lattice['source_file']})")
    print(f"nelec={edges['nelec']}  noncolin={edges['noncolin']}  "
          f"VBM band #{edges['vbm_index']}  CBM band #{edges['cbm_index']}")
    print(f"Valence bands (top->down)    : {edges['valence_band_indices']}")
    print(f"Conduction bands (bottom->up): {edges['conduction_band_indices']}")
    print("Saved to material_config.json")


if __name__ == "__main__":
    main()

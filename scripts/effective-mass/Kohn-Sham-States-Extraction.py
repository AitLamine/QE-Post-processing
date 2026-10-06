#!/usr/bin/env python3
"""
Splits the band .dat.gnu file (blank-line-separated blocks, one per band)
and extracts the bands around the VBM/CBM identified by Detect-Configuration.py
(auto mode) or Manual-Configuration.py (manual mode).

Requires material_config.json in the current directory (run
Detect-Configuration.py or Manual-Configuration.py first). Unmodified from
the validated one-off toolkit: this step only reads generic
"band_gnu_file"/"band_edges" keys, so it never needs to know which mode
produced material_config.json.
"""

import json
import os
import sys


def extract_sections(band_gnu_file):
    sections = []
    current = []
    with open(band_gnu_file) as f:
        for line in f:
            if line.strip():
                current.append(line)
            else:
                if current:
                    sections.append(current)
                    current = []
    if current:
        sections.append(current)
    return sections


def main():
    if not os.path.exists("material_config.json"):
        print("ERROR: material_config.json not found. Run Detect-Configuration.py "
              "(auto mode) or Manual-Configuration.py (manual mode) first.")
        sys.exit(1)

    with open("material_config.json") as f:
        config = json.load(f)

    band_gnu_file = config["band_gnu_file"]
    edges = config["band_edges"]

    sections = extract_sections(band_gnu_file)

    max_needed = max(edges["conduction_band_indices"] + edges["valence_band_indices"])
    if len(sections) < max_needed:
        print(f"ERROR: {band_gnu_file} has only {len(sections)} bands/sections, "
              f"need at least {max_needed}. Reduce n_bands_below_vbm/n_bands_above_cbm "
              "in Pipeline-Settings.json (or the manual-mode form) or check the input file.")
        sys.exit(1)

    produced = []

    for rank, band_idx in enumerate(edges["valence_band_indices"], start=1):
        filename = f"VB{rank}-Valence-Band.dat"
        with open(filename, "w") as out:
            out.writelines(sections[band_idx - 1])
        produced.append(filename)

    for rank, band_idx in enumerate(edges["conduction_band_indices"], start=1):
        filename = f"CB{rank}-Conduction-Band.dat"
        with open(filename, "w") as out:
            out.writelines(sections[band_idx - 1])
        produced.append(filename)

    config["produced_band_files"] = produced
    with open("material_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"Extracted {len(produced)} band files from {band_gnu_file} "
          f"({len(sections)} total bands found):")
    for p in produced:
        print(f"  - {p}")


if __name__ == "__main__":
    main()

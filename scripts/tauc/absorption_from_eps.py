#!/usr/bin/env python3
"""epsr/epsi (real/imaginary dielectric function) -> per-axis absorption coefficient.

This replaces the subset of the ~20-script
`All-Scripts/0-Updated-V2-Scripts-Optical-Properties-Calculation/` folder (from the user's
validated one-off Tauc-gap pipeline) that is actually consumed downstream by the Tauc-plot /
band-gap extractor. Traced consumption chain in that folder's driver
(`Script-Optical-Properties-Calcualtion.sl`) plus the two `*-Global-Commands-*-Approach.sh`
scripts:

  12E-Copy-Columns-epsr.py + 13E-Copy-Columns-epsi.py
      -> strip the epsilon.x header, write "XYZ-epsr_<tag>.dat" / "XYZ-epsi_<tag>.dat"
         (these scripts ALSO wrote per-axis wavelength-space files, but nothing downstream in
         the Tauc pipeline reads them -- they feed the separate "Optical-magnitudes plotter"
         module instead, so that half is intentionally not ported here)
  18E-Absorption-Coefficient.py
      -> combines the two merged files into X/Y/Z-Absorption_Coefficient_<tag>.dat

14E (eels), 15E (reverse-lines), 16E/17E (refractive index / extinction coefficient), 19E-21E
(reflectivity/EELS/optical conductivity), and the whole "L" (In-Wavelength) family are NOT
needed for a Tauc gap and are out of scope for this module (they belong to the "Dielectric
function plotter" / "Optical-magnitudes plotter" candidate modules in the outline).

Physics (unchanged from the original, validated script):
    wavelength(nm) = h*c / (E(eV) * e * 1e-9)
    alpha_axis      = (4*pi / wavelength_nm) * (1/sqrt(2))
                       * sqrt( sqrt(epsr_axis**2 + epsi_axis**2) - epsr_axis )
                       * 1e7 * 1e-4                       # -> units of 10^4 / cm
Output: two columns (Energy(eV), Alpha[x10^4/cm]) per axis, matching what
`merge_absorption.py` (the port of `1-Absorption-Coefficient-Data-Processor.py`) expects.

Generalization vs. the original: the original stripped exactly `lines[3:]` (2 "#" header lines
plus the first E=0 data row) from the epsilon.x output, hardcoded to files that always look
like the validated corpus's files. Here we instead (a) skip every line starting with "#" and
(b) drop the first data row only if its energy is ~0 (avoids a division by zero in the
wavelength formula), which reproduces the exact original behavior on the corpus's own files
while tolerating epsilon.x output that doesn't have precisely two header lines.
"""

import argparse
import math
import os
import sys

H_PLANCK = 6.62607015e-34
C_LIGHT = 299792458
E_CHARGE = 1.60217663e-19


def _load_eps_file(path):
    """Return list of (energy, x, y, z) tuples from an epsilon.x-style file.

    Skips leading '#' comment lines and, if the first remaining row's energy is ~0, drops it
    too (the physics below divides by energy).
    """
    rows = []
    with open(path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            parts = stripped.split()
            if len(parts) < 4:
                continue
            rows.append(tuple(float(p) for p in parts[:4]))

    if not rows:
        raise ValueError(f"No numeric data rows found in {path}")

    if abs(rows[0][0]) < 1e-9:
        rows = rows[1:]

    if not rows:
        raise ValueError(f"{path} only contained a single (E=0) data row after filtering")

    return rows


def energy_to_wavelength_nm(energy_ev):
    return (H_PLANCK * C_LIGHT) / (energy_ev * E_CHARGE * 1e-9)


def compute_absorption(epsr_path, epsi_path, out_dir, tag, energy_tolerance=1e-3):
    """Write X/Y/Z-Absorption_Coefficient_<tag>.dat into out_dir. Returns the 3 output paths."""
    epsr_rows = _load_eps_file(epsr_path)
    epsi_rows = _load_eps_file(epsi_path)

    if len(epsr_rows) != len(epsi_rows):
        raise ValueError(
            "epsr and epsi files don't have the same number of data rows "
            f"({len(epsr_rows)} vs {len(epsi_rows)}). Make sure both files come from the same "
            "epsilon.x run."
        )

    os.makedirs(out_dir, exist_ok=True)
    out_paths = [os.path.join(out_dir, f"{axis}-Absorption_Coefficient_{tag}.dat") for axis in ('X', 'Y', 'Z')]
    handles = [open(p, 'w') for p in out_paths]

    try:
        for i, (er, ei) in enumerate(zip(epsr_rows, epsi_rows)):
            e_r, x_r, y_r, z_r = er
            e_i, x_i, y_i, z_i = ei

            if abs(e_r - e_i) > energy_tolerance:
                raise ValueError(
                    "epsr and epsi energy grids don't line up at row "
                    f"{i} ({e_r} eV vs {e_i} eV). These files don't look like a matching "
                    "epsr/epsi pair from the same calculation."
                )

            wavelength_nm = energy_to_wavelength_nm(e_i)
            prefactor = (4 * math.pi / wavelength_nm) * (1 / math.sqrt(2)) * 1e7 * 1e-4

            for handle, eps_r_axis, eps_i_axis in zip(handles, (x_r, y_r, z_r), (x_i, y_i, z_i)):
                under_sqrt = math.sqrt(eps_r_axis ** 2 + eps_i_axis ** 2) - eps_r_axis
                alpha = prefactor * math.sqrt(max(under_sqrt, 0.0))
                handle.write(f"{e_i:12.5f}\t{alpha:12.5f}\n")
    finally:
        for handle in handles:
            handle.close()

    return out_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('epsr_file')
    parser.add_argument('epsi_file')
    parser.add_argument('out_dir')
    parser.add_argument('tag')
    args = parser.parse_args()

    if not os.path.exists(args.epsr_file):
        print(f"Error: epsr file not found: {args.epsr_file}")
        sys.exit(1)
    if not os.path.exists(args.epsi_file):
        print(f"Error: epsi file not found: {args.epsi_file}")
        sys.exit(1)

    try:
        out_paths = compute_absorption(args.epsr_file, args.epsi_file, args.out_dir, args.tag)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    for p in out_paths:
        print(f"Wrote {p}")


if __name__ == '__main__':
    main()

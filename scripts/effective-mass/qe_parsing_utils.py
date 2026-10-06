#!/usr/bin/env python3
"""
Shared helpers for auto-discovering per-material information from Quantum
Espresso input/output files, so nothing about a specific material (ZnO, ZnS,
...) ever needs to be hardcoded in the pipeline scripts.

Ported unchanged from the validated one-off toolkit
(Bulk-ZnX-Wurtzite-EM-Calculations-without-SOC/*/All-Scripts/qe_parsing_utils.py),
confirmed byte-identical between the with-SOC and without-SOC copies (SOC is
handled transparently via the QE `noncolin` flag, not a separate code path).

Expected layout per direction folder (as produced by pw.x / bands.x):
    <direction_dir>/dat/<prefix>-Bands.dat.gnu
    <direction_dir>/<material>-scf-bands-Calculation.{in,out}
    <direction_dir>/<material>-Bands-Calculation.{in,out}
"""

import glob
import os
import re

BOHR_TO_ANGSTROM = 0.529177210903


class ConfigError(Exception):
    pass


def _find_single(pattern, description):
    matches = sorted(glob.glob(pattern))
    if len(matches) == 0:
        raise ConfigError(f"No {description} found matching: {pattern}")
    if len(matches) > 1:
        raise ConfigError(
            f"Multiple {description} found matching {pattern}: {matches}. "
            "Keep exactly one in this folder so it can be picked automatically."
        )
    return matches[0]


def find_band_gnu_file(direction_dir):
    return _find_single(os.path.join(direction_dir, "dat", "*.dat.gnu"), "band .dat.gnu file")


def find_scf_bands_input(direction_dir):
    for pattern in ("*scf-bands-Calculation.in", "*scf*bands*.in"):
        matches = sorted(glob.glob(os.path.join(direction_dir, pattern)))
        if matches:
            return matches[0]
    raise ConfigError(
        f"No SCF/bands QE input file (*scf-bands-Calculation.in) found in {direction_dir}"
    )


def find_bands_calculation_input(direction_dir):
    return _find_single(
        os.path.join(direction_dir, "*Bands-Calculation.in"), "bands-calculation QE input file"
    )


def find_matching_output(input_file):
    if not input_file.endswith(".in"):
        raise ConfigError(f"Expected a '.in' file, got: {input_file}")
    out_file = input_file[:-3] + ".out"
    if not os.path.exists(out_file):
        raise ConfigError(f"Expected matching output file not found: {out_file}")
    return out_file


def parse_celldm(qe_input_file):
    text = open(qe_input_file).read()
    ibrav_m = re.search(r"ibrav\s*=\s*(-?\d+)", text)
    if not ibrav_m:
        raise ConfigError(f"Could not find 'ibrav' in {qe_input_file}")
    ibrav = int(ibrav_m.group(1))

    celldm = {}
    for i in range(1, 7):
        m = re.search(rf"celldm\({i}\)\s*=\s*([-\d.eE]+)", text)
        if m:
            celldm[i] = float(m.group(1))

    if 1 not in celldm:
        raise ConfigError(f"Could not find celldm(1) in {qe_input_file}")

    return ibrav, celldm


def parse_number_of_electrons(qe_output_file):
    text = open(qe_output_file).read()
    m = re.search(r"number of electrons\s*=\s*([\d.]+)", text)
    if not m:
        raise ConfigError(f"Could not find 'number of electrons' in {qe_output_file}")
    return float(m.group(1))


def parse_noncolin(qe_input_file):
    text = open(qe_input_file).read()
    m = re.search(r"noncolin\s*=\s*\.?(true|false)\.?", text, re.IGNORECASE)
    if not m:
        return False
    return m.group(1).lower() == "true"


def parse_kpath_axis(bands_calculation_input_file):
    """
    Reads the K_POINTS crystal_b block and determines whether the k-path runs
    mainly along the in-plane (a*) or out-of-plane/c-axis (c*) reciprocal
    direction of a hexagonal (ibrav=4) cell, by comparing the path's start
    and end fractional coordinates.

    Returns 'a' or 'c'.
    """
    text = open(bands_calculation_input_file).read()
    m = re.search(r"K_POINTS\s+crystal_b\s*\n\s*(\d+)\s*\n((?:.*\n?)+)", text)
    if not m:
        raise ConfigError(
            f"Could not find a 'K_POINTS crystal_b' block in {bands_calculation_input_file}"
        )

    n_points = int(m.group(1))
    body_lines = [l for l in m.group(2).splitlines() if l.strip()][:n_points]
    if len(body_lines) < 2:
        raise ConfigError(
            f"K_POINTS crystal_b block in {bands_calculation_input_file} has fewer than 2 points"
        )

    coords = []
    for line in body_lines:
        parts = line.split()
        coords.append([float(parts[0]), float(parts[1]), float(parts[2])])

    start, end = coords[0], coords[-1]
    delta = [abs(end[i] - start[i]) for i in range(3)]
    dominant_axis = delta.index(max(delta))
    return "c" if dominant_axis == 2 else "a"


def resolve_lattice_constant_angstrom(direction_dir):
    scf_in = find_scf_bands_input(direction_dir)
    ibrav, celldm = parse_celldm(scf_in)

    bands_in = find_bands_calculation_input(direction_dir)
    axis = parse_kpath_axis(bands_in)

    a_bohr = celldm[1]
    c_bohr = a_bohr * celldm[3] if 3 in celldm else None

    if axis == "c":
        if ibrav != 4:
            raise ConfigError(
                f"K-path runs along the c-axis but ibrav={ibrav} in {scf_in} is not "
                "hexagonal (4). This template assumes wurtzite-like (ibrav=4) cells."
            )
    # plotband.x always reports k-distance in units of 2*pi/a, regardless of
    # k-path direction, so the conversion length is always a, never c.
    length_bohr = a_bohr

    return {
        "lattice_axis_used": axis,
        "ibrav": ibrav,
        "celldm1_bohr": a_bohr,
        "celldm3_ratio": celldm.get(3),
        "a_angstrom": a_bohr * BOHR_TO_ANGSTROM,
        "c_angstrom": (c_bohr * BOHR_TO_ANGSTROM) if c_bohr is not None else None,
        "lattice_constant_angstrom": length_bohr * BOHR_TO_ANGSTROM,
        "source_file": scf_in,
        "kpath_source_file": bands_in,
    }


def resolve_band_edge_indices(direction_dir, n_below=3, n_above=3):
    bands_in = find_bands_calculation_input(direction_dir)
    bands_out = find_matching_output(bands_in)

    nelec = parse_number_of_electrons(bands_out)
    noncolin = parse_noncolin(bands_in)

    divisor = 1.0 if noncolin else 2.0
    vbm_index = round(nelec / divisor)
    cbm_index = vbm_index + 1

    valence_indices = [vbm_index - k for k in range(n_below)]
    conduction_indices = [cbm_index + k for k in range(n_above)]

    if min(valence_indices) < 1:
        raise ConfigError(
            f"Requested {n_below} valence bands below the VBM (band #{vbm_index}) "
            "but that goes below band 1. Reduce n_bands_below_vbm in Pipeline-Settings.json."
        )

    return {
        "nelec": nelec,
        "noncolin": noncolin,
        "vbm_index": vbm_index,
        "cbm_index": cbm_index,
        "valence_band_indices": valence_indices,
        "conduction_band_indices": conduction_indices,
        "source_file": bands_out,
    }

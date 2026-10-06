#!/usr/bin/env python3
"""Shared parsing for the Band structure + DOS plotter, for any material.

bands.x-style ".dat.gnu" file (the standard plotband.x/bands.x gnuplot output): two columns
(cumulative k-path distance, energy in eV) per band, with blank lines separating each band's
block -- this is a fixed QE convention, not material-specific.

dos.x output: a '#' header line of the form
    #  E (eV)   dos(E)     Int dos(E) EFermi =    5.938 eV
followed by 3 columns (E, dos, integrated dos). The Fermi energy in that header is used as the
default energy-zero reference unless the caller supplies their own (e.g. the true VBM for an
insulator, which can differ from where dos.x places EFermi depending on smearing/occupations).
"""

import re

EFERMI_RE = re.compile(r'EFermi\s*=\s*([-\d.]+)', re.IGNORECASE)


def load_bands_gnu(path):
    """Return a list of bands; each band is a list of (k_distance, energy) tuples."""
    bands = []
    current = []
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                if current:
                    bands.append(current)
                    current = []
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            current.append((float(parts[0]), float(parts[1])))
    if current:
        bands.append(current)
    if not bands:
        raise ValueError(f"No band data found in {path} (expected 2-column k-distance/energy blocks).")
    return bands


def load_dos(path):
    """Return (energies, dos, efermi_from_header_or_None)."""
    energies, dos = [], []
    efermi = None
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('#'):
                m = EFERMI_RE.search(stripped)
                if m:
                    efermi = float(m.group(1))
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            energies.append(float(parts[0]))
            dos.append(float(parts[1]))
    if not energies:
        raise ValueError(f"No DOS data found in {path} (expected dos.x-style output).")
    return energies, dos, efermi


def split_occupied_unoccupied(bands, energy_shift, tol=1e-3):
    """Shift every band's energy by -energy_shift, then classify each whole band as occupied
    (every point <= tol) or unoccupied (otherwise) -- valid for a real insulator/semiconductor
    gap, where no single band straddles the Fermi level.
    """
    occupied, unoccupied = [], []
    for band in bands:
        shifted = [(k, e - energy_shift) for k, e in band]
        if all(e <= tol for _, e in shifted):
            occupied.append(shifted)
        else:
            unoccupied.append(shifted)
    return occupied, unoccupied


def parse_kpath_ticks(spec):
    """'0:Γ,0.577:M,0.911:K' -> [(0.0, 'Γ'), (0.577, 'M'), (0.911, 'K')]."""
    ticks = []
    for item in spec.split(','):
        item = item.strip()
        if not item or ':' not in item:
            continue
        pos, label = item.split(':', 1)
        try:
            ticks.append((float(pos.strip()), label.strip()))
        except ValueError:
            continue
    return ticks

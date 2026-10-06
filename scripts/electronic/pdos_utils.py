#!/usr/bin/env python3
"""Shared pDOS parsing, ported from the user's own validated `Generate-atom-dat-from-pdos.py`:
sums the ldos column across every m-projection/atom file for a given (species, orbital-letter)
group, from raw `projwfc.x` output filenames of the form:

    <prefix>.pdos_atm#<N>(<Species>)_wfc#<M>(<orbital>)

This is QE's own fixed naming convention (not material-specific), so the regex below works for
any species/orbital projwfc.x was run on.
"""

import re

PDOS_FILENAME_RE = re.compile(r'pdos_atm#\d+\((\w+)\)_wfc#\d+\(([\w.]+)\)')

ORBITAL_COLORS = {
    's': ['blue', 'cyan', 'teal'],
    'p': ['magenta', 'violet', 'purple'],
    'd': ['brown', 'orange', 'olive'],
    'f': ['darkgray', 'pink', 'lime'],
}


def parse_species_orbital(filename):
    m = PDOS_FILENAME_RE.search(filename)
    if not m:
        return None
    return m.group(1), m.group(2)


def load_pdos_columns(path):
    """Return (energies, ldos) from one raw projwfc.x pdos_atm file (column 1 = E, column 2 = ldos)."""
    energies, ldos = [], []
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            cols = stripped.split()
            if len(cols) < 2:
                continue
            energies.append(float(cols[0]))
            ldos.append(float(cols[1]))
    return energies, ldos


def aggregate_by_explicit_labels(labeled_uploads):
    """labeled_uploads: list of (species, orbital_letter, saved_path) -- explicitly supplied by
    the caller per file (the web form), rather than parsed from the filename. This is the
    primary, more reliable path: a browser upload's filename can be trusted to round-trip, but
    asking the student to confirm what each file actually is directly is more robust than
    depending on it.

    Returns {(species, orbital_letter): (energies, summed_ldos)}, same shape as
    aggregate_by_species_orbital.
    """
    groups = {}
    for species, orbital_letter_val, path in labeled_uploads:
        energies, ldos = load_pdos_columns(path)
        key = (species, orbital_letter_val.lower())
        if key not in groups:
            groups[key] = (energies, list(ldos))
        else:
            existing_energies, existing_ldos = groups[key]
            if len(existing_ldos) == len(ldos):
                groups[key] = (existing_energies, [a + b for a, b in zip(existing_ldos, ldos)])
    return groups


def aggregate_by_species_orbital(file_paths_with_names):
    """file_paths_with_names: list of (original_filename, saved_path).

    Returns {(species, orbital): (energies, summed_ldos)}, summing ldos across every file that
    matches the same (species, orbital) group (i.e. every m-projection/equivalent atom).
    """
    groups = {}
    for original_name, path in file_paths_with_names:
        parsed = parse_species_orbital(original_name)
        if not parsed:
            continue
        species, orbital = parsed
        energies, ldos = load_pdos_columns(path)
        key = (species, orbital)
        if key not in groups:
            groups[key] = (energies, list(ldos))
        else:
            existing_energies, existing_ldos = groups[key]
            if len(existing_ldos) == len(ldos):
                groups[key] = (existing_energies, [a + b for a, b in zip(existing_ldos, ldos)])
    return groups


def orbital_letter(orbital):
    """'s', 'p', 'd', 'f' from an orbital label like 's', '4s', 'd.z2' etc. -- the first
    alphabetic character, since a leading principal quantum number (e.g. '4' in '4s') is
    display-only and not part of the orbital type itself.
    """
    for ch in orbital or '':
        if ch.isalpha():
            return ch.lower()
    return ''

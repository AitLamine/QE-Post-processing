#!/usr/bin/env python3
"""Hubbard U / V reader: parses the standard QE `HUBBARD` card block that `hp.x` prints at the
end of a linear-response run (the same card syntax documented in Quantum ESPRESSO's own
INPUT_PW.txt for pw.x, e.g.:

    HUBBARD (ortho-atomic)
    U   Zn-3d   7.4321
    U   O-2p    6.1234
    V   Zn-3d O-2p  1  2   0.5678

Material-agnostic by construction: species/orbital labels are read from the file itself, never
hardcoded. Only the fixed card keywords ("HUBBARD", leading "U"/"V") are relied on, so it works
for any element pair hp.x was run on. Optional `atoms_orbitals` filter (comma-separated
substrings) narrows the output to matching species-orbital labels.
"""

import argparse
import re

U_LINE = re.compile(r'^\s*U\s+(\S+)\s+([-\d.eE]+)\s*$')
V_LINE = re.compile(r'^\s*V\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+([-\d.eE]+)\s*$')


def parse_hubbard_card(path):
    """Return {'U': [(species_orbital, value)], 'V': [(sp_orb1, sp_orb2, site1, site2, value)]}."""
    u_values = []
    v_values = []
    in_card = False
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            stripped = line.strip()
            if stripped.upper().startswith('HUBBARD'):
                in_card = True
                continue
            if not in_card:
                continue
            if not stripped:
                continue
            m_u = U_LINE.match(line)
            if m_u:
                u_values.append((m_u.group(1), float(m_u.group(2))))
                continue
            m_v = V_LINE.match(line)
            if m_v:
                v_values.append((m_v.group(1), m_v.group(2), int(m_v.group(3)), int(m_v.group(4)), float(m_v.group(5))))
                continue
            # A non-matching, non-blank line after the card started means the card ended
            # (e.g. hp.x prints further output below it).
            if in_card and not (stripped.startswith('U') or stripped.startswith('V')):
                break

    if not u_values and not v_values:
        raise ValueError(
            f"No HUBBARD card found in {path}. Expected a block starting with 'HUBBARD' "
            "followed by 'U <species-orbital> <value>' and/or 'V ...' lines, as printed by hp.x."
        )
    return {'U': u_values, 'V': v_values}


def filter_by_atoms_orbitals(values, atoms_orbitals):
    if not atoms_orbitals:
        return values
    needles = [s.strip().lower() for s in atoms_orbitals.split(',') if s.strip()]
    if not needles:
        return values
    return [v for v in values if any(n in v[0].lower() for n in needles)]


def write_table(path, result, atoms_orbitals=None):
    u_values = filter_by_atoms_orbitals(result['U'], atoms_orbitals)
    v_values = result['V']
    if atoms_orbitals:
        needles = [s.strip().lower() for s in atoms_orbitals.split(',') if s.strip()]
        v_values = [v for v in v_values if any(n in v[0].lower() or n in v[1].lower() for n in needles)]

    with open(path, 'w') as f:
        f.write("Type,Species-Orbital(1),Species-Orbital(2),Site1,Site2,Value(eV)\n")
        for species_orbital, value in u_values:
            f.write(f"U,{species_orbital},,,,{value:.5f}\n")
        for sp1, sp2, site1, site2, value in v_values:
            f.write(f"V,{sp1},{sp2},{site1},{site2},{value:.5f}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hp_output_file')
    parser.add_argument('out_csv')
    parser.add_argument('--atoms-orbitals', default='')
    args = parser.parse_args()

    result = parse_hubbard_card(args.hp_output_file)
    write_table(args.out_csv, result, args.atoms_orbitals)
    print(f"Wrote {args.out_csv} ({len(result['U'])} U value(s), {len(result['V'])} V value(s))")


if __name__ == '__main__':
    main()

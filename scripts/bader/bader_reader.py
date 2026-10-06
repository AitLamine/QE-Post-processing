#!/usr/bin/env python3
"""Bader charge analyzer: parses ACF.dat from the Henkelman-group `bader` code
(http://theory.cm.utexas.edu/henkelman/code/bader/), whose column layout is fixed by that
tool regardless of material:

    #    X       Y       Z       CHARGE     MIN DIST    ATOMIC VOL
  -----------------------------------------------------------------
    1  0.0000  0.0000  0.0000   10.234567    0.500000    12.345678
    ...
  -----------------------------------------------------------------
    VACUUM CHARGE:      0.0000
    VACUUM VOLUME:      0.0000
    NUMBER OF ELECTRONS: 64.0000

Per-atom species labels aren't in ACF.dat itself (bader doesn't know chemistry), so an optional
element-order list (e.g. "Zn,Zn,O,O") lets the caller label rows; without it, atoms are left
labeled only by their ACF.dat index, which still works for any material.

Net charge, ionicity and covalency follow the methodology in the user's own validated
Bader-charge analysis (Paper-2 revision, "Bader charge analysis" section,
`Paragraph-Bader-Charges-Bulk-Wurtzite-ZnX.tex`):

    Q_Bader   = Z_valence - N_Bader           (net atomic charge, in units of e)
    Ionicity  = |Q_Bader| / |Q_formal| * 100  (%, ratio to the formal ionic charge)
    Covalency = 100 - Ionicity                (%, complement of ionicity)

`N_Bader` is ACF.dat's own CHARGE column (the Bader electron population). `Z_valence`
(pseudopotential valence electron count) and `Q_formal` (formal ionic charge, e.g. +2 for
Zn2+, -2 for O2-) are NOT in ACF.dat -- they depend on which pseudopotential and which
material's formal oxidation state, so both are supplied per-species by the caller rather than
hardcoded to any one material.
"""

import argparse
import re

HEADER_RE = re.compile(r'#\s*X\s+Y\s+Z\s+CHARGE', re.IGNORECASE)
DASH_RE = re.compile(r'^-{5,}\s*$')
NUM_ELECTRONS_RE = re.compile(r'NUMBER OF ELECTRONS:\s*([-\d.]+)', re.IGNORECASE)


def parse_acf(path):
    """Return (rows, meta) where rows = [{'index','x','y','z','charge','min_dist','atomic_vol'}],
    meta = {'number_of_electrons': float or None}.
    """
    rows = []
    number_of_electrons = None
    in_table = False
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            stripped = line.strip()
            if HEADER_RE.search(stripped):
                in_table = True
                continue
            if DASH_RE.match(stripped):
                continue
            m_elec = NUM_ELECTRONS_RE.search(stripped)
            if m_elec:
                number_of_electrons = float(m_elec.group(1))
                continue
            if not in_table or not stripped:
                continue
            parts = stripped.split()
            if len(parts) < 7 or not parts[0].isdigit():
                continue
            rows.append({
                'index': int(parts[0]),
                'x': float(parts[1]),
                'y': float(parts[2]),
                'z': float(parts[3]),
                'charge': float(parts[4]),
                'min_dist': float(parts[5]),
                'atomic_vol': float(parts[6]),
            })

    if not rows:
        raise ValueError(
            f"No per-atom charge table found in {path}. Expected the standard bader-code ACF.dat "
            "format (header line with X, Y, Z, CHARGE, MIN DIST, ATOMIC VOL columns)."
        )
    return rows, {'number_of_electrons': number_of_electrons}


def _parse_species_map(spec):
    """Parse 'Zn:20,O:6' -> {'Zn': 20.0, 'O': 6.0}."""
    result = {}
    if not spec:
        return result
    for item in spec.split(','):
        item = item.strip()
        if not item or ':' not in item:
            continue
        species, value = item.split(':', 1)
        try:
            result[species.strip()] = float(value.strip())
        except ValueError:
            continue
    return result


def compute_charge_analysis(rows, element_order, valence_map_spec='', formal_charge_map_spec=''):
    """Add net_charge/ionicity/covalency to each row (species must be resolvable from
    element_order). Rows for species missing from valence_map or formal_charge_map get None
    for the fields that can't be computed, rather than a guessed value.
    """
    labels = [s.strip() for s in element_order.split(',')] if element_order else []
    valence_map = _parse_species_map(valence_map_spec)
    formal_map = _parse_species_map(formal_charge_map_spec)

    enriched = []
    for row in rows:
        idx = row['index'] - 1
        species = labels[idx] if 0 <= idx < len(labels) else ''
        net_charge = None
        ionicity = None
        covalency = None
        if species and species in valence_map:
            net_charge = valence_map[species] - row['charge']
            if species in formal_map and formal_map[species]:
                ionicity = abs(net_charge) / abs(formal_map[species]) * 100
                covalency = 100 - ionicity
        enriched.append({**row, 'species': species, 'net_charge': net_charge,
                          'ionicity': ionicity, 'covalency': covalency})
    return enriched


def write_table(path, rows, element_order=None, valence_map_spec='', formal_charge_map_spec=''):
    enriched = compute_charge_analysis(rows, element_order or '', valence_map_spec, formal_charge_map_spec)
    with open(path, 'w') as f:
        f.write("Atom,Species,X,Y,Z,BaderCharge(N),NetCharge(Q),Ionicity(%),Covalency(%),MinDist,AtomicVolume\n")
        for row in enriched:
            def fmt(v):
                return f"{v:.5f}" if v is not None else ''
            f.write(
                f"{row['index']},{row['species']},{row['x']:.6f},{row['y']:.6f},{row['z']:.6f},"
                f"{row['charge']:.6f},{fmt(row['net_charge'])},{fmt(row['ionicity'])},"
                f"{fmt(row['covalency'])},{row['min_dist']:.6f},{row['atomic_vol']:.6f}\n"
            )


def summarize_by_species(rows, element_order, valence_map_spec='', formal_charge_map_spec=''):
    """Per-species means of Bader charge, net charge, ionicity and covalency."""
    enriched = compute_charge_analysis(rows, element_order, valence_map_spec, formal_charge_map_spec)
    sums = {}
    counts = {}
    for row in enriched:
        species = row['species'] or f"atom-{row['index']}"
        bucket = sums.setdefault(species, {'charge': 0.0, 'net_charge': 0.0, 'ionicity': 0.0, 'covalency': 0.0,
                                            'net_charge_n': 0, 'ionicity_n': 0})
        bucket['charge'] += row['charge']
        if row['net_charge'] is not None:
            bucket['net_charge'] += row['net_charge']
            bucket['net_charge_n'] += 1
        if row['ionicity'] is not None:
            bucket['ionicity'] += row['ionicity']
            bucket['covalency'] += row['covalency']
            bucket['ionicity_n'] += 1
        counts[species] = counts.get(species, 0) + 1

    summary = {}
    for species, bucket in sums.items():
        n = counts[species]
        summary[species] = {
            'mean_charge': bucket['charge'] / n,
            'mean_net_charge': (bucket['net_charge'] / bucket['net_charge_n']) if bucket['net_charge_n'] else None,
            'mean_ionicity': (bucket['ionicity'] / bucket['ionicity_n']) if bucket['ionicity_n'] else None,
            'mean_covalency': (bucket['covalency'] / bucket['ionicity_n']) if bucket['ionicity_n'] else None,
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('acf_file')
    parser.add_argument('out_csv')
    parser.add_argument('--element-order', default='', help='Comma-separated species per ACF.dat index, e.g. Zn,Zn,O,O')
    parser.add_argument('--valence-electrons', default='', help="Z_valence per species, e.g. 'Zn:20,O:6'")
    parser.add_argument('--formal-charges', default='', help="Formal ionic charge per species, e.g. 'Zn:2,O:-2'")
    args = parser.parse_args()

    rows, meta = parse_acf(args.acf_file)
    write_table(args.out_csv, rows, args.element_order, args.valence_electrons, args.formal_charges)
    print(f"Wrote {args.out_csv} ({len(rows)} atom(s))")
    if meta['number_of_electrons'] is not None:
        print(f"NUMBER OF ELECTRONS (from file): {meta['number_of_electrons']}")


if __name__ == '__main__':
    main()

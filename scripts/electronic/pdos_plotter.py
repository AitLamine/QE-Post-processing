#!/usr/bin/env python3
"""Projected DOS (pDOS) plotter: raw projwfc.x pdos_atm files (any material) -> one figure per
species (cation, anion, ...), each overlaying that species' selected orbitals, styled to match
the user's own validated pgfplots figure (`Figure-pDos-PBESOL-PlusU.tex`): a vertical dashed
line at E=0 (the VBM/Fermi reference), and a fixed color per orbital letter (s/p/d/f) that
cycles per panel so consecutive species-panels stay visually distinct, exactly like the real
figure's blue/magenta/brown (panel 1) vs cyan/violet (panel 2) scheme.

Each uploaded file is labeled explicitly by the caller (species, orbital letter, shell number)
rather than parsed from its filename: a browser upload's filename usually survives intact, but
asking the student to confirm what each file actually is directly is more robust than depending
on that, and it also gets the shell number (the "4" in "Zn-4s") for free, which the projwfc.x
filename convention alone doesn't carry.

The energy-zero reference (VBM/Fermi) has no equivalent in a raw pdos_atm file the way dos.x
carries its own `EFermi = ... eV` header, so it's either supplied explicitly, or auto-detected
from that same dos.x header if the caller also passes that file (same mechanism as the Band
structure + DOS plotter) -- one or the other is required; this module refuses to silently plot
un-referenced energies.

Kept as one image per species (not stacked into one multi-panel figure), per the module's
"one image per figure" convention.
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdos_utils import aggregate_by_explicit_labels, ORBITAL_COLORS  # noqa: E402
from bands_dos_utils import EFERMI_RE  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from pgfplots_export import Curve, export_pgfplots, resolve_range, compile_pgfplots_to_pdf  # noqa: E402

DEFAULT_PLOT_SETTINGS = {
    'x_range': '',
    'y_range': '',
    'figure_format': 'png',
    'template_path': None,
}


def load_plot_settings(config_path='material_config.json'):
    settings = dict(DEFAULT_PLOT_SETTINGS)
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
            settings.update(config.get('settings', {}).get('plot', {}))
        except Exception as e:
            print(f"Warning: could not read plot settings from {config_path}: {e}")
    return settings


def detect_efermi_from_dos_file(dos_path):
    """Best-effort: read a dos.x-style '#'-header EFermi value, for auto-detecting the pDOS
    energy-zero reference without asking the student to type it in. Returns None if not found.
    """
    if not dos_path or not os.path.exists(dos_path):
        return None
    with open(dos_path, 'r', errors='ignore') as f:
        for line in f:
            if line.strip().startswith('#'):
                m = EFERMI_RE.search(line)
                if m:
                    return float(m.group(1))
    return None


def plot_pdos(file_entries, out_dir, tag, energy_shift, plot_settings=None):
    """file_entries: list of dicts {'species', 'orbital', 'shell', 'path'}, one per uploaded
    pdos_atm file, explicitly labeled by the caller. `energy_shift` (eV) is required (resolve
    it -- explicit value or dos.x auto-detect -- before calling this). Returns output paths.
    """
    plot_settings = plot_settings or dict(DEFAULT_PLOT_SETTINGS)
    if energy_shift is None:
        raise ValueError(
            "No energy reference (VBM/Fermi) available: supply one explicitly, or upload the "
            "matching dos.x output file so it can be auto-detected from its 'EFermi = ...' header."
        )

    labeled_uploads = [(e['species'], e['orbital'], e['path']) for e in file_entries]
    aggregated = aggregate_by_explicit_labels(labeled_uploads)
    if not aggregated:
        raise ValueError("No pDOS files to plot.")

    # Panels in first-seen species order; legend label built from the caller's own labels.
    species_order = []
    legend_by_key = {}
    for e in file_entries:
        species, orbital, shell = e['species'], e['orbital'], e.get('shell', '')
        if species not in species_order:
            species_order.append(species)
        key = (species, orbital.lower())
        legend_by_key[key] = f"{species}-{shell}{orbital}" if shell else f"{species}-{orbital}"

    os.makedirs(out_dir, exist_ok=True)
    out_paths = []
    csv_rows = {}

    figure_format = (plot_settings.get('figure_format') or 'png').lower()
    want_png = figure_format in ('png', 'both')
    want_latex = figure_format in ('latex', 'both')

    for panel_idx, species in enumerate(species_order):
        curves = []
        for (sp, letter), (energies, ldos) in aggregated.items():
            if sp != species:
                continue
            label = legend_by_key.get((sp, letter), f"{sp}-{letter}")
            shifted = [e - energy_shift for e in energies]
            color_cycle = ORBITAL_COLORS.get(letter, ['black', 'gray'])
            color = color_cycle[panel_idx % len(color_cycle)]
            curves.append((label, shifted, ldos, color))
            csv_rows.setdefault('Energy(eV)', shifted)
            csv_rows[f"pDOS_{label}"] = ldos

        if not curves:
            continue

        all_energies = curves[0][1]
        all_ldos_values = [v for _, _, ldos, _ in curves for v in ldos]
        xlim = resolve_range(plot_settings.get('x_range'), all_energies, pad_frac=0.02)
        ylim = resolve_range(plot_settings.get('y_range'), all_ldos_values, pad_frac=0.05)

        if want_png:
            png_path = os.path.join(out_dir, f"pDOS-{species}_{tag}.png")
            plt.figure(figsize=(8, 6))
            for label, energies, ldos, color in curves:
                plt.plot(energies, ldos, color=color, linewidth=1.5, label=label)
            plt.axvline(0, color='gray', linestyle='--', linewidth=1)
            plt.xlabel('Energy (eV)')
            plt.ylabel('pDOS (states/eV)')
            plt.xlim(xlim)
            plt.ylim(ylim)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(png_path, dpi=300)
            plt.close()
            out_paths.append(png_path)

        if want_latex:
            tex_path = os.path.join(out_dir, f"pDOS-{species}_{tag}.tex")
            # Vertical gray dashed VBM/Fermi reference line at E=0, matching the PNG path's
            # plt.axvline(0, ...) and Figure-pDos-PBESOL-PlusU.tex's own convention.
            vbm_line = Curve(x=[0, 0], y=[ylim[0], ylim[1]], color='gray', dashed=True)
            dat_paths = export_pgfplots(
                tex_path,
                [vbm_line] + [Curve(x=e, y=ldos, label=label, color=color) for label, e, ldos, color in curves],
                xlabel='Energy (eV)', ylabel='pDOS (states/eV)',
                xlim=xlim, ylim=ylim,
                template_path=plot_settings.get('template_path'),
            )
            out_paths.append(tex_path)
            out_paths.extend(dat_paths)
            pdf_path = compile_pgfplots_to_pdf(tex_path)
            if pdf_path:
                out_paths.append(pdf_path)

    if csv_rows:
        csv_path = os.path.join(out_dir, f"pDOS_{tag}.csv")
        keys = list(csv_rows.keys())
        n = len(csv_rows['Energy(eV)'])
        with open(csv_path, 'w') as f:
            f.write(",".join(keys) + "\n")
            for i in range(n):
                f.write(",".join(f"{csv_rows[k][i]:.5f}" if i < len(csv_rows[k]) else '' for k in keys) + "\n")
        out_paths.append(csv_path)

    return out_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out_dir')
    parser.add_argument('tag')
    parser.add_argument('--file', action='append', required=True,
                         help="'path:species:orbital:shell', repeatable, e.g. "
                              "'zn_s.dat:Zn:s:4' --file 'zn_p.dat:Zn:p:4'")
    parser.add_argument('--energy-shift', type=float, default=None)
    parser.add_argument('--dos-file', default=None, help='Optional dos.x output, to auto-detect EFermi')
    parser.add_argument('--config', default='material_config.json')
    args = parser.parse_args()

    entries = []
    for item in args.file:
        parts = item.split(':')
        if len(parts) < 3:
            print(f"Error: --file entry '{item}' must be 'path:species:orbital[:shell]'")
            sys.exit(1)
        path, species, orbital = parts[0], parts[1], parts[2]
        shell = parts[3] if len(parts) > 3 else ''
        entries.append({'path': path, 'species': species, 'orbital': orbital, 'shell': shell})

    energy_shift = args.energy_shift
    if energy_shift is None and args.dos_file:
        energy_shift = detect_efermi_from_dos_file(args.dos_file)

    settings = load_plot_settings(args.config)
    out_paths = plot_pdos(entries, args.out_dir, args.tag, energy_shift, settings)
    for p in out_paths:
        print(f"Wrote {p}")


if __name__ == '__main__':
    main()

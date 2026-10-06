#!/usr/bin/env python3
"""Band structure + DOS plotter: bands.x .dat.gnu + dos.x output (any material) -> two
SEPARATE figures (bands, DOS), styled to match the user's own validated pgfplots figure
(`Figure-Bands-Dos-PBESOL.tex`): teal for occupied bands, purple for unoccupied, a magenta
line at E=0 (VBM), gray vertical lines at the supplied high-symmetry k-points.

High-symmetry tick positions/labels are NOT auto-derived: they depend on the reciprocal
lattice and the exact k-path chosen for the bands.x run, which is real, material-specific
information the app has no reliable way to reconstruct from the .dat.gnu file alone. The
caller supplies them directly (same numbers already known from setting up the k-path), e.g.
"0:Γ,0.577:M,0.911:K,1.577:Γ". If left blank, the bands still plot correctly, just without the
labeled high-symmetry lines.

The energy-zero reference (VBM/Fermi) defaults to the `EFermi = ... eV` value dos.x itself
prints in its header, so the common case needs no typed value at all; an explicit override is
still honored when given (e.g. the true VBM, which can differ from dos.x's own Fermi placement).
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bands_dos_utils import load_bands_gnu, load_dos, split_occupied_unoccupied, parse_kpath_ticks  # noqa: E402

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


def plot_bands_dos(bands_gnu_path, dos_path, out_dir, tag, energy_shift=None,
                    kpath_ticks_spec='', occupied_split='Show both', plot_settings=None):
    """Write a bands figure and a DOS figure (+ CSVs) into out_dir. Returns list of output paths.

    `occupied_split` in {'Show both', 'Occupied only', 'Unoccupied only'} controls which bands
    are drawn/exported to LaTeX; the CSV always records both, since it costs nothing extra and
    is more useful for a student who wants to replot elsewhere.
    """
    plot_settings = plot_settings or dict(DEFAULT_PLOT_SETTINGS)
    bands = load_bands_gnu(bands_gnu_path)
    dos_energies, dos_values, efermi_header = load_dos(dos_path)

    shift = energy_shift if energy_shift is not None else (efermi_header or 0.0)
    occupied, unoccupied = split_occupied_unoccupied(bands, shift)
    dos_energies_shifted = [e - shift for e in dos_energies]
    ticks = parse_kpath_ticks(kpath_ticks_spec)

    drawn_occupied = occupied if occupied_split != 'Unoccupied only' else []
    drawn_unoccupied = unoccupied if occupied_split != 'Occupied only' else []

    os.makedirs(out_dir, exist_ok=True)
    out_paths = []
    figure_format = (plot_settings.get('figure_format') or 'png').lower()
    want_png = figure_format in ('png', 'both')
    want_latex = figure_format in ('latex', 'both')

    all_k = [k for band in (occupied + unoccupied) for k, _ in band]
    all_e = [e for band in (occupied + unoccupied) for _, e in band]
    energy_ylim = resolve_range(plot_settings.get('y_range'), all_e, pad_frac=0.05)
    k_xlim = resolve_range(plot_settings.get('x_range'), all_k, pad_frac=0.0) if all_k else (0, 1)

    # --- Bands figure ---
    bands_csv = os.path.join(out_dir, f"Bands_{tag}.csv")
    with open(bands_csv, 'w') as f:
        f.write("Band,Occupancy,K-distance,Energy(eV)\n")
        for i, band in enumerate(occupied):
            for k, e in band:
                f.write(f"{i},Occupied,{k:.6f},{e:.6f}\n")
        for i, band in enumerate(unoccupied):
            for k, e in band:
                f.write(f"{i},Unoccupied,{k:.6f},{e:.6f}\n")
    out_paths.append(bands_csv)

    if want_png:
        png_path = os.path.join(out_dir, f"Bands_{tag}.png")
        plt.figure(figsize=(8, 6))
        for band in drawn_occupied:
            k, e = zip(*band)
            plt.plot(k, e, color='teal', linewidth=1.2)
        for band in drawn_unoccupied:
            k, e = zip(*band)
            plt.plot(k, e, color='purple', linewidth=1.2)
        plt.axhline(0, color='magenta', linewidth=1)
        for pos, label in ticks:
            plt.axvline(pos, color='gray', linewidth=0.8)
        if ticks:
            plt.xticks([p for p, _ in ticks], [l for _, l in ticks])
        plt.xlim(k_xlim)
        plt.ylim(energy_ylim)
        plt.ylabel('Energy (eV)')
        plt.xlabel('K-points path' if ticks else 'K-path distance')
        plt.tight_layout()
        plt.savefig(png_path, dpi=300)
        plt.close()
        out_paths.append(png_path)

    if want_latex:
        tex_path = os.path.join(out_dir, f"Bands_{tag}.tex")
        # Matches Figure-Bands-Dos-PBESOL.tex: a magenta E=0 (VBM) reference line and gray
        # vertical lines at each high-symmetry k-point, same as the PNG path above already does.
        curves = (
            [Curve(x=[k for k, _ in b], y=[e for _, e in b], color='teal') for b in drawn_occupied]
            + [Curve(x=[k for k, _ in b], y=[e for _, e in b], color='purple') for b in drawn_unoccupied]
            + [Curve(x=[k_xlim[0], k_xlim[1]], y=[0, 0], color='magenta')]
            + [Curve(x=[pos, pos], y=[energy_ylim[0], energy_ylim[1]], color='gray') for pos, _ in ticks]
        )
        dat_paths = export_pgfplots(
            tex_path, curves, xlabel='K-points path', ylabel='Energy (eV)',
            xlim=k_xlim, ylim=energy_ylim, legend=False,
            template_path=plot_settings.get('template_path'),
            xtick_labels=ticks or None,
        )
        out_paths.append(tex_path)
        out_paths.extend(dat_paths)
        pdf_path = compile_pgfplots_to_pdf(tex_path)
        if pdf_path:
            out_paths.append(pdf_path)

    # --- DOS figure ---
    dos_csv = os.path.join(out_dir, f"DOS_{tag}.csv")
    with open(dos_csv, 'w') as f:
        f.write("Energy(eV),DOS\n")
        for e, d in zip(dos_energies_shifted, dos_values):
            f.write(f"{e:.6f},{d:.6f}\n")
    out_paths.append(dos_csv)

    dos_xlim = resolve_range(None, dos_values, pad_frac=0.05)
    if want_png:
        png_path = os.path.join(out_dir, f"DOS_{tag}.png")
        plt.figure(figsize=(4, 6))
        plt.plot(dos_values, dos_energies_shifted, color='blue', linewidth=1.2)
        plt.axhline(0, color='magenta', linewidth=1)
        plt.xlim(dos_xlim)
        plt.ylim(energy_ylim)
        plt.xlabel('DOS (states/eV)')
        plt.ylabel('Energy (eV)')
        plt.tight_layout()
        plt.savefig(png_path, dpi=300)
        plt.close()
        out_paths.append(png_path)

    if want_latex:
        tex_path = os.path.join(out_dir, f"DOS_{tag}.tex")
        curves = [
            Curve(x=dos_values, y=dos_energies_shifted, color='blue'),
            Curve(x=[dos_xlim[0], dos_xlim[1]], y=[0, 0], color='magenta'),
        ]
        dat_paths = export_pgfplots(
            tex_path, curves,
            xlabel='DOS (states/eV)', ylabel='Energy (eV)',
            xlim=dos_xlim, ylim=energy_ylim, legend=False,
            template_path=plot_settings.get('template_path'),
        )
        out_paths.append(tex_path)
        out_paths.extend(dat_paths)
        pdf_path = compile_pgfplots_to_pdf(tex_path)
        if pdf_path:
            out_paths.append(pdf_path)

    return out_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bands_gnu_file')
    parser.add_argument('dos_file')
    parser.add_argument('out_dir')
    parser.add_argument('tag')
    parser.add_argument('--energy-shift', type=float, default=None,
                         help='VBM/Fermi (eV) to shift to 0; defaults to dos.x header EFermi')
    parser.add_argument('--kpath-ticks', default='', help="e.g. '0:Γ,0.577:M,0.911:K'")
    parser.add_argument('--occupied-split', default='Show both',
                         choices=['Show both', 'Occupied only', 'Unoccupied only'])
    parser.add_argument('--config', default='material_config.json')
    args = parser.parse_args()

    settings = load_plot_settings(args.config)
    out_paths = plot_bands_dos(
        args.bands_gnu_file, args.dos_file, args.out_dir, args.tag,
        energy_shift=args.energy_shift, kpath_ticks_spec=args.kpath_ticks,
        occupied_split=args.occupied_split, plot_settings=settings,
    )
    for p in out_paths:
        print(f"Wrote {p}")


if __name__ == '__main__':
    main()

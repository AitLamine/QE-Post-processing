#!/usr/bin/env python3
"""Dielectric function plotter: epsr/epsi (real/imaginary dielectric function, any material) ->
two separate figures, epsilon_1(E) and epsilon_2(E), for the chosen polarization axis.

Kept as two separate images rather than one combined panel so a student can lay them out
however they want in their own document, instead of being locked into this tool's layout.

Same generic epsilon.x-style file format as the Tauc module (`scripts/tauc/absorption_from_eps.py`):
any material works as long as both files are `epsilon.x` output (Energy(eV), X, Y, Z columns),
skipping '#' comment lines. No material-specific assumptions.

Figure format (PNG / LaTeX pgfplots / both), and X/Y axis range (auto from data, or manual
override), come from plot_settings the same way as the effective-mass module.
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eps_utils import load_eps_file, AXIS_INDEX, energy_to_wavelength_nm, DEFAULT_WAVELENGTH_RANGE_NM  # noqa: E402

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


def _draw(x_values, values, xlabel, ylabel, xlim, ylim, out_png):
    plt.figure(figsize=(8, 6))
    plt.plot(x_values, values, 'b-', linewidth=1.8)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xlim(xlim)
    plt.ylim(ylim)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


def plot_dielectric_function(epsr_path, epsi_path, out_dir, tag, polarization='Ordinary',
                              x_axis='Energy (eV)', plot_settings=None):
    """Write two figures (epsilon_1, epsilon_2) + one CSV into out_dir. Returns list of output paths.

    `x_axis`: 'Energy (eV)' (default) or 'Wavelength (nm)' -- same data either way, epsilon.x's
    own energy grid converted via lambda(nm) = hc/E, so the x-axis just presents whichever
    quantity is more natural for the reader.
    """
    plot_settings = plot_settings or dict(DEFAULT_PLOT_SETTINGS)
    epsr_rows = load_eps_file(epsr_path)
    epsi_rows = load_eps_file(epsi_path)
    if len(epsr_rows) != len(epsi_rows):
        raise ValueError("epsr and epsi files don't have the same number of data rows.")

    axis_idx = AXIS_INDEX.get(polarization, 1)
    energies = [r[0] for r in epsi_rows]
    eps1 = [r[axis_idx] for r in epsr_rows]
    eps2 = [r[axis_idx] for r in epsi_rows]

    use_wavelength = (x_axis or '').lower().startswith('wavelength')
    x_values = [energy_to_wavelength_nm(e) for e in energies] if use_wavelength else energies
    xlabel = 'Wavelength (nm)' if use_wavelength else 'Energy (eV)'
    x_header = 'Wavelength(nm)' if use_wavelength else 'Energy(eV)'

    os.makedirs(out_dir, exist_ok=True)
    out_paths = []

    csv_path = os.path.join(out_dir, f"Dielectric-Function_{tag}.csv")
    with open(csv_path, 'w') as f:
        f.write(f"{x_header},epsilon1,epsilon2\n")
        for x, e1, e2 in zip(x_values, eps1, eps2):
            f.write(f"{x:.5f},{e1:.5f},{e2:.5f}\n")
    out_paths.append(csv_path)

    figure_format = (plot_settings.get('figure_format') or 'png').lower()
    want_png = figure_format in ('png', 'both')
    want_latex = figure_format in ('latex', 'both')
    if plot_settings.get('x_range'):
        xlim = resolve_range(plot_settings.get('x_range'), x_values, pad_frac=0.01)
    elif use_wavelength:
        xlim = DEFAULT_WAVELENGTH_RANGE_NM
    else:
        xlim = resolve_range(None, x_values, pad_frac=0.01)

    for label, values, symbol in (('epsilon1', eps1, r'$\varepsilon_1(E)$'),
                                   ('epsilon2', eps2, r'$\varepsilon_2(E)$')):
        ylim = resolve_range(plot_settings.get('y_range'), values, pad_frac=0.05)
        if want_png:
            png_path = os.path.join(out_dir, f"{label.capitalize()}_{tag}.png")
            _draw(x_values, values, xlabel, symbol, xlim, ylim, png_path)
            out_paths.append(png_path)
        if want_latex:
            tex_path = os.path.join(out_dir, f"{label.capitalize()}_{tag}.tex")
            # Gray dashed zero-reference line, matching Figure-Dielectric-Functions.tex's own
            # convention (`\addplot [gray, dashed, ...] coordinates {(0, 0) (20, 0)}`) -- no
            # label, so _default_axis_block skips \addlegendentry for it, same effect as that
            # template's `forget plot`.
            zero_line = Curve(x=[xlim[0], xlim[1]], y=[0, 0], color='gray', dashed=True)
            dat_paths = export_pgfplots(
                tex_path,
                [zero_line, Curve(x=x_values, y=values, label=symbol)],
                xlabel=xlabel, ylabel=symbol,
                xlim=xlim, ylim=ylim,
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
    parser.add_argument('epsr_file')
    parser.add_argument('epsi_file')
    parser.add_argument('out_dir')
    parser.add_argument('tag')
    parser.add_argument('--polarization', choices=['Ordinary', 'Extraordinary'], default='Ordinary')
    parser.add_argument('--x-axis', choices=['Energy (eV)', 'Wavelength (nm)'], default='Energy (eV)')
    parser.add_argument('--config', default='material_config.json')
    args = parser.parse_args()

    settings = load_plot_settings(args.config)
    out_paths = plot_dielectric_function(
        args.epsr_file, args.epsi_file, args.out_dir, args.tag,
        polarization=args.polarization, x_axis=args.x_axis, plot_settings=settings,
    )
    for p in out_paths:
        print(f"Wrote {p}")


if __name__ == '__main__':
    main()

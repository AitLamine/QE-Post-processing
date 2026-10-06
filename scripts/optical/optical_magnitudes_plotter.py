#!/usr/bin/env python3
"""Optical-magnitudes plotter: epsr/epsi (any material) -> one separate figure per selected
magnitude (refractive index, extinction coefficient, reflectivity, absorption coefficient,
energy-loss function, optical conductivity) plus one combined CSV.

Formulas ported unchanged from the user's validated one-off pipeline (see
`scripts/optical/eps_utils.py` docstring for the exact source scripts and equations). Kept as
one image per magnitude, never combined into a single multi-panel figure, so a student can
arrange them however they want in their own document.
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eps_utils import (load_eps_file, AXIS_INDEX, MAGNITUDE_FUNCS, MAGNITUDE_YLABEL,  # noqa: E402
                        energy_to_wavelength_nm, DEFAULT_WAVELENGTH_RANGE_NM)

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


def _slug(name):
    return name.replace(' ', '-').replace('/', '-')


def plot_optical_magnitudes(epsr_path, epsi_path, out_dir, tag, magnitudes,
                             polarization='Ordinary', x_axis='Energy (eV)', plot_settings=None):
    """Write one figure per magnitude in `magnitudes` + one combined CSV into out_dir.

    `x_axis`: 'Energy (eV)' (default) or 'Wavelength (nm)' -- same computed values either way,
    just presented against whichever quantity is more natural for the reader.
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

    computed = {}
    for name in magnitudes:
        func = MAGNITUDE_FUNCS.get(name)
        if func is None:
            continue
        computed[name] = [func(e1, e2, e) for e1, e2, e in zip(eps1, eps2, energies)]

    use_wavelength = (x_axis or '').lower().startswith('wavelength')
    x_values = [energy_to_wavelength_nm(e) for e in energies] if use_wavelength else energies
    xlabel = 'Wavelength (nm)' if use_wavelength else 'Energy (eV)'
    x_header = 'Wavelength(nm)' if use_wavelength else 'Energy(eV)'

    os.makedirs(out_dir, exist_ok=True)
    out_paths = []

    csv_path = os.path.join(out_dir, f"Optical-Magnitudes_{tag}.csv")
    with open(csv_path, 'w') as f:
        header = [x_header] + list(computed.keys())
        f.write(",".join(header) + "\n")
        for i, x in enumerate(x_values):
            row = [f"{x:.5f}"] + [f"{computed[name][i]:.5f}" for name in computed]
            f.write(",".join(row) + "\n")
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

    for name, values in computed.items():
        ylabel = MAGNITUDE_YLABEL.get(name, name)
        ylim = resolve_range(plot_settings.get('y_range'), values, pad_frac=0.05)
        slug = _slug(name)
        if want_png:
            png_path = os.path.join(out_dir, f"{slug}_{tag}.png")
            plt.figure(figsize=(8, 6))
            plt.plot(x_values, values, 'b-', linewidth=1.8)
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.xlim(xlim)
            plt.ylim(ylim)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(png_path, dpi=300)
            plt.close()
            out_paths.append(png_path)
        if want_latex:
            tex_path = os.path.join(out_dir, f"{slug}_{tag}.tex")
            dat_paths = export_pgfplots(
                tex_path,
                [Curve(x=x_values, y=values, label=name)],
                xlabel=xlabel, ylabel=ylabel,
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
    parser.add_argument('--magnitudes', nargs='+', default=['Refractive index'],
                         choices=list(MAGNITUDE_FUNCS.keys()))
    parser.add_argument('--polarization', choices=['Ordinary', 'Extraordinary'], default='Ordinary')
    parser.add_argument('--config', default='material_config.json')
    args = parser.parse_args()

    settings = load_plot_settings(args.config)
    out_paths = plot_optical_magnitudes(
        args.epsr_file, args.epsi_file, args.out_dir, args.tag,
        magnitudes=args.magnitudes, polarization=args.polarization, plot_settings=settings,
    )
    for p in out_paths:
        print(f"Wrote {p}")


if __name__ == '__main__':
    main()

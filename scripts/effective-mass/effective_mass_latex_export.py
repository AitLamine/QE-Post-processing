#!/usr/bin/env python3
"""Combined multi-direction, multi-band LaTeX export for the effective-mass module, matching
Figure-Effective-Mass.tex's real convention: each band gets ONE axis panel with every k-direction
concatenated along a shared k-axis (direction segments separated by gray vertical boundary
lines, each segment labeled with its own m*/m0 value), and the band panels (CB highest-index
down to CB1, then VB1 down to VB-lowest-index) stacked vertically via `at=`/`anchor=` chaining --
the same technique the real figure uses to stack CB/VB pairs, generalized here to however many
directions (1-3) and bands a single run actually has, instead of the real figure's fixed
4-material layout.

Simplification vs. the real figure, noted here rather than silently claimed as exact: the real
figure hand-places hole/hbar-style hbar arrows and mass-value text at tuned pixel offsets, which
only make sense for that one paper's specific data range. This instead places a simple corner
text node per direction segment ("<label>: m*/m0 = <value>") -- conveys the same information
without betting on untested collision-prone arrow placement for arbitrary data.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from pgfplots_export import _write_dat_file  # noqa: E402


def read_plot_data(path):
    """Return (k, E_orig, E_fit) lists from a Effective-Mass-Calculation-Plot-Data-Generation.py
    `*_plot_data.txt` file (header line + space-separated k, Original_E, Fitted_E rows)."""
    k, e_orig, e_fit = [], [], []
    with open(path) as f:
        next(f, None)
        for line in f:
            parts = line.split()
            if len(parts) < 3:
                continue
            k.append(float(parts[0]))
            e_orig.append(float(parts[1]))
            e_fit.append(float(parts[2]))
    return k, e_orig, e_fit


def _band_panel_data(direction_entries):
    """direction_entries: list of (direction_label, plot_data_path, m_eff).

    Returns (segments, xlim, ylim) where segments is a list of dicts with the direction's
    shifted (k, e_orig, e_fit), its label, its mass value, and the boundary x-position at its
    right edge (used both to draw the gray divider and to place the next segment).
    """
    segments = []
    offset = 0.0
    all_e = []
    for direction_label, plot_data_path, m_eff in direction_entries:
        if not os.path.exists(plot_data_path):
            continue
        k, e_orig, e_fit = read_plot_data(plot_data_path)
        if not k:
            continue
        k0 = k[0]
        k_shifted = [ki - k0 + offset for ki in k]
        all_e.extend(e_orig)
        segments.append({
            "label": direction_label,
            "m_eff": m_eff,
            "k": k_shifted,
            "e_orig": e_orig,
            "e_fit": e_fit,
            "start": offset,
            "end": k_shifted[-1],
        })
        offset = k_shifted[-1]
    xlim = (0.0, offset if segments else 1.0)
    ylim = (min(all_e), max(all_e)) if all_e else (0.0, 1.0)
    pad = (ylim[1] - ylim[0]) * 0.08 or 1.0
    ylim = (ylim[0] - pad, ylim[1] + pad)
    return segments, xlim, ylim


def _axis_block(name, at_clause, segments, xlim, ylim, carrier_color, dat_dir, dat_prefix,
                 x_precision, y_precision, show_xlabel):
    dat_paths = []
    lines = [
        rf"\begin{{axis}}[name={name}, {at_clause}",
        "    x tick label style={/pgf/number format/.cd, fixed, fixed zerofill, "
        f"precision={x_precision}, /tikz/.cd}},",
        "    y tick label style={/pgf/number format/.cd, fixed, fixed zerofill, "
        f"precision={y_precision}, /tikz/.cd}},",
        f"    xmin={xlim[0]:.6g}, xmax={xlim[1]:.6g},",
        f"    ymin={ylim[0]:.6g}, ymax={ylim[1]:.6g},",
        "    width=10cm, height=4.2cm, line width=1.25,",
        "    xlabel near ticks, ylabel near ticks,",
        "    minor y tick num=4,",
    ]
    if show_xlabel:
        lines.append("    xlabel={K-path distance},")
    else:
        lines.append("    xticklabels={},")
    lines.append("]")

    for i, seg in enumerate(segments):
        data_name = f"{dat_prefix}-{i + 1}-data"
        fit_name = f"{dat_prefix}-{i + 1}-fit"
        dat_paths.append(_write_dat_file(dat_dir, data_name, seg["k"], seg["e_orig"]))
        dat_paths.append(_write_dat_file(dat_dir, fit_name, seg["k"], seg["e_fit"]))
        lines.append(
            rf"\addplot [{carrier_color}, mark=none, line cap=round] table[col sep=tab] {{dat/{data_name}.dat}};"
        )
        lines.append(
            rf"\addplot [Black, dashed, mark=none, line cap=round] table[col sep=tab] {{dat/{fit_name}.dat}};"
        )
        if i < len(segments) - 1:
            lines.append(
                rf"\addplot [gray, solid, line cap=round] coordinates {{({seg['end']:.6g}, {ylim[0]:.6g}) ({seg['end']:.6g}, {ylim[1]:.6g})}};"
            )
        mid = (seg["start"] + seg["end"]) / 2
        mass_str = f"{seg['m_eff']:.3f}$m_0$" if seg["m_eff"] is not None else "n/a"
        lines.append(
            rf"\node [purple, anchor=north, font=\tiny] at (axis cs: {mid:.6g}, {ylim[1]:.6g}) {{{seg['label']}: {mass_str}}};"
        )
    lines.append(r"\end{axis}")
    return "\n".join(lines), dat_paths


def export_effective_mass_tex(output_path, band_entries, template_path=None):
    """band_entries: ordered list of (role, carrier_color, direction_entries) -- one per band
    panel to draw, topmost first (conduction bands highest-index-first, then valence bands
    lowest-index-first, matching Figure-Effective-Mass.tex's CB-then-VB-below convention).
    direction_entries: list of (direction_label, plot_data_path, m_eff) as in _band_panel_data.

    Writes output_path (a standalone .tex) plus its sibling dat/ files. Returns the list of
    .dat paths written (same contract as pgfplots_export.export_pgfplots).
    """
    dat_dir = os.path.join(os.path.dirname(output_path) or ".", "dat")
    base_name = os.path.splitext(os.path.basename(output_path))[0]

    blocks = []
    all_dat_paths = []
    prev_name = None
    for idx, (role, carrier_color, direction_entries) in enumerate(band_entries):
        segments, xlim, ylim = _band_panel_data(direction_entries)
        if not segments:
            continue
        name = f"plot{idx + 1}"
        at_clause = "" if prev_name is None else f"at=({prev_name}.below south east), anchor=above north east, yshift=-0.1cm,"
        x_precision = 2
        y_precision = 2 if any(abs(v) < 10 for seg in segments for v in seg["e_orig"]) else 0
        is_last = idx == len(band_entries) - 1
        block, dat_paths = _axis_block(
            name, at_clause, segments, xlim, ylim, carrier_color, dat_dir,
            f"{base_name}-{role}", x_precision, y_precision, show_xlabel=is_last,
        )
        blocks.append(f"% {role}\n{block}")
        all_dat_paths.extend(dat_paths)
        prev_name = name

    tikz_body = "\n\n".join(blocks)

    if template_path and os.path.exists(template_path):
        with open(template_path) as f:
            template = f.read()
        if "%%PGFPLOTS_AXIS%%" in template:
            content = template.replace("%%PGFPLOTS_AXIS%%", tikz_body)
        else:
            content = (
                template
                + "\n% WARNING: uploaded template had no %%PGFPLOTS_AXIS%% token;"
                " generated panels appended below instead of being merged in.\n"
                + "\\begin{tikzpicture}\n" + tikz_body + "\n\\end{tikzpicture}\n"
            )
    else:
        content = (
            "\\documentclass{standalone}\n"
            "\\usepackage[dvipsnames]{xcolor}\n"
            "\\usepackage{pgfplots}\n"
            "\\pgfplotsset{compat=1.18}\n"
            "\\begin{document}\n"
            "\\begin{tikzpicture}\n"
            f"{tikz_body}\n"
            "\\end{tikzpicture}\n"
            "\\end{document}\n"
        )

    with open(output_path, "w") as f:
        f.write(content)

    return all_dat_paths

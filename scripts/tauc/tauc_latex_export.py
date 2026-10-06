#!/usr/bin/env python3
"""LaTeX/pgfplots export for the Tauc-plot module, styled to match the user's own
`Figure-Tauc-Plot.tex` paper figure: a single axis with the ordinary (blue) and extraordinary
(magenta) Tauc curves plotted as inline `coordinates` (not a `dat/` table -- the real figure
inlines the data directly), a dotted linear-fit line + arrow-and-label annotation marking the
fitted band gap for each polarization that found one, and a bottom-left exponent note.

Column convention (matches `slope_line_bandgap.py`'s own "col_2"/"col_3"/"col_4" labels, which
are the 2nd/3rd/4th columns of the Tauc data file = the x/y/z-axis Tauc functions): col_2 (x) is
used as the "ordinary" curve and col_4 (z) as "extraordinary" -- col_3 (y) is the wurtzite-degenerate
duplicate of col_2 and is not separately plotted, matching the real figure's two-curve convention.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from pgfplots_export import auto_range, compile_pgfplots_to_pdf  # noqa: E402

PLACEHOLDER_TOKEN = "%%PGFPLOTS_AXIS%%"


def _read_tauc_columns(tauc_data_path):
    """Return (energy, tf_o, tf_e) from a tauc-function(-trimmed).dat file: energy = col 0,
    tf_o = col 2 (x-axis Tauc function, 'col_2'), tf_e = col 4 (z-axis, 'col_4')."""
    energy, tf_o, tf_e = [], [], []
    with open(tauc_data_path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("\t") if "\t" in stripped else stripped.split()
            if len(parts) < 5:
                continue
            try:
                e, _wl, t2, _t3, t4 = (float(p) for p in parts[:5])
            except ValueError:
                continue
            energy.append(e)
            tf_o.append(t2)
            tf_e.append(t4)
    return energy, tf_o, tf_e


def _parse_gap_results(gap_results_path):
    """Return {'col_2': [candidate_dict, ...], 'col_4': [...]} from band-gap-results.txt,
    candidates in file order (slope_line_bandgap.py already lists its best candidate first).
    """
    columns = {}
    current = None
    header_seen = False
    with open(gap_results_path) as f:
        for line in f:
            stripped = line.rstrip("\n")
            m = re.match(r"^COLUMN:\s*(\S+)", stripped)
            if m:
                current = m.group(1)
                columns[current] = []
                header_seen = False
                continue
            if current is None or not stripped.strip():
                continue
            if stripped.startswith("Search_Type"):
                header_seen = True
                continue
            if not header_seen or stripped.startswith("#") or stripped.startswith("="):
                continue
            parts = stripped.split("\t")
            if len(parts) < 9:
                continue
            search_type, band_gap, equation, valid_range, r2, slope, intercept, n_points, validation = parts[:9]
            try:
                range_parts = [p.strip().replace("eV", "").strip() for p in valid_range.split(" - ")]
                range_start, range_end = float(range_parts[0]), float(range_parts[1])
                columns[current].append({
                    "search_type": search_type,
                    "band_gap": float(band_gap),
                    "range_start": range_start,
                    "range_end": range_end,
                    "r_squared": float(r2),
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "validation": validation.strip(),
                })
            except (ValueError, IndexError):
                continue
    return columns


def _best_candidate(candidates):
    """Prefer a PASSED candidate (highest R² among those); fall back to the overall highest-R²
    candidate if none passed validation, so the figure still shows the script's best guess."""
    if not candidates:
        return None
    passed = [c for c in candidates if c["validation"] == "PASSED"]
    pool = passed or candidates
    return max(pool, key=lambda c: c["r_squared"])


def _coords(xs, ys):
    return " ".join(f"({x:.4f},{y:.6f})" for x, y in zip(xs, ys))


def export_tauc_tex(tauc_data_path, gap_results_path, output_tex_path, transition_type,
                     exponent, approach_label, material_label="", template_path=None):
    """Write a standalone (or custom-template-merged) .tex reproducing the user's Tauc-plot
    paper-figure style for this run's data. Returns output_tex_path.
    """
    energy, tf_o, tf_e = _read_tauc_columns(tauc_data_path)
    gap_candidates = _parse_gap_results(gap_results_path) if os.path.exists(gap_results_path) else {}
    best_o = _best_candidate(gap_candidates.get("col_2", []))
    best_e = _best_candidate(gap_candidates.get("col_4", []))

    all_y = tf_o + tf_e
    xlim = auto_range(energy)
    ylim = (0.0, auto_range(all_y)[1])

    lines = [
        r"\begin{axis}[",
        "    x tick label style={/pgf/number format/.cd, fixed, fixed zerofill, precision=1, /tikz/.cd},",
        "    y tick label style={/pgf/number format/.cd, fixed, fixed zerofill, precision=2, /tikz/.cd},",
        "    scaled y ticks=false,",
        "    width=8.2cm, height=6cm, line width=1.5,",
        f"    xmin={xlim[0]:.4f}, xmax={xlim[1]:.4f},",
        f"    ymin={ylim[0]:.4f}, ymax={ylim[1]:.4f},",
        "    minor x tick num=4, minor y tick num=3,",
        r"    ylabel=Tauc function $(\alpha h\nu)^{n}$,",
        "    xlabel=Energy (eV),",
        "    xlabel near ticks, ylabel near ticks,",
        "    legend columns=1, legend cell align={left},",
        "    legend style={draw=none, fill=none, column sep=2.5pt, at={(0,0.5)}, anchor=west, xshift=+2pt},",
        "]",
        rf"\addplot [blue, solid, line cap=round, mark=none] coordinates {{{_coords(energy, tf_o)}}};",
        r"\addlegendentry{$T_{\mathrm{o}}^{\mathrm{cal}}$};",
        rf"\addplot [magenta, solid, line cap=round, mark=none] coordinates {{{_coords(energy, tf_e)}}};",
        r"\addlegendentry{$T_{\mathrm{e}}^{\mathrm{cal}}$};",
    ]

    def _add_fit(best, fit_color, arrow_color, label_tex, y_rel):
        if not best:
            return
        lines.append(
            rf"\addplot [{fit_color}, dotted, mark=none, line cap=round, forget plot, "
            f"domain={best['range_start']:.4f}:{best['range_end']:.4f}, samples=50]"
            f"{{{best['slope']:.6f}*x + ({best['intercept']:.6f})}};"
        )
        lines.append(
            rf"\addplot [{fit_color}, mark=*, mark size=1.5pt, forget plot] coordinates {{({best['band_gap']:.4f}, 0)}};"
        )
        # Keep the arrow short and anchored near the actual gap point -- the real figure's
        # fixed 0.55/0.7 relative positions were hand-tuned for that specific figure's narrow
        # x-range and only happen to sit near the gap there; for arbitrary run data the gap can
        # fall anywhere on the axis, so the label/arrow position is derived from the gap's own
        # relative x-position instead of a hardcoded constant.
        gap_rel = (best["band_gap"] - xlim[0]) / (xlim[1] - xlim[0]) if xlim[1] > xlim[0] else 0.5
        end_rel = max(0.08, min(0.95, gap_rel - 0.02))
        start_rel = max(0.02, end_rel - 0.14)
        lines.append(
            rf"\draw[-stealth, {arrow_color}, line cap=round, line width=1pt] "
            f"(rel axis cs: {start_rel:.4f}, {y_rel:.4f}) node[left, font=\\footnotesize] "
            f"{{{label_tex}={best['band_gap']:.3f}\\,eV}} -- (rel axis cs: {end_rel:.4f}, {y_rel:.4f}) -- "
            f"(axis cs: {best['band_gap']:.4f}, 0);"
        )

    _add_fit(best_o, "cyan", "teal", r"$E_{\mathrm{g},\mathrm{o}}$", 0.60)
    _add_fit(best_e, "orange", "purple", r"$E_{\mathrm{g},\mathrm{e}}$", 0.75)

    if material_label:
        lines.append(f"\\node [anchor=north west, xshift=2pt, yshift=-2pt] at (rel axis cs: 0.02, 1) {{{material_label}}};")
    lines.append(f"\\node [anchor=north east, xshift=-2pt, yshift=-2pt] at (rel axis cs: 0.98, 1) {{{approach_label}}};")
    n_str = "2" if exponent == 2.0 else ("1/2" if exponent == 0.5 else f"{exponent:g}")
    lines.append(
        r"\node [anchor=south west, xshift=+2pt, yshift=+2pt] at (rel axis cs: 0, 0) "
        f"{{\\color{{Brown}} Tauc exponent $n={n_str}$ ({transition_type})}};"
    )
    lines.append(r"\end{axis}")
    axis_block = "\n".join(lines)

    if template_path and os.path.exists(template_path):
        with open(template_path) as f:
            template = f.read()
        if PLACEHOLDER_TOKEN in template:
            content = template.replace(PLACEHOLDER_TOKEN, axis_block)
        else:
            content = (
                template
                + "\n% WARNING: uploaded template had no %%PGFPLOTS_AXIS%% token;"
                " generated axis appended below instead of being merged in.\n"
                + "\\begin{tikzpicture}\n" + axis_block + "\n\\end{tikzpicture}\n"
            )
    else:
        content = (
            "\\documentclass{standalone}\n"
            "\\usepackage[dvipsnames]{xcolor}\n"
            "\\usepackage{pgfplots}\n"
            "\\pgfplotsset{compat=1.18}\n"
            "\\begin{document}\n"
            "\\begin{tikzpicture}\n"
            f"{axis_block}\n"
            "\\end{tikzpicture}\n"
            "\\end{document}\n"
        )

    with open(output_tex_path, "w") as f:
        f.write(content)
    return output_tex_path

#!/usr/bin/env python3
"""Shared figure-output helpers used by every plotting module: auto-ranged axis limits, a
LaTeX/pgfplots export styled to match the user's own validated paper figures (tick-label
formatting, line widths, legend style, `dat/` subfolder convention for the actual numbers --
see e.g. `Figure-Effective-Mass.tex`'s `dat/ZnO-PBESOL-X-CB1.gnu` references), and a PDF
compile step via the vendored Tectonic engine.

Usage:
    from pgfplots_export import auto_range, Curve, export_pgfplots

    curves = [Curve(x=energies, y=alpha_x, label="X"), Curve(x=energies, y=alpha_y, label="Y")]
    dat_paths = export_pgfplots("figure.tex", curves, xlabel="Energy (eV)",
                                 ylabel=r"$(\\alpha h\\nu)^2$", legend=True,
                                 legend_position="north east")
    # dat_paths: the per-curve data files written to <same dir>/dat/ -- add these to your
    # module's own output-file list so they end up in the result zip alongside the .tex.
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

PLACEHOLDER_TOKEN = "%%PGFPLOTS_AXIS%%"

# Vendored self-contained LaTeX engine (github.com/tectonic-typesetting/tectonic) -- no system
# TeX Live needed, so this runs the same way in a Vercel Python function as it does locally.
_TECTONIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "tectonic")

DEFAULT_LINE_WIDTH = 1.5


@dataclass
class Curve:
    x: Sequence[float]
    y: Sequence[float]
    label: str = ""
    color: Optional[str] = None
    dashed: bool = False


def auto_range(values: Iterable[float], pad_frac: float = 0.01):
    """[min, max] of `values` padded by `pad_frac` of the span on each side.

    Falls back to a +/-1 window if all values are equal (zero span), so the axis never
    collapses to a single point.
    """
    values = [v for v in values if v == v]  # drop NaN
    if not values:
        return (0.0, 1.0)
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return (lo - 1, hi + 1)
    pad = span * pad_frac
    return (lo - pad, hi + pad)


def resolve_range(explicit_range: Optional[str], values: Iterable[float], pad_frac: float = 0.01):
    """Manual override (`"min,max"` string) wins; otherwise auto_range(values)."""
    if explicit_range:
        parts = [p.strip() for p in explicit_range.split(",")]
        if len(parts) == 2:
            try:
                return (float(parts[0]), float(parts[1]))
            except ValueError:
                pass
    return auto_range(values, pad_frac)


_LEGEND_POS_TO_PGF = {
    "best": "north east",
    "upper right": "north east",
    "upper left": "north west",
    "lower right": "south east",
    "lower left": "south west",
    "outside": "outer north east",
}


def _pgf_legend_pos(position: str) -> str:
    return _LEGEND_POS_TO_PGF.get((position or "").strip().lower(), "north east")


def _tick_precision(values: Sequence[float]) -> int:
    """0 decimals if every value is (near-enough) an integer, else 2 -- matches the
    precision=0 / precision=2 split seen across the user's own figures (bands/DOS axes use
    precision=0, Tauc/pDOS-style axes use precision=2).
    """
    if all(abs(v - round(v)) < 1e-6 for v in values if v == v):
        return 0
    return 2


def _write_dat_file(dat_dir: str, name: str, x: Sequence[float], y: Sequence[float]) -> str:
    os.makedirs(dat_dir, exist_ok=True)
    path = os.path.join(dat_dir, f"{name}.dat")
    with open(path, "w") as f:
        for xi, yi in zip(x, y):
            f.write(f"{xi:.6g}\t{yi:.6g}\n")
    return path


def _default_axis_block(curves: Sequence[Curve], curve_dat_names: Sequence[str], xlabel: str,
                         ylabel: str, xlim, ylim, legend: bool, legend_position: str,
                         line_width: float, xtick_labels: Optional[Sequence] = None) -> str:
    x_precision = _tick_precision([xlim[0], xlim[1]])
    y_precision = _tick_precision([ylim[0], ylim[1]])
    lines = [
        r"\begin{axis}[",
        "    x tick label style={/pgf/number format/.cd, fixed, fixed zerofill, "
        f"precision={x_precision}, /tikz/.cd}},",
        "    y tick label style={/pgf/number format/.cd, fixed, fixed zerofill, "
        f"precision={y_precision}, /tikz/.cd}},",
        f"    xlabel={{{xlabel}}},",
        f"    ylabel={{{ylabel}}},",
        f"    xmin={xlim[0]:.6g}, xmax={xlim[1]:.6g},",
        f"    ymin={ylim[0]:.6g}, ymax={ylim[1]:.6g},",
        f"    line width={line_width:.2f},",
        "    width=10cm, height=7cm,",
        "    xlabel near ticks, ylabel near ticks,",
        "    minor x tick num=4, minor y tick num=4,",
    ]
    if xtick_labels:
        # High-symmetry k-path ticks (e.g. Gamma/M/K), matching Figure-Bands-Dos-PBESOL.tex's
        # own xtick/xticklabels convention instead of leaving plain numeric k-distance ticks.
        lines.append(f"    xtick={{{','.join(f'{p:.6g}' for p, _ in xtick_labels)}}},")
        lines.append(f"    xticklabels={{{', '.join(l for _, l in xtick_labels)}}},")
    if legend and any(c.label for c in curves):
        lines.append(
            "    legend cell align={left}, "
            f"legend style={{draw=none, fill=none, at={{(0.98,0.5)}}, anchor={_pgf_legend_pos(legend_position)}}},"
        )
    lines.append("]")
    for curve, dat_name in zip(curves, curve_dat_names):
        style = curve.color or "blue"
        if curve.dashed:
            style += ", dashed"
        style += ", line cap=round, mark=none"
        lines.append(rf"\addplot [{style}] table[col sep=tab] {{dat/{dat_name}.dat}};")
        if legend and curve.label:
            lines.append(f"\\addlegendentry{{{curve.label}}}")
    lines.append(r"\end{axis}")
    return "\n".join(lines)


def export_pgfplots(output_path: str, curves: Sequence[Curve], xlabel: str, ylabel: str,
                     xlim=None, ylim=None, legend: bool = True, legend_position: str = "best",
                     line_width: float = DEFAULT_LINE_WIDTH,
                     template_path: Optional[str] = None,
                     xtick_labels: Optional[Sequence] = None):
    """Write a standalone .tex file plotting `curves` with pgfplots, styled to match the user's
    own paper figures: fixed-precision tick labels, `line cap=round`, `xlabel/ylabel near
    ticks`, and each curve's data in its own file under a `dat/` subfolder next to the .tex
    (exactly the convention `Figure-Effective-Mass.tex` etc. already use), rather than
    inlining coordinates directly in the .tex.

    If `template_path` is given, its content is used verbatim except that the token
    `%%PGFPLOTS_AXIS%%` (if present) is replaced with the generated `axis` environment; the
    axis is appended after the template's content if the token is missing, with a warning
    comment so the mismatch is visible rather than silently swallowed.

    Returns the list of `.dat` file paths written (add these to your module's own output-file
    list so they end up in the result zip alongside the .tex).
    """
    all_x = [v for c in curves for v in c.x]
    all_y = [v for c in curves for v in c.y]
    xlim = xlim or auto_range(all_x)
    ylim = ylim or auto_range(all_y)

    dat_dir = os.path.join(os.path.dirname(output_path) or ".", "dat")
    base_name = os.path.splitext(os.path.basename(output_path))[0]
    dat_paths = []
    curve_dat_names = []
    for i, curve in enumerate(curves):
        dat_name = f"{base_name}-{i + 1}" if len(curves) > 1 else base_name
        dat_paths.append(_write_dat_file(dat_dir, dat_name, curve.x, curve.y))
        curve_dat_names.append(dat_name)

    axis_block = _default_axis_block(curves, curve_dat_names, xlabel, ylabel, xlim, ylim,
                                      legend, legend_position, line_width, xtick_labels)

    if template_path:
        with open(template_path, "r") as f:
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

    with open(output_path, "w") as f:
        f.write(content)

    return dat_paths


def compile_pgfplots_to_pdf(tex_path: str, timeout: int = 60):
    """Best-effort: compile `tex_path` to a PDF alongside it with the vendored Tectonic engine.
    `tex_path`'s sibling `dat/` folder (written by export_pgfplots) is picked up automatically
    since Tectonic runs with `tex_path`'s directory as its working directory.

    Returns the PDF path on success, or None on failure (missing binary, network-fetch failure
    for Tectonic's package bundle on first run, or a genuinely broken .tex -- e.g. an uploaded
    custom template with a LaTeX error). Never raises: a failed PDF compile should not break an
    otherwise-successful PNG/`.tex` result, so the caller can just skip adding the PDF.
    """
    if not os.path.exists(_TECTONIC_PATH):
        return None
    pdf_path = os.path.splitext(tex_path)[0] + ".pdf"
    env = dict(os.environ)
    env.setdefault("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
    try:
        subprocess.run(
            [_TECTONIC_PATH, os.path.basename(tex_path)],
            cwd=os.path.dirname(tex_path) or ".",
            env=env, capture_output=True, text=True, timeout=timeout, check=True,
        )
    except Exception:
        return None
    return pdf_path if os.path.exists(pdf_path) else None

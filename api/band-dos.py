"""Vercel Python Function for the "Band structure + DOS plotter" module.

Endpoint: POST /api/band-dos
Fields expected: moduleId, parameters (JSON: energyShift, kPathTicks, occupiedSplit,
figureFormat, xRange, yRange), files: bandsGnu (bands.x .dat.gnu), dos (dos.x output),
templateFile (optional custom .tex template for the pgfplots export).
Response: application/zip (figures/ + tables/), or JSON error.
"""

import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import BaseTaskHandler, PipelineError, classify_uploads_by_role, classify_output_folder, safe_filename  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "electronic"))
from bands_dos_plotter import plot_bands_dos  # noqa: E402


def _build_zip(out_paths, module_title):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = (
            f"{module_title} - results\n" + "=" * 60 + "\n\n"
            "figures/       - Bands figure and DOS figure, kept separate (PNG, LaTeX pgfplots and/or compiled PDF)\n"
            "figures/dat/   - the plotted data, referenced by the .tex file(s) (dat/<name>.dat)\n"
            "tables/        - per-point CSV of both curves\n"
        )
        zf.writestr("README.txt", readme)
        for p in out_paths:
            zf.write(p, classify_output_folder(p))
    return buf.getvalue()


class handler(BaseTaskHandler):
    MODULE_ID = "band-dos-plotter"

    def handle_task(self, fields, files, parameters, scratch_dir):
        # No fixed keyword identifies a bands.x .dat.gnu file's content (it's just numbers), so
        # only the dos.x file is keyword-validated; the other upload is taken positionally.
        uploads = files.get("files") or []
        if len(uploads) < 2:
            raise PipelineError("Expected 2 files: a bands.x .dat.gnu file and a dos.x output file.")

        dos_path = None
        bands_path = None
        for original_name, payload in uploads:
            dest = os.path.join(scratch_dir, safe_filename(original_name))
            with open(dest, "wb") as fh:
                fh.write(payload)
            if "dos" in (original_name or "").lower() and dos_path is None:
                dos_path = dest
            elif bands_path is None:
                bands_path = dest
            elif dos_path is None:
                dos_path = dest
        if not dos_path or not bands_path:
            raise PipelineError(
                "Could not tell the bands file and the dos.x file apart. Please make sure the "
                "dos.x output filename contains 'dos' (case-insensitive)."
            )

        energy_shift = None
        raw_shift = (parameters.get("energyShift") or "").strip()
        if raw_shift:
            try:
                energy_shift = float(raw_shift)
            except ValueError:
                raise PipelineError(f"'{raw_shift}' is not a valid number for the VBM/Fermi energy.")

        kpath_ticks = parameters.get("kPathTicks") or ""
        occupied_split = parameters.get("occupiedSplit") or "Show both"
        figure_format_raw = (parameters.get("figureFormat") or "PNG").lower()
        figure_format = "both" if "both" in figure_format_raw else ("latex" if "latex" in figure_format_raw else "png")

        plot_settings = {
            "figure_format": figure_format,
            "x_range": parameters.get("xRange") or "",
            "y_range": parameters.get("yRange") or "",
            "template_path": None,
        }
        template_uploads = files.get("templateFile") or []
        if template_uploads:
            template_name, template_bytes = template_uploads[0]
            if template_name.lower().endswith(".tex"):
                template_path = os.path.join(scratch_dir, "template.tex")
                with open(template_path, "wb") as fh:
                    fh.write(template_bytes)
                plot_settings["template_path"] = template_path

        try:
            out_paths = plot_bands_dos(
                bands_path, dos_path, scratch_dir, tag="Bands-DOS",
                energy_shift=energy_shift, kpath_ticks_spec=kpath_ticks,
                occupied_split=occupied_split, plot_settings=plot_settings,
            )
        except ValueError as e:
            raise PipelineError(str(e))

        module_title = fields.get("moduleTitle") or "Band structure + DOS plotter"
        zip_bytes = _build_zip(out_paths, module_title)
        filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-')}-Results.zip"
        return zip_bytes, filename

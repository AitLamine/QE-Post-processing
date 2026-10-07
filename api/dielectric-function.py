"""Vercel Python Function for the "Dielectric function plotter" module.

Endpoint: POST /api/dielectric-function
Fields expected: moduleId, parameters (JSON: polarization, figureFormat, xRange, yRange),
files: epsr, epsi (any material's epsilon.x output -- see scripts/optical/eps_utils.py).
Response: application/zip (figures/ + tables/), or JSON {"error": ...} on failure.
"""

import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import BaseTaskHandler, PipelineError, classify_output_folder, save_upload  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "optical"))
from dielectric_function_plotter import plot_dielectric_function  # noqa: E402


def _build_zip(out_paths, module_title):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = (
            f"{module_title} - results\n"
            "=" * 60 + "\n\n"
            "figures/       - Epsilon1 and Epsilon2 figures (PNG, LaTeX pgfplots and/or compiled PDF)\n"
            "figures/dat/   - the plotted data, referenced by the .tex file(s) (dat/<name>.dat)\n"
            "tables/        - combined CSV of both curves\n"
        )
        zf.writestr("README.txt", readme)
        for p in out_paths:
            zf.write(p, classify_output_folder(p))
    return buf.getvalue()


class handler(BaseTaskHandler):
    MODULE_ID = "dielectric-function-plotter"

    def handle_task(self, fields, files, parameters, scratch_dir):
        epsr_path = save_upload(files, "epsr", scratch_dir, role="epsr")
        epsi_path = save_upload(files, "epsi", scratch_dir, role="epsi")

        polarization = parameters.get("polarization") or "Ordinary"
        x_axis = parameters.get("xAxis") or "Energy (eV)"
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
            out_paths = plot_dielectric_function(
                epsr_path, epsi_path, scratch_dir, tag="Dielectric-Function",
                polarization=polarization, x_axis=x_axis, plot_settings=plot_settings,
            )
        except ValueError as e:
            raise PipelineError(str(e))

        module_title = fields.get("moduleTitle") or "Dielectric function plotter"
        zip_bytes = _build_zip(out_paths, module_title)
        filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-')}-Results.zip"
        return zip_bytes, filename

"""Vercel Python Function for the "Projected DOS (pDOS) plotter" module.

Endpoint: POST /api/pdos-plotter
Fields expected: moduleId, parameters (JSON: energyShift, pdosFileLabels [{filename, species,
orbital, shell}], figureFormat, xRange, yRange), files: files (raw projwfc.x pdos_atm uploads,
one per orbital/atom), dosForFermi (optional, dos.x output, only used to auto-detect EFermi).
Response: application/zip (figures/ + tables/), or JSON error.
"""

import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import BaseTaskHandler, PipelineError, classify_output_folder  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "electronic"))
from pdos_plotter import plot_pdos, detect_efermi_from_dos_file  # noqa: E402


def _build_zip(out_paths, module_title):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = (
            f"{module_title} - results\n" + "=" * 60 + "\n\n"
            "figures/       - one figure per species (PNG, LaTeX pgfplots and/or compiled PDF)\n"
            "figures/dat/   - the plotted data, referenced by the .tex file(s) (dat/<name>.dat)\n"
            "tables/        - combined CSV of all plotted orbitals\n"
        )
        zf.writestr("README.txt", readme)
        for p in out_paths:
            zf.write(p, classify_output_folder(p))
    return buf.getvalue()


class handler(BaseTaskHandler):
    MODULE_ID = "pdos-plotter"

    def handle_task(self, fields, files, parameters, scratch_dir):
        uploads = files.get("files") or []
        if not uploads:
            raise PipelineError("No pdos_atm files uploaded.")

        labels = parameters.get("pdosFileLabels") or []
        if len(labels) != len(uploads):
            raise PipelineError(
                f"Got {len(uploads)} uploaded file(s) but {len(labels)} label entries. "
                "Please label every uploaded file (species, orbital, shell) before submitting."
            )

        file_entries = []
        for (original_name, payload), label in zip(uploads, labels):
            species = (label.get("species") or "").strip()
            orbital = (label.get("orbital") or "").strip()
            shell = (label.get("shell") or "").strip()
            if not species or not orbital:
                raise PipelineError(
                    f"'{original_name}' is missing a species and/or orbital label. "
                    "Nothing was processed -- please label every file."
                )
            dest = os.path.join(scratch_dir, original_name)
            with open(dest, "wb") as fh:
                fh.write(payload)
            file_entries.append({'species': species, 'orbital': orbital, 'shell': shell, 'path': dest})

        energy_shift = None
        raw_shift = (parameters.get("energyShift") or "").strip()
        if raw_shift:
            try:
                energy_shift = float(raw_shift)
            except ValueError:
                raise PipelineError(f"'{raw_shift}' is not a valid number for the VBM/Fermi energy.")

        dos_uploads = files.get("dosForFermi") or []
        if energy_shift is None and dos_uploads:
            dos_name, dos_payload = dos_uploads[0]
            dos_path = os.path.join(scratch_dir, dos_name)
            with open(dos_path, "wb") as fh:
                fh.write(dos_payload)
            energy_shift = detect_efermi_from_dos_file(dos_path)

        if energy_shift is None:
            raise PipelineError(
                "No VBM/Fermi energy available: type one in, or upload the dos.x output file so "
                "it can be auto-detected from its 'EFermi = ...' header. Nothing was processed."
            )

        figure_format_raw = (parameters.get("figureFormat") or "PNG").lower()
        figure_format = "both" if "both" in figure_format_raw else ("latex" if "latex" in figure_format_raw else "png")
        plot_settings = {
            "figure_format": figure_format,
            "x_range": parameters.get("xRange") or "",
            "y_range": parameters.get("yRange") or "",
            "template_path": None,
        }

        try:
            out_paths = plot_pdos(file_entries, scratch_dir, tag="pDOS", energy_shift=energy_shift,
                                   plot_settings=plot_settings)
        except ValueError as e:
            raise PipelineError(str(e))

        module_title = fields.get("moduleTitle") or "Projected DOS (pDOS) plotter"
        zip_bytes = _build_zip(out_paths, module_title)
        filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-')}-Results.zip"
        return zip_bytes, filename

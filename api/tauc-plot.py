"""Vercel Python Function for the "Tauc-plot / band-gap extractor" module.

Endpoint: POST /api/tauc-plot
Fields expected: moduleId, parameters (JSON: transitionType, fitWindow, electronicGap, approach,
figureFormat -- xRange/yRange are not used here since the gap-extraction step below controls its
own plot), files: epsr, epsi (any material's epsilon.x output).

Two approaches, matching the original toolkit's two driver scripts exactly (`All-Scripts/
1-Global-Commands-First-Approach.sh` and `2-Global-Commands-Second-Approach.sh`):
  - First approach : skip peak-trimming entirely, fit the gap directly on the full Tauc function.
  - Second approach : run peak_trim.process_tauc_data first (trims noise + everything past the
    3rd detected peak), then fit the gap on the trimmed data.
These can genuinely disagree -- peak-trim can lock onto a strong low-energy dielectric feature
(e.g. an LO-TO phonon response in a polar/ionic material) instead of the real electronic edge,
which is exactly why the original toolkit always ran both and kept the outputs in separate,
clearly-labeled folders rather than silently picking one. `approach` selects "first", "second",
or "both" (default); both are attempted independently when "both" is selected, so one approach
finding no fit doesn't hide a result the other approach did find.

Full pipeline per approach (each step a direct, validated port -- see scripts/tauc/*.py
docstrings):
  1. absorption_from_eps.compute_absorption : epsr/epsi -> per-axis absorption coefficient
  2. merge_absorption.merge                 : 3 axis files -> one energy-sorted file
  3. tauc_function.compute_tauc             : absorption -> Tauc function (direct/indirect)
  4. [second approach only] peak_trim.process_tauc_data : trims noise + everything past the
     3rd peak
  5. slope_line_bandgap.py (subprocess)     : fits the linear region, extracts the band gap,
     saves its own plot -- ported unchanged (see that script's own docstring) rather than
     re-implemented inline, since it's a large, already-validated adaptive algorithm.

Response: application/zip (figures/ + tables/ + a plain-language gap-value summary), or JSON error.
"""

import os
import io
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import BaseTaskHandler, PipelineError, save_upload  # noqa: E402

TAUC_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "tauc")
)
sys.path.insert(0, TAUC_SCRIPTS_DIR)
from absorption_from_eps import compute_absorption  # noqa: E402
from merge_absorption import merge as merge_absorption  # noqa: E402
from tauc_function import compute_tauc  # noqa: E402
from peak_trim import process_tauc_data  # noqa: E402
from tauc_latex_export import export_tauc_tex  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "common"))
from pgfplots_export import compile_pgfplots_to_pdf  # noqa: E402


def _run_slope_line(input_file, output_file, fit_window, electronic_gap):
    """Run slope_line_bandgap.py. Returns an error message string on failure, or None on
    success. Doesn't raise directly: when both approaches are requested, one failing shouldn't
    hide a result the other approach did find -- the caller decides what to do with the error.
    """
    cmd = [sys.executable, os.path.join(TAUC_SCRIPTS_DIR, "slope_line_bandgap.py"), input_file, output_file]
    if fit_window:
        parts = [p.strip() for p in fit_window.split(",")]
        if len(parts) == 2:
            try:
                start, end = float(parts[0]), float(parts[1])
                cmd += ["--range", str(start), str(end)]
            except ValueError:
                pass
    if electronic_gap:
        try:
            cmd += ["--electronic-gap", str(float(electronic_gap))]
        except ValueError:
            pass
    result = subprocess.run(cmd, cwd=os.path.dirname(input_file), capture_output=True, text=True)
    # slope_line_bandgap.py can exit 0 while still finding no valid fit candidates (it just
    # prints "No results to save" and skips writing output_file in that case), so success can't
    # be judged from the exit code alone -- check the file actually landed before trusting it.
    if result.returncode != 0 or not os.path.exists(output_file):
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-8:]
        return (
            "Band-gap extraction step failed. This usually means the Tauc data doesn't have a "
            "clean linear region to fit (check the uploaded epsr/epsi files, the fit-window "
            "value, or try the other approach). Details:\n" + "\n".join(tail)
        )
    return None


def _run_approach(label, input_file, fit_window, electronic_gap, transition_type, exponent,
                   material_label, want_latex, template_path):
    """Run slope_line_bandgap.py on `input_file` for one approach. Returns a dict with either
    {'plot_png', 'gap_results_path', ['tex_path', 'pdf_path']} on success or {'error'} on
    failure -- never raises, so the caller can still build a zip from whichever approach(es)
    succeeded.
    """
    gap_results_path = os.path.splitext(input_file)[0] + "_band-gap-results.txt"
    error = _run_slope_line(input_file, gap_results_path, fit_window, electronic_gap)
    if error:
        return {"label": label, "error": error}
    plot_png = os.path.splitext(input_file)[0] + "_enhanced_analysis.png"
    result = {"label": label, "gap_results_path": gap_results_path, "plot_png": plot_png}
    if want_latex:
        tex_path = os.path.splitext(input_file)[0] + "_tauc-plot.tex"
        export_tauc_tex(
            input_file, gap_results_path, tex_path, transition_type=transition_type,
            exponent=exponent, approach_label=label, material_label=material_label,
            template_path=template_path,
        )
        result["tex_path"] = tex_path
        pdf_path = compile_pgfplots_to_pdf(tex_path)
        if pdf_path:
            result["pdf_path"] = pdf_path
    return result


class handler(BaseTaskHandler):
    MODULE_ID = "tauc-plot-extractor"

    def handle_task(self, fields, files, parameters, scratch_dir):
        epsr_path = save_upload(files, "epsr", scratch_dir, role="epsr")
        epsi_path = save_upload(files, "epsi", scratch_dir, role="epsi")

        transition_type = parameters.get("transitionType") or "Direct"
        exponent = 2.0 if transition_type.lower().startswith("direct") else 0.5
        fit_window = parameters.get("fitWindow") or ""
        electronic_gap = parameters.get("electronicGap") or ""
        material_label = parameters.get("materialLabel") or ""

        figure_format_raw = (parameters.get("figureFormat") or "PNG").lower()
        want_png = "both" in figure_format_raw or "latex" not in figure_format_raw
        want_latex = "latex" in figure_format_raw or "both" in figure_format_raw

        template_path = None
        template_uploads = files.get("templateFile") or []
        if template_uploads:
            template_name, template_bytes = template_uploads[0]
            if template_name.lower().endswith(".tex"):
                template_path = os.path.join(scratch_dir, "template.tex")
                with open(template_path, "wb") as fh:
                    fh.write(template_bytes)

        approach_raw = (parameters.get("approach") or "both").strip().lower()
        run_first = "first" in approach_raw or "both" in approach_raw
        run_second = "second" in approach_raw or "both" in approach_raw
        if not run_first and not run_second:
            run_first = run_second = True

        try:
            abs_x, abs_y, abs_z = compute_absorption(epsr_path, epsi_path, scratch_dir, tag="Tauc")

            merged_energy = os.path.join(scratch_dir, "merged-energy-sorted.dat")
            merged_wavelength = os.path.join(scratch_dir, "merged-wavelength-sorted.dat")
            merge_absorption(abs_x, abs_y, abs_z, merged_energy, merged_wavelength)

            tauc_out = os.path.join(scratch_dir, "tauc-function.dat")
            compute_tauc(merged_energy, tauc_out, exponent, transition_label=transition_type)
        except ValueError as e:
            raise PipelineError(str(e))

        results = {}
        trim_info_out = None

        if run_first:
            results["First-Approach"] = _run_approach(
                "First approach (no peak-trim)", tauc_out, fit_window, electronic_gap,
                transition_type, exponent, material_label, want_latex, template_path,
            )

        if run_second:
            try:
                trimmed_out = os.path.join(scratch_dir, "tauc-function-trimmed.dat")
                trim_info_out = os.path.join(scratch_dir, "tauc-trim-report.txt")
                process_tauc_data(tauc_out, trim_info_out, trimmed_out)
            except ValueError as e:
                results["Second-Approach"] = {"label": "Second approach (peak-trimmed)", "error": str(e)}
            else:
                results["Second-Approach"] = _run_approach(
                    "Second approach (peak-trimmed)", trimmed_out, fit_window, electronic_gap,
                    transition_type, exponent, material_label, want_latex, template_path,
                )

        if all("error" in r for r in results.values()):
            combined = "\n\n".join(f"{r['label']}:\n{r['error']}" for r in results.values())
            raise PipelineError(f"Band-gap extraction failed for every selected approach.\n\n{combined}")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            readme_lines = [
                "Tauc-plot / band-gap extractor - results\n" + "=" * 60,
                f"\nTransition type: {transition_type} (Tauc exponent {exponent})\n",
                "Two independent approaches can be run (they can genuinely disagree -- peak-",
                "trimming can lock onto a strong low-energy feature instead of the real",
                "electronic edge, which is why both are kept separate rather than silently",
                "picking one):\n",
            ]
            for key, r in results.items():
                folder = key
                if "error" in r:
                    readme_lines.append(f"{r['label']}: FAILED -- no result in this zip.")
                    readme_lines.append(f"  {r['error'].splitlines()[0]}\n")
                    continue
                readme_lines.append(f"{r['label']}: see figures/{folder}/ and tables/{folder}/\n")
                if want_png and os.path.exists(r["plot_png"]):
                    zf.write(r["plot_png"], f"figures/{folder}/{os.path.basename(r['plot_png'])}")
                if r.get("tex_path") and os.path.exists(r["tex_path"]):
                    zf.write(r["tex_path"], f"figures/{folder}/{os.path.basename(r['tex_path'])}")
                if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                    zf.write(r["pdf_path"], f"figures/{folder}/{os.path.basename(r['pdf_path'])}")
                zf.write(r["gap_results_path"], f"tables/{folder}/band-gap-results.txt")
            if trim_info_out and os.path.exists(trim_info_out):
                zf.write(trim_info_out, "tables/Second-Approach/tauc-trim-report.txt")

            zf.writestr("README.txt", "\n".join(readme_lines) + "\n")
            for p in (abs_x, abs_y, abs_z, merged_energy, tauc_out):
                zf.write(p, f"raw-parsed-data/{os.path.basename(p)}")
            if run_second and os.path.exists(os.path.join(scratch_dir, "tauc-function-trimmed.dat")):
                zf.write(os.path.join(scratch_dir, "tauc-function-trimmed.dat"), "raw-parsed-data/tauc-function-trimmed.dat")

        module_title = fields.get("moduleTitle") or "Tauc-plot / band-gap extractor"
        filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-')}-Results.zip"
        return buf.getvalue(), filename

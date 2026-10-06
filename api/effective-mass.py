"""
Vercel Python Function for the "Effective mass extractor" module
(dft-postprocessing/lib/modules.js -> effective-mass-extractor).

Endpoint: POST /api/effective-mass

Convention used: the documented Vercel "Python functions in the /api
directory" file-based convention (a top-level `handler` class subclassing
`http.server.BaseHTTPRequestHandler`), confirmed current against Vercel's own
docs (vercel.com/docs/functions/runtimes/python/api-directory, checked while
writing this file) rather than assumed from stale memory. This coexists with
the Next.js app's `app/api/process/route.js` (Node) since they are different
path segments; no shared config needed. FastAPI/Flask/Django "framework
preset" detection does NOT apply here since this project has no such
framework declared, so Vercel falls back to the file-based-handler flow.

Multipart parsing: no `cgi` module (removed in Python 3.13, and Vercel
projects created without a pinned Python version can build on newer
runtimes) and no third-party dependency (requirements.txt is shared with the
other modules and shouldn't gain a multipart-parsing package just for this
handler). Instead this file re-uses the stdlib `email` package: a
multipart/form-data body is byte-for-byte a MIME multipart body, so
prepending a synthetic `Content-Type`/`MIME-Version` header and feeding the
result to `email.parser.BytesParser` parses it correctly with zero extra
dependencies. See `_parse_multipart` below.

Request fields expected (see this module's final report for the full
parameter/field-name contract handed to the frontend):
  - moduleId, moduleTitle
  - parameters: JSON string (detectionMode, shared pipeline settings, plot
    settings, and manual-mode lattice/VBM values)
  - files, named by slot with no numeric prefix (Auto mode: `datgnu`,
    `scfBandsIn`, `scfBandsOut`, `bandsCalcIn`, `bandsCalcOut`; Manual mode:
    `bandFile`)
  - templateFile: optional custom LaTeX template (.tex) for the pgfplots
    export

One k-direction per request, by design: an earlier version of this module
accepted 1-3 directions in a single request, chaining up to 3x the
subprocess pipeline below into one HTTP call. That's exactly the kind of
request a serverless function timeout can kill partway through, and it's
also just not how every other module in this app works (upload once,
process once, download once). A student wanting more than one direction
runs this module once per direction instead.

Response: a binary `application/zip` body (same header pattern as
app/api/process/route.js) containing README.txt / figures/ / tables/ /
raw-parsed-data/, or a small JSON `{"error": "..."}` body with a 4xx/5xx
status on failure (plain-language messages, no raw tracebacks, per the
module outline's "Error messages" requirement).
"""

import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "effective-mass")
)

AUTO_FILE_SLOTS = {
    "datgnu": "dat",  # goes into raw/dat/
    "scfBandsIn": "",
    "scfBandsOut": "",
    "bandsCalcIn": "",
    "bandsCalcOut": "",
}


class PipelineError(Exception):
    """Raised for any problem we can explain in plain language to the student."""


# ---------------------------------------------------------------------------
# Multipart parsing (stdlib only - see module docstring)
# ---------------------------------------------------------------------------

def _parse_multipart(content_type_header, body_bytes):
    """Parse a multipart/form-data body with the stdlib `email` package.

    Returns (fields: dict[str, str], files: dict[str, (filename, bytes)]).
    """
    synthetic_header = (
        f"Content-Type: {content_type_header}\r\nMIME-Version: 1.0\r\n\r\n"
    ).encode("utf-8")
    msg = BytesParser(policy=policy.compat32).parsebytes(synthetic_header + body_bytes)

    fields = {}
    files = {}
    if not msg.is_multipart():
        return fields, files

    for part in msg.get_payload():
        disposition = part.get("Content-Disposition", "")
        if not disposition:
            continue
        params = {}
        for item in disposition.split(";")[1:]:
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                params[k.strip().lower()] = v.strip().strip('"')
        name = params.get("name")
        if name is None:
            continue
        filename = params.get("filename")
        payload = part.get_payload(decode=True) or b""
        if filename:
            files[name] = (filename, payload)
        else:
            try:
                fields[name] = payload.decode("utf-8")
            except UnicodeDecodeError:
                fields[name] = payload.decode("latin-1")
    return fields, files


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _friendly_subprocess_error(e, direction_label):
    script_name = os.path.basename(e.cmd[1]) if len(e.cmd) > 1 else str(e.cmd)
    tail_source = (e.stderr or e.stdout or "").strip()
    tail = tail_source.splitlines()[-6:] if tail_source else ["(no output captured)"]
    return (
        f"Processing failed for {direction_label} while running {script_name}. "
        "This usually means one of the uploaded files doesn't look like the expected "
        "Quantum ESPRESSO output, or a typed value (lattice constant / band index) doesn't "
        "match the uploaded band file. Details:\n" + "\n".join(tail)
    )


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value, default=True):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _direction_label(parameters):
    return parameters.get("directionLabel") or "Direction"


def _extract_effective_mass(info_text):
    m_match = re.search(r"EFFECTIVE MASS:\s*m\*/m.\s*=\s*([-\d.]+)", info_text)
    return float(m_match.group(1)) if m_match else None


def _extract_r_squared(info_text):
    r_match = re.search(r"R.:\s*([-\d.]+)", info_text)
    return float(r_match.group(1)) if r_match else None


# ---------------------------------------------------------------------------
# Per-direction pipeline (mirrors Run-Effective-Mass-Direction.sl exactly,
# branching only at the Detect-Configuration.py / Manual-Configuration.py step)
# ---------------------------------------------------------------------------

def _run_direction(mode, parameters, files, scratch_dir, template_path):
    label = _direction_label(parameters)
    direction_cwd = os.path.join(scratch_dir, "direction")
    raw_dir = os.path.join(direction_cwd, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    n_below = _int(parameters.get("nBandsBelowVbm"), 3)
    n_above = _int(parameters.get("nBandsAboveCbm"), 3)
    points_around_extremum = _int(parameters.get("pointsAroundExtremum"), 10)
    material_label = parameters.get("materialLabel") or ""

    # Normalize the raw dropdown value ("PNG" / "LaTeX (pgfplots)" / "Both") down to the
    # plain "png"/"latex"/"both" token create_enhanced_plot checks for exact equality against
    # -- a bare .lower() left "latex (pgfplots)" matching neither "latex" nor "both", which
    # silently produced no figure at all when "LaTeX (pgfplots)" was selected. Every other
    # module's api/*.py already does this substring-based normalization; this one didn't.
    figure_format_raw = (parameters.get("figureFormat") or "png").lower()
    figure_format = "both" if "both" in figure_format_raw else ("latex" if "latex" in figure_format_raw else "png")

    pipeline_settings = {
        "material_label": material_label,
        "n_bands_below_vbm": n_below,
        "n_bands_above_cbm": n_above,
        "points_around_extremum": points_around_extremum,
        "plot": {
            "x_range": parameters.get("xRange") or "",
            "y_range": parameters.get("yRange") or "",
            "legend_show": _bool(parameters.get("legendShow"), True),
            "legend_label_data": parameters.get("legendLabelData") or "DFT data points",
            "legend_label_fit": parameters.get("legendLabelFit") or "Fitted parabola",
            "legend_position": parameters.get("legendPosition") or "best",
            "figure_format": figure_format,
            "template_path": template_path,
        },
    }
    with open(os.path.join(direction_cwd, "Pipeline-Settings.json"), "w") as fh:
        json.dump(pipeline_settings, fh, indent=2)

    uploaded_names = []

    if mode == "auto":
        dat_dir = os.path.join(raw_dir, "dat")
        os.makedirs(dat_dir, exist_ok=True)
        missing = []
        for slot, subdir in AUTO_FILE_SLOTS.items():
            if slot not in files:
                missing.append(slot)
                continue
            fname, fbytes = files[slot]
            uploaded_names.append(fname)
            dest_dir = dat_dir if subdir == "dat" else raw_dir
            with open(os.path.join(dest_dir, fname), "wb") as fh:
                fh.write(fbytes)
        if missing:
            raise PipelineError(
                f"{label}: Auto mode needs all 4 raw QE files, but "
                f"{len(missing)} field(s) were missing from the upload ({', '.join(missing)}). "
                "Auto mode expects the .dat.gnu band file plus the scf-bands and "
                "Bands-Calculation .in/.out pairs, exactly as pw.x/bands.x produced them."
            )
        try:
            _run(
                [sys.executable, os.path.join(SCRIPTS_DIR, "Detect-Configuration.py"), "raw", label],
                direction_cwd,
            )
        except subprocess.CalledProcessError as e:
            raise PipelineError(_friendly_subprocess_error(e, label))
    else:
        if "bandFile" not in files:
            raise PipelineError(
                f"{label}: Manual mode needs one band-structure data file "
                "('bandFile') plus the typed lattice constant and VBM band index."
            )
        fname, fbytes = files["bandFile"]
        uploaded_names.append(fname)
        band_path = os.path.join(raw_dir, fname)
        with open(band_path, "wb") as fh:
            fh.write(fbytes)

        lattice_constant = _float(parameters.get("latticeConstant"))
        vbm_index = _int(parameters.get("vbmIndex"), None)
        if lattice_constant is None or vbm_index is None:
            raise PipelineError(
                f"{label}: Manual mode needs both a lattice constant (Angstrom) and a "
                "VBM band index typed in ('latticeConstant' and 'vbmIndex')."
            )
        try:
            _run(
                [
                    sys.executable,
                    os.path.join(SCRIPTS_DIR, "Manual-Configuration.py"),
                    band_path,
                    label,
                    str(lattice_constant),
                    str(vbm_index),
                    str(n_below),
                    str(n_above),
                    str(points_around_extremum),
                    material_label,
                ],
                direction_cwd,
            )
        except subprocess.CalledProcessError as e:
            raise PipelineError(_friendly_subprocess_error(e, label))

    try:
        _run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "Kohn-Sham-States-Extraction.py")],
            direction_cwd,
        )

        band_files = sorted(glob.glob(os.path.join(direction_cwd, "VB*.dat"))) + sorted(
            glob.glob(os.path.join(direction_cwd, "CB*.dat"))
        )
        for bf in band_files:
            _run(
                [sys.executable, os.path.join(SCRIPTS_DIR, "Extract-Extremum.py"), os.path.basename(bf)],
                direction_cwd,
            )
        for bf in band_files:
            _run(
                [
                    sys.executable,
                    os.path.join(SCRIPTS_DIR, "Kohn-Sham-States-Polynomial-Fitting-Script.py"),
                    os.path.basename(bf),
                ],
                direction_cwd,
            )

        fit_results_files = sorted(glob.glob(os.path.join(direction_cwd, "*_scipy_fitting_results.txt")))
        for ff in fit_results_files:
            _run(
                [
                    sys.executable,
                    os.path.join(SCRIPTS_DIR, "Effective-Mass-Calculation-Plot-Data-Generation.py"),
                    os.path.basename(ff),
                ],
                direction_cwd,
            )

        _run([sys.executable, os.path.join(SCRIPTS_DIR, "Final-Results-Organization.py")], direction_cwd)
    except subprocess.CalledProcessError as e:
        raise PipelineError(_friendly_subprocess_error(e, label))

    with open(os.path.join(direction_cwd, "material_config.json")) as fh:
        material_config = json.load(fh)

    band_results = []
    for produced in material_config.get("produced_band_files", []):
        folder_name = os.path.splitext(produced)[0]
        folder_path = os.path.join(direction_cwd, folder_name)
        info_path = os.path.join(folder_path, f"{folder_name}_info.txt")
        m_eff, r_squared = None, None
        if os.path.exists(info_path):
            info_text = open(info_path, encoding="utf-8").read()
            m_eff = _extract_effective_mass(info_text)
            r_squared = _extract_r_squared(info_text)
        band_results.append(
            {
                "folder": folder_name,
                "folder_path": folder_path,
                "carrier": "Valence (hole)" if folder_name.startswith("VB") else "Conduction (electron)",
                "m_eff": m_eff,
                "r_squared": r_squared,
            }
        )

    return {
        "label": label,
        "mode": mode,
        "direction_cwd": direction_cwd,
        "material_config": material_config,
        "band_results": band_results,
        "uploaded_names": uploaded_names,
        "settings": pipeline_settings,
    }


# ---------------------------------------------------------------------------
# Output assembly (README.txt / figures/ / tables/ / raw-parsed-data/, per
# the shared output convention in Post-Processing-WebApp-Outline.md)
# ---------------------------------------------------------------------------

def _build_readme(module_title, mode, parameters, direction_results, template_path):
    lines = [f"{module_title} — Results", ""]
    lines.append(f"Detection mode: {'Auto (parsed from raw QE files)' if mode == 'auto' else 'Manual (typed values)'}")
    if template_path:
        lines.append("Custom LaTeX template: supplied and used for the pgfplots export.")
    lines.append("")

    for dr in direction_results:
        lattice = dr["material_config"]["lattice"]
        edges = dr["material_config"]["band_edges"]
        lines.append(f"Direction: {dr['label']}")
        lines.append(f"  Uploaded file(s): {', '.join(dr['uploaded_names']) or '(none)'}")
        if dr["mode"] == "auto":
            lines.append(
                f"  Auto-detected: lattice constant = {lattice['lattice_constant_angstrom']:.6f} Ang "
                f"(axis {lattice['lattice_axis_used']}), VBM band #{edges['vbm_index']}, "
                f"CBM band #{edges['cbm_index']} (nelec={edges['nelec']}, noncolin={edges['noncolin']})"
            )
        else:
            lines.append(
                f"  Manually entered: lattice constant = {lattice['lattice_constant_angstrom']:.6f} Ang, "
                f"VBM band #{edges['vbm_index']}, CBM band #{edges['cbm_index']}"
            )
        for br in dr["band_results"]:
            m_str = f"{br['m_eff']:.6f}" if br["m_eff"] is not None else "n/a"
            r_str = f"{br['r_squared']:.6f}" if br["r_squared"] is not None else "n/a"
            lines.append(f"    {br['folder']} ({br['carrier']}): m*/m0 = {m_str}, R^2 = {r_str}")
        lines.append("")

    lines.append("Parameters used:")
    for key, value in parameters.items():
        lines.append(f"  - {key}: {value}")
    lines.append("")

    lines.append("Output files:")
    lines.append("  - tables/mass-summary.csv : one row per band, per direction (m*/m0, R^2, lattice info)")
    lines.append("  - tables/mass-summary.tex : the same table as a copy-pasteable LaTeX table")
    for dr in direction_results:
        for br in dr["band_results"]:
            fmt = dr["settings"]["plot"]["figure_format"]
            if fmt in ("png", "both"):
                lines.append(f"  - figures/{dr['label']}/{br['folder']}_scipy_fitting_plot.png")
            if fmt in ("latex", "both"):
                lines.append(f"  - figures/{dr['label']}/{br['folder']}_scipy_fitting_plot.tex")
            lines.append(f"  - raw-parsed-data/{dr['label']}/{br['folder']}_plot_data.txt")
            lines.append(f"  - raw-parsed-data/{dr['label']}/{br['folder']}_scipy_fitting_results.txt")
            lines.append(f"  - raw-parsed-data/{dr['label']}/{br['folder']}_info.txt")
        lines.append(f"  - raw-parsed-data/{dr['label']}/material_config.json")
    lines.append("")
    return "\n".join(lines)


def _build_mass_table(direction_results):
    header = ["Direction", "Band", "Carrier type", "m*/m0", "R^2", "Lattice constant (Ang)", "Axis used"]
    rows = []
    for dr in direction_results:
        lattice = dr["material_config"]["lattice"]
        axis = lattice["lattice_axis_used"]
        a_lat = lattice["lattice_constant_angstrom"]
        for br in dr["band_results"]:
            rows.append(
                [
                    dr["label"],
                    br["folder"],
                    br["carrier"],
                    f"{br['m_eff']:.6f}" if br["m_eff"] is not None else "n/a",
                    f"{br['r_squared']:.6f}" if br["r_squared"] is not None else "n/a",
                    f"{a_lat:.6f}" if a_lat is not None else "n/a",
                    axis,
                ]
            )

    csv_lines = [",".join(header)]
    for row in rows:
        csv_lines.append(",".join(str(c) for c in row))
    csv_text = "\n".join(csv_lines) + "\n"

    tex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\begin{tabular}{l l l r r r l}",
        r"\hline",
        " & ".join(header) + r" \\",
        r"\hline",
    ]
    for row in rows:
        tex_lines.append(" & ".join(str(c) for c in row) + r" \\")
    tex_lines += [r"\hline", r"\end{tabular}", r"\caption{Effective masses extracted per direction/band.}", r"\end{table}"]
    tex_text = "\n".join(tex_lines) + "\n"

    return csv_text, tex_text


def _build_zip(module_title, mode, parameters, direction_results, template_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", _build_readme(module_title, mode, parameters, direction_results, template_path))

        csv_text, tex_text = _build_mass_table(direction_results)
        zf.writestr("tables/mass-summary.csv", csv_text)
        zf.writestr("tables/mass-summary.tex", tex_text)

        zf.mkdir("figures") if hasattr(zf, "mkdir") else None

        for dr in direction_results:
            slug = dr["label"]
            for br in dr["band_results"]:
                folder_path = br["folder_path"]
                if not os.path.isdir(folder_path):
                    continue
                for fname in sorted(os.listdir(folder_path)):
                    full_path = os.path.join(folder_path, fname)
                    if fname.endswith(".png") or fname.endswith(".tex") or fname.endswith(".pdf"):
                        zf.write(full_path, f"figures/{slug}/{fname}")
                    else:
                        zf.write(full_path, f"raw-parsed-data/{slug}/{fname}")

            mc_path = os.path.join(dr["direction_cwd"], "material_config.json")
            if os.path.exists(mc_path):
                zf.write(mc_path, f"raw-parsed-data/{slug}/material_config.json")
            extremum_path = os.path.join(dr["direction_cwd"], "Extracted-max-min-values-with-kpoint.txt")
            if os.path.exists(extremum_path):
                zf.write(extremum_path, f"raw-parsed-data/{slug}/Extracted-max-min-values-with-kpoint.txt")

            # LaTeX figures reference their data via a `dat/` sibling folder
            # (scripts/common/pgfplots_export.py); Final-Results-Organization.py only moves
            # each band's own named files into its per-band folder, so the shared dat/
            # directory is collected here instead, once per direction.
            dat_dir = os.path.join(dr["direction_cwd"], "dat")
            if os.path.isdir(dat_dir):
                for fname in sorted(os.listdir(dat_dir)):
                    zf.write(os.path.join(dat_dir, fname), f"figures/{slug}/dat/{fname}")

    return buf.getvalue()


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_zip(self, zip_bytes, filename):
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(zip_bytes)))
        self.end_headers()
        self.wfile.write(zip_bytes)

    def do_GET(self):
        self._send_json(405, {"error": "Use POST with a multipart/form-data upload."})

    def do_POST(self):
        scratch_dir = None
        try:
            content_length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(content_length) if content_length else b""
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_json(400, {"error": "Expected a multipart/form-data upload."})
                return

            fields, files = _parse_multipart(content_type, body)

            module_id = fields.get("moduleId", "effective-mass-extractor")
            module_title = fields.get("moduleTitle") or "Effective mass extractor"
            if module_id and module_id != "effective-mass-extractor":
                self._send_json(
                    400, {"error": f"This endpoint only handles 'effective-mass-extractor', got '{module_id}'."}
                )
                return

            try:
                parameters = json.loads(fields.get("parameters") or "{}")
            except json.JSONDecodeError:
                self._send_json(400, {"error": "The 'parameters' field is not valid JSON."})
                return

            mode = (parameters.get("detectionMode") or "auto").strip().lower()
            if mode not in ("auto", "manual"):
                self._send_json(400, {"error": f"Unknown detectionMode '{mode}'; expected 'auto' or 'manual'."})
                return

            scratch_dir = tempfile.mkdtemp(prefix="effective-mass-")

            template_path = None
            if "templateFile" in files:
                template_name, template_bytes = files["templateFile"]
                if template_name.lower().endswith(".tex"):
                    template_path = os.path.join(scratch_dir, "template.tex")
                    with open(template_path, "wb") as fh:
                        fh.write(template_bytes)

            direction_results = [_run_direction(mode, parameters, files, scratch_dir, template_path)]

            zip_bytes = _build_zip(module_title, mode, parameters, direction_results, template_path)
            filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-') or 'Effective-Mass'}-Results.zip"
            self._send_zip(zip_bytes, filename)

        except PipelineError as e:
            self._send_json(422, {"error": str(e)})
        except Exception as e:  # noqa: BLE001 - last-resort plain-language fallback
            self._send_json(500, {"error": f"Unexpected error while processing the request: {e}"})
        finally:
            # Explicit cleanup rather than relying on /tmp's own ephemeral
            # lifecycle, since a single function instance may be reused for
            # several invocations before Vercel recycles it.
            if scratch_dir and os.path.isdir(scratch_dir):
                shutil.rmtree(scratch_dir, ignore_errors=True)

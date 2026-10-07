"""Shared multipart-parsing and HTTP-response helpers for every /api/*.py Vercel Python
function in this project. Not itself a route: it defines no top-level `handler` class, so
Vercel's file-based Python convention does not turn it into an endpoint (see
api/effective-mass.py's module docstring for why the `handler` class convention is used here).

Every endpoint built on `BaseTaskHandler` gets, for free:
  - stdlib-only multipart/form-data parsing (no third-party dependency)
  - JSON and zip response helpers
  - the "reject unrecognized moduleId" and "parameters must be valid JSON" checks
  - fail-closed keyword validation for each named upload, via `validate_uploads`
    (scripts/common/file_validation.py) -- if an uploaded file doesn't contain the expected
    keyword for its role, the request is rejected before any processing runs.
"""

import json
import os
import sys
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "common"))
from file_validation import validate_file_role, FileValidationError  # noqa: E402


def safe_filename(name, fallback="upload"):
    """Strip any directory components from an uploaded file's original filename before it's
    ever joined into a scratch-dir path. The filename in a multipart Content-Disposition
    header is attacker-controlled -- a crafted `filename="../../../etc/passwd"` would
    otherwise let a malicious request write outside the per-request scratch directory.
    `os.path.basename` collapses both `../` segments and absolute paths down to just the
    final component; an empty or dot-only result falls back to a safe default name.
    """
    base = os.path.basename((name or "").replace("\\", "/"))
    return base if base and base not in (".", "..") else fallback


class PipelineError(Exception):
    """Raised for any problem we can explain in plain language to the student."""


def classify_output_folder(path):
    """Return the zip-relative path for a generated output file: a `.dat` file that lives in a
    `dat/` sibling folder (written by scripts/common/pgfplots_export.py, next to its .tex)
    keeps that `figures/dat/...` nesting so the .tex's own `dat/<name>.dat` reference still
    resolves after unzipping; tables (.csv/.txt reports) go to `tables/`; everything else
    (.png/.tex/.pdf) goes to `figures/`.
    """
    fname = os.path.basename(path)
    parent = os.path.basename(os.path.dirname(path))
    if parent == "dat":
        return f"figures/dat/{fname}"
    if fname.endswith(".csv") or fname.endswith(".txt"):
        return f"tables/{fname}"
    return f"figures/{fname}"


def parse_multipart(content_type_header, body_bytes):
    """Parse a multipart/form-data body with the stdlib `email` package.

    The frontend uploads every file under one repeated field name ("files"), so file fields
    accumulate into a list rather than overwriting each other. Returns
    (fields: dict[str, str], files: dict[str, list[(filename, bytes)]]).
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
            files.setdefault(name, []).append((filename, payload))
        else:
            try:
                fields[name] = payload.decode("utf-8")
            except UnicodeDecodeError:
                fields[name] = payload.decode("latin-1")
    return fields, files


def save_upload(files, field_name, scratch_dir, role=None):
    """Write the (first) file under files[field_name] to scratch_dir, optionally
    keyword-validating it for `role` first (see scripts/common/file_validation.py).
    Returns the saved path. Raises PipelineError if the field is missing or empty, or if
    role validation fails.
    """
    uploads = files.get(field_name) or []
    if not uploads:
        raise PipelineError(f"Missing required upload: '{field_name}'.")
    original_name, payload = uploads[0]
    dest_path = os.path.join(scratch_dir, safe_filename(original_name, field_name))
    with open(dest_path, "wb") as fh:
        fh.write(payload)
    if role:
        try:
            validate_file_role(dest_path, original_name, role)
        except FileValidationError as e:
            raise PipelineError(str(e))
    return dest_path


class BaseTaskHandler(BaseHTTPRequestHandler):
    """Subclass and set `MODULE_ID`, then implement `handle_task(fields, files, scratch_dir)`
    returning (zip_bytes, download_filename). Everything else (multipart parsing, error
    shapes, scratch-dir cleanup) is handled here.
    """

    MODULE_ID = None

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
        import shutil
        import tempfile

        scratch_dir = None
        try:
            content_length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(content_length) if content_length else b""
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_json(400, {"error": "Expected a multipart/form-data upload."})
                return

            fields, files = parse_multipart(content_type, body)

            module_id = fields.get("moduleId", self.MODULE_ID)
            if self.MODULE_ID and module_id != self.MODULE_ID:
                self._send_json(
                    400, {"error": f"This endpoint only handles '{self.MODULE_ID}', got '{module_id}'."}
                )
                return

            try:
                parameters = json.loads(fields.get("parameters") or "{}")
            except json.JSONDecodeError:
                self._send_json(400, {"error": "The 'parameters' field is not valid JSON."})
                return

            scratch_dir = tempfile.mkdtemp(prefix=f"{self.MODULE_ID or 'task'}-")
            zip_bytes, filename = self.handle_task(fields, files, parameters, scratch_dir)
            self._send_zip(zip_bytes, filename)

        except PipelineError as e:
            self._send_json(422, {"error": str(e)})
        except Exception as e:  # noqa: BLE001 - last-resort plain-language fallback
            self._send_json(500, {"error": f"Unexpected error while processing the request: {e}"})
        finally:
            if scratch_dir and os.path.isdir(scratch_dir):
                shutil.rmtree(scratch_dir, ignore_errors=True)

    def handle_task(self, fields, files, parameters, scratch_dir):
        raise NotImplementedError

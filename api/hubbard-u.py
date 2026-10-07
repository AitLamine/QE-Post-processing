"""Vercel Python Function for the "Hubbard U (linear response) reader" module.

Endpoint: POST /api/hubbard-u
Fields expected: moduleId, parameters (JSON: atomsOrbitals), files: hp (hp.x output,
any material -- see scripts/hubbard/hp_reader.py for the HUBBARD-card format this relies on),
sent under its own field name by TaskPage.jsx's per-role FileSlot (module.manualEntryFiles[0].key
== "hp"), not a shared "files" field.
Response: application/zip (tables/hubbard-values.csv), or JSON error.
"""

import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import BaseTaskHandler, PipelineError, save_upload  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "hubbard"))
from hp_reader import parse_hubbard_card, write_table  # noqa: E402


class handler(BaseTaskHandler):
    MODULE_ID = "hubbard-u-reader"

    def handle_task(self, fields, files, parameters, scratch_dir):
        hp_path = save_upload(files, "hp", scratch_dir, role="hp")

        try:
            result = parse_hubbard_card(hp_path)
        except ValueError as e:
            raise PipelineError(str(e))

        csv_path = os.path.join(scratch_dir, "hubbard-values.csv")
        write_table(csv_path, result, parameters.get("atomsOrbitals"))

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "README.txt",
                "Hubbard U (linear response) reader - results\n" + "=" * 60 +
                "\n\ntables/hubbard-values.csv - U (and V, if inter-site) values parsed from the "
                "HUBBARD card printed by hp.x.\n",
            )
            zf.write(csv_path, "tables/hubbard-values.csv")

        module_title = fields.get("moduleTitle") or "Hubbard U reader"
        filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-')}-Results.zip"
        return buf.getvalue(), filename

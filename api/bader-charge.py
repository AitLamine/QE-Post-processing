"""Vercel Python Function for the "Bader charge analyzer" module.

Endpoint: POST /api/bader-charge
Fields expected: moduleId, parameters (JSON: elementOrder, valenceElectrons, formalCharges),
files: acf (ACF.dat, any material -- see scripts/bader/bader_reader.py for the fixed column
format this relies on, and for the net-charge/ionicity/covalency formulas ported from the
user's own validated Bader-charge analysis), sent under its own field name by TaskPage.jsx's
per-role FileSlot (module.manualEntryFiles[0].key == "acf").
Response: application/zip (tables/bader-charges.csv + charge-summary-by-species.csv), or JSON error.
"""

import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import BaseTaskHandler, PipelineError, save_upload  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "bader"))
from bader_reader import parse_acf, write_table, summarize_by_species  # noqa: E402


class handler(BaseTaskHandler):
    MODULE_ID = "bader-charge-analyzer"

    def handle_task(self, fields, files, parameters, scratch_dir):
        acf_path = save_upload(files, "acf", scratch_dir, role="acf")

        try:
            rows, meta = parse_acf(acf_path)
        except ValueError as e:
            raise PipelineError(str(e))

        element_order = parameters.get("elementOrder") or ""
        valence_electrons = parameters.get("valenceElectrons") or ""
        formal_charges = parameters.get("formalCharges") or ""

        csv_path = os.path.join(scratch_dir, "bader-charges.csv")
        write_table(csv_path, rows, element_order, valence_electrons, formal_charges)

        summary_lines = ["Species,MeanBaderCharge(N),MeanNetCharge(Q),MeanIonicity(%),MeanCovalency(%)\n"]
        if element_order:
            summary = summarize_by_species(rows, element_order, valence_electrons, formal_charges)

            def fmt(v):
                return f"{v:.5f}" if v is not None else ''

            for species, stats in summary.items():
                summary_lines.append(
                    f"{species},{stats['mean_charge']:.6f},{fmt(stats['mean_net_charge'])},"
                    f"{fmt(stats['mean_ionicity'])},{fmt(stats['mean_covalency'])}\n"
                )
        summary_path = os.path.join(scratch_dir, "charge-summary-by-species.csv")
        with open(summary_path, "w") as f:
            f.writelines(summary_lines)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            readme = (
                "Bader charge analyzer - results\n" + "=" * 60 + "\n\n"
                "tables/bader-charges.csv - per-atom Bader charge N, net charge Q = Z_valence - N,\n"
                "  ionicity = |Q|/|formal charge| * 100 (%), covalency = 100 - ionicity (%),\n"
                "  min distance, atomic volume. Net charge/ionicity/covalency are blank for any\n"
                "  species missing from the valence-electrons / formal-charges inputs.\n"
                "tables/charge-summary-by-species.csv - per-species means of the above "
                "(empty unless an element order was provided).\n"
            )
            if meta.get("number_of_electrons") is not None:
                readme += f"\nNUMBER OF ELECTRONS (from ACF.dat): {meta['number_of_electrons']}\n"
            zf.writestr("README.txt", readme)
            zf.write(csv_path, "tables/bader-charges.csv")
            zf.write(summary_path, "tables/charge-summary-by-species.csv")

        module_title = fields.get("moduleTitle") or "Bader charge analyzer"
        filename = f"{re.sub(r'[^a-zA-Z0-9]+', '-', module_title).strip('-')}-Results.zip"
        return buf.getvalue(), filename

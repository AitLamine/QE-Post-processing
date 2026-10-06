#!/usr/bin/env python3
"""Detect a material/functional/approach tag from an epsr filename.

Ported from the user's own validated one-off script (All-Scripts/material_detect.py in the
ZnX-Materials-All-Results corpus), which expected a filename of the form:

    epsr_Bulk-<MATERIAL>-Wurtzite-<FUNCTIONAL>[-Plus<U|VC>].dat

and used the material/functional/approach purely to build human-readable output filenames
(TAG), not for any physics. The original raised on a non-matching filename, which is fine for
the author's own consistently-named corpus but too brittle for arbitrary student uploads on a
self-service web tool, where the epsr file could be named anything the student's own QE run
produced. This version keeps the exact regex/behavior for filenames that DO match (so output
naming stays identical to the validated pipeline), but falls back to a generic, still-unique tag
built from the filename instead of raising when the pattern doesn't match.
"""

import os
import re

FILENAME_RE = re.compile(
    r'^(?P<prop>epsr|epsi|eels)_Bulk-(?P<material>[^-]+)-Wurtzite-'
    r'(?P<functional>[A-Za-z0-9]+?)(?P<approach_suffix>-Plus(?P<approach_code>U|VC))?\.dat$'
)

APPROACH_LABELS = {None: 'DFT', 'U': 'DFT+U', 'VC': 'DFT+V'}


def _sanitize(token):
    """Keep a tag filesystem/LaTeX-friendly: letters, digits, dot, dash, underscore only."""
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', token).strip('-')
    return cleaned or 'Sample'


def detect_from_epsr_filename(epsr_filename):
    """Detect material/functional/approach from an epsr_Bulk-*.dat basename.

    Returns a dict with: material, functional, approach_label, approach_suffix, tag, and
    matched (bool, whether the strict validated-corpus filename pattern was recognized).
    Never raises: on no match, `tag` is derived from the filename stem instead.
    """
    basename = os.path.basename(epsr_filename)
    match = FILENAME_RE.match(basename)

    if match:
        material = match.group('material')
        functional = match.group('functional')
        approach_suffix = match.group('approach_suffix') or ''
        approach_label = APPROACH_LABELS[match.group('approach_code')]
        tag = f"{material}-Wurtzite-{functional}{approach_suffix}"
        return {
            'material': material,
            'functional': functional,
            'approach_label': approach_label,
            'approach_suffix': approach_suffix,
            'tag': tag,
            'matched': True,
        }

    # Fallback: derive a tag from whatever filename was actually uploaded.
    stem = os.path.splitext(basename)[0]
    stem = re.sub(r'^epsr[_-]?', '', stem, flags=re.IGNORECASE)
    tag = _sanitize(stem) or 'Sample-Material'
    return {
        'material': tag,
        'functional': 'Unknown',
        'approach_label': 'Unknown',
        'approach_suffix': '',
        'tag': tag,
        'matched': False,
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 material_detect.py <epsr_filename>")
        sys.exit(1)
    info = detect_from_epsr_filename(sys.argv[1])
    for key, value in info.items():
        print(f"{key}: {value}")

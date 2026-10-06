#!/usr/bin/env python3
"""Fail-closed keyword validation for uploaded files, shared by every module's API handler.

Rationale: a student can rename a file to anything, or upload the wrong slot by mistake (e.g.
swapping epsr and epsi, or uploading a bands.x file where an ACF.dat was expected). Rather than
silently parsing whatever bytes arrive and producing a wrong result, every upload is checked
against a keyword set for its expected role before any processing starts. If none of the
keywords for a role are found -- in either the original filename or the file's own content --
the request is rejected with a clear message instead of being processed.

This is deliberately a simple substring/keyword check, not a full format parser: it is a
tripwire against obviously-wrong uploads, not a guarantee of well-formed data. The real parser
(e.g. eps_utils.load_eps_file) still does its own validation on top of this.
"""

FILE_ROLE_KEYWORDS = {
    # QE epsilon.x output: filenames conventionally start with epsr_/epsi_, and this
    # tool's own material_detect.py (validated against the user's own epsilon.x runs)
    # relies on that same "epsr"/"epsi" substring to tell the two apart.
    'epsr': ['epsr', 'eps_r', 'eps-r'],
    'epsi': ['epsi', 'eps_i', 'eps-i'],
    # Henkelman-group `bader` code output: ACF.dat's column header is a fixed, documented
    # string across all versions of the code, independent of filename.
    'acf': ['acf', 'charge', 'min dist', 'atomic vol'],
    'avf': ['avf'],
    'bcf': ['bcf'],
    # QE hp.x (Hubbard linear-response) output always prints "Hubbard" repeatedly, including
    # in the final HUBBARD card block this reader depends on.
    'hp': ['hubbard'],
}


class FileValidationError(ValueError):
    pass


def validate_file_role(path, original_filename, role, max_header_bytes=4096):
    """Raise FileValidationError unless `role`'s keywords appear in the filename or the file's
    own leading bytes. Case-insensitive. `role` must be a key of FILE_ROLE_KEYWORDS.
    """
    keywords = FILE_ROLE_KEYWORDS.get(role)
    if not keywords:
        raise KeyError(f"Unknown file role for validation: {role}")

    name_lower = (original_filename or '').lower()
    if any(kw in name_lower for kw in keywords):
        return

    try:
        with open(path, 'r', errors='ignore') as f:
            head = f.read(max_header_bytes).lower()
    except Exception:
        head = ''

    if any(kw in head for kw in keywords):
        return

    raise FileValidationError(
        f"'{original_filename or path}' does not look like a {role} file: expected to find one "
        f"of {keywords} in its filename or content, found none. Upload was not processed."
    )

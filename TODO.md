# Backlog — not urgent, pick up later

Captured at the end of a session that: verified all 8 modules end-to-end with real
data, added the manual-entry (paste-instead-of-upload) mode, gave Tauc a dual-approach
pipeline, matched LaTeX/PDF output to the real paper figures for all 5 figure-producing
modules, and set up git locally (no GitHub push yet, no deployment yet — both deferred
pending an explicit decision).

## UX
- [ ] Wire up the "sample data" link — every module page currently shows a disabled,
      non-functional "try it with sample data" link (`components/SampleDataLink.jsx` is
      a stub). Real fixture data already exists for most modules (ZnO epsr/epsi under
      `scripts/tauc/fixtures/`, ZnSe bands under `scripts/effective-mass/fixtures/`) —
      use those rather than fabricating new sample files.

## Correctness
- [ ] Minor edge case: a very narrow/degenerate y-axis range can hit a "Dimension too
      large" TeX compile error in `pgfplots_export.py`. Low-probability with real data,
      not fixed yet.

## Consistency
- [ ] Hubbard U (`hubbard-u-reader`) doesn't have the manual-entry mode the other 7
      modules have — it was wired into the GUI this session but didn't get the
      paste-instead-of-upload treatment.

## Before any real deployment (not before — infra, not features)
- [ ] Data retention: uploaded files / result zips should auto-delete after download or
      a fixed window (per the app's own outline doc, Section 0).
- [ ] Rate limiting if the app ever goes public-facing (per-IP cap on uploads).
- [ ] Async job queue for anything that can run past ~60s — effective-mass's multi-script
      subprocess pipeline (especially 3-direction auto-detect mode) is the most likely to
      exceed a serverless function timeout; currently synchronous.
- [ ] Zip-bomb / path-traversal checks on uploads — outline calls for this explicitly;
      confirm it's actually implemented, not just documented as a requirement.

## Deferred, explicit user decision required (not a coding task)
- [ ] Push to GitHub (currently local-only, by request)
- [ ] Deploy to Vercel, preview or production (not done, by request)

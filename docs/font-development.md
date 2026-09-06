# Reference font development

Quintessential Serif 0.220 is the reference build, with an unreleased optical
revision to Roman U+F2B18. The four UFO masters
and two designspaces are editable source; routine builds use only the checked-in
STIX Two Text donors. Donor checksums are verified before compilation.

## Invariants

- All 832 Roman and 232 Italic mappings retain their explicit scalar values,
  stable identities, advances, and kerning. Roman U+F2B18 has revised counters;
  all other outlines retain their reference geometry.
- Roman and Italic remain separate variable fonts with compatible 400/700
  endpoint masters, a wght axis, and the inherited nonlinear mapping.
- Code points, stable construction IDs, internal glyph names, historical recipe
  keys, and display order are separate. Internal historical names are not
  public character names.
- The allocation stores neutral structural components. Canonical naming v2
  reads those components and never rewrites the font outlines.
- Middle-component companions follow their bases in specimen presentation.
  Numeric charts and names lists follow code order.

## Preservation fixtures

The standalone fixtures preserve the complete source/static/variable glyph
geometry needed from 0.210 and the independent 0.150 reference. They contain
font software and neutral identity records, with exact fixture inventories.

The 0.210 comparison retains all earlier outlines, advances, and effective
pairs except the previously authorized stemless-spine terminal correction and
pairs involving that identity. The subsequent U+F2B18 optical revision permits
only that Roman outline to differ, while retaining its original outer contour,
advance, sidebearings, and all pairs. Historical fixtures remain immutable.

## Project emblem

U+F2B18, **stem with spine and stem**, is the project mark. Its stable identity
is `opposed-bowls-0-0`; its internal historical font name is `uF2B1C`.
The outline review is documented in [U+F2B18 optical design](f2b18-optical-design.md).
The pilot refinement applies to this reviewed construction across Roman weights
400–700. Related constructions retain their existing recipes until separately
reviewed; the icon does not imply that the whole repertoire is optically final.

To regenerate the targeted editable masters and their downstream assets:

```sh
python tools/refine_project_glyph.py
python tools/build_quintessential_font.py
python tools/export_project_icon.py
python tools/export_font_coverage.py
node tools/export_glyph_catalogue.js
python tools/build_pdfs.py
npm run build
```

The targeted updater writes only the Regular and Bold target GLIFs. Never use
the full foundation `--force` import for this refinement. The icon exporter
reads the actual compiled Roman cmap and outline; its SVGs contain paths and
need no installed font. Use `--check` to verify the exported assets.

When proof data changes, refresh its tracked gzip copy with `mtime=0`, and
record the revised source and output hashes separately from historical evidence.
The optical revision's isolated repeat-build record is generated with
`python tools/verify_repeat_build.py --report resources/provenance/f2b18-repeat-build.json`.

The independent 0.150 checks retain exactly 129 historical forms and all 16,641
ordered pairs. Membership is encoded by stable font identity and does not
depend on current code-point ranges.

## Build and verification

Use a Python virtual environment with tools/requirements-fonts.txt. Run the
base-neutral build and test commands documented in the root README.
Detailed proof output is generated into resources/fonts/QuintessentialSerif/
and excluded from Git; it is not a website dependency.

Production web builds use the compact generated catalogue. Updating font
coverage requires regeneration from actual compiled cmap data and verification
against the immutable source allocation, not editing a UI count.

A release requires source and output hashes, the full acceptance suite,
baseline comparisons, reproducibility, and representative visual review.
Engineering completion, visual inspection, and user acceptance must be recorded
separately. The existing reference design has not acquired user acceptance merely
because it has been extracted or published.

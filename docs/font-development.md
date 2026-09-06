# Reference font development

Quintessential Serif 0.220 is the preserved reference build. The four UFO masters
and two designspaces are editable source; routine builds use only the checked-in
STIX Two Text donors. Donor checksums are verified before compilation.

## Invariants

- All 832 Roman and 232 Italic mappings retain their explicit scalar values,
  stable identities, outlines, advances, and kerning.
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
pairs involving that identity. This extraction makes no new geometry exception.

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

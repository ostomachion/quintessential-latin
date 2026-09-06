# Reference font development

Quintessential Serif 0.250 maps the existing 1,216 constructions in each native
posture into the [gapless logical allocation](logical-allocation.md). The 0.240
outlines, advances, effective kerning pairs, and internal glyph identities are
preserved by that allocation migration; public code points change without compatibility aliases.
The subsequent [stemless terminal revision](stemless-terminals.md) adds a second
bulb to the spine and both turned open bowls in all four masters, preserving
their advances, body placement, and kerning.
The four UFO masters
and two designspaces are editable source; routine builds use only the checked-in
STIX Two Text donors. Donor checksums are verified before compilation.

## Invariants

- All 1,216 Roman and Italic forms retain their construction identities, internal
  glyph names, advances, and effective kerning pairs from 0.240. Only the three
  stemless forms have the subsequent terminal changes described above.
  The current numeric map is U+F2A00–U+F2EBF; earlier code-point assignments
  are historical and must not be used to identify current glyphs.
- Roman and Italic remain separate variable fonts with compatible 400/700
  endpoint masters, a wght axis, and the inherited nonlinear mapping.
- Code points, stable construction IDs, internal glyph names, historical recipe
  keys, and display order are separate. Internal historical names are not
  public character names.
- The allocation stores neutral structural components. Canonical naming
  reads those components and never rewrites the font outlines.
- Middle-component companions immediately follow each base in its family.
  Presentation, numeric charts, and names lists share the same logical order.

The earlier [Italic completion](italic-completion.md) added the remaining 600 Italics
with `python tools/complete_italic_sources.py`. It left every existing GLIF
untouched, appended new Italic glyph IDs after the complete previous prefix, and
added only pairs involving those new forms. All four masters received release
version metadata. Allocation version 0.220 and naming version 3 remained unchanged;
only posture availability expanded.

The [independent middle extension revision](independent-middle-extensions.md)
added two asymmetric states for every form with two middle components.
The `middleLegExtensions` tuple uses final visual left-to-right order; reversed
forms must transform those positions before using their construction donors.
That increment used allocation and font version 0.240. The current map and font
version are 0.250; canonical naming remains version 3.

## Preservation fixtures

The standalone fixtures preserve the complete source/static/variable glyph
geometry needed from 0.210 and the independent 0.150 reference. They contain
font software and neutral identity records, with exact fixture inventories.

The 0.210 comparison retains all earlier outlines, advances, and effective
pairs except the previously authorized stemless-spine terminal correction and
pairs involving that identity. The later shared-spine revision extends the
U+F2B18 counter refinement to 396 explicitly identified Roman constructions.
The deeper connection audit additionally permits the localized exterior body
returns, arch-to-spine ports, and closed lower-hook joins documented in that
revision. Comparisons isolate those segments and preserve every remaining
curve and line, including unaffected endings, arch ribbons, enclosures, and
middle-foot bridges. Advances, sidebearings, and all pairs remain unchanged.
This adds no spacing exception. Historical fixtures and the original
single-emblem review remain immutable.

The newer two-bulb stemless revision changes only twelve GLIFs: the spine,
turned open bowl, and turned open double bowl in Regular, Bold, Italic, and
Bold Italic. Its frozen pre-change source evidence bridges historical checks;
the new source and compiled table hashes are pinned separately. Upright open
forms and every unrelated outline, advance, and kerning pair remain protected.
Regenerate only these sources with `python tools/refine_stemless_terminals.py`;
use `--check` to verify their reconstruction without writing files.

## Project emblem

U+F2ADC, **stem with spine and stem**, is the project mark (historically U+F2B18). Its stable identity
is `opposed-bowls-0-0`; its internal historical font name is `uF2B1C`.
The initial outline review is documented in
[U+F2B18 optical design](f2b18-optical-design.md). The
[shared-spine revision](shared-spine-optical-design.md) carries those paired
curves and reinforced joins through the complete related construction family
across Roman weights 400–700. Native endings, additional arches, and extended
middle legs reuse that body without stretching it. The emblem does not imply
that unrelated constructions are optically final.

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

The targeted updater must write only the eligible Regular and Bold GLIFs: 396
identities and 792 source files. It must preserve their advances and every
kerning pair. Never use the full foundation `--force` import for this refinement. The icon exporter
reads the actual compiled Roman cmap and outline at weight 400 for the README
icon and weight 500 for the favicon. Its SVGs contain paths and need no installed
font. The site header and introduction render the mark with the reference font
and shared font controls. Use `--check` to verify the exported assets.

When proof data changes, refresh its tracked gzip copy with `mtime=0`, and
record the revised source and output hashes separately from historical evidence.
The optical revision's isolated repeat-build record is generated with
`python tools/verify_repeat_build.py --report resources/provenance/shared-spine-repeat-build.json`.
The earlier `f2b18-*` records remain the historical single-emblem evidence.

Generate the labeled connection proofs with
`python tools/export_shared_spine_connections.py --expect-font-sha SHA256 --png`,
substituting the compiled Roman TTF's exact digest. The exporter rejects a
mismatching font before writing output. Its self-contained SVGs, optional
PNGs, and index in `docs/images/shared-spine-connections/` show 50 paired
Regular/Bold cases at 680px em, 24/48px contexts, and a five-class overview.
Every sheet displays its font hash and UTC export time; the manifest records
the image hashes and filled topology of every endpoint specimen.

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

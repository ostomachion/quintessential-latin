# Independent middle extensions

Quintessential Serif and allocation version 0.240 complete the combinations for
constructions with two middle legs or arms. Each middle component can be short
or extended independently, giving four states: neither, left only, right only,
or both. These positions describe the final visible glyph from left to right,
including reversed forms.

The left-only and right-only states add 384 constructions at
U+F2E00–U+F2F7F. The preceding corrected 0.230 build's 832 character identities,
code points, names, outlines, advances, and effective pairs are preserved. Extended-B expands to
U+F2C00–U+F2FFF; its existing unassigned gap at U+F2D80–U+F2DFF is retained.
The full repertoire now has 1,216 forms in each native posture, Roman and Italic,
across weights 400–700.

## Construction and naming

The allocation records asymmetric states with `middleLegExtensions` arrays
`[true, false]` and `[false, true]`. A leg includes its connecting upper arch;
an arm includes its connecting lower arch. The extension belongs to that middle
component alone. Canonical naming remains version 3 and spells out the resulting
visible components in order, so the asymmetric names remain distinct.

Donor construction accounts for the final left-to-right order before reversing
or turning a form. The short middle component retains its native terminal;
the selected component reuses the existing native extended terminal. The older
neither-extended and both-extended constructions retain their existing recipes
and mappings.

Regenerate the new sources, compiled fonts, and coverage in dependency order:

```sh
python tools/add_independent_middle_legs.py
python tools/build_quintessential_font.py
python tools/export_font_coverage.py
node tools/export_glyph_catalogue.js
python tools/export_independent_middle_proof.py --png
python tools/build_pdfs.py
python tools/test_pdfs.py
npm run build
npm test
npm run test:browser
```

The source updater's `--check` option reconstructs and compares the additions
without rewriting authoritative files. Run the source updater only for this
increment; it does not reconstruct the preserved earlier GLIFs.

## Publication

The website, numeric names list, and all five publication PDFs use the same
allocation and compiled-font coverage. There are six 256-position grid sheets:
one main, one Extended-A, and four Extended-B. All 1,216 assigned and 320
unallocated positions are represented in numeric order. The existing final
output filenames are retained.

## Verification status

All 192 four-state comparisons, covering every one of the 384 additions, were
visually inspected on [24 compiled-font proof sheets](images/independent-middle-legs/index.html).
The proofs show both native postures at weights 400/550/700, with 16px and 24px
text contexts. No new visible defects were identified. The
[optical review record](../resources/verification/independent-middle-extensions-optical-review.json)
binds those inspections to the exact compiled fonts and proof images.

The four-page site builds successfully. All 20 naming tests, 12 site acceptance
groups, 152 browser checks, and 9 PDF checks pass. Every one of the 70 pages in
the five publication PDFs was visually inspected, along with all 26 pages of an
Italic 700 browser print. Desktop and phone checks include the four extension
states in actual Roman 400 and Italic 700 character dialogs. No clipping,
overlap, missing glyphs, or broken wrapping was found. All five PDFs and their
manifest reproduce byte for byte; the
[publication and browser review](../resources/verification/independent-middle-extensions-publication-review.json)
records the exact file and image hashes.

All 384 additions pass source and compiled geometry checks in both postures at
400/500/550/600/700. The preceding corrected 0.230 build's 832 identities,
3,336 GLIF files, outlines, advances, effective pairs, and glyph-order prefixes
are preserved. All 1,216 glyphs per posture pass interpolation and individual
contour checks; all 14,786,560 ordered-pair samples pass the overlap test.
The 1,536 new static glyph instances pass the existing endpoint geometry test,
while exact preservation carries forward the earlier static comparisons.
Coverage, master compatibility, metrics, hinting, WOFF2 tables, and proof
metadata also pass. The [font verification record](../resources/verification/independent-middle-extensions/font-validation.json)
documents the scoped and retained test runs.

The source updater reproduces the additions byte for byte. An isolated rebuild
from 4,925 source files reproduces all 16 outputs and the complete build manifest
byte for byte; see the [repeat-build record](../resources/provenance/independent-middle-legs-repeat-build.json).
Engineering checks for this local increment are complete.
Engineering completion, agent visual inspection, external publication,
and the user's visual acceptance remain separate.

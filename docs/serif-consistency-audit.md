# Roman serif consistency and construction audit

This revision unifies the free Roman heads in 328 constructions around the
native lowercase-u design already used by their neighbors. It changes 483
heads in each of the Regular and Bold masters. All 1,216 Italics retain their
previous outlines. Character identities, assignments, advance widths and
kerning remain unchanged.

## Where F2A2B came from

Current **U+F2A2B, arm with descender**, has stable identity
`turned-arch-descender` and historical internal name `uF2A1B`. The internal
name `uF2A2B` belongs to a different character, currently U+F2A20. The current
allocation must be used when tracing a public code point.

`ARCH_RECIPES` in `tools/import_stix_foundation.py` selects the pinned STIX
Two Text **U+0265 turned h** for this character. Its neighbors U+F2A2A and
U+F2A2C use **U+0075 u**. The turned-h recipe had already replaced the donor's
incomplete lower serif with the full p descender foot, but deliberately kept
its native upper heads. That left the short heads inconsistent with the
neighboring u-based arms.

The difference is present in the standalone repository's first commit,
`becb4925ab92482ef5361896cc6db25da7e7a835`, dated 5 September 2026. That is the
earliest evidence available in this repository; it does not establish the
earlier authoring date. The raw pinned STIX donors remain immutable.

The old heads have a steeper top wedge and a small concave entrance. The
turned-h right head also changes its top from y=476 at Regular to y=482 at
Bold; both native u heads end at y=478 throughout the endpoint masters.
Turned m, U+026F, brought essentially the same alternate head into repeated
arches. These are the two redundant open-arch head sources consolidated here.

## Which glyphs use it

| Inherited source | Glyphs with visible old heads | Heads per master |
| --- | ---: | ---: |
| Turned h, U+0265 | 49 | 51 |
| Turned m, U+026F | 279 | 432 |
| Total | 328 | 483 |

The immediate turned-h cases include U+F2A2B, U+F2A2E, U+F2A37 and U+F2A43.
The pattern also occurs in arched hips, bowls, double bowls, spines, repeated
arches, and their independent middle extensions. Turned-m examples begin
with U+F2A84, arm with two stems, and U+F2A85, arm with ascender and stem.

There are 442 constructions with one of these donors in their ancestry.
In 114 of them the relevant heads are already replaced or removed. Those
constructions do not change. The inventory was established from visible
source segments in both Roman masters, then independently checked by
comparing every old and new generator result.

The [complete character inventory](open-arch-head-inventory.md) lists every
affected current assignment and name. The machine-readable
[target inventory](../resources/serif-consistency-targets.json) also records
family membership, donor identity and original head locations.

## What was simplified

`open_arch_recording` is the single rule for the Roman turned-h and turned-m
heads. Left and middle arms use the native u left head; the final stem uses
its right head. Their slightly different overhangs remain contextual, exactly
as in u. The helper copies the native quadratic curves without refitting,
stretching the shaft, or moving the body. It preserves the operation slots
used by later arch and terminal splices. Those splice references use the same
normalized construction edges.

`tools/refine_open_arch_heads.py` reconstructs only the audited 656 GLIFs and
supports `--check`. Their source metadata records the new head donor and
design. Older method text records the underlying recipe; the new explicit
head fields supersede its original head treatment. Detailed font proofs also
record the head override and native u reference separately.

The shared `tools/stix_geometry.py` now owns the identical translation/turn,
affine-operation fitting and recursive metadata-cleanup helpers previously
repeated across family modules. Old and new helper implementations produced
exactly equal outlines and metadata for all **4,864 glyph/master results**.

Font proof generation now skips GPOS/GDEF processing in its private in-memory
copies. Those proofs draw isolated glyphs and do not use pair positioning.
The optimized pass took 18.779 seconds and reproduced every existing field in
all 9,728 glyph/face proof records exactly. Only the new explicit u-head
provenance records were added. The emitted fonts retain their complete
positioning tables.

## Remaining potentially redundant construction

| Finding | Evidence | Suggested next step |
| --- | --- | --- |
| Dense zero kerning matrix | Each master stores all 1,216 squared pairs in a roughly 72 MB plist. 1,407,714 Roman pair keys and 1,456,313 Italic keys are zero in both masters. There are no kerning groups. | Store the union of nonzero endpoint pairs and verify identical effective variable kerning. This is the largest storage/build-speed opportunity found; pair records remain unchanged in this revision. |
| Duplicate short-bowl preparation | The inline pathway in `stix_arched_terminals.py` and `_terminal(..., 'bowl', turned)` in `stix_extensions.py` give identical outlines in all 48 tested combinations. | Share one prepared-bowl operation. |
| Duplicate opposed-side trimming | `_left_terminal` / `_right_terminal` in `stix_arched_opposed_bowls.py` match `opposed_terminal(..., extended=False)` followed by `fair_spine_arch_port` in all 24 Roman comparisons. | Route both through the same prepared receiving port. |
| Inconsistent tuple order | `_terminal` returns `(outline, center, metadata)`; `italic_terminal` and `prepared_terminal` return `(outline, metadata, center)`. | Use a small named result when consolidating terminal preparation. |
| More affine wrappers | `_fit` repeats the same general mapping in the normal-spine and stemless modules; some translation wrappers remain local. | Consolidate when their parameter contracts can be made explicit without changing callers' geometry. |
| Revision bookkeeping repeats infrastructure | Stemless, hip-tail, Italic-shaft and this revision each retain separate before/after verification. | A common revision-evidence utility could reduce repeated plumbing while retaining independently frozen fixtures and strict scope checks. |

The terminal-preparation and tuple-order findings are concrete opportunities
for a later interface refactor. They were left as reported candidates because they involve a broader
interface change than the exact helper consolidation performed here. None of
these findings by itself demonstrates a malformed join.

Each authoritative UFO has 1,218 glyphs including space and .notdef. The audit
found **zero UFO component references**, **zero exact duplicate whole-outline
records**, and **zero exact repeated contour records within a glyph**. Shared
construction currently happens in Python and is flattened into the UFOs.
These exact-identity checks do not rule out geometrically equivalent curves
with different point order or representation. A conservative reference scan
also found no unreferenced top-level definitions in the `stix*.py` modules.

## Differences retained intentionally

Roman and Italic use distinct native designs. Italic u/turned-h heads already
agree, so they do not need this correction. Straight-shaft connectors, curved
bowl-quarter receivers, short and extended terminals, port insets, and the
reviewed shared-spine joins solve different geometric constraints.

The standalone dotless-i head remains distinct. Native n/m top wedges differ
by about two units; p/r/i/j also have different entry curves, shaft widths and
bearings. The l/h/b/d/thorn ascender heads share a y=706 top with approximately
one-unit entrance differences. These smaller contextual differences are
reasonable candidates for a separate close optical comparison, but this audit
does not justify replacing every head with one universal shape.

## Verification and review

The durable evidence is under
[`resources/verification/serif-consistency`](../resources/verification/serif-consistency/).
It separates generator equivalence, source preservation, compiled geometry,
pair spacing and rendered review. Historical baselines are not rewritten.

- All 4,864 generator results were compared: exactly 328 change in each Roman
  master, with 888 Roman and all 1,216 Italic results unchanged per master.
- All 656 revised source glyphs have exactly zero filled-outline difference
  outside the localized head regions. Their other metadata is preserved.
- All 966 source heads, 966 static CFF heads and 2,415 variable head fragments
  pass independent native-u shape checks. Left/right donor roles stay correct
  through all five sampled weights; compiled deviations remain within integer
  coordinate rounding.
- Source reconstruction with `--check` writes zero files. The sealed revision
  verifies all 4,872 source glyphs and all twelve font files against their
  prior data. Only the relevant outline tables and hmtx change: 38 left
  sidebearings move inward by one unit at Regular and seven at Bold. All
  advances, kerning, other glyph metrics and all Italic font tables stay fixed.
- All **3,450,560** ordered pairs involving a revised Roman glyph pass at
  weights 400, 500, 550, 600 and 700. Ambiguous projection checks use actual
  filled intersections: 96,049 such checks found zero collisions.
- Eight broader font geometry checks pass: master compatibility, sampled
  interpolation, simple contours and winding, repeated arch curves, arch
  bodies, constructed terminals, extended arch endings and direct native
  mappings. Desktop hinting and webfont equivalence checks also pass. These
  focused checks complement the revision-specific preservation tests.
- [Before/after proofs](images/open-arch-heads/index.html) show all 328 forms
  in Regular and Bold, plus neighboring base forms at five weights. They use
  compiled outlines and include 24px samples. Their manifest pins the exact
  before and after font hashes.
- The regenerated PDFs pass all nine publication tests. All 76 pages were
  rendered and reviewed on contact sheets, with nine dense or affected
  pages inspected at full size. No visible layout or glyph-rendering defects
  were found. Per-document review records pin the PDF and image hashes.
- The site build, site acceptance tests and all 231 browser checks pass,
  including font loading and responsive charts. The Unifont dependency refresh
  changes reference/proof hashes only; all 1,216 bitmap records retain their
  pixels and other metadata.

Automated preservation and agent visual inspection are evidence for this
revision, not a claim of final author approval for the entire repertoire.

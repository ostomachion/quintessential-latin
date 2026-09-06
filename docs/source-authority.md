# Source authority and publication maintenance

This map identifies the editable sources and the generated publications. Use
the allocation and implementation checks to resolve technical facts; use the
project's authorial explanation for its motivation. A font, a chart, and a
short introductory specimen each show only one aspect of the system.

## Authorities

| Subject | Editable authority | Derived material and checks |
| --- | --- | --- |
| Current inventory, component arrays, stable IDs, active codes, families and public order | [`resources/quintessential-latin-allocation.json`](../resources/quintessential-latin-allocation.json) | `tools/test_logical_allocation.js` checks uniqueness, contiguous assignment, family order, extension adjacency and preservation against the previous allocation. |
| Canonical construction names | [`tools/canonical_glyph_names.js`](../tools/canonical_glyph_names.js), especially `nameParts(parts)` | [Naming specification v3](quintessential-latin-canonical-naming-spec-v3.md) explains the rules; `tools/test_canonical_glyph_names.js` tests the primitive vocabulary, actual adjacent bowl closure, interior uprights and formatting independently of rendered examples. |
| Underlying structural distinctions | Ordered `parts` and extension/closure fields in the allocation, interpreted by the naming specification and construction implementation | The construction reference explains the current rules. These records do not encode a handwriting start point or pen trajectory. |
| Serif outlines, metrics and interpolation | Four UFO masters and two designspaces in [`fonts/QuintessentialSerif/`](../fonts/QuintessentialSerif/) | `tools/build_quintessential_font.py` compiles them. The build manifest binds source files and outputs. Donors are pinned under `resources/fonts/STIXTwoText/`. |
| Actual Serif character availability | Compiled font cmaps, checked by [`tools/export_font_coverage.py`](../tools/export_font_coverage.py) | `resources/font-coverage.json` binds variable TTF hashes and sampled metric envelopes; the catalogue exporter checks those hashes before publishing posture availability. |
| Bitmap drawings | Source JSON drawings under [`resources/unifont/`](../resources/unifont/), listed in its [README](../resources/unifont/README.md) | `tools/build_unifont_glyphs.mjs` creates HEX and `glyphs.json`; `tools/test_unifont.mjs` checks pixels, native donors, extension states and provenance. |
| Installable Unifont implementation | Generated project HEX, pinned native companion HEX, `tools/build_unifont_font.py` | `resources/fonts/QuintessentialUnifont/manifest.json` binds sources and outputs; `tools/verify_unifont_font.mjs` rejects stale downloads. |
| Proposal wording and citations | [`docs/proposal.json`](proposal.json) | Both HTML and the standalone proposal PDF consume this source. Example IDs resolve through the catalogue; they are not a second inventory. |
| Public explanatory pages and controls | [`tools/build_site.mjs`](../tools/build_site.mjs), its editorial renderer modules, and [`site/assets/`](../site/assets/) | `dist/` is generated. Edit the source rather than a deployed HTML copy. |
| Chart dimensions and typography | [`resources/chart-presentation.json`](../resources/chart-presentation.json) | Both the website and `tools/build_pdfs.py` consume these settings. |
| UCD-style property interpretation | [`tools/export_ucd.js`](../tools/export_ucd.js) and [format research](ucd-research.md) | `resources/ucd/` is a generated, opt-in private-use supplement. It does not change the Unicode Character Database or application defaults. |
| Licenses and attribution | [`LICENSE`](../LICENSE), [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), and each font's bundled OFL/provenance notices | Preserve code/document/data licensing separately from font licensing and third-party publication rights. |

## Identity and version boundaries

The current allocation declares version **0.250**, naming version **3**, **1,216
entries** and **30 families**. All three proposed ranges are fully assigned:
U+F2A00–U+F2ABF (192), U+F2AC0–U+F2BBF (256), and U+F2BC0–U+F2EBF (768).
These are the project's proposed divisions of private-use space.

Keep the following fields separate:

- `glyphId` is the stable construction identity used to join source records.
- `codePoint` is the active assignment for this allocation version.
- `canonicalName` is the readable structural name. `name` adds the proposed
  `QUINTESSENTIAL LATIN SMALL LETTER` prefix in capital letters.
- `glyphName` is the internal font name. Its spelling can retain an older code
  and must not be parsed as the current assignment.
- `oldCodePoint`, `recipeCodePoint`, `legacyName` and `legacyIndex` record
  earlier implementation history; they are not active aliases.
- `familyId`, family titles and `displayOrder` organize presentation. A family
  title is not a canonical character name or a linguistic category.

For example, BOWL has stable ID `special-ring`, current code U+F2A00 and
internal font name `uF2B00`. Public labels must use BOWL; renaming the historical
ID or reading the internal font name as a code would break separate contracts.

Both Serif postures cover all current entries. The Serif manifest's 1,217
encoded characters include ordinary U+0020 SPACE in addition to the repertoire.
The Unifont manifest distinguishes 1,216 project characters from 214 native
companions, for 1,430 encoded characters. The native companions are not new
Quintessential Latin entries. Font `.notdef` glyphs likewise do not increase
the encoded inventory. The editorial tests compare these counts across the
current manifests and publication sources.

Version 0.250 replaced earlier numeric assignments without compatibility
aliases; see the dated [logical allocation history](logical-allocation.md).
Preserve that history even when the introduction changes. A later font-design
revision need not change character identities or assignments. A repertoire or
allocation revision requires an explicit decision and synchronized data,
fonts and publications. This editorial update makes no such revision.

## What the checks establish

The allocation and naming tests check the implemented inventory against its
component rules. Font coverage checks establish that the current entries have
compiled mappings in the claimed postures. Neither check proves that every
theoretically possible combination has been enumerated, that every distinction
will be accepted for registration, or that a human has approved every design.

The single-stroke design principle means that an underlying form can be
written with one continuous pen movement without lifting the pen. Ordered
component arrays and canonical name order describe construction from left to
right; they are not handwriting instructions. Filled font outlines contain
stylistic details and are not pen paths. Instructional paths are illustrative;
there is no complete normative start-point, direction, retracing or stroke-order
standard in the allocation. Do not infer those stronger rules from one diagram.

Source-bound automated results, rendered-output inspection, author aesthetic
acceptance, external publication and registry acceptance are separate events.
Historical verification reports remain dated evidence for their recorded
revision. Run and report the checks relevant to a new change instead of
silently treating an older report as a new test run.

## Build dependencies and routine editorial changes

The publication flow is:

```text
allocation + canonical naming + compiled font coverage
  -> resources/catalogue.json + glyph-catalogue.js + flat names exports
allocation + proposal + UCD exporter
  -> resources/ucd/* + UCD manifest
catalogue + proposal + chart presentation + compiled fonts + PDF builder
  -> five output/pdf/*.pdf files + PDF build manifest
catalogue + proposal + editorial renderers + site assets + verified downloads
  -> dist/ (six reference pages, static proofs, fonts, data and PDFs)
```

For a prose-only update, edit the appropriate renderer or `docs/proposal.json`.
When the proposal changes, regenerate UCD provenance and PDFs before the site
build, because their manifests bind the proposal source bytes. With the
documented PDF dependencies installed, run:

```sh
node tools/export_glyph_catalogue.js --check
node tools/export_ucd.js
python tools/build_pdfs.py
python tools/test_pdfs.py
npm run build
npm test
npm run test:browser
```

An HTML/CSS-only change does not require a font or PDF rebuild unless it changes
one of that artifact's declared inputs. `npm run build` checks catalogue/UCD
freshness, regenerates bitmap publication data from its sources, verifies PDF
and installable Unifont manifests, then builds the static site. It does not
compile the Serif masters. Font builds and exhaustive geometry/pair tests are
appropriate for font changes, not required evidence for editorial changes.

Inspect actual generated pages at desktop and narrow widths, keyboard focus,
character dialogs, copy results, permanent links and font failure/recovery.
For PDF changes, use `tools/render_pdf_review.py` and review the fresh rendered
pages for clipping, missing glyphs, tables and pagination. A hash check alone
does not establish good typography. `tools/test_editorial.mjs` adds publication
drift checks; it cannot judge the conceptual quality of the explanation.

`dist/` and generated downloads should never become an independently edited
inventory. Commit source and affected durable generated artifacts together.
The Pages workflow can publish a push to `main`; a local build or inspection
does not itself request a release, registry submission or external contact.

# Verification record

Current reference font **0.220**, canonical naming **3**.

## Unicode chart presentation

The 6 September 2026 presentation revision brings the code-chart PDFs and
responsive charts close to the supplied Unicode references. Letter pages use
compact covers, four 16-by-16 grid sheets, external hexadecimal coordinates,
black rules and diagonal vacancy hatching, thin continuation edges, and dense
two-column names with family headings. Source Sans 3 supplies chart typography;
Quintessential Serif retains its native glyph proportions.

All **nine PDF tests**, **seventeen naming tests**, **twelve static-site acceptance
groups**, and **147 browser checks** pass. The three block PDFs contain **6, 7,
and 10 pages**; the combined catalogue contains **23**; the proposal contains
**4**. All **50 publication pages** were visually inspected from fresh Poppler
renders. An independent review covered all 23 combined pages, with native-size
inspection of the widest grids and dense names. All five PDFs and their manifest
reproduce byte for byte in a second build.

The webpage shows 16, 8, or 4 columns according to its available width. Checks at
320, 375, 768, and 1440 pixels cover every assigned and vacant position, both
postures, weights 400/550/700, names flow, pending and failed-font markers,
no-JavaScript content, copying, keyboard access, and focus restoration across
responsive and dialog changes. Desktop and mobile screenshots and all **18
pages** of an Italic 700 browser print were visually reviewed. No clipping,
overlap, or pagination defects were found.

Catalogue data, canonical names, proposal text, and the reference font files
retain their pre-revision hashes. The rebuilt proposal has different compressed
stream bytes in the current Python runtime, but its decoded page content and
fonts are unchanged and all four pages are pixel-identical at 120 dpi.

Evidence: [current chart review and hashes](../resources/verification/unicode-chart-review.json),
[PDF test log](../resources/verification/unicode-chart-pdf-tests.log), and
[publication manifest](../output/pdf/build-manifest.json). This revision is a
local build; deployment and user visual acceptance remain separate. The records
below describe earlier revisions and retain their historical counts and hashes.

## Historical naming revision

The 6 September 2026 naming revision gives all 832 characters the
`QUINTESSENTIAL LATIN LETTER` prefix and simplifies 696 construction labels.
All seventeen naming tests and the generated-export check pass. The allocation
is unchanged apart from names and naming version: code points, stable identities,
component geometry, display order, and posture coverage are preserved.

The site now has four pages after removing Specimens. Both project marks use
the shared font controls and existing native-posture availability; U+F2B18's
Italic form remains pending. The favicon is a fixed Roman weight-500 outline.
The build, twelve static-site acceptance groups, and 73 browser checks pass,
including logo weight changes and stable controls at 375, 768, and 1440 pixels.

All five PDFs were regenerated for naming version 3 and all six PDF tests pass.
The block PDFs contain 7, 9, and 14 pages; the combined catalogue contains 30;
the proposal contains 4. All 64 pages were visually reviewed from fresh Poppler
renders, with full-size inspection of representative dense names and final
pages. No clipping, overlap, missing glyphs, or broken name wrapping was observed.
Their current source and output hashes are in
[the publication manifest](../output/pdf/build-manifest.json).

## Shared-spine optical revision

The current family refinement applies the reviewed U+F2B18 body to all 396
related Roman constructions: 216 base forms and 180 extended-middle-leg
companions. Revision 2 also corrects localized exterior body returns,
arch-to-spine ports, and closed lower-hook joins. All remaining segments,
advances, and spacing are preserved. See [shared-spine optical design](shared-spine-optical-design.md)
for eligibility, preservation boundaries, and the final family evidence.

The initial emblem's `f2b18-*` results remain historical and do not validate the
expanded family by themselves. Final family geometry passes for all 396 forms
at seven weights, with localized connection exceptions isolated from the
remaining preserved segments. All 792 Regular
and Bold specimens have been reviewed across 11 proof sheets.
The [connection review](../resources/verification/shared-spine-connection-review.json)
also covers 50 labeled cases at 680px em in both masters, with 24px and 48px
contexts. It includes every enclosure count from two through five and the
corrected body returns, arch valleys, and closed lower-tail connections.
The [final font-test record](../resources/verification/shared-spine-font-tests.json)
binds the relevant compiled tests and complementary reports to the final font.

All five PDFs were rebuilt from the final family font and pass six acceptance
tests. All 32 affected pages were rendered; the 16 affected block pages and
four representative combined pages were inspected directly. Every affected
combined page body matches its reviewed block page pixel for pixel. The final
four-page site also passes 17 naming tests, 12 site acceptance groups, and 73
browser checks. Desktop/mobile marks and small-size SVG, favicon, and native
text renders were reviewed. These results are bound to the final assets in
[family PDF review](../resources/verification/shared-spine-pdf-review.json) and
[family browser review](../resources/verification/shared-spine-browser-review.json).

## Historical extraction and publication

Reference font **0.220**, canonical naming **2**, reviewed **6 September 2026**.
The first subsequent optical revision introduced the Roman U+F2B18 project
icon. Its checks and visual review are recorded in
[U+F2B18 optical design](f2b18-optical-design.md). The later shared-spine family
revision is documented separately above. The sections below describe the
original extraction and publication;
their dated hashes are historical evidence, not hashes of the revised artifacts.

## Extraction and font preservation

- All 832 stable identities, canonical names, numeric assignments and presentation
  identities match the extraction inventory.
- All 2,162 original editable font-source files, twelve compiled font binaries
  and immutable STIX donors retain their exact hashes.
- Neutral structural parts replace language construction models. Font builds
  and tests use only files in this repository.
- Portable 0.210 and 0.150 fixtures retain source, static and variable geometry,
  spacing, and the independent 129-form baseline with all 16,641 ordered pairs.
- All **42 primary font test methods** and **16 focused preservation methods**
  passed. The primary kerning check covered **3,730,240 ordered-pair samples**
  across five weights and both available postures.
- The first sequential primary invocation was intentionally interrupted after
  four completed methods; the interrupted method and all remaining methods were
  subsequently completed in bounded independent groups. The report enumerates
  all 42 unique completed methods; the interrupted attempt is not counted.
- An isolated build reproduced all **sixteen manifested outputs** and the build
  manifest byte for byte, without access to any conlang data dependency.

Evidence: [extraction hashes](../resources/provenance/extraction-preservation.json),
[fixture origins](../resources/provenance/fixture-origin-verification.json),
[complete font results](../resources/provenance/font-validation.json),
[raw validation logs](../resources/provenance/font-validation-logs.zip), and
[isolated repeat build](../resources/provenance/repeat-build.json).

A final reread of the source workspace confirmed all 2,182 captured build inputs,
six donor files, sixteen outputs and the original build manifest are unchanged.
This is a comparison of the captured font/build inventory; no complete
workspace-wide hash inventory was available.

## Website

The sixteen canonical-naming tests and eleven static-site acceptance groups pass.
The browser suite passed **76 checks**, including native font loading, shared
controls, default Roman posture, weight changes and persistence, all 600 pending
Italic forms, numeric names, code/name search, deep links, real keyboard access,
copying supplementary-plane characters and codes, native sequence shaping,
print annotations, no-JavaScript charts and explicit font-loading failures.

All five pages fit 375-, 768- and 1440-pixel viewports. The reference chart retains
hexadecimal coordinates in a contained scrolling table, and names lists collapse
to a single column. Screenshots were inspected for typography, navigation,
spacing and clipped content. The editor preserves native kerning and whitespace;
its Roman input field provides complete coverage and its preview follows the
selected posture.

Evidence: [browser checks and render hashes](../resources/verification/browser-review.json)
and [long-form review](../resources/verification/long-form-review.json). All eighteen
combinations of Roman/Italic, weights 400/550/700 and widths 375/768/1440 were
checked; all 36 names-list and specimen screenshots were visually inspected.
No clipping, overlapping text or document overflow was observed.
Screenshots are regenerable with `npm run test:browser`; they are development
output, not deployed assets.

## PDF publications

All six PDF acceptance tests pass. The three block documents contain **7, 9 and
16 pages**; the combined catalogue contains **32 pages**; the separate proposal
contains **4 pages**. All **68 pages** were rendered and visually reviewed,
including the eight 128-position grid sheets, dense two-column names lists,
headers, page numbers, long constructions and references.

Every assigned scalar appears in its grid and names list, all uppercase names
are complete and numerically ordered, all fonts are embedded, and chart text
remains vector text. The supplementary-plane ToUnicode mappings use correct
UTF-16 surrogate pairs. All five PDFs reproduced byte for byte on a second build.

Evidence: [page-by-page review and file hashes](../resources/verification/pdf-review.json),
[automated PDF results](../resources/verification/pdf-tests.log), and
[reproduction instructions](pdf-development.md).

## Registry and publication

The [UCSUR registry](https://www.kreativekorp.com/ucsur/) was rechecked at
**2026-09-06 02:03:47 UTC**. Its four rows covering U+F2A00–U+F2DFF were
listed as unassigned. This is a dated availability check, not a reservation or
registry acceptance. The proposal is a draft and has not been submitted.

A clean Git clone of the committed repository independently passed the website
build, all sixteen naming tests, eleven site groups, 76 browser checks, proof
restoration, exact font preservation and exporter consistency. Every generated
site asset matches the working repository byte for byte. See the
[clean-checkout record](../resources/verification/clean-checkout.json).

The public repository is [ostomachion/quintessential-latin](https://github.com/ostomachion/quintessential-latin),
with GitHub Issues enabled for contact. The
[first Pages workflow](https://github.com/ostomachion/quintessential-latin/actions/runs/34006176899)
completed successfully at **2026-09-06 02:20:25 UTC**, including the build,
all naming/site checks, 76 browser checks on Linux, and deployment of only
static website assets.

The [live site](https://ostomachion.github.io/quintessential-latin/) passed all
76 browser checks. All **38 public assets**, including five HTML pages and five
PDF downloads, returned successfully and matched the validated local build byte
for byte. The non-public .nojekyll hosting marker is excluded from the HTTP asset
inventory. See [live asset hashes](../resources/verification/live-assets.json)
and [live browser checks](../resources/verification/live-browser.json).
Publication does not imply user visual acceptance.

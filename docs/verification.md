# Verification record

Reference font **0.220**, canonical naming **2**, reviewed **6 September 2026**.
The current working tree includes a subsequent, unpublished Roman U+F2B18
optical revision and project icon. Its checks and visual review are recorded in
[U+F2B18 optical design](f2b18-optical-design.md). User visual acceptance remains
pending. The sections below describe the original extraction and publication;
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

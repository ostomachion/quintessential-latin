# Shared-spine optical design

The paired spine and reinforced joins established for U+F2B18 are shared by
396 Roman constructions. This revision carries the same optical treatment
through their ending combinations, attached arches, and extended middle legs
at weights 400–700. U+F2B18 remains the project emblem and the compact reference
for this construction system.

The [initial emblem review](f2b18-optical-design.md) records the STIX references,
stroke decisions, and earlier measurements. Its single-character scope and
verification records remain historical; they do not establish family coverage.

The current revision is `shared-spine-2`, retaining the `compact-spine-3` body
and adding the localized `shared-spine-joins-1` connection treatment.

## Construction coverage

Each base group contains the complete six-by-six product of left and right
ending choices. Arch-bearing groups also have their complete set of companions
with extended middle legs.

| Construction group | Base forms | Middle-leg companions | Total |
| --- | ---: | ---: | ---: |
| Two stems with a shared spine | 36 · [proof](images/shared-spines/01-opposed-bowls.svg) | 0 | 36 |
| Left arch with a shared spine | 36 · [proof](images/shared-spines/02-left-arched-opposed-bowls.svg) | 36 · [proof](images/shared-spines/03-left-arched-opposed-bowls-extended-middle-legs.svg) | 72 |
| Right arch with a shared spine | 36 · [proof](images/shared-spines/04-right-arched-opposed-bowls.svg) | 36 · [proof](images/shared-spines/05-right-arched-opposed-bowls-extended-middle-legs.svg) | 72 |
| Two left arches with a shared spine | 36 · [proof](images/shared-spines/06-left-double-arched-opposed-bowls.svg) | 36 · [proof](images/shared-spines/07-left-double-arched-opposed-bowls-extended-middle-legs.svg) | 72 |
| Two right arches with a shared spine | 36 · [proof](images/shared-spines/08-right-double-arched-opposed-bowls.svg) | 36 · [proof](images/shared-spines/09-right-double-arched-opposed-bowls-extended-middle-legs.svg) | 72 |
| Arches on both sides of a shared spine | 36 · [proof](images/shared-spines/10-double-arched-opposed-bowls.svg) | 36 · [proof](images/shared-spines/11-double-arched-opposed-bowls-extended-middle-legs.svg) | 72 |
| **Complete family** | **216** | **180** | **396** |

Each linked proof sheet contains all 36 forms at Regular and Bold. The
[proof manifest](images/shared-spines/manifest.json) binds the sheets to the
compiled font and enumerates every displayed code point.

Eligibility follows immutable recipe identities: `F2B1C–F2B3F`,
`F2B58–F2B9F`, and `F2C54–F2CBF`, including every allocated middle-leg companion
of those recipes. These historical recipe keys are distinct from current
public code points and character names. The eligible identities occupy current
assignments U+F2B18–U+F2B3B, U+F2B6C–U+F2BFB, and U+F2CA8–U+F2D7F.

All 396 forms are Roman. The one-counter bowled-spine families and the stemless
special spine use separate constructions and are outside this revision.

## Shared optical treatment

The two facing counter edges are designed together. Their normal separation
gives the spine moderate, gently varying weight while retaining flowing
curvature. Reinforced counter returns support the upper-left shoulder and the
opposing lower connection. Counter extrema, curved bowl returns, and native
shaft proportions retain the Quintessential Latin design language established
from the pinned STIX Two Text donors.

The same paired body belongs in every ending and arch combination. Adding an
ascender, descender, hook, arch, or middle leg must preserve its proportions.
The body may translate to meet an attached arch; it must not stretch, reflect,
or acquire independently fitted counter edges. Compatible Regular and Bold
curves retain economical quadratic segments throughout interpolation.

## Connections at close range

The close-up audit identified three distinct defects: pinched exterior body
returns beside extended uprights in Bold, flat shelves where arches joined
the spine, and an abrupt narrowing at closed lower-hook joins. The revised
returns flow into their receiving shafts, curved arch ports remove the
shelves, and closed lower hooks retain a supported transition into the
adjoining upright. The paired spine itself retains its reviewed weight and
curvature.

The [connection overview](images/shared-spine-connections/overview.svg) shows
five representative classes at 220px em. The
[complete connection index](images/shared-spine-connections/index.html)
contains 50 paired Regular/Bold sheets: 15 body/ending cases, 25 arch cases,
and 10 middle-leg/closure cases. Each sheet labels the joins being inspected,
uses a fixed 680px em, and adds 24px and 48px contexts. The inventory covers
single, repeated, and bilateral arches; every native arch ending; extended
receiving shafts; one- and two-bridge constructions; and closed tails beside
both ordinary uprights and middle legs. The final U+F2CDF case combines two
foot bridges and a terminal enclosure, covering the five-space interaction.

Every sheet is a self-contained compiled outline, with a visible font SHA-256
and UTC export time. The [connection manifest](images/shared-spine-connections/manifest.json)
binds all SVG/PNG images and records connected bodies and enclosed spaces for
each endpoint specimen. These close-ups supplement the full 396-form sheets.

## Preservation boundaries

The eligible source set contains 792 GLIFs: Regular and Bold for each identity.
The source comparison identifies 395 newly revised forms plus the unchanged,
already-refined emblem. The authorized changes are the two body counters and
the reviewed exterior body-return, arch-port, and lower-hook closure segments.
Every remaining curve and line is preserved, including unaffected native
endings, terminal enclosures, arch ribbons, and middle-foot bridges. Advances,
sidebearings, code points, posture coverage, and all spacing pairs retain their
existing values.

The independent 0.210 baseline contains 216 of the eligible identities; the
other 180 are the later middle-leg companions. Historical fixtures are not
rewritten. Unrelated Roman outlines and every native Italic outline retain
their prior geometry. The earlier stemless-spine spacing exception remains
separate and is not expanded by this revision.

Source and compiled comparisons must isolate each permitted connection segment
and preserve every untouched segment and independent contour. A counter
topology change can alter sparse
variable-font delta packing for the whole glyph, so preserving only the first
exterior contour is insufficient where other unchanged contours are present.

## Downstream assets and verification

Roman font binaries, coverage data, proof data, and the publication manifest
are regenerated from the revised masters. The family affects the Extended-A,
Extended-B, and combined catalogue PDFs. The project SVG and weight-500 favicon
are exported from the compiled U+F2B18 outline. Both website marks retain the
shared font controls and native-posture availability.

Family verification must cover source compatibility, counter topology, shared
body reuse under rigid translation, preserved native regions, advances and
effective pairs, and compiled interpolation. Optical profiles are checked
across the weight axis, followed by representative ending, arch, and middle-leg
proofs at display and text sizes.

The family evidence is recorded separately from the earlier `f2b18-*` files:

- [Source and output provenance](../resources/provenance/shared-spine-optical-revision.json)
- [Isolated repeat build](../resources/provenance/shared-spine-repeat-build.json)
- [Final compiled-font test runs](../resources/verification/shared-spine-font-tests.json)
- [Preservation checks](../resources/verification/shared-spine-preservation.json)
- [Geometry across the weight axis](../resources/verification/shared-spine-geometry.json)
- [Dense arch-port profiles and STIX guard](../resources/verification/shared-spine-arch-ports.json)
- [Labeled close-up connection review](../resources/verification/shared-spine-connection-review.json)
- [Current emblem endpoints and interpolation](../resources/verification/shared-spine-emblem-geometry.json)
- [Complete family proof review](../resources/verification/shared-spine-sheet-review.json)
- [Publication PDF review](../resources/verification/shared-spine-pdf-review.json)
- [Website and project-mark review](../resources/verification/shared-spine-browser-review.json)

The family geometry suite, `tools/test_shared_spines.py`, checks all 396 forms
for shared-counter congruence, topology, enclosure counts, remaining native
segments, and metrics across seven weights. Family proof sheets cover both
Regular and Bold in `docs/images/shared-spines/`. All 11 sheets have been
visually reviewed, covering 396 forms at both masters: 792 displayed specimens.

Compiled counter congruence differs by at most 2.28 × 10⁻¹³ font units. The
localized connection exceptions are checked separately; every remaining
segment is preserved. The shared spine's measured normal width
ranges from 62.59 to 69.30 units in Regular and 92.39 to 100.59 in Bold. Every
family member retains its enclosure count and supported shoulder joins.

The updater is byte-idempotent. Four packaging tests, two existing compiled-family
tests, four additions-preservation tests, three full-family tests, three
connection-regression tests, and four emblem tests pass on the final font.
An isolated repeat build
reproduces all 16 font and proof outputs and the build manifest byte for byte.

All five publication PDFs were rebuilt from the final Roman font, and all six
PDF acceptance tests pass. Fresh Poppler renders cover all 32 affected pages.
The 16 affected Extended-A and Extended-B pages and four representative combined
pages were inspected directly; every affected combined page body also matches
its corresponding block page pixel for pixel. No clipping, label collisions,
broken name wrapping, or illegible counters were found.

The final four-page site build, 17 naming tests, 12 site acceptance groups,
and 73 browser checks pass. The live emblem was inspected on desktop and
mobile; the SVG mark, weight-500 favicon, and native Roman text were also
reviewed at 16, 24, 32, and 64 CSS pixels at two pixel densities.

Engineering checks, agent visual inspection, user aesthetic acceptance, and
publication are separate outcomes.

# Quintessential Latin Unifont drawings

All **1,216 drawings at 8 × 16 pixels**, across the current 30 families:
136 forms without middle components, 156 short/extended pairs (312 glyphs),
and 192 independent-extension quartets (768 glyphs). The previously approved
148 bitmaps are preserved exactly. These are project drawings, not part
of an official GNU Unifont release. Copyright (c) 2026 Josh Hufford; native donor
attribution and OFL 1.1 are in `OFL.txt`.

The user reviewed the foundation and authorized expansion with corrections:
native simple terminals, smoother spine curves and double-bowl joins, and the
narrow spine crossover one row higher. Agent inspection and final aesthetic
acceptance remain separate. The Unifont commands do not build installable fonts,
Italic, additional weights, outline masters or PDFs.

## Editable sources and commands

- `design.json`: metrics, drawing rules, authorized batch scope and width policy.
- `primitives.json`: all 16 primitives, seven stemless and nine upright.
- `pairs.json`: 11 shoulder/hip, bowl, arch, double-bowl and spine constructions.
- `stress.json`: three quartets at U+F2C20–F2C23, U+F2CA8–F2CAB and
  U+F2EBC–F2EBF, with explicit contact and extension pixels.
- `unextended-branches.json`: 54 added shoulder, bowl and arch forms.
- `unextended-spines.json`: 55 added double-bowl and spine forms.
- `middle-branches.json`: 496 added shoulder, bowl, arch, double-bowl and
  one-sided-spine forms; explicit compact templates and attachment masks.
- `middle-shared-spines.json`: 284 added shared-spine forms with one arch
  on either side or one on each side.
- `double-middle-shared-spines.json`: 288 added shared-spine forms with
  two arches on one side.
- `approved-baseline.hex`: the pinned 148-character preservation baseline.
- `donors.hex` and `donors.json`: 40 unmodified native donor bitmaps, names,
  individual checksums, original archive checksums and attribution.
- `review.json`: inspection records bound to bitmap and proof-input hashes.
- `quintessential-latin.hex` and `glyphs.json`: **generated outputs**.

Edit the 16 rows of `.` and `#` in a source drawing. Each drawing has a stable
ID, donors, rationale, expected topology and local review notes. Added forms also have an exact
base-plus-pixel recipe with explicit permitted body join coordinates. Names, codes
and ordered parts come from `resources/quintessential-latin-allocation.json`.
Historical STIX recipe codes never determine bitmap assignments. The historic
ID `special-ring` remains internal; its public structural name is BOWL.

```sh
npm run build:unifont
npm run test:unifont
npm run test:unifont:sources
npm run test:unifont:review
node tools/build_unifont_glyphs.mjs --check
npm run preview:unifont
npm run test:unifont:browser
```

`preview:unifont` refreshes the Unifont page, assets and static proofs in an
existing `dist` site. Run normal `npm run build` once to create that site. The
bitmap preview does not rebuild or replace outline-font PDFs. Set `QLAT_BASE_URL`
to a running preview's repository-prefixed URL to reuse it for browser tests.

The tab retains five 256-position charts and one selected-character inspector.
Static pages under `unifont/proofs/` include `foundation.html`, `primitives.html`,
`pairs.html`, `stress.html`, `expansions.html`, `donors.html` and each drawn
family's page. Every
character includes native donors, the frozen current Roman STIX-based reference,
1× and 2× views, gridded and clear 8× views, and repeated and mixed Latin strings.
Static proofs work without JavaScript.

Each middle-component family is arranged as complete pairs or quartets in
the allocation's visual order: neither, left only, right only, both. The
interactive inspector loads a compact metadata file; full coordinate flags
and review evidence remain available in `glyphs.json` and `review.json`.

The three middle-component source generators are stored beside their JSON
drawings. `test:unifont:sources` reconstructs and compares these sources
without writing files or resetting inspection records. Literal templates,
outer masks and middle-extension masks must reproduce every exported drawing.

## Pixel conventions after foundation feedback

Coordinates are zero-based. Body rows are 6–13, with the baseline below row 13.
Ordinary ascenders reach row 3; descenders use rows 14–15. Column 0 is blank.
Four staves occupy columns 1, 3, 5 and 7. Three-stave branch forms follow
native m/turned m at columns 1, 4 and 7; a three-stave shared spine instead
reserves five columns for its paired counters. All drawings fit eight pixels;
there are no 16-pixel exceptions.

STEM and BOWL exactly remap native U+0131 DOTLESS I and U+006F O:

```text
0F2A03:000000000000180808080808083E0000
0F2A00:0000000000003C4242424242423C0000
```

| Context | Native precedent and provisional treatment | Visible proof |
| --- | --- | --- |
| Standalone upright | Dotless i/l: column-4 stave, two-pixel head, five-pixel foot. Descenders put the foot on row 15. | STEM, ASCENDER, DESCENDER primitives |
| Shoulder or hip | r, turned r, n and u supply supported entrances and hip returns. Internal staves omit full dotless-i feet. | Paired shoulder/hip and arch forms |
| Bowl attachment | b/p and Latin alpha supply returns; epsilon supplies the two-storey waist. | Paired bowls and double bowls |
| Hook and tail | f, dotless j, hooked Latin and eng provide bends. Omit f's crossbar where the identity is only a hook. | Upright primitives and stress groups |
| Compact arches | Compress m shoulders to one crest per two-column interval, with diagonal joins and open undersides. | U+F2C20–U+F2C23 |
| Long-bowl closure | Return (3,5) meets only its designated neighbor. Remote column-5 extension cannot close it. h/q terminals avoid serif bridges. | U+F2CA8–U+F2CAB |
| Free terminals | Preserve exact native s, open o and reversed epsilon pixels; no added bulbs or thickened terminals. | Corresponding three stemless primitives |
| Attached/shared spines | Preserve exact native a/turned a for one-sided forms; combine their upper/lower connections with a balanced thin waist for shared forms. The independent stemless spine uses exact native s. | Paired spines and shared-spine emblem |

Turned forms retain their structural orientation and body height. Rotating the
whole 16-row cell is not a construction method.

U+F2EBC–U+F2EBF now use a horizontal crossover at row 9, as requested, with
upper/lower counter areas of two and three pixels. At ordinary width, spine
with stem exactly copies native Unifont a (U+0061); stem with spine exactly
copies native turned a (U+0250). Shared spines combine the turned-a upper connection with the upright-a lower
connection. Their paired waist returns form a thin central step and the body
has half-turn symmetry with equally sized counters. The one-sided native donors
remain exact, including their original horizontal waist. The turned double bowl uses the native d/q lower
return instead of forcing alpha's return into the compressed waist; this removes
the 2×2 cluster while preserving both counters. The normal double bowl retains
its already thin native b/p joins.

Compound left hooks use native f's bend, without its crossbar. Compound right
tails use the simple three-pixel return at (6,14), (5,15), (4,15), following the
compact eng treatment. An extra upturned tip would create an unintended enclosed
gap against some hips and is omitted consistently. Standalone primitives retain
their native dotless-i/l heads and feet and dotless-j-based return.

For long bowls, the full return spans the immediately adjacent stave instead of
using that compact tail. Lower returns close at (1,14); upper returns close at
(6,5), only when the designated adjacent extension is present. Ordinary bodies
remain unchanged. Straight extensions on spines may fill (1,13) or (6,6) to carry
the stave continuously through the rounded body corner; each repair is recorded
in `recipe.joinPixels` and preserves the existing counter.

Five-column shared cores retain equal six-pixel counters and the balanced
two-row waist derived from both native a orientations. Three-column cores
retain the approved row-9 crossover and two-/three-pixel counters. The native
m shoulder and turned-m hip use one-pixel diagonal joins in each two-column
interval, without repeated dotless-i feet beneath internal staves.

In 48 states with two arches on one side of a shared spine, the ordinary
outer hook meets its immediately neighboring extended stave. This makes a
small terminal counter, distinct from the two unchanged spine counters.
Examples: U+F2D1A (lower-right contact) and U+F2DD1 (upper-left contact).
The hook remains visibly different from a straight ending. These are natural
compact hook contacts, recorded in `structuralChecks.terminalContact`;
they do not declare a long-bowl return contact. Their explicit coordinate
proof is in `qa-double-middle-shared-spines/compact-hook-contacts.png`.

## Validation and inspection evidence

Build checks reject missing batch identities, duplicate assignments or
bitmaps, non-8-pixel cells, blank substitutes, occupied column 0, changed exact
donors and incorrect declared component/counter counts. Tests check HEX/SVG
agreement, independent extension masks, adjacent-only closure, shared counter
preservation and deterministic rebuilds.

Topology uses 8-neighbor ink and 4-neighbor background. Diagonal contacts,
isolated pixels, solid 2×2 clusters and small counters have coordinate flags
for inspection. Near-duplicates differing in at most four pixels are listed
separately for review. Extension-state differences are intentional only where
their prescribed pixels account for them.

Each inspection record binds the exact HEX line and proof-input hashes. Proof
inputs include source drawings, allocation, donors, geometry checks, SVG and
proof renderers, proof CSS and the frozen outline font. Editing a shared source
currently invalidates all drawing records conservatively. The static proof
manifest also hashes the generated HTML. Inspection does not grant user acceptance.

All drawings have individual inspection records. Durable family contact
sheets are retained in the `qa-*` directories, with per-glyph bitmap hashes
and evidence image hashes. Browser verification additionally captures every
static character proof and verifies its exact HEX pixels and integer sizes.
The final review command requires all 1,216 current records, complete
near-duplicate review records, and independent review evidence. Agent visual
inspection, engineering verification and the user's final aesthetic acceptance
are recorded separately.

## Pinned sources and chart geometry

- [Official GNU Unifont 17.0.05 bitmaps](https://unifoundry.com/pub/unifont/unifont-17.0.05/font-builds/unifont-17.0.05.hex.gz)
- [GNU Unifont glyphs and downloads](https://unifoundry.com/unifont/index.html)
- [GNU Unifont manual](https://unifoundry.com/unifont/doc/unifont.pdf)
- [17.0.05 source archive](https://unifoundry.com/pub/unifont/unifont-17.0.05/unifont-17.0.05.tar.gz):
  `src/unihex2png` supplies chart geometry; `OFL-1.1.txt` supplies licensing.

Gzip SHA-256: `2ae5311c8e123e9e85f5331cd012aa99757071df23243f1487fdbf8f3acd86be`.
Decompressed SHA-256: `fd79af3613ec1b984a98d33428fdd43fcf06018d18059960d78edeb63d958622`.
The subset and every individual donor are checked at build time.

For column c and row r (0–F), code = page start + 16*c + r. Each chart uses
16 × 16 tiles of 32 × 32 pixels, a 48-pixel label margin and a 32-pixel heading.
The first border is (47,31); the glyph starts at (52,39), or (5,8) from that
border. Horizontal gaps are 5,12,13,20,21,28; vertical gaps are 8,15,16,23.
A chart is 560 × 544 pixels, matching `unihex2png`. Pending positions have no
exported bitmap. The chart uses pending dots; unallocated positions are hatched.

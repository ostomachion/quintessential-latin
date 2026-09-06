# Native Italic completion

Quintessential Serif 0.230 adds the remaining 600 native Italic forms. All 832
allocated characters now have Roman and Italic outlines across weights 400–700.
The character allocation remains version 0.220 and canonical naming remains
version 3; only font posture availability changes.

## Construction

| Added construction | Forms, including middle-leg companions |
| --- | ---: |
| Double bowls, with zero, one, or two attached arches | 60 |
| Opposed bowls, with all ending and arch combinations | 396 |
| Extended arms, bowls, spines, and repeated arches | 144 |
| **Total** | **600** |

All new outlines use the pinned STIX Two Text 2.13 b171 Italic donors.
Independently drawn epsilon and reversed-e lobes supply the double bowls;
native b and alpha provide their slanted receiving shafts and curved counter
returns. The opposed body uses native turned-a diagonal counter curves and a
rigid half-turn for the lower direction. Both counters are fitted together and
reused under horizontal translation throughout the family. The single-storey
Italic a is not used as a diagonal bowl donor.

The shared shoulder trims the donor's buried overlap at the receiving shaft's
actual axis. Prepared arch ports use a direct entrance without retracing that
overlap. This keeps each contour simple at Bold, removes a small join spur,
and preserves the body counters, advances, bounds, and all kerning values.

Native p, b, hooked b, d, q, and single-storey g supply the independently chosen
heads, feet, and hooks. Facing endings close against their neighboring shaft
where required. Native m, hooked m, and turned-m ribbons supply repeated arches;
the hooked triple uses its own donor's middle ribbon to retain a supported join
at Bold. Internal free legs receive native p descenders or l/d ascenders.

Roman constructions and the preceding 232 Italics retain their original
outlines, advances, assignments, and old-to-old kerning. All previous Italic
glyph IDs remain a prefix of the expanded font. New glyphs append after them;
only pairs involving a new glyph are added. The source updater writes new
Italic GLIFs and the corresponding contents, glyph-order, and kerning tables.
All four masters receive version metadata. It does not run the foundation
force-import or regenerate the reviewed Roman geometry.

## Regeneration and proofs

```sh
python tools/complete_italic_sources.py
python tools/build_quintessential_font.py
python tools/export_font_coverage.py
node tools/export_glyph_catalogue.js
python tools/export_italic_completion_proof.py --png
python tools/build_pdfs.py
npm run build
python tools/test_fonts.py
npm test
npm run test:browser
```

PNG proof export uses Pillow from `tools/requirements-pdfs.txt`. Source updates
are byte-idempotent; repeat font builds use the isolated verification command
documented in the font development guide.

The [complete proof index](images/italic-completion/index.html) covers every
addition at weights 400, 550, and 700, with 16px and 24px contexts. Each sheet
is bound to the compiled font hash. The source and compiled preservation
fixture is [the independent 0.220 capture](../resources/provenance/italic-completion-baseline.json.gz).
It records all four original source masters, four static faces, and ten
variable-font instances, including every old effective kerning pair.

The pair check retains every ordered pair at five weights. It caches lossless
in-memory font instances and uses strict integer projection separation to rule
out disjoint sampled outlines. Pairs without that certificate still receive the
original filled-outline intersection check. Boundary and collision tests verify
the shortcut independently; font geometry and placement remain unchanged.

Current results belong in [the verification record](verification.md).
Engineering checks, agent optical inspection, user visual acceptance, and
publication remain separate outcomes.

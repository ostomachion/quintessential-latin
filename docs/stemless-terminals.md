# Stemless terminal revision

The spine, turned open bowl, and turned open double bowl use bulb terminals at
both ends in Roman and native Italic. This follows the user's preference after
reviewing the terminal alternatives. The upright open bowl and open double bowl
retain their existing drawing.

The stable construction identities are `special-spine`,
`special-turned-open-bowl`, and `special-turned-double-open-bowl`. In the current
0.250 allocation these are U+F2AC3, U+F2A02, and U+F2AC2 respectively. Allocation,
canonical names, release version, advances, and kerning remain unchanged.

The four UFO masters are the editable authority. Optical proof sheets read the
two compiled variable fonts directly, at weights 400, 500, 550, 600, and 700.
Each revised form and both upright references appear at 160px em and at 18px,
24px, and 32px. The vector files contain actual compiled paths; PNG versions
render the same compiled fonts through FreeType. The proof manifest binds the
font hashes, build manifest, allocation, and generated sheets.

Generate the proof after rebuilding the font:

```sh
python tools/export_stemless_terminal_proof.py --png
```

The exporter verifies both font hashes against the current build manifest before
writing the [Roman and Italic proof sheets](images/stemless-terminals/index.html).
Optional `--expect-roman-sha` and `--expect-italic-sha` arguments bind an invocation
to explicitly selected build outputs.

The five refreshed publication PDFs pass all nine PDF tests and retain their
67-page pagination (6 main, 7 Extended-A, 18 Extended-B, 31 combined, 5 proposal).
All pages were rendered with Poppler at 110 dpi and inspected on 19 contact
sheets. The eight pages containing revised forms were also inspected at full
rendered resolution: main pages 2-3, Extended-A pages 2-3, and combined catalogue
pages 2-3 and 8-9. The 22-point chart specimens and 10-point names-list specimens
fit cleanly, with no observed clipping, overlapping text, or broken wrapping.
The [PDF review record](../resources/verification/stemless-terminals/pdf-review.json)
binds these observations to the exact font, PDFs, and rendered pages.

Both compiled proof sheets were visually inspected in full: 30 revised
weight/posture specimens and 20 unchanged reference specimens, each at four
sizes. The bulbs and openings remain clear through the intermediate weights and
Bold, including the repeated text-size samples. No new visible joins, spikes,
clipping, or unexpected changes in weight progression were observed. The
[optical review record](../resources/verification/stemless-terminals/optical-review.json)
binds this inspection to the final Roman and Italic font hashes and PNG sheets.

All seven targeted font test methods passed across the recorded staged runs.
Exactly 12 GLIFs changed; every other captured source byte remains exact.
Four static faces and ten variable samples preserve every unrelated outline and
sidebearing, plus all advances and effective pairs. Both pair directions against
the complete repertoire pass at five weights in each posture: 72,870 source and
72,870 compiled ordered pairs, with no collisions. All 60 source/variable shape
samples remain open and simple, and all 12 revised static glyphs match their
variable endpoints within the existing geometric tolerance. See the
[font validation record](../resources/verification/stemless-terminals/validation.json)
for exact scope, hashes, and staged results. The full unrelated-family suites
and exhaustive all-glyph-pair suite were not rerun.

The final PDF rebuild uses the refreshed catalogue and is byte-identical to the
fully rendered and reviewed PDFs. All nine PDF tests pass again, and all final
PDF source/output hashes validate. User visual acceptance of the implemented
drawings and external publication remain separate from these checks.

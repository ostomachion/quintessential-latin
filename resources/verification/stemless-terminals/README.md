# Stemless terminal verification

**Passed:** the spine, turned open bowl, and turned open double bowl use two bulbs in all four masters. All seven methods in `tools/test_stemless_terminals.py` passed across the staged runs recorded in [validation.json](validation.json).

- Exactly 12 GLIFs changed. Every other captured source byte remains exact; every advance, pair, glyph order, and encoding remains exact.
- All 1,215 unrelated outlines and sidebearings per face remain exact across four static faces and ten variable samples. All 1,218 advances and all effective pairs remain exact. Only the three revised glyphs may change outline and sidebearing.
- **145,740 ordered pairs** involving a revised glyph passed: 72,870 source and 72,870 compiled pairs, Roman and Italic at 400, 500, 550, 600, and 700. Bounding boxes excluded disjoint ink; 3,630 remaining cases used actual filled-outline intersections. Compiled positioning resolves the actual GPOS variation values. No collisions were found.
- Native body curves and both complete bulb runs passed. All 60 source/variable shape samples remain one open, simple contour. All **12 static target glyphs** match their variable endpoints within the existing refined 1.0 square-font-unit geometric tolerance.
- Existing checks passed: three source stemless geometry methods, master interpolation/kerning compatibility, historical Italic and independent-middle source preservation, and three font-format methods covering WOFF2 parity, variable structure, and hinted CFF statics.

The logs and JSON identify each staged run. Source pair, expanded topology, old source-class, and master-compatibility outputs were observed directly and are summarized in the JSON; their initial runs were not redirected to files. The full legacy unrelated-family suites and exhaustive all-glyph-pair suite were not rerun. Optical review and publishing are separate from these engineering checks.

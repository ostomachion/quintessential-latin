# Italic shaft alignment

The rendered review of U+F2A08, **long hook**, exposed different slopes in
its upper and lower halves. In the pinned native Italic donors, the long-s
shaft is about 9.415 degrees at 400 and 8.595 degrees at 700; the p descender
is about 11.707 and 11.711 degrees. The earlier construction placed their
short connecting region on the font's nominal 12-degree axis. A test confined
to that connection did not detect the mismatch between the donor shafts.

The correction covers fifteen stem/shoulder/hip forms plus three descending
arch shafts and their 132 derivatives: 150 glyphs in each of the Italic and
Bold Italic masters. The upper component gets
a small horizontal shear about its shaft cut to match the actual lower shaft's mean
edge slope. The connector follows that measured axis too. All heights and
horizontal ink widths in the upper donor are preserved; its slant is an
intentional adaptation. Lower terminals retain their native shapes under a
rigid horizontal translation. Independent shoulder and hip contours retain
their original coordinates.

| Code | Construction | Stable identity |
| --- | --- | --- |
| U+F2A05 | hook | `hook` |
| U+F2A06 | descender | `descender` |
| U+F2A07 | long stem | `ascender-descender` |
| U+F2A08 | long hook | `hook-descender` |
| U+F2A0A | long tail | `ascender-tail` |
| U+F2A0D | ascender with shoulder | `arm-ascender` |
| U+F2A0E | hook with shoulder | `arm-hook` |
| U+F2A0F | descender with shoulder | `arm-descender` |
| U+F2A10 | long stem with shoulder | `arm-ascender-descender` |
| U+F2A11 | long hook with shoulder | `arm-hook-descender` |
| U+F2A13 | hip with descender | `turned-arm-descender` |
| U+F2A14 | hip with tail | `turned-arm-tail` |
| U+F2A15 | hip with ascender | `turned-arm-ascender` |
| U+F2A16 | hip with long stem | `turned-arm-ascender-descender` |
| U+F2A17 | hip with long tail | `turned-arm-ascender-tail` |
| U+F2A27 | descender with leg | `arch-descender` |
| U+F2A28 | long stem with leg | `arch-ascender-descender` |
| U+F2A29 | long hook with leg | `arch-hook-descender` |

The four uses of long s are included. Direct native letters, such as the
hook-and-tail at U+F2A0B, retain their donor design. A differential recipe audit
confirmed that every listed descending-arch derivative retains the changed
shaft; it did not count discarded intermediate donors. The complete explicit
inventory is [italic-shaft-targets.json](../resources/italic-shaft-targets.json).
The stem and arm cut is y=300; the descending-arch cut is y=150. Roman masters,
character assignments, and advances are preserved. The changed hooks need
additional clearance in some contexts, so only pairs involving the 150
affected Italics are recalculated; all other pairs are preserved.

Regenerate only the 300 affected GLIFs and their two kerning files with
`python tools/refine_italic_shafts.py`; `--check` verifies reconstruction
without writing. Do not force-import the complete foundation.
`python tools/test_italic_shaft_alignment.py` measures the separate shaft
halves and their connection, checks compiled desktop/web formats, and tests
spacing in both orders against the full repertoire at five weights.

The pre-edit evidence and the separate revision record under
`resources/provenance/italic-shaft-*` keep the historical preservation fixtures
immutable. The bridge validates the new bytes or geometry before substituting
the captured pre-edit evidence for older comparisons. It is limited to the
150 named Italic forms and pairs involving those forms. Rendered proof inspection
and user acceptance are separate from those geometric checks.

## Review and verification

The [before/after proofs](images/italic-shaft-alignment/index.html) show all
eighteen base shafts at weights 400, 500, 550, 600 and 700, and all 150 affected
constructions at both endpoints. The 25 sheets include text-size specimens
and record the exact compiled font hashes.

The [focused verification summary](../resources/verification/italic-shaft-alignment/summary.json)
records nine passing checks, including all 3,423,000 affected ordered pairs
across source and compiled geometry, with zero collisions. Independent source
comparisons protect every companion contour and the native lower terminals.
The dependency audit enumerates all 1,216 construction recipes to guard against
omitting a derivative.

The adjacent publication report records the refreshed website and font
downloads, 231 passing browser checks, and nine passing PDF checks. The five
PDFs use Roman fonts and remain byte-identical; all 76 rendered pages were
reviewed. These are local engineering and visual-review results, not a record
of user acceptance or website publication.

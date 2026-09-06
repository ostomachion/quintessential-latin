# Logical allocation

Font and allocation version 0.250 arrange all 1,216 constructions in one
continuous private-use range, U+F2A00–U+F2EBF. Every position is assigned.
The 0.240 glyph designs, advances, kerning, stable construction identities,
and internal font glyph names are retained; public code points are replaced
without compatibility aliases.

| Block | Range | Characters |
| --- | --- | ---: |
| Quintessential Latin | U+F2A00–U+F2ABF | 192 |
| Quintessential Latin Extended-A | U+F2AC0–U+F2BBF | 256 |
| Quintessential Latin Extended-B | U+F2BC0–U+F2EBF | 768 |

## Construction order

The main block begins with bowl, open bowl, and turned open bowl. Extended-A
begins with double bowl, double open bowl, turned double open bowl, and spine.
These four stemless constructions form the `stemless-double-bowls-and-spine`
family, before the upright-bearing double-bowl and spine families.

The 19 former extended-middle companion families merge into their base families,
leaving 30 families overall. A form with one middle component is immediately
followed by its extended form. A form with two middle components has four
adjacent states in visual left-to-right order: neither extended, left only,
right only, and both extended. The 384 asymmetric forms are integrated with
their bases instead of occupying a later additions area.

Numeric code order, names lists, and presentation order agree. The allocation's
internal entry order and font glyph order remain separate from this public order.
Consumers must use the current allocation or stable construction identity to
locate a form; earlier private-use numbers do not identify the same construction.

## Charts and publication

Five reference sheets contain 192, 256, 256, 256, and 256 positions. The first
has 12 hexadecimal columns; the others have 16. Every sheet uses 16 rows and
the existing cell dimensions, font sizes, and native glyph proportions. A
block may begin between 256-position boundaries, so sheets begin at the block's
actual first code point and stop at its final point.

Responsive charts show up to 16, 8, or 4 columns. The shorter final section
retains only its actual columns. No chart displays another block's characters
or invents vacant cells to fill out a page. The same five PDF filenames remain
the public downloads.

## Verification status

The migration changes only source Unicode assignments and font version metadata.
It retains every other source byte, internal glyph order, drawing, advance, and
kerning pair. Re-running the migration check makes zero changes. The compiled
comparison restores only the authorized encoding/version fields before comparing
tables with 0.240; matching normalized tables preserves the previous geometry,
metrics, and kerning results. New allocation tests verify the public order.

Regenerate and verify in this order using the font-development Python environment:

```sh
python tools/reallocate_catalogue.py
python tools/reallocate_catalogue.py --check
python tools/build_quintessential_font.py
python tools/verify_logical_allocation.py
python tools/verify_font_preservation.py
python tools/export_font_coverage.py
node tools/export_glyph_catalogue.js
node tools/test_logical_allocation.js
```

All 24 sheets in the [0.250 proof index](images/logical-allocation/index.html)
retain the exact previous SVG drawing and placement trees apart from text and
code-derived reference IDs. New-label spot checks cover sheets 01, 04, 07, 09,
16, and 21. The [proof comparison](../resources/verification/logical-allocation/proof-path-comparison.json)
binds both revisions by hash; the earlier 0.240 proof files remain unchanged.

All 12 rebuilt font files pass the source, mapping, metadata, and normalized
compiled-table preservation checks. The final coverage and catalogue exports
match freshly generated data. See the
[font verification record](../resources/verification/logical-allocation/font-validation.json).
This encoding-only revision does not claim a fresh repeat font build: the
verified 0.240 repeat build remains dated historical evidence.

The 5 allocation tests, 20 naming tests, 14 site acceptance groups, 153 browser
checks, and 9 PDF checks pass. The five PDFs contain 67 pages: 6 main, 7
Extended-A, 18 Extended-B, 31 combined, and 5 proposal. All pages were inspected
from fresh Poppler renders; the PDFs and their manifest reproduce byte for byte.
The complete 25-page Italic 700 browser print, desktop/mobile page layouts,
eight block-boundary captures, and sixteen native-font dialogs comparing all
four middle-extension states were also inspected without visible defects.
The [publication review](../resources/verification/logical-allocation/publication-review.json)
binds these checks to the exact fonts, PDFs, and inspected images. This is a
local build; external publication and user visual acceptance remain separate.

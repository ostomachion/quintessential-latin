# Quintessential Latin naming

Canonical naming version 3 describes visible construction from left to right.
Names do not assign pronunciation or language membership. The allocation stores
ordered neutral component arrays as parts; the canonical naming function reads
those arrays without editing them.

The first named component is followed by "with", and further components by "and".
A closing long bowl can imply the straight extension of its immediately adjoining
upright. That implied extension is omitted from the name without changing the
underlying component geometry. Interior uprights use the ordinary stem, ascender,
and descender vocabulary. Equal adjacent uprights combine into count phrases such
as "two stems", "three stems", and "two ascenders". Terminal arms and legs retain
their connection-specific names.

The seven stemless forms retain the names bowl, double bowl, open bowl, turned
open bowl, double open bowl, turned double open bowl, and spine. The two explicit
turned names distinguish opposite-facing stemless open forms. Other constructions
use component order instead of a global turned modifier.

Every full character name starts with QUINTESSENTIAL LATIN SMALL LETTER, including
these seven stemless forms. All 1,216 characters are lowercase letters; uppercase
and titlecase counterparts and mappings are undefined. The capitalized spelling
of a character name does not change the character's case. The SMALL LETTER
prefix clarification retains version 3 of the construction-name algorithm and
does not change assignments, structural names, or internal font glyph names.

The [naming specification](quintessential-latin-canonical-naming-spec-v3.md) gives the complete primitive table, closure rules,
and structural examples. The implementation's nameParts(parts) function is the
single naming authority. The source allocation, public catalogue, browser
catalogue, Markdown name list, and NamesList.txt must remain consistent.

Run node tools/export_glyph_catalogue.js to regenerate the public exports.
Run node tools/export_glyph_catalogue.js --check to verify them without changes.
Run node tools/test_canonical_glyph_names.js to check primitive vocabulary,
local closure, count rules, all 1,216 unique names, and input nonmutation.

Canonical names, presentation families, stable glyph IDs, internal font names,
legacy recipe codes, and active private-use assignments are separate identities.
Changing a family title must not alter a character name or font mapping.


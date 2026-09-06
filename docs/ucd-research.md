# UCD export research

Checked 6 September 2026 for the 0.250 repertoire: 1,216 constructions at
U+F2A00–U+F2EBF. These findings guide a project-owned private-use data supplement,
not a Unicode data release or an assertion of UCSUR registration.

## Files relevant to UCSUR

The [UCSUR UNIDATA directory](https://www.kreativekorp.com/ucsur/UNIDATA/)
publishes the following six text files. Matching these existing formats gives
reviewers useful input without guessing at an unpublished submission checklist.
The CSUR's public [proposal guidance](https://www.evertype.com/standards/csur/)
points authors to existing registration documents and describes preliminary
comment followed by final registration; it does not specify a required UCD bundle.

| File | Recommended project content |
| --- | --- |
| `UnicodeData.txt` | One complete, individually named record for each construction. |
| `Blocks.txt` | The three exact proposed block ranges and titles. |
| `NamesList.txt` | Block headers, structural family headings, and canonical names in numeric order. |
| `CaseFolding.txt` | Comments documenting identity folding; no mapping records. |
| `Charts.txt` | Block headers, reference font directives, and glyph mappings at their actual scalar values. |
| `Sources.txt` | Project agreement identification and bibliographic provenance. |

An accompanying `ReadMe.txt` and checksummed provenance manifest are useful
project additions. They can explain scope, regeneration, formats, and property
tailoring without putting comments into `UnicodeData.txt`.

## Format details

`UnicodeData.txt` has a fixed set of 15 semicolon-separated fields, including
empty trailing fields; do not trim them or append columns. Use one line per
assigned scalar and no inline comments or header rows. `X..Y` range syntax is
not its range convention. UTF-8 and LF are the UCD conventions. These points
follow [UAX #44, file formats and property definitions](https://www.unicode.org/reports/tr44/tr44-36.html#File_Format_Conventions).
The [UCSUR UnicodeData file](https://www.kreativekorp.com/ucsur/UNIDATA/UnicodeData.txt)
provides direct precedents for individually named PUA letters in this format;
their character categories are specific to each agreement. The project uses
`Ll;0;L;;;;;N;;;;;` for its lowercase letters without case counterparts.

`Blocks.txt` uses `START..END; Block Name`. Keep names identical to the chart
headers. The three project ranges are already aligned to hexadecimal columns.
Use [UCSUR Blocks.txt](https://www.kreativekorp.com/ucsur/UNIDATA/Blocks.txt)
as a format precedent, not a current availability inventory: its own header is
dated 5 June 2022.

The [NamesList grammar](https://www.unicode.org/Public/17.0.0/ucd/NamesList.html)
requires literal tabs: `@@<tab>START<tab>TITLE<tab>END` and
`CODE<tab>NAME`. Family subheaders use `@<tab><tab>LABEL`, as seen in
[UCSUR NamesList.txt](https://www.kreativekorp.com/ucsur/UNIDATA/NamesList.txt).
Use uppercase hexadecimal scalars, not UTF-16 surrogate halves. File comments
start with `;`. A first-line `; charset=UTF-8` declaration avoids legacy
encoding ambiguity. Do not invent aliases, decomposition annotations, or
semantic readings from structural names.

[UCSUR's Charts format documentation](https://www.kreativekorp.com/ucsur/UNIDATA/Charts.html)
uses the same tab-separated block header, then a directive such as
`@font=Quintessential Serif, 18pt`, then `CODE;TEXT` mappings. Text may include
XML character references or ODF markup. Consequently, a parser must split the
mapping at its first semicolon: `F2A00;&#xF2A00;` contains an additional
semicolon belonging to the entity. A direct literal scalar also works.
Font size is a chart-generation preference; publishing this configuration does
not establish that the external UCSUR chart generator has rendered it correctly.

[UCSUR Sources.txt](https://www.kreativekorp.com/ucsur/UNIDATA/Sources.txt)
contains blank-line-separated `Key: Value` paragraphs. Its first paragraph uses
`Agreement-Type`, `Agreement-Name`, `Agreement-FCC`, and `Generated`; source
paragraphs use `Title`, `Author`, `Publication-Date`, `URL`, and `Access-Date`.
This is an observed layout, not a separately documented schema. Identify the
project's own draft agreement and cite the project sources. Do not copy
`Agreement-FCC: ucsu`, which identifies the UCSUR agreement, or imply a registry
grant. Omit any field whose value is not established.

## Conservative property choices

The [current project proposal](proposal.json) specifies spacing, lowercase,
left-to-right letters without numeric values or automatic composition.
Accordingly, `General_Category=Ll`, `Canonical_Combining_Class=0`,
`Bidi_Class=L`, `Bidi_Mirrored=N`, and empty decomposition, numeric, and case
fields are suitable proposed reference behavior. Reversed and turned forms
have independent identities; their outlines do not make them bidi mirrors.
Font posture and weight do not produce case mappings.

This corrects the initial export's `Lo`/uncased interpretation following the
author's clarification that every character is lowercase. The full names now
use `QUINTESSENTIAL LATIN SMALL LETTER ...`. Lowercase status does not require
an uppercase counterpart: [Unicode section 4.2, Case](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-4/)
treats case properties separately from case conversion and defines an absent
case mapping as identity. All three simple case-mapping fields remain empty;
no uppercase or titlecase counterparts are allocated or inferred.

[UAX #44's property definitions](https://www.unicode.org/reports/tr44/tr44-36.html#Property_List_Table)
derive `Lowercase=Yes` and `Cased=Yes` from `Ll`. `Cased` differs from
`Changes_When_Casemapped`: these letters have case even though conversion
leaves them unchanged. Applications adopting this overlay must apply those
derivations consistently. A separate partial derived-property file is not
needed to express the lowercase category already present in `UnicodeData.txt`.

`Ll` is an explicit private agreement. Ordinary Unicode libraries retain the
default `Co` classification and have no standardized character names for these
constructions. Unicode [section 23.5, Private-Use Characters](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-23/)
permits agreed behavioral overrides, but normalization is a firm exception:
private-use characters must retain combining class zero, identity decomposition,
and identity NFC/NFD/NFKC/NFKD behavior. Constructing a glyph from components
does not justify a Unicode decomposition mapping.

The [UCSUR case-folding convention](https://www.kreativekorp.com/ucsur/UNIDATA/CaseFolding.txt)
maps omitted characters to themselves. A comment-only project supplement is
therefore complete for the specified identity folding of this lowercase
repertoire; explicit self-mappings add no behavior. The absence of case
counterparts alone would not determine folding, so the project explicitly
specifies that each of its characters folds to itself.

Do not generate `Scripts.txt`, script aliases, break tailoring, identifier
properties, numeric properties, normalization exceptions, or variation sequences
without a concrete agreement requiring them. UCSUR's published directory does
not currently contain `Scripts.txt`; this absence does not establish that its
maintainer would reject one. The project currently defines Latin-derived
constructions without establishing a Script property assignment. Additional
Unicode-looking files would make unnecessary semantic commitments.

## Registry availability snapshot

The [live UCSUR allocation table](https://www.kreativekorp.com/ucsur/)
listed U+F2A00–U+F2AFF, U+F2B00–U+F2BFF, U+F2C00–U+F2CFF,
U+F2D00–U+F2DFF, and U+F2E00–U+F2EFF as unassigned when checked.
The proposed range lies entirely inside those entries. This is a dated
observation, establishes no reservation, and says nothing about unregistered
private agreements. Data generation does not submit the proposal or update the
registry.

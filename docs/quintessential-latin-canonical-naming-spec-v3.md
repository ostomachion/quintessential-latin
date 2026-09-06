# Quintessential Latin: canonical glyph naming specification v3

## 1. Purpose and scope

Canonical construction names describe the existing Quintessential Latin repertoire from left to right. They describe typographic structure, not pronunciation, language membership, drawing order, font styling, or a mechanically rotated outline.

Use the existing structural components and constructors. Naming must preserve the 832 glyph identities, code points, full component arrays, and outlines. Do not infer components from pixels or introduce hypothetical glyphs to fit a naming rule.

Every full character name, including the seven stemless forms, is the uppercase canonical construction name prefixed by `QUINTESSENTIAL LATIN LETTER `.

## 2. Canonical text format

Canonical construction names use lowercase words and single spaces. Normalize components and combine equal adjacent uprights before formatting the final ordered terms:

- One term: `A`.
- Two terms: `A with B`.
- Three or more terms: `A with B and C`, continuing with ` and ` for every further term.

Use `with` exactly once in a multi-term name. A count phrase such as `two stems` is one final term. Do not insert commas, parentheses, hyphens, or repeated `with` separators.

The separators serialize a flat left-to-right construction. `and` does not make the sequence unordered or mean that every subsequent component attaches to the first. In `two stems with long open bowl`, the bowl's closing neighbor is the second stem, not the first.

Use `long open bowl`, not `open long bowl`. Number words precede modifiers, as in `two long stems`. Left-to-right order replaces global left/right qualifiers: use `bowl with ascender`, not `ascender with left bowl`.

`turned` occurs only in the two stemless names `turned open bowl` and `turned double open bowl`. Other constructions express orientation through component order.

## 3. Primitive vocabulary

An upright has independent upper and lower extensions, each absent, straight, or curved. Use this table after omitting only straight extensions entailed by adjacent closed bowls:

| Lower extension / Upper extension | None | Straight | Curved |
|---|---|---|---|
| None | `stem` | `ascender` | `hook` |
| Straight | `descender` | `long stem` | `long hook` |
| Curved | `tail` | `long tail` | `long spine` |

These names identify complete upright primitives. A stem occupies the baseline-to-x-height region; an ascender extends upward and a descender downward. Hook and tail identify curved upper and lower extensions.

An interior upright uses the same table as an outer upright. A short interior upright is a `stem`; with a straight upper extension it is an `ascender`, and with a straight lower extension it is a `descender`. Internal branch-connection roles remain in the structural data but do not add positional modifiers to names.

| Component | Structural role |
|---|---|
| `shoulder` | Short, free-ended upper branch in an r-like construction. |
| `hip` | Lower, turned-r-like counterpart of a shoulder. |
| `leg` | Complete terminal right-side descending branch, including its upper connecting arch. |
| `arm` | Complete terminal left-side ascending branch, including its lower connecting arch. |
| `bowl` | Ordinary closed rounded body. |
| `spine` | Ordinary x-height s-shaped body. |
| `double bowl` | Existing stemless doubled rounded body. |

Terminal arms and legs retain their connection-specific names. A `long leg` extends below the baseline with a straight continuation; a `long arm` extends above x-height. A `long bowl` is an extended bowl, upward-reaching on the left of its closing upright or downward-reaching on its right. `long` follows each family's established geometry, not one global scaling operation.

The ordinary spine and its extended counterpart never acquire an opening state. The `long spine` primitive and the long member of the spine family represent the same form.

The seven stemless construction names are `bowl`, `double bowl`, `open bowl`, `turned open bowl`, `double open bowl`, `turned double open bowl`, and `spine`.

## 4. Left-to-right construction examples

| Informal form or construction | Canonical construction name |
|---|---|
| r | `stem with shoulder` |
| Turned r | `hip with stem` |
| n | `stem with leg` |
| u | `arm with stem` |
| h | `ascender with leg` |
| b | `ascender with bowl` |
| d | `bowl with ascender` |
| p | `descender with bowl` |
| q | `bowl with descender` |
| o | `bowl` |
| Single-storey g | `bowl with tail` |
| Double-storey a | `spine with stem` |
| Turned double-storey a | `stem with spine` |
| Upper-joined ascending left upright and descending right branch | `ascender with long leg` |
| Lower-joined ascending left branch and descending right upright | `long arm with descender` |
| Upper-joined hooked left upright and tailed right branch | `hook with long open bowl` |
| Lower-joined hooked left branch and tailed right upright | `long open bowl with tail` |

Do not give both n/u constructions the ambiguous name `ascender with descender`; their terminal arm/leg names retain the connection type. Curved terminal branches use the long-bowl constructor rather than canonical labels such as `tailed leg` or `hooked arm`.

## 5. Bowl opening and closure-implied extensions

An upward-reaching long bowl on the left closes against its immediately following upright's upper straight extension. A downward-reaching long bowl on the right closes against its immediately preceding upright's lower straight extension. Otherwise use `long open bowl`.

Determine closure from the existing component records, their exact closing-neighbor reference, and actual return-contact information. A distant upright, a bounding box, or a similarly tall curved extension cannot establish closure. The closing neighbor must be immediately adjacent and on the side specified by the bowl's return.

Evaluate every bowl against the full geometry before omitting naming information. Collect all straight upper/lower extensions entailed by closed bowls, then name each upright from its remaining features. Do not mutate geometry or recalculate closure from the shortened labels. An open bowl entails no extension; a curved feature is never omitted.

| Actual construction | Canonical construction name |
|---|---|
| Upward bowl, short closing upright, return open | `long open bowl with stem` |
| Upward bowl closed by an ascender | `long bowl with stem` |
| Same closed bowl, upright also descends | `long bowl with descender` |
| Same closed bowl, upright also has a tail | `long bowl with tail` |
| Downward bowl, short closing upright, return open | `stem with long open bowl` |
| Downward bowl closed by a descender | `stem with long bowl` |
| Same closed bowl, upright also ascends | `ascender with long bowl` |
| Same closed bowl, upright also has a hook | `hook with long bowl` |

If one upright closes valid bowls on both sides, collect both implied extensions before naming it. A straight-extended upright between an upward bowl and a downward bowl can therefore be named `stem`, while its original geometry retains both extensions.

`open` is specific to bowls. Never emit `open spine` or `long open spine` or decompose a spine into bowls to manufacture opening qualifiers.

## 6. Interior uprights and local closure

Interior uprights use the primitive vocabulary independently of the terminal body. For example, a shoulder-ended upper chain is `two stems with shoulder`, and an m-like form is `two stems with leg`. The lower-joined counterparts are `hip with two stems` and `arm with two stems`.

| Extended interior construction | Canonical construction name |
|---|---|
| First stem, interior descender, ordinary final leg | `stem with descender and leg` |
| First stem, interior stem, long final leg | `two stems with long leg` |
| Ordinary first arm, interior ascender, final stem | `arm with ascender and stem` |
| Long first arm, interior stem, final stem | `long arm with two stems` |

For a final downward-reaching bowl, the adjacent interior upright determines closure. For an initial upward-reaching bowl, the adjacent interior upright likewise determines closure. The far outer upright cannot close either return.

| First upright | Interior upright, actual geometry | Final bowl | Canonical construction name |
|---|---|---|---|
| Stem | Stem | Open | `two stems with long open bowl` |
| Descender | Stem | Open | `descender with stem and long open bowl` |
| Stem | Descender closing the return | Closed | `two stems with long bowl` |
| Descender | Descender closing the return | Closed | `descender with stem and long bowl` |

| Initial bowl | Interior upright, actual geometry | Final upright | Canonical construction name |
|---|---|---|---|
| Open | Stem | Stem | `long open bowl with two stems` |
| Open | Stem | Ascender | `long open bowl with stem and ascender` |
| Closed | Ascender closing the return | Stem | `long bowl with two stems` |
| Closed | Ascender closing the return | Ascender | `long bowl with stem and ascender` |

The shortened interior name in a closed row does not alter its actual extension. Apply closure omission before combining equal adjacent upright names.

## 7. Count abbreviations

After component naming and closure omission, combine equal adjacent upright names into count phrases. Interior and outer uprights participate equally. The current repertoire requires runs of two or three:

| Adjacent upright names | Count phrase |
|---|---|
| `stem`, `stem` | `two stems` |
| `stem`, `stem`, `stem` | `three stems` |
| `ascender`, `ascender` | `two ascenders` |
| `descender`, `descender` | `two descenders` |

Preserve the order of all remaining components. Do not combine unequal primitives, terminal arms/legs with uprights, or uprights separated by a body. A long arm and an ascender remain distinct despite both extending upward.

| Code point | Full character name |
|---|---|
| U+F2A61 | QUINTESSENTIAL LATIN LETTER HIP WITH TWO ASCENDERS |
| U+F2AA9 | QUINTESSENTIAL LATIN LETTER LONG ARM WITH TWO ASCENDERS |
| U+F2C00 | QUINTESSENTIAL LATIN LETTER THREE STEMS WITH SHOULDER |
| U+F2A7C | QUINTESSENTIAL LATIN LETTER TWO STEMS WITH LEG |

## 8. Spines and attachment order

One-sided and two-sided spines follow the same ordered serialization: `spine with stem`, `stem with spine`, `stem with spine and stem`, and `ascender with spine and descender`.

Each attachment retains its own features. Do not reorder `stem with spine and stem` into a body-first name or combine its nonadjacent stems. A spine remains a body even when surrounded by uprights.

## 9. Implementation and acceptance contract

`nameParts(parts)` is the single naming authority. Its structural input retains ordered components, terminal/interior connection roles, full extensions, bowl length and return contact, and exact closing-neighbor references. Internal identity fields and historical labels are separate from current character names.

Evaluate bowl returns, collect implied extensions, name components, combine equal adjacent uprights, then serialize the final terms. Use semantic component records rather than unrestricted text replacement. The function must be deterministic and must never mutate the input.

Preserve glyph IDs, code points, font mappings, posture coverage, and outlines. Regenerate the allocation's names and dependent public catalogue, browser catalogue, Markdown names list, NamesList, and PDFs consistently. The naming version is independent of the font/repertoire version.

Required structural fixtures and properties:

- All nine primitive names and the ordinary body vocabulary.
- The Section 4 forms and distinct upper/lower terminal connections.
- Upward and downward bowl closure, failed contact, curved extensions, and both implied ends on a shared upright.
- Interior stems, ascenders, and descenders; repeated runs of two and three; unequal and nonadjacent uprights that must remain separate.
- Every local closure case in Section 6. Changing only a distant upright must not affect opening.
- One-sided and two-sided spine forms without opening qualifiers.
- The four exact code-point names in Section 7 and the uniform full-name prefix for all seven stemless forms.
- One-term and multi-term separators, applying counts before formatting. An empty construction is an error.
- All 832 names remain unique. Report any collision as an error rather than appending an arbitrary suffix.
- Naming leaves all underlying component geometry intact, including straight extensions omitted because of closure.

The current canonical vocabulary emits no positional arm/leg modifier. Archived labels and stable recipe identifiers may retain older terminology for provenance; they are not character display names.

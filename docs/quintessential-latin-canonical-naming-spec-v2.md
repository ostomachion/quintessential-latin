# Quintessential Latin: canonical glyph naming specification

## 1. Purpose and scope

Implement canonical constructional names for the existing Quintessential Latin glyph inventory. Names describe typographic structure, not pronunciation, Unicode character identity, drawing order, font styling, or a mechanically rotated outline.

Use the project's existing structural glyph data and constructors. This is a naming specification, not a request to redesign the glyphs, infer components from pixels, generate additional combinations, or change glyph IDs or code points. The examples refer to lowercase structural forms even where a letter is used as an informal label.

The central rule is:

> Read the construction from left to right. Use ` with ` after the first named component and ` and ` between all subsequent components. Preserve the connection type through the component vocabulary. A closed bowl supplies any straight upright extension required to close it; do not name that extension twice.

`open` applies to bowls only. There is no `open spine` or `long open spine` category.

## 2. Canonical text format

Canonical names use lowercase words and single spaces. After all component normalization and count abbreviations, format the final ordered terms as follows:

- One term: `A`.
- Two terms: `A with B`.
- Three or more terms: `A with B and C`, continuing with ` and ` before every further term.

Use `with` exactly once in a multi-term name, after the first final term. Do not repeat `with`, insert commas, or replace the canonical separators with plus signs, parentheses, or hyphens. A count phrase such as `two arms` is one final term.

The separators serialize one flat, ordered, left-to-right construction. `and` does not make the sequence unordered, imply that every later component attaches directly to the first, or change structural adjacency. For example, in `stem with middle leg and long open bowl`, the bowl's closing neighbor is the middle leg, not the first stem.

Apply abbreviations before choosing separators: `arm with middle arm and stem` becomes `two arms with stem`, not `two arms and stem`.

Use these modifier orders:

- `long open bowl`, not `open long bowl`;
- `long middle leg` and `long middle arm`;
- `two long legs` and `two long arms`.

In the constructions specified here, left-to-right placement replaces the former `left/right` modifiers: use `bowl with ascender`, not `ascender with left bowl`. Do not choose a global main component and move it to the beginning of the name.

`turned` is retained only in the two stemless names `turned open bowl` and `turned double open bowl`. Other canonical construction names express orientation through left-to-right component order. Turning a form does not mean mechanically rotating its font outline.

## 3. Primitive vocabulary

### 3.1 Stem-family primitives

A stem-family primitive has independently specified upper and lower extensions. Each end is absent, straight, or curved. For an isolated primitive, use this complete lookup table:

| Lower extension / Upper extension | None | Straight | Curved |
|---|---|---|---|
| None | `stem` | `ascender` | `hook` |
| Straight | `descender` | `long stem` | `long hook` |
| Curved | `tail` | `long tail` | `long spine` |

A `stem` occupies the baseline-to-x-height region. An `ascender` extends upward; a `descender` extends downward. A `hook` has the curved upper extension, and a `tail` has the curved lower extension. These names identify complete primitive forms, not merely the portions outside the x-height region.

`spine` names the ordinary x-height s-shaped component. `long spine` is its extended counterpart, with both upper and lower curved extensions. The `long spine` in the table and the long member of the spine family are the same form, not two independently named primitives.

Within a compound, a primitive's printed name can be shorter than its isolated name when a closed bowl already supplies a straight extension. This is specified in Section 6; it does not alter the primitive's actual geometry.

### 3.2 Branch and body components

| Component | Structural role |
|---|---|
| `shoulder` | The short, free-ended upper branch in an r-like construction. |
| `hip` | Its lower, turned-r-like counterpart. |
| `leg` | A complete right-side descending branch joined through an upper arch, as in n. |
| `arm` | A complete left-side ascending branch joined through a lower arch, as in u. |
| `bowl` | The ordinary closed rounded body. |
| `spine` | The ordinary s-shaped body. |

A leg or arm includes the relevant connecting curve. It is not just another independently specified vertical stroke. This is why these names preserve upper-versus-lower attachment information.

### 3.3 Meaning of `long`

`long` is a family-specific structural extension, not an arbitrary scaling operation and not a universal instruction to extend both ends.

- `long stem`, `long hook`, `long tail`, and `long spine` follow the primitive table.
- `long leg` extends below the baseline with a straight continuation.
- `long arm` extends above the x-height with a straight continuation.
- `long middle leg` and `long middle arm` have the corresponding extensions in an intermediate position.
- `long bowl` is the extended bowl form: upward-reaching on the left of its closing upright, or downward-reaching on the right of its closing upright, in the constructions described below.

Use the established geometry of each family. Do not implement `long` as one global transform.

## 4. Left-to-right construction names

The principal short-form examples are:

| Form | Canonical name |
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
| Single-storey g, bowl with right-hand tail | `bowl with tail` |
| Double-storey a | `spine with stem` |
| Turned double-storey a | `stem with spine` |

The distinction between leg and arm must survive straight extensions:

| Same upright extents, different connection | Canonical name |
|---|---|
| Upper-joined: ascending left upright, descending right upright | `ascender with long leg` |
| Lower-joined: ascending left upright, descending right upright | `long arm with descender` |

Do not name both constructions `ascender with descender`. That discards their connection type.

Similarly, a curved extended branch is classified using the long-bowl family described next, rather than losing its connection role through an undifferentiated `hook` or `tail` label. `tailed leg` and `hooked arm` may be useful internal descriptions, but are not the canonical labels for those branches in this scheme.

## 5. Extended bowls and opening

### 5.1 The two orientations

A hooked-arm-like body on the left of an upright is an upward-reaching long bowl. Its upper return closes only when it meets the appropriate upper extension of the adjacent upright.

A tailed-leg-like body on the right of an upright is a downward-reaching long bowl. Its lower return closes only when it meets the appropriate lower extension of the adjacent upright.

If the return does not close, add `open`: `long open bowl`. Without `open`, the bowl is closed.

These are structural contacts, not visual approximations. Determine closure from the existing construction data or its actual connection rules, not from a bounding box, apparent proximity, or the fact that another stroke somewhere in the glyph reaches the same height. A curved extension must not be treated as a matching straight closing segment merely because their vertical extents are similar.

The closing upright can be a main upright, a middle leg, or a middle arm. Section 8 defines the middle-component cases.

### 5.2 Upward-reaching bowl: examples

| Actual geometry | Canonical name |
|---|---|
| Hooked left body; short right upright; upper return remains open | `long open bowl with stem` |
| Same body; right upright reaches ascender height and closes it | `long bowl with stem` |
| Closed form; right upright also has a straight descender | `long bowl with descender` |
| Closed form; right upright also has a lower tail | `long bowl with tail` |

The second row is the tall single-storey-a-like form. Its right upright physically ascends, but that ascent is already required by `long bowl`.

### 5.3 Downward-reaching bowl: examples

| Actual geometry | Canonical name |
|---|---|
| Short left upright; tailed right body; lower return remains open | `stem with long open bowl` |
| Left upright descends far enough to close the lower return | `stem with long bowl` |
| Closed form; left upright also has a straight ascender | `ascender with long bowl` |
| Closed form; left upright also has an upper hook | `hook with long bowl` |

Thus the eng-like form is `stem with long open bowl`, and its turned counterpart is `long open bowl with stem`.

These names also preserve the curved-extension version of the earlier n/u distinction:

| Construction | Canonical name |
|---|---|
| Upper-joined hooked left upright and tailed right branch | `hook with long open bowl` |
| Lower-joined hooked left branch and tailed right upright | `long open bowl with tail` |

### 5.4 Bowl-specific modifier

Do not propagate `open` to every component category. In particular, spines have no open/closed naming state. Keep the existing attachment semantics of `spine` and `long spine`; do not decompose them into bowls to manufacture additional opening qualifiers.

The same bowl modifier ordering can describe an ordinary open bowl if such a form already exists in the inventory. This specification does not require adding one or any other new glyph.

## 6. Omit extensions entailed by closure

### 6.1 General rule

> Omit a straight extension from a component's printed name when that extension is already entailed by an adjacent closed bowl.

Keep the actual geometry unchanged. Only the redundant naming information is omitted.

A closed upward-reaching long bowl entails the relevant upper reach of its closing upright. A closed downward-reaching long bowl entails the relevant lower reach. An open bowl does not entail the missing closure extension.

Name all remaining independently specified extensions normally. Never erase a curved feature merely because a bowl requires a stroke to reach the same region.

### 6.2 Canonical reductions

These describe semantic normalization of a known construction, not blind string replacements:

| Redundantly explicit description | Canonical name |
|---|---|
| `long bowl with ascender` | `long bowl with stem` |
| `long bowl with long stem` | `long bowl with descender` |
| `long bowl with long tail` | `long bowl with tail` |
| `descender with long bowl` | `stem with long bowl` |
| `long stem with long bowl` | `ascender with long bowl` |
| `long hook with long bowl` | `hook with long bowl` |

If more than one valid adjacent body supplies requirements for an upright, collect the requirements before choosing its printed primitive name. Do not mutate its full extension data while processing the first neighbor.

### 6.3 Required evaluation order

First determine whether the bowl actually closes against the full neighboring geometry. Only then record the extension implied by that closed bowl and omit it from the printed upright name.

Do not shorten the upright first and then recompute closure from the shortened label. For example, the word `stem` in `long bowl with stem` is not evidence that the bowl is open.

## 7. Middle legs, middle arms, and m-like forms

A `middle leg` is the intermediate leg in an m-like upper-joined construction. A `middle arm` is its counterpart in a turned-m-like lower-joined construction.

The expanded component sequences are:

| Form | Expanded name |
|---|---|
| m | `stem with middle leg and leg` |
| Turned m | `arm with middle arm and stem` |

`middle` describes the component's role in this branch chain. It does not mean that every component geometrically between two others should be given a middle modifier. In particular, a spine between two stems remains `spine`.

An intermediate component remains a middle leg or middle arm when the outer component is a bowl, shoulder, hip, or other valid terminal body rather than a matching terminal leg or arm. For example, the existing m-like shoulder-ended construction is described as `stem with middle leg and shoulder`.

Middle components can be long. Before any bowl-derived omission or count abbreviation:

| Geometry | Name |
|---|---|
| Long middle leg, ordinary final leg | `stem with long middle leg and leg` |
| Ordinary middle leg, long final leg | `stem with middle leg and long leg` |
| Ordinary first arm, long middle arm | `arm with long middle arm and stem` |
| Long first arm, ordinary middle arm | `long arm with middle arm and stem` |

Do not substitute the main upright's extension for the middle component's extension. Store and inspect them separately.

## 8. Bowl closure next to a middle component

### 8.1 Local-neighbor rule

For an m-like form ending in a downward-reaching long bowl, the closing neighbor is the immediately preceding middle leg. The far-left main upright does not determine closure.

For a turned-m-like form beginning with an upward-reaching long bowl, the closing neighbor is the immediately following middle arm. The far-right main upright does not determine closure.

The relevant middle component may physically be long. Apply the same closure-derived omission rule as for any other upright: if its straight extension is already supplied by the closed bowl, the canonical name need not repeat `long` on the middle component.

### 8.2 Downward-reaching final bowl

| Main upright | Middle leg in the actual geometry | Bowl state | Canonical name |
|---|---|---|---|
| Short stem | Ordinary | Open | `stem with middle leg and long open bowl` |
| Descender | Ordinary | Open | `descender with middle leg and long open bowl` |
| Short stem | Long, closing the return | Closed | `stem with middle leg and long bowl` |
| Descender | Long, closing the return | Closed | `descender with middle leg and long bowl` |

In the closed rows, the middle leg really does descend. The absence of `long` before `middle leg` is deliberate: the closed long bowl already entails that descent.

Accordingly, the redundant description `stem with long middle leg and long bowl` canonicalizes to `stem with middle leg and long bowl`.

### 8.3 Upward-reaching initial bowl

| Middle arm in the actual geometry | Main right upright | Bowl state | Canonical name |
|---|---|---|---|
| Ordinary | Short stem | Open | `long open bowl with middle arm and stem` |
| Ordinary | Ascender | Open | `long open bowl with middle arm and ascender` |
| Long, closing the return | Short stem | Closed | `long bowl with middle arm and stem` |
| Long, closing the return | Ascender | Closed | `long bowl with middle arm and ascender` |

The redundant description `long bowl with long middle arm and stem` canonicalizes to `long bowl with middle arm and stem`.

### 8.4 Critical regression requirement

With the relevant middle component held fixed, changing only the distant main upright must not change the bowl's open/closed classification. Conversely, changing the middle component so that the return closes must change `long open bowl` to `long bowl`, even when the main upright is unchanged.

## 9. Count abbreviations

After component naming and closure-derived omission, perform these exact role-aware collapses:

| Adjacent semantic terms, in order | Canonical abbreviation |
|---|---|
| `middle leg`, `leg` | `two legs` |
| `long middle leg`, `long leg` | `two long legs` |
| `arm`, `middle arm` | `two arms` |
| `long arm`, `long middle arm` | `two long arms` |

These are adjacent component pairs, not literal substring replacements. Their separator in an expanded name depends on their position: the leg pair in `stem with middle leg and leg` uses `and`, while the arm pair in `arm with middle arm and stem` uses `with`. Collapse the semantic terms first, then format the entire final sequence using Section 2.

Examples:

| Expanded name | Canonical name |
|---|---|
| `stem with middle leg and leg` | `stem with two legs` |
| `ascender with middle leg and leg` | `ascender with two legs` |
| `stem with long middle leg and long leg` | `stem with two long legs` |
| `arm with middle arm and stem` | `two arms with stem` |
| `long arm with long middle arm and stem` | `two long arms with stem` |

`two legs` means two leg components in addition to the preceding main upright. It does not mean that the entire glyph has only two uprights. The corresponding rule applies to `two arms`.

Do not collapse mixed-length pairs. Do not collapse across intervening bodies. Do not replace a middle component plus a bowl with a count phrase. Do not collapse two middle components as though one were the terminal component.

These four pair rules are the required count abbreviations. They do not require inventing larger glyphs or a general number-word subsystem. Any longer constructions already in the inventory can retain explicit component sequences outside these exact collapses unless the project already has a specified compatible counting convention.

## 10. Spines with one or two attachments

Spines participate in the same left-to-right serialization without requiring a privileged main stem:

| Construction | Canonical name |
|---|---|
| Spine, right stem | `spine with stem` |
| Left stem, spine | `stem with spine` |
| Left stem, spine, right stem | `stem with spine and stem` |
| Left ascender, spine, right descender | `ascender with spine and descender` |
| Left stem, long spine, right stem | `stem with long spine and stem` |

Use the actual valid spine construction from the project for each example. Each attachment retains its own independently specified features under that constructor's semantics.

Do not reorder the two-sided form into `spine with two stems`; that was a different, body-first naming scheme. Do not count-collapse the stems across the spine. Do not add `open`, `closed`, `left-open`, or `right-open` to either spine token.

## 11. Implementation contract

### 11.1 Structural input

Adapt the existing project model rather than requiring a new geometry architecture. The naming logic needs access to:

1. The semantic components in left-to-right order, including leg/arm and middle-component roles.
2. Their full upper and lower extensions before naming omissions.
3. Bowl family and length, the exact closing-neighbor reference, and the constructor's actual return-contact information.

Keep spine components distinct from bowls. Opening should be a bowl-specific concept, not a generic modifier applied indiscriminately to every body.

Do not discover the closing neighbor by looking for the first, last, tallest, or longest upright. Use explicit structural adjacency. In an m-like chain, that reference must point to the middle component when appropriate.

### 11.2 Naming pipeline

```text
canonicalName(glyph):
    parts = getSemanticPartsInLeftToRightOrder(glyph)
    fullGeometry = retainOriginalComponentGeometry(parts)

    bowlStates = evaluateBowlReturnsAgainstActualNeighbors(
        parts, fullGeometry
    )

    impliedExtensions = collectExtensionsEntailedByClosedBowls(
        parts, bowlStates
    )

    namingParts = nameComponents(
        parts,
        fullGeometry,
        bowlStates,
        impliedExtensions
    )

    namingParts = collapseMatchingLegAndArmPairs(namingParts)
    return formatParts(namingParts)

formatParts(parts):
    if length(parts) == 0:
        fail("Cannot name an empty construction")
    if length(parts) == 1:
        return parts[0]
    return parts[0] + " with " + join(parts[1:], " and ")
```

`nameComponents` omits only the redundant straight extensions specified in Section 6. It must not change geometry, recalculate opening from abbreviated labels, erase middle roles, or discard a curved extension.

Use semantic component records for normalization. Do not implement the rules as unrestricted regular-expression replacements on already formatted names.

The function must be deterministic and free of geometry mutation. Equivalent structural representations should produce the same canonical name. Serif details, stroke contrast, weight, and other stylistic differences do not participate in the name.

### 11.3 Project integration

Preserve stable glyph IDs, code points, and outlines. Update the canonical-name provider and any dependent display labels, exports, snapshots, and tests consistently. If the project currently uses names as identifiers, update the affected references explicitly rather than silently treating renamed glyphs as new glyphs.

A name parser is not required solely for this task. If one already exists, update its separator handling, count expansions, and closure-implied extensions so that it reconstructs the same ordered structure. The canonical serializer emits only the format in Section 2. If existing compatibility requirements retain repeated-`with` input as a legacy alias, normalize it to the new format on output rather than treating it as another canonical name.

## 12. Acceptance tests

Turn the example tables into tests against structural fixtures, not against whichever font happens to render a sample letter.

Required coverage:

- All nine primitive names; ordinary `spine` and `bowl`; the base-letter examples in Section 4.
- Distinct names for the upper-joined and lower-joined ascender/descender pair, and for the corresponding hook/tail pair.
- The four upward-bowl and four downward-bowl examples, including omission of the already required extension.
- Ordinary and long middle legs/arms, all four count collapses, and mixed-length pairs that must not collapse.
- Every middle-component closure row in Section 8, especially the cases where the distant main upright is long but the middle component is not.
- One-sided and two-sided spine forms with no opening qualifiers.
- Separator formatting for one, two, three, and (where supported) more final terms; ensure count abbreviations occur before formatting.

Required formatter unit tests (these test term serialization, not the validity of hypothetical glyphs):

| Final ordered terms | Expected output |
|---|---|
| [`stem`] | `stem` |
| [`stem`, `leg`] | `stem with leg` |
| [`stem`, `middle leg`, `long open bowl`] | `stem with middle leg and long open bowl` |
| [`stem`, `spine`, `stem`] | `stem with spine and stem` |
| [`two arms`, `stem`] | `two arms with stem` |
| [`A`, `B`, `C`, `D`] (placeholder terms) | `A with B and C and D` |

An empty term sequence is an error, not an empty canonical name.

Also enforce these properties:

**Locality:** Changing a nonadjacent main upright cannot change whether a long bowl closes against its middle neighbor.

**Information preservation:** A physically long middle component omitted from the printed name must remain recoverable from the adjacent closed bowl's requirements. The underlying geometry must remain long.

**Stable normalization:** Equivalent redundant and abbreviated descriptions resolve to the same name when such descriptions are accepted by the existing model or parser.

**Injectivity within the inventory:** Structurally distinct valid glyphs must not receive the same canonical name. Compare structural identities, not outline bytes; stylistic renderings of one structure may share a name. Report a collision as a naming error rather than hiding it with an arbitrary numeric suffix.

**Canonical separators:** After normalization and count abbreviation, a one-term name has no construction separator. A name of two or more terms contains exactly one ` with `, immediately after its first term, and ` and ` between all remaining terms. Do not repeat `with`, use commas, or reorder terms. Changing separators must not change bowl closure, adjacency, or count normalization.

**Vocabulary restrictions:** Never emit `open spine`, `long open spine`, `tailed leg`, or `hooked arm` as canonical component names under this specification. Never use the ambiguous bare pair `ascender with descender` for the two n/u constructions in Section 4.

**No scope expansion:** The naming implementation must not add hypothetical glyphs, change attachment geometry to make a label fit, or introduce new component categories merely to avoid reporting unsupported input.

## 13. Most important implementation rule

> Determine a long bowl's opening from its actual adjacent closing upright. In an m-like or turned-m-like form, that upright is the middle leg or middle arm, not the distant main stem. Evaluate this before omitting closure-implied extensions and before collapsing repeated legs or arms.


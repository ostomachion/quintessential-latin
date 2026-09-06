# Independent native-donor audit

Date: 2026-09-06. This read-only audit compared the editable bitmap drawings before the tail revision with pinned GNU Unifont 17.0.05 donors and the verified full upstream HEX archive. Coordinates below are zero-based within the 8 by 16 cell. This records construction evidence and preservation decisions, not user visual approval.

## Required corrections

- `tail` (U+F2A09) was not the native dotless j. Its head and upright used x=4, while U+0237 uses x=5. The former bitmap was `00000000000018080808080808084830`; native U+0237 is `0000000000000C040404040404044830`. Use U+0237 exactly. Carry its x=5 upright into `ascender-tail` and `hook-tail`, with the corresponding translated native l head or f hook. Preserve the other single-stem primitives.
- Native script g U+0261 is `0000000000003A46424242463A02423C`. Its bowl returns at row 12, followed by the right upright at row 13, both outer columns at row 14, and the inner return at row 15. This is the direct model for `turned-bowl-tail` (U+F2A20) and its related bowl-tail contexts. Appending the old three-pixel eng return to the full-height alpha body does not reproduce this precedent.
- Native y U+0079 is `0000000000004242424242261A02023C`. It provides the direct arm-with-tail model for `turned-arch-tail` (U+F2A2C): the lower join is at rows 11–12 (`26 1A`), with right upright rows 13–14 and a broad tipless return at row 15. Apply the same lower-arch convention to its structural relatives.

## Long lower bowls require a contextual exception

Keep the tipless return beneath an upper arch when its long lower bowl must remain open until the declared immediate straight neighbor extends. For example, `arch-right-tail` (U+F2A3C) already has the native y tail trajectory: right upright at rows 13–14 and columns 2–5 at row 15. Its short left arch stem ends at (1,13). Adding script g's free return pixel at (1,14) would close this long bowl prematurely; only the declared neighbor's descender is supposed to add that contact. This is a structural reason for preserving that context, not an arbitrary tail variant. Shared-spine bowl tails retain the native g tip, adapted to their bay width. Where the shortened bowl leaves an adjacent middle leg ending at row 12, that leg's straight extension explicitly adds its row-13 bridge along with rows 14–15; the short state preserves the opening.

## Unaffected donor drawings verified exactly

All 15 existing `design.json` exact-donor mappings matched all 128 donor pixels:

| Construction | Native donor |
| --- | --- |
| `special-ring` | o U+006F |
| `stem` | dotless i U+0131 |
| `ascender` | l U+006C |
| `special-open-bowl`, `special-turned-open-bowl` | c U+0063, open o U+0254 |
| `special-double-open-bowl`, `special-turned-double-open-bowl` | open e U+025B, reversed open e U+025C |
| `arm`, `turned-arm` | r U+0072, turned r U+0279 |
| `arch`, `turned-arch` | n U+006E, u U+0075 |
| `turned-bowl` | alpha U+0251 |
| `special-spine` | s U+0073 |
| `bowled-spine`, `turned-bowled-spine` | turned a U+0250, a U+0061 |

Five further complete drawings also matched native donors exactly: `double-arch`/m U+006D, `turned-double-arch`/turned m U+026F, `bowl-ascender`/b U+0062, `bowl-descender`/p U+0070, and `arch-ascender`/h U+0068.

The unextended left-stave `bowl` preserves every native b/p body pixel, without either extension. Closed double bowls combine the native epsilon and reversed-epsilon lobes. Shared spines deliberately combine a and turned-a connections, and repeated bodies use native m/turned-m shoulders or hips. These are structural combinations with no single exact upstream character; there is no evidence here that their body geometry should change for the tail correction.

## Other differences and narrow preservation decisions

`turned-bowl-ascender` and `turned-bowl-descender` differ from native d/q at (5,11), (4,12), (5,12), and (4,13). They intentionally retain the exact alpha lower return of their unextended `turned-bowl` base. Changing these non-tail bodies would replace an established paired-body choice, so preserve them.

There is one additional upper-hook inconsistency: 168 compact shared-spine drawings use the previously approved rounded hook with (2,3), (1,4), and (3,4), while ordinary joined hooks and the later double-middle shared-spine constructions use the translated native f hook with (2,3), (3,3), and (1,4). Both occupy the same three-column width, so compression does not require the difference. The user's request to audit unnecessary drift supports correcting these affected hooks to the existing native-f convention: add (3,3), remove the free hook pixel (3,4), and preserve the upright at (1,4) and (1,5). Retain any independently required component pixel rather than clearing it as a hook tip. This small related correction changes no body or unrelated ordinary hook.

Preserve unaffected bitmap pixels, non-tail donors, ordinary upper hooks, body counters, independent middle-extension order, and the declared long-bowl closure relationship. Do not copy script g's full return into a context where it would close an intentionally open bowl or create an unrelated terminal pocket.

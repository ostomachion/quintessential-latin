# Tails below hips

U+F2A14 **HIP WITH TAIL** and U+F2A17 **HIP WITH LONG TAIL** use the
same broad STIX Two single-story-g tail as the bowl and arch constructions.
The change covers Roman and native Italic, throughout weights 400–700.
The native hip, upper terminal, character identity and advance remain fixed.
Kerning for pairs involving these two characters accommodates the broader
leftward sweep; unrelated pairs retain their previous spacing.

These are the two forms with a tail immediately below a hip. The twelve
hip-containing forms with intervening middle arms already use the broad tail
of their final arch, and retain their existing outlines.

The editable authority remains the four UFO masters. Reconstruct this focused
revision with `python tools/refine_hip_tails.py`, or verify it without writing
with `--check`. `tools/import_stix_foundation.py` contains the donor splice;
it retains the complete lower sweep without scaling it. Historical recipe
names `uF2A13` and `uF2A14` are internal names, not current code points.

## Proofs and verification

The compiled [Roman](images/hip-tails/roman.png) and
[Italic](images/hip-tails/italic.png) sheets compare both characters before and
after, alongside unchanged arch and bowl references, at five weights and two
sizes. Their [manifest](images/hip-tails/manifest.json) binds the font bytes.

`tools/test_hip_tails.py` checks the scoped revision, preservation of the rest
of the repertoire, native-tail geometry, and actual filled-outline collisions
for every ordered pair involving either revised character. Older preservation
checks use the pinned hip-tail revision record to recognize these changes.

## Unifont

No pixel changes are needed. U+F2A14 and U+F2A17 already share the native-y
tail with the corresponding arm form, including the full four-pixel bottom
return. The four one-middle and eight two-middle variants likewise match
the corresponding arm and bowl tails within the same final component width.
All fourteen were compared at enlarged, 1× and 2× sizes.

The [pixel comparison](../resources/verification/hip-tails/unifont.png) and
[checks](../resources/verification/hip-tails/unifont-checks.json) record that
review. Font engineering checks and agent visual review do not imply author
aesthetic acceptance or publication.

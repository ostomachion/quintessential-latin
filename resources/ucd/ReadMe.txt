Quintessential Latin 0.250; draft private-use agreement, not a registration.

This is the project's proposed UCD-style subset for UCSUR review and explicit
private-use agreements. It is not an official Unicode Character Database, a
complete copy of UCSUR's database, or evidence of submission or registration.
Format references were checked on 2026-09-06; Unicode 17.0.0 is the format
baseline, not a character Age or a claim of Unicode encoding.

Repertoire
==========
U+F2A00..U+F2ABF  Quintessential Latin  (192)
U+F2AC0..U+F2BBF  Quintessential Latin Extended-A  (256)
U+F2BC0..U+F2EBF  Quintessential Latin Extended-B  (768)
All 1216 positions are assigned in allocation 0.250, naming version 3.
Earlier numeric assignments were replaced without compatibility aliases.
The files use numeric order, exact canonical names, UTF-8 without a BOM, and LF.
Author: Josh Hufford
Project: https://github.com/ostomachion/quintessential-latin
Website: https://ostomachion.github.io/quintessential-latin/

Files
=====
Blocks.txt       Three proposed block ranges and titles, in UCD range syntax.
UnicodeData.txt  1216 records, exactly 15 semicolon-separated fields each.
NamesList.txt    All names with UCSUR/Unicode block and construction headings.
CaseFolding.txt  Intentionally no mappings: every lowercase letter folds to itself.
Charts.txt       UCSUR-specific font and character mapping directives.
Sources.txt      UCSUR-style key/value bibliography, with project sources.
manifest.json    Source and output SHA-256 hashes, byte counts and scope.

Property policy
===============
UnicodeData.txt proposes General_Category=Ll (Lowercase_Letter) for the complete
repertoire, including stemless forms. This is an OPT-IN project interpretation
for registry review and cooperating applications. In the Unicode Standard these
code points remain General_Category=Co (Private_Use), have no assigned names,
and belong to Supplementary Private Use Area-A, not these three proposed blocks.
Installing a font or copying these files does not change runtime Unicode data.

The characters are lowercase even though no uppercase/titlecase counterparts
are defined. Their names use QUINTESSENTIAL LATIN SMALL LETTER followed by the
canonical construction name. This identifies their case independently of any
future capital letters; it does not allocate or invent capital counterparts.

Each UnicodeData record has:
  0: Code point                 Current supplementary private-use scalar
  1: Name                       Canonical structural name
  2: General_Category           Ll (proposed private-use interpretation)
  3: Canonical_Combining_Class  0
  4: Bidi_Class                 L (horizontal left-to-right spacing text)
  5: Decomposition_Mapping     empty
  6-8: Numeric values          empty (no digits or numeric system specified)
  9: Bidi_Mirrored             N
  10-11: Legacy fields         empty (no Unicode 1 name or ISO comment)
  12-14: Simple case mappings  empty (identity; no case counterparts defined)

Opposite-facing constructions are separate characters; their visual relation
does not establish bidi mirroring, case pairs, or decomposition mappings.
Roman, Italic and font weights use the same character codes. A construction
name's components are not combining-character or normalization decompositions.
CCC=0 and the absence of decompositions preserve Unicode's immutable PUA
normalization behavior; NFC, NFD, NFKC and NFKD leave these characters unchanged.
CaseFolding's omitted records mean identity, not deletion or missing data.
Empty simple case-mapping fields likewise mean identity; they do not mean the
characters are uncased. Consumers following UAX #44 derivations from Ll should
treat them as Lowercase=Yes and Cased=Yes, with no change under case conversion
or folding. Cased and Changes_When_Casemapped are distinct properties.

Integration
===========
Treat this as a scoped overlay requiring explicit agreement. Do not replace a
full Unicode/UCSUR data file with this subset, or simply append the named Ll
records to UnicodeData's enclosing PUA First/Last range. A consumer must split
or override containing ranges deliberately and retain behavior outside these
three blocks. This package supplies no global @missing defaults.

UnicodeData.txt and Charts.txt have no comment preamble for legacy readers.
Read this file with them. The existing resources/NamesList.txt and website
data/names-list.txt remain a flat names-only export for existing consumers;
this directory's NamesList.txt adds block and family headings.

For Charts.txt install the supplied Roman Regular static OTF (family name
Quintessential Serif). Each CODE;character record maps to the identical scalar
in that font. Supplementary characters require intact surrogate pairs in
UTF-16. The 18pt font directive is a starting chart setting; registry chart
pagination and layout remain subject to the registry's own production tools.
These directives do not rebuild or alter the project's published PDF charts.

Files deliberately omitted
=========================
Scripts/ScriptExtensions: no registered script identifier or agreed Script
tailoring is specified; a Latin-derived drawing alone does not settle it.
NameAliases/NamedSequences/StandardizedVariants: no aliases, separately encoded
sequences or variation-selector sequences have been established.
SpecialCasing/BidiMirroring/BidiBrackets: no applicable mappings are proposed.
DerivedAge: a project version/date is not a Unicode character Age.
Break, identifier, collation and other derived files: the proposal specifies
no such tailorings; mechanically copying every Unicode default adds no agreed
behavior. Consumers opting into Ll must apply its lowercase/cased derivations
and decide the remaining derived-property policy
consistently, rather than assuming this package is a complete tailored UCD.

Regeneration and verification (from repository root)
===================================================
  npm run build:ucd
  node tools/export_ucd.js --check
  npm run test:ucd

The allocation and proposal are authoritative; tools/export_ucd.js records
the reviewed property policy. Generated files must be committed together.
The manifest binds those sources, canonical naming code, this exporter and
all seven text files. It intentionally omits volatile generation timestamps.
Normal site builds check freshness before copying these files to data/ucd/.

Sources and licensing
=====================
Sources.txt records project and format references. The project review notes
are at https://github.com/ostomachion/quintessential-latin/blob/main/docs/ucd-research.md.
The six data formats follow UCSUR's published UNIDATA directory; Charts.txt
and Sources.txt are UCSUR conventions rather than Unicode UCD property files.
Original project data and documentation use the repository's MIT license:
https://github.com/ostomachion/quintessential-latin/blob/main/LICENSE
No Unicode or UCSUR character dataset is copied into this package. Reference
font software retains its separate SIL Open Font License and attribution.

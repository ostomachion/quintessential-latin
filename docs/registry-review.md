# Registry review and proposal evidence

Checked **6 September 2026** for allocation and font version **0.250**, canonical
naming version **3**. This records the evidence behind the editorial proposal;
it does not record a submission, a reservation, or contact with a maintainer.
The public proposal text is maintained once in [proposal.json](proposal.json)
and rendered into the website and standalone PDF.

## Which sources control which facts

| Subject | Authority and interpretation |
| --- | --- |
| Motivation and intended use | The author's instructions for this revision: a deliberate abstraction from familiar Latin forms into components and consistent constructions; a language-neutral repertoire with an underlying single-stroke principle. |
| Inventory, identities, assignments, families | [Explicit allocation](../resources/quintessential-latin-allocation.json): `entries`, `glyphId`, `codePoint`, `glyphName`, ordered `parts`, `blocks`, and `displayOrder`. Historical IDs and recipe fields are not current display names. |
| Canonical names | [Naming algorithm](../tools/canonical_glyph_names.js), [version 3 specification](quintessential-latin-canonical-naming-spec-v3.md), and [naming tests](../tools/test_canonical_glyph_names.js). The `nameParts(parts)` function is authoritative; its full-name prefix is `QUINTESSENTIAL LATIN SMALL LETTER`. |
| Public catalogue | [Catalogue exporter](../tools/export_glyph_catalogue.js) and its generated [catalogue](../resources/catalogue.json), [plain names list](../resources/NamesList.txt), and [Markdown names list](../resources/quintessential-latin-name-catalogue.md). No second inventory was introduced for this revision. |
| Font designs and available mappings | Editable UFO/designspace sources under `fonts/QuintessentialSerif/`; actual compiled fonts, [build manifest](../resources/fonts/QuintessentialSerif/build-manifest.json), and [coverage export](../resources/font-coverage.json). A successful mapping/coverage check is not a handwriting-path proof or aesthetic acceptance. |
| Bitmap implementation | [Drawing sources and notes](../resources/unifont/README.md), generated `glyphs.json` and HEX, and the [installable font manifest](../resources/fonts/QuintessentialUnifont/manifest.json). The bitmap implementation renders the same identities; it is not an additional repertoire. |
| Text-property agreement | [UCD exporter](../tools/export_ucd.js), [package notes](../resources/ucd/ReadMe.txt), and [format research](ucd-research.md). Proposed property values belong to the explicit agreement, not automatically to Unicode or operating systems. |
| Revisions | [Logical allocation](logical-allocation.md), [independent middle extensions](independent-middle-extensions.md), and the proposal's preserved revision history. Allocation 0.250 replaced older numeric assignments without compatibility aliases. |
| Licensing | [Project license](../LICENSE), [third-party notices](../THIRD_PARTY_NOTICES.md), and the individual Serif, Unifont, donor, and Source Sans font license files. |

The current allocation has 1,216 entries in 30 families, covering every position
from U+F2A00 through U+F2EBF. Block counts computed from entries are 192, 256,
and 768. There are seven stemless forms. The implementation and tests establish
the finite inventory and its component rules; they do not establish an exhaustive
enumeration of all imaginable combinations. The single-stroke principle is
authorial design intent, distinguished from a complete normative handwriting
standard and from filled font outlines.

## Primary registry sources checked

Every external page listed below was fetched successfully during this review.
The check date is the date of observation, not a claimed update date for the
source page. The original CSUR pages contain historical text and dates.

| Primary source | Observation and scope |
| --- | --- |
| [UCSUR allocation table](https://www.kreativekorp.com/ucsur/) | Five rows, U+F2A00–U+F2AFF through U+F2E00–U+F2EFF, were marked unassigned. The proposed interval fits within them. The table separately labels proposals, reservations, and registrations. |
| [Linked UCSUR roadmap](https://www.kreativekorp.com/ucsur/roadmap.shtml) | Rows F2A through F2E showed question marks. Read alongside the explicit table; neither page grants this project a reservation. |
| [Original CSUR introduction](https://www.evertype.com/standards/csur/) | Historical guidance describes preliminary comment and final registration, directs authors to existing documents, and says final registrations stay stable while allowing enlargement. It does not verify present UCSUR administrative procedure. |
| [CSUR naming guidance](https://www.evertype.com/standards/csur/naming.html) | Requires unique names restricted to uppercase English letters, spaces, and hyphen-minus; describes script and character-type prefixes. For letters it prefers traditional names or romanizations. Structural names therefore need an explained rationale, rather than a blanket compliance claim. |
| [Unicode private-use FAQ](https://www.unicode.org/faq/private_use.html) | Published private agreements and matching fonts are possible without standardization; conflicting interpretations and ordinary application behavior remain relevant. |
| [Unicode 17.0, section 23.5](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-23/) | Confirms agreement-specific property overrides while preserving normative private-use normalization constraints. Section 23.6 explains surrogate pairs. |
| [Seussian Latin Extensions](https://www.evertype.com/standards/csur/seuss.html) | Explicitly registered 1997-01-21, with later revisions. This is a Latin-extension precedent based on literary letters, not proof of eligibility for a language-neutral structural repertoire. |
| [Sitelen Pona Radicals](https://www.kreativekorp.com/ucsur/charts/sp-radicals.html) | Explicitly a proposal dated 2024-04-11, for recurring graphical components of Sitelen Pona. It supports discussion of component analysis; it does not establish registration or a general eligibility rule. |
| [UCSUR UNIDATA directory](https://www.kreativekorp.com/ucsur/UNIDATA/) | Publishes the six file formats mirrored by the existing project package. Observed publishing practice is not a mandatory submission checklist. |

The [STIX source release](https://github.com/stipub/stixfonts/releases/tag/v2.13b171)
and [official OFL 1.1 text](https://openfontlicense.org/open-font-license-official-text/)
were also fetched. Project-specific provenance and licensing statements come
from the pinned manifests and distributed notices, rather than assumptions
about all files sharing the repository's MIT license.

## Implementation facts checked directly

Read-only inspection with FontTools opened all 12 supplied Quintessential Serif
files and both supplied Quintessential Latin Unifont files. Every binary has
all 1,216 current private-use assignments and a positive advance for each.
Every Serif cmap entry matches the allocation's internal `glyphName`. All
font versions are 0.250. The four variable Serif files advertise the `wght`
axis from 400 to 700; separate Roman and Italic sources and binaries provide
the native postures. The static faces are OTF and WOFF2, not static TTF.

Serif has 1,217 cmap entries: the repertoire plus U+0020 SPACE. Both Unifont
files have 1,430: the repertoire plus 214 native companion characters. This
exposed an old 1,429 total in the Unifont README, which needed correction.
Unifont includes EBDT and EBLC bitmap tables; its source manifest and build
documentation specify an exact monochrome 16-ppem strike and square outlines.
No supplied font has a GSUB table. Serif uses GPOS pair positioning; Unifont
has no GPOS table. Component sequences therefore have no supplied automatic
ligature mechanism. These checks did not rebuild or alter fonts.

The catalogue exporter in check mode verified names, assignments, posture
coverage, font hashes, and freshness of the existing public exports. All
20 canonical naming tests passed, including uniqueness, nonmutation, local
bowl closure, connection roles, and independent middle-extension states.
Additional site, browser, and publication rendering checks belong in the
implementation report; this research note does not claim those checks ran
as part of this read-only source audit.

The proposal's examples store only stable IDs. Renderers resolve their names,
code points, and glyphs from the current catalogue. The identity examples
compare bowl orientation, upper versus lower connections, and actual adjacent
long-bowl closure. The middle-extension quartet uses the existing triple-arch
family. No outlines, component records, names, or assignments were changed to
make an example fit.

## Interpretation and unresolved decisions

The following are project review questions, not unpublished registry rules:

- Whether a shared structural repertoire without one assigned language is an
  appropriate registration unit, and what concrete intended text uses would
  make that scope clearest.
- How recognizable counterparts should be treated after a systematic identity
  comparison with standardized Latin and registered forms. Some supplied
  bitmap glyphs intentionally copy native Latin drawings exactly. Appearance
  alone establishes neither distinct character identity nor automatic unification.
- Whether the complete structural naming approach and lowercase interpretation
  are suitable. Syntax and repertoire-wide uniqueness can be checked locally;
  acceptance of the naming rationale cannot.
- What stable assignment and identity-based migration policy should accompany
  eventual submission, given the recorded 0.250 reassignment history.

No minimum user count, publication requirement, waiting period, mandatory font
format, or current submission procedure was established by the checked sources.
The draft does not invent those requirements. Detailed handwriting conventions,
linguistic values, and orthographic punctuation or numeral choices remain
separate from the current proposal. No submission, maintainer contact, release,
or external project-setting change was performed.

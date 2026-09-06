#!/usr/bin/env node
"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { nameParts } = require("./canonical_glyph_names.js");

const ROOT = path.resolve(__dirname, "..");
const UCD_SOURCE_PATHS = Object.freeze([
  "resources/quintessential-latin-allocation.json",
  "docs/proposal.json",
  "tools/canonical_glyph_names.js",
  "tools/export_ucd.js"
]);
const UCD_FILES = Object.freeze([
  "Blocks.txt", "UnicodeData.txt", "NamesList.txt", "CaseFolding.txt",
  "Charts.txt", "Sources.txt", "ReadMe.txt", "manifest.json"
]);
const hex = value => value.toString(16).toUpperCase();
const sha256 = bytes => crypto.createHash("sha256").update(bytes).digest("hex");
const repo = "https://github.com/ostomachion/quintessential-latin";
const site = "https://ostomachion.github.io/quintessential-latin/";
const formatDate = "2026-09-06";

function validateAllocation(allocation, proposal) {
  // The property policy is reviewed for this repertoire, not inferred from names
  // for arbitrary future additions such as punctuation, numbers or capital letters.
  if (allocation.version !== "0.250" || allocation.namingVersion !== 3 || proposal.version !== allocation.version)
    throw new Error("Review the UCD property policy for the new allocation/proposal version.");
  const entries = [...allocation.entries].sort((a, b) => a.codePoint - b.codePoint);
  const blocks = [...allocation.blocks].sort((a, b) => a.start - b.start);
  const families = new Map(allocation.families.map(family => [family.id, family.title]));
  const names = new Set(), codes = new Set(), identities = new Set();
  if (entries.length !== 1216 || blocks.length !== 3) throw new Error("Unexpected UCD repertoire size.");
  for (const entry of entries) {
    if (!Number.isInteger(entry.codePoint) || entry.codePoint < 0xF0000 || entry.codePoint > 0xFFFFD)
      throw new Error("UCD assignments must be Supplementary Private Use Area-A scalars.");
    const canonicalName = nameParts(entry.parts);
    if (entry.canonicalName !== canonicalName || entry.name !== "QUINTESSENTIAL LATIN SMALL LETTER " + canonicalName.toUpperCase())
      throw new Error("Stale canonical UCD name: " + entry.glyphId);
    if (!/^[A-Z0-9 -]+$/.test(entry.name) || names.has(entry.name) || codes.has(entry.codePoint) || identities.has(entry.glyphId))
      throw new Error("Invalid or duplicate UCD identity: " + entry.glyphId);
    if (!families.has(entry.familyId)) throw new Error("Missing UCD family: " + entry.familyId);
    names.add(entry.name); codes.add(entry.codePoint); identities.add(entry.glyphId);
  }
  for (const [index, block] of blocks.entries()) {
    if (!Number.isInteger(block.start) || !Number.isInteger(block.end) || block.start > block.end ||
        block.start % 16 || (block.end + 1) % 16 || !/^[A-Za-z0-9 -]+$/.test(block.title) ||
        (index && blocks[index - 1].end >= block.start)) throw new Error("Invalid UCD block: " + block.title);
    const assigned = entries.filter(entry => entry.blockId === block.id);
    if (assigned.length !== block.end - block.start + 1 || assigned.some((entry, offset) => entry.codePoint !== block.start + offset))
      throw new Error("UCD block coverage mismatch: " + block.title);
  }
  if (blocks.reduce((sum, block) => sum + block.end - block.start + 1, 0) !== entries.length ||
      entries.some((entry, index) => allocation.displayOrder[index] !== entry.glyphId) ||
      allocation.displayOrder.length !== entries.length) throw new Error("UCD allocation order mismatch.");
  return { entries, blocks, families };
}

function renderFiles(allocation, proposal) {
  const { entries, blocks, families } = validateAllocation(allocation, proposal);
  const status = `Quintessential Latin ${allocation.version}; draft private-use agreement, not a registration.`;
  const header = block => `@@\t${hex(block.start)}\t${block.title}\t${hex(block.end)}`;
  const inBlock = block => entries.filter(entry => entry.blockId === block.id);
  const files = {};
  files["Blocks.txt"] = `# ${status}\n# Proposed block overlay; not the Unicode Block property. See ReadMe.txt.\n# Start..End; Block Name\n` +
    blocks.map(block => `${hex(block.start)}..${hex(block.end)}; ${block.title}`).join("\n") + "\n";
  // UnicodeData's legacy format has exactly 15 fields, with no header/comments.
  files["UnicodeData.txt"] = entries.map(entry => [
    hex(entry.codePoint), entry.name, "Ll", "0", "L", "", "", "", "", "N", "", "", "", "", ""
  ].join(";")).join("\n") + "\n";
  const names = ["; charset=UTF-8", "; " + status,
    "; Structural names only; Roman and Italic share each assignment."];
  const charts = [];
  for (const block of blocks) {
    names.push(header(block));
    charts.push(header(block), "@font=Quintessential Serif, 18pt");
    let previousFamily;
    for (const entry of inBlock(block)) {
      if (entry.familyId !== previousFamily) names.push("@\t\t" + families.get(entry.familyId));
      names.push(hex(entry.codePoint) + "\t" + entry.name);
      previousFamily = entry.familyId;
      // UCSUR Charts maps a code to text in a named font, not to a glyph ID.
      charts.push(hex(entry.codePoint) + ";" + String.fromCodePoint(entry.codePoint));
    }
  }
  files["NamesList.txt"] = names.join("\n") + "\n";
  files["Charts.txt"] = charts.join("\n") + "\n";
  files["CaseFolding.txt"] = `# ${status}\n# All ${entries.length} characters are lowercase letters with identity case folding.\n# No uppercase/titlecase counterparts or other case mappings are defined.\n# Unlisted characters map to themselves; identity records are not emitted.\n# Lowercase status does not require an uppercase counterpart.\n# This fragment covers only these three proposed blocks. See ReadMe.txt.\n`;
  const sourceRecords = [
    { "Agreement-Type": "Public", "Agreement-Name": "Quintessential Latin private-use agreement (draft)" },
    { Title: "Quintessential Latin draft UCSUR proposal", Author: proposal.author,
      "Publication-Date": proposal.date, URL: repo + "/blob/main/docs/proposal.json" },
    { Title: "Quintessential Latin explicit allocation " + allocation.version, Author: proposal.author,
      URL: repo + "/blob/main/resources/quintessential-latin-allocation.json" },
    { Title: "Quintessential Latin canonical naming version " + allocation.namingVersion, Author: proposal.author,
      URL: repo + "/blob/main/docs/quintessential-latin-canonical-naming-spec-v3.md" },
    { Title: "Quintessential Latin reference fonts and code charts", Author: proposal.author, URL: site + "downloads.html" },
    { Title: "Under-ConScript Unicode Registry data directory", URL: "https://www.kreativekorp.com/ucsur/UNIDATA/", "Access-Date": formatDate },
    { Title: "UCSUR Charts File Format, revision 1.0", Author: "Ian Jacobi", "Publication-Date": "2013-02-05",
      URL: "https://www.kreativekorp.com/ucsur/UNIDATA/Charts.html", "Access-Date": formatDate },
    { Title: "UCSUR source bibliography format", URL: "https://www.kreativekorp.com/ucsur/UNIDATA/Sources.txt", "Access-Date": formatDate },
    { Title: "Unicode Character Database, UAX #44, Unicode 17.0.0",
      URL: "https://www.unicode.org/reports/tr44/tr44-36.html", "Access-Date": formatDate },
    { Title: "Unicode 17.0.0, Chapter 4, section 4.2 Case",
      URL: "https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-4/", "Access-Date": formatDate },
    { Title: "Unicode 17.0.0 NamesList format", URL: "https://www.unicode.org/Public/17.0.0/ucd/NamesList.html", "Access-Date": formatDate },
    { Title: "Unicode 17.0.0, Chapter 23, section 23.5 Private-Use Characters",
      URL: "https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-23/", "Access-Date": formatDate }
  ];
  files["Sources.txt"] = sourceRecords.map(record => Object.entries(record).map(([key, value]) => `${key}: ${value}`).join("\n")).join("\n\n") + "\n";
  files["ReadMe.txt"] = `${status}

This is the project's proposed UCD-style subset for UCSUR review and explicit
private-use agreements. It is not an official Unicode Character Database, a
complete copy of UCSUR's database, or evidence of submission or registration.
Format references were checked on ${formatDate}; Unicode 17.0.0 is the format
baseline, not a character Age or a claim of Unicode encoding.

Repertoire
==========
${blocks.map(block => `U+${hex(block.start)}..U+${hex(block.end)}  ${block.title}  (${block.end - block.start + 1})`).join("\n")}
All ${entries.length} positions are assigned in allocation ${allocation.version}, naming version ${allocation.namingVersion}.
Earlier numeric assignments were replaced without compatibility aliases.
The files use numeric order, exact canonical names, UTF-8 without a BOM, and LF.
Author: ${proposal.author}
Project: ${repo}
Website: ${site}

Files
=====
Blocks.txt       Three proposed block ranges and titles, in UCD range syntax.
UnicodeData.txt  ${entries.length} records, exactly 15 semicolon-separated fields each.
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
are at ${repo}/blob/main/docs/ucd-research.md.
The six data formats follow UCSUR's published UNIDATA directory; Charts.txt
and Sources.txt are UCSUR conventions rather than Unicode UCD property files.
Original project data and documentation use the repository's MIT license:
${repo}/blob/main/LICENSE
No Unicode or UCSUR character dataset is copied into this package. Reference
font software retains its separate SIL Open Font License and attribution.
`;
  return { files, blocks, entries };
}

async function exportUcd({ root = ROOT, check = false } = {}) {
  const sourceBytes = new Map();
  for (const relative of UCD_SOURCE_PATHS) sourceBytes.set(relative, await fs.readFile(path.join(root, relative)));
  const allocation = JSON.parse(sourceBytes.get(UCD_SOURCE_PATHS[0]).toString("utf8"));
  const proposal = JSON.parse(sourceBytes.get(UCD_SOURCE_PATHS[1]).toString("utf8"));
  const { files, blocks, entries } = renderFiles(allocation, proposal);
  const manifest = {
    schemaVersion: 1, repertoireVersion: allocation.version, namingVersion: allocation.namingVersion,
    unicodeVersion: "17.0.0", status: "draft-private-use", characterCount: entries.length,
    blocks: blocks.map(block => ({ start: hex(block.start), end: hex(block.end), name: block.title, count: block.end - block.start + 1 })),
    sources: Object.fromEntries([...sourceBytes].map(([name, bytes]) => [name, sha256(bytes)])),
    files: Object.fromEntries(Object.entries(files).map(([name, text]) => [name, { bytes: Buffer.byteLength(text), sha256: sha256(text) }]))
  };
  files["manifest.json"] = JSON.stringify(manifest, null, 2) + "\n";
  const destination = path.join(root, "resources/ucd");
  if (!check) await fs.mkdir(destination, { recursive: true });
  for (const name of UCD_FILES) {
    if (check) {
      let actual;
      try { actual = await fs.readFile(path.join(destination, name), "utf8"); } catch (error) { if (error.code !== "ENOENT") throw error; }
      if (actual !== files[name]) throw new Error(`Stale or missing UCD file: resources/ucd/${name}. Regenerate with: npm run build:ucd`);
    } else await fs.writeFile(path.join(destination, name), files[name]);
  }
  return manifest;
}

module.exports = { exportUcd, UCD_FILES, UCD_SOURCE_PATHS };
if (require.main === module) {
  const check = process.argv.includes("--check");
  exportUcd({ check }).then(manifest => console.log(`${check ? "Verified" : "Exported"} ${manifest.characterCount} UCD records across ${manifest.blocks.length} proposed blocks.`)).catch(error => { console.error(error.message); process.exitCode = 1; });
}

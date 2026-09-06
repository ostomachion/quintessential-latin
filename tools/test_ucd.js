"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createHash } = require("node:crypto");
const test = require("node:test");
const { exportUcd, UCD_FILES, UCD_SOURCE_PATHS } = require("./export_ucd.js");

const root = path.resolve(__dirname, "..");
const ucdRoot = path.join(root, "resources/ucd");
const allocation = JSON.parse(fs.readFileSync(path.join(root, "resources/quintessential-latin-allocation.json"), "utf8"));
const entries = [...allocation.entries].sort((a, b) => a.codePoint - b.codePoint);
const expectedNames = entries.map(entry => [entry.codePoint, entry.name]);
const expectedBlocks = allocation.blocks.map(block => [block.start, block.title, block.end]);

function readLines(filename) {
  const bytes = fs.readFileSync(path.join(ucdRoot, filename));
  const text = bytes.toString("utf8");
  assert.deepEqual(Buffer.from(text, "utf8"), bytes, `${filename}: valid UTF-8`);
  assert.ok(!text.startsWith("\uFEFF"), `${filename}: no byte-order mark`);
  assert.ok(text.endsWith("\n"), `${filename}: final newline`);
  assert.ok(!text.includes("\r"), `${filename}: LF line endings`);
  return text.slice(0, -1).split("\n");
}

function dataLines(filename) {
  return readLines(filename).map(line => line.split("#", 1)[0].trim()).filter(Boolean);
}

function parseHex(value) {
  assert.match(value, /^[0-9A-F]{4,6}$/, `UCD scalar: ${value}`);
  const scalar = Number.parseInt(value, 16);
  assert.ok(scalar <= 0x10FFFF && !(scalar >= 0xD800 && scalar <= 0xDFFF), value);
  return scalar;
}

function parseBlockHeader(line) {
  const match = /^@@\t([0-9A-F]{4,6})\t([^\t]+)\t([0-9A-F]{4,6})$/.exec(line);
  assert.ok(match, `Block header syntax: ${line}`);
  return [parseHex(match[1]), match[2], parseHex(match[3])];
}

test("UCD block ranges cover the current three project blocks exactly", () => {
  const records = dataLines("Blocks.txt").map(line => {
    const match = /^([0-9A-F]{4,6})\.\.([0-9A-F]{4,6});\s*([^;]+)$/.exec(line);
    assert.ok(match, `Blocks syntax: ${line}`);
    return [parseHex(match[1]), match[3], parseHex(match[2])];
  });
  assert.deepEqual(records, expectedBlocks);
  assert.equal(entries.length, 1216);
  assert.deepEqual(entries.map(entry => entry.codePoint), Array.from({ length: 1216 }, (_, index) => 0xF2A00 + index));
});

test("UnicodeData independently parses all 15 fields and exact names in scalar order", () => {
  const lines = readLines("UnicodeData.txt");
  assert.equal(lines.length, entries.length);
  const parsed = lines.map(line => {
    const fields = line.split(";");
    assert.equal(fields.length, 15, `UnicodeData field count: ${line}`);
    const scalar = parseHex(fields[0]);
    assert.match(fields[1], /^QUINTESSENTIAL LATIN SMALL LETTER [A-Z -]+$/);
    assert.deepEqual(fields.slice(2), ["Ll", "0", "L", "", "", "", "", "N", "", "", "", "", ""], fields[0]);
    return [scalar, fields[1]];
  });
  assert.deepEqual(parsed, expectedNames);
  assert.equal(new Set(parsed.map(([scalar]) => scalar)).size, entries.length);
});

test("NamesList has UTF-8 declaration, block and family headings, and complete names", () => {
  const lines = readLines("NamesList.txt");
  assert.match(lines[0], /^;.*UTF-8/i);
  const blocks = [];
  const families = [];
  const parsed = [];
  let block;
  let family;
  for (const line of lines) {
    if (!line || line.startsWith(";")) continue;
    if (line.startsWith("@@")) {
      block = parseBlockHeader(line);
      blocks.push(block);
      family = undefined;
    } else if (line.startsWith("@")) {
      const match = /^@\t\t([^\t]+)$/.exec(line);
      assert.ok(match, `NamesList family heading: ${line}`);
      assert.ok(block, "Family heading follows block header");
      family = match[1];
      families.push([block[1], family]);
    } else {
      const match = /^([0-9A-F]{4,6})\t([^\t]+)$/.exec(line);
      assert.ok(match, `NamesList record syntax: ${line}`);
      const scalar = parseHex(match[1]);
      const entry = entries[parsed.length];
      assert.ok(block && scalar >= block[0] && scalar <= block[2], `NamesList block membership: ${line}`);
      assert.equal(family, allocation.families.find(item => item.id === entry.familyId)?.title, `NamesList family: ${line}`);
      parsed.push([scalar, match[2]]);
    }
  }
  assert.deepEqual(blocks, expectedBlocks);
  assert.deepEqual(families, allocation.families.map(item => [allocation.blocks.find(block => block.id === item.blockId).title, item.title]));
  assert.deepEqual(parsed, expectedNames);
});

test("Charts specifies the reference font and maps each scalar to its literal character", () => {
  const lines = readLines("Charts.txt");
  const blocks = [];
  const mapped = [];
  let block;
  let font;
  for (const line of lines) {
    if (!line || line.startsWith("#") || line.startsWith(";")) continue;
    if (line.startsWith("@@")) {
      block = parseBlockHeader(line);
      blocks.push(block);
      font = undefined;
    } else if (line.startsWith("@font=")) {
      assert.match(line, /^@font=Quintessential Serif, [1-9][0-9]*(?:\.[0-9]+)?pt$/);
      font = line;
    } else {
      const match = /^([0-9A-F]{4,6});(.)$/u.exec(line);
      assert.ok(match, `Charts scalar mapping: ${line}`);
      const scalar = parseHex(match[1]);
      assert.ok(block && scalar >= block[0] && scalar <= block[2], `Charts block membership: ${line}`);
      assert.ok(font, `Charts font is set before mapping ${match[1]}`);
      assert.equal(match[2].codePointAt(0), scalar, "Each chart mapping is a literal scalar, not a construction or ligature sequence");
      mapped.push(scalar);
    }
  }
  assert.deepEqual(blocks, expectedBlocks);
  assert.deepEqual(mapped, entries.map(entry => entry.codePoint));
});

test("CaseFolding preserves every lowercase letter without case counterparts", () => {
  assert.deepEqual(dataLines("CaseFolding.txt"), []);
});

test("Sources describes a draft public agreement and provides identifiable source URLs", () => {
  const text = readLines("Sources.txt").filter(line => !line.startsWith("#")).join("\n");
  const records = text.trim().split(/\n\s*\n/).map(record => {
    const fields = new Map();
    for (const line of record.split("\n")) {
      const match = /^([A-Za-z][A-Za-z-]*):\s+(.+)$/.exec(line);
      assert.ok(match, `Sources field syntax: ${line}`);
      assert.ok(!fields.has(match[1]), `Duplicate Sources field: ${match[1]}`);
      fields.set(match[1], match[2]);
    }
    return fields;
  });
  assert.equal(records[0].get("Agreement-Type"), "Public");
  assert.match(records[0].get("Agreement-Name"), /Quintessential Latin.*draft/i);
  assert.ok(records.every(record => !record.has("Agreement-FCC")), "No claim of a registered agreement identifier");
  assert.ok(records.length > 1, "Bibliographic source records are supplied");
  for (const record of records.slice(1)) {
    assert.ok(record.get("Title"), "Each source has a title");
    if (record.has("Author")) assert.ok(record.get("Author"), "An optional author field is nonempty");
    const url = new URL(record.get("URL"));
    assert.ok(["http:", "https:"].includes(url.protocol), `Source URL: ${url}`);
    if (record.has("Access-Date")) assert.match(record.get("Access-Date"), /^\d{4}-\d{2}-\d{2}$/);
  }
});

function digest(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

test("manifest records the format baseline, draft status, repertoire, and exact file hashes", () => {
  const manifest = JSON.parse(readLines("manifest.json").join("\n"));
  assert.equal(manifest.schemaVersion, 1);
  assert.equal(manifest.repertoireVersion, allocation.version);
  assert.equal(manifest.namingVersion, allocation.namingVersion);
  assert.equal(manifest.unicodeVersion, "17.0.0");
  assert.equal(manifest.status, "draft-private-use");
  assert.equal(manifest.characterCount, entries.length);
  assert.deepEqual(manifest.blocks.map(block => [parseHex(block.start), block.name, parseHex(block.end)]), expectedBlocks);
  for (const block of manifest.blocks) {
    assert.equal(block.count, parseHex(block.end) - parseHex(block.start) + 1);
  }
  assert.deepEqual([...UCD_FILES].sort(), ["Blocks.txt", "UnicodeData.txt", "NamesList.txt", "CaseFolding.txt", "Charts.txt", "Sources.txt", "ReadMe.txt", "manifest.json"].sort());
  assert.deepEqual(Object.keys(manifest.files).sort(), UCD_FILES.filter(filename => filename !== "manifest.json").sort());
  for (const [filename, expected] of Object.entries(manifest.files)) {
    const bytes = fs.readFileSync(path.join(ucdRoot, filename));
    assert.equal(expected.bytes, bytes.length, `${filename}: byte count`);
    assert.equal(expected.sha256, digest(bytes), `${filename}: SHA-256`);
  }
  assert.deepEqual(Object.keys(manifest.sources).sort(), [...UCD_SOURCE_PATHS].sort());
  for (const [filename, expectedHash] of Object.entries(manifest.sources)) {
    assert.equal(expectedHash, digest(fs.readFileSync(path.join(root, filename))), `${filename}: source SHA-256`);
  }
});

function makeFixture(t) {
  const tempRoot = fs.realpathSync(os.tmpdir());
  const fixtureRoot = fs.mkdtempSync(path.join(tempRoot, "quintessential-ucd-"));
  t.after(() => {
    assert.equal(path.dirname(path.resolve(fixtureRoot)), path.resolve(tempRoot));
    assert.ok(path.basename(fixtureRoot).startsWith("quintessential-ucd-"));
    fs.rmSync(fixtureRoot, { recursive: true, force: true });
  });
  for (const relative of UCD_SOURCE_PATHS) {
    assert.ok(!path.isAbsolute(relative) && !relative.split(/[\\/]/).includes(".."), relative);
    const output = path.join(fixtureRoot, relative);
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.copyFileSync(path.join(root, relative), output);
  }
  return fixtureRoot;
}

test("export check accepts checked-in files and a deterministic fresh export", async t => {
  await exportUcd({ root, check: true });
  const fixtureRoot = makeFixture(t);
  await exportUcd({ root: fixtureRoot, check: false });
  await exportUcd({ root: fixtureRoot, check: true });
  const first = UCD_FILES.map(filename => fs.readFileSync(path.join(fixtureRoot, "resources/ucd", filename)));
  await exportUcd({ root: fixtureRoot, check: false });
  assert.deepEqual(UCD_FILES.map(filename => fs.readFileSync(path.join(fixtureRoot, "resources/ucd", filename))), first);
});

test("export check rejects deleted and modified generated files without repairing them", async t => {
  const fixtureRoot = makeFixture(t);
  await exportUcd({ root: fixtureRoot, check: false });
  const filename = path.join(fixtureRoot, "resources/ucd/UnicodeData.txt");
  const original = fs.readFileSync(filename);
  fs.unlinkSync(filename);
  await assert.rejects(async () => exportUcd({ root: fixtureRoot, check: true }));
  assert.ok(!fs.existsSync(filename), "Check mode does not recreate a missing file");
  fs.writeFileSync(filename, original.toString("utf8").replace(";Ll;0;L;", ";Lu;0;L;"));
  const changed = fs.readFileSync(filename);
  await assert.rejects(async () => exportUcd({ root: fixtureRoot, check: true }));
  assert.deepEqual(fs.readFileSync(filename), changed, "Check mode does not repair a changed file");
});

test("export check rejects allocation name and scalar drift", async t => {
  const fixtureRoot = makeFixture(t);
  await exportUcd({ root: fixtureRoot, check: false });
  const filename = path.join(fixtureRoot, "resources/quintessential-latin-allocation.json");
  const original = fs.readFileSync(filename, "utf8");
  const changedName = JSON.parse(original);
  changedName.entries[0].name += " ALTERED";
  fs.writeFileSync(filename, JSON.stringify(changedName));
  await assert.rejects(async () => exportUcd({ root: fixtureRoot, check: true }));
  const changedScalar = JSON.parse(original);
  changedScalar.entries[0].codePoint = 0xF2EC0;
  fs.writeFileSync(filename, JSON.stringify(changedScalar));
  await assert.rejects(async () => exportUcd({ root: fixtureRoot, check: true }));
});

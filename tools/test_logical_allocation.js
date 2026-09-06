"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { gunzipSync } = require("node:zlib");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const allocation = JSON.parse(fs.readFileSync(path.join(root, "resources/quintessential-latin-allocation.json"), "utf8"));
const captured = JSON.parse(gunzipSync(fs.readFileSync(path.join(root, "resources/provenance/logical-allocation-baseline.json.gz"))));
const baseline = captured.allocation || captured;
const byId = new Map(allocation.entries.map(entry => [entry.glyphId, entry]));
const numeric = [...allocation.entries].sort((a, b) => a.codePoint - b.codePoint);
const moved = ["special-closed-double-bowl", "special-double-open-bowl", "special-turned-double-open-bowl", "special-spine"];
const blocks = [
  ["quintessential-latin", 0xF2A00, 0xF2ABF, 192],
  ["quintessential-latin-abbreviations", 0xF2AC0, 0xF2BBF, 256],
  ["quintessential-latin-extensions", 0xF2BC0, 0xF2EBF, 768]
];
const families = [
  ["reserved-forms", 3], ["stems", 9], ["arms", 12], ["bowls", 12], ["arches", 12],
  ["descending-arches", 12], ["hooked-arches", 12], ["arched-arms", 24], ["arched-bowls", 24],
  ["double-arches", 24], ["descending-double-arches", 24], ["hooked-double-arches", 24],
  ["stemless-double-bowls-and-spine", 4], ["double-bowls", 12], ["bowled-spines", 12], ["opposed-bowls", 36],
  ["arched-double-bowls", 24], ["arched-bowled-spines", 24], ["left-arched-opposed-bowls", 72],
  ["right-arched-opposed-bowls", 72], ["double-arched-arms", 48], ["double-arched-bowls", 48],
  ["triple-arches", 48], ["descending-triple-arches", 48], ["hooked-triple-arches", 48],
  ["double-arched-double-bowls", 48], ["double-arched-bowled-spines", 48],
  ["left-double-arched-opposed-bowls", 144], ["right-double-arched-opposed-bowls", 144],
  ["double-arched-opposed-bowls", 144]
];

function middleState(entry) {
  return entry.parts.filter(part => part.middle).map(part => part[part.kind === "leg" ? "lower" : "upper"] === "straight");
}

test("all 1216 assignments and the three declared blocks are contiguous", () => {
  assert.equal(allocation.entries.length, 1216);
  assert.deepEqual([allocation.version, allocation.previousVersion], ["0.250", "0.240"]);
  assert.deepEqual(numeric.map(entry => entry.codePoint), Array.from({length:1216}, (_, index) => 0xF2A00 + index));
  assert.deepEqual(allocation.displayOrder, numeric.map(entry => entry.glyphId));
  for (const field of ["glyphId", "glyphName", "codePoint", "canonicalName", "legacyIndex"]) {
    assert.equal(new Set(allocation.entries.map(entry => entry[field])).size, 1216, field);
  }
  assert.deepEqual(allocation.blocks.map(block => [block.id, block.start, block.end]), blocks.map(block => block.slice(0, 3)));
  for (const [blockId, start, end, count] of blocks) {
    const entries = numeric.filter(entry => entry.blockId === blockId);
    assert.equal(entries.length, count, blockId);
    assert.equal(start % 16, 0, blockId);
    assert.equal((end + 1) % 16, 0, blockId);
    assert.deepEqual(entries.map(entry => entry.codePoint), Array.from({length:count}, (_, index) => start + index), blockId);
  }
});

test("the requested four stemless constructions begin Extended-A", () => {
  const entries = numeric.filter(entry => entry.blockId === "quintessential-latin-abbreviations");
  assert.deepEqual(entries.slice(0, 4).map(entry => entry.glyphId), moved);
  assert.deepEqual(entries.slice(0, 4).map(entry => entry.codePoint), [0xF2AC0, 0xF2AC1, 0xF2AC2, 0xF2AC3]);
  assert.ok(entries.slice(0, 4).every(entry => entry.stemless && entry.familyId === "stemless-double-bowls-and-spine"));
  assert.deepEqual(numeric.slice(0, 3).map(entry => entry.glyphId), ["special-ring", "special-open-bowl", "special-turned-open-bowl"]);
  assert.ok(numeric.slice(0, 3).every(entry => entry.stemless && entry.familyId === "reserved-forms"));
});

test("all 30 families are complete, unfragmented, and ordered by construction", () => {
  assert.deepEqual(allocation.families.map(family => family.id), families.map(([id]) => id));
  assert.ok(allocation.families.every(family => !family.baseFamilyId));
  let offset = 0;
  for (const [familyId, count] of families) {
    const family = allocation.families.find(item => item.id === familyId);
    const expected = numeric.slice(offset, offset + count);
    assert.equal(numeric.filter(entry => entry.familyId === familyId).length, count, familyId);
    assert.ok(expected.every(entry => entry.familyId === familyId && entry.blockId === family.blockId), familyId);
    offset += count;
  }
  assert.equal(offset, numeric.length);
});

test("each base is immediately followed by its independent middle states", () => {
  const bases = numeric.filter(entry => !entry.middleLegs);
  const counts = [0, 0, 0];
  for (const base of bases) {
    const middleCount = middleState(base).length;
    counts[middleCount] += 1;
    const suffixes = middleCount === 2
      ? ["", "-extended-left-middle-leg", "-extended-right-middle-leg", "-extended-middle-legs"]
      : middleCount === 1 ? ["", "-extended-middle-legs"] : [""];
    const expectedMasks = middleCount === 2 ? [[false, false], [true, false], [false, true], [true, true]]
      : middleCount === 1 ? [[false], [true]] : [[]];
    const start = base.codePoint - 0xF2A00;
    const entries = numeric.slice(start, start + suffixes.length);
    assert.deepEqual(entries.map(entry => entry.glyphId), suffixes.map(suffix => base.glyphId + suffix), base.glyphId);
    assert.deepEqual(entries.map(middleState), expectedMasks, base.glyphId);
    assert.ok(entries.every(entry => entry.familyId === base.familyId && entry.blockId === base.blockId), base.glyphId);
    assert.ok(entries.slice(1).every(entry => entry.baseGlyphId === base.glyphId), base.glyphId);
  }
  assert.deepEqual(counts, [136, 156, 192]);
});

test("reallocation preserves construction identities, names, parts, and previous base order", () => {
  assert.equal(baseline.entries.length, 1216);
  const identityFields = ["glyphId", "glyphName", "legacyIndex", "recipeCodePoint", "oldCodePoint", "baseGlyphId",
    "middleLegs", "middleLegExtensions", "postures", "parts", "stemless", "name", "canonicalName", "legacyName"];
  const identity = entry => Object.fromEntries(identityFields.map(field => [field, entry[field]]));
  for (const previous of baseline.entries) {
    assert.ok(byId.has(previous.glyphId), previous.glyphId);
    assert.deepEqual(identity(byId.get(previous.glyphId)), identity(previous), previous.glyphId);
  }
  const previousById = new Map(baseline.entries.map(entry => [entry.glyphId, entry]));
  for (const [familyId] of families.filter(([id]) => id !== "stemless-double-bowls-and-spine")) {
    const previous = baseline.displayOrder.map(id => previousById.get(id))
      .filter(entry => entry.familyId === familyId && !entry.middleLegs && !moved.includes(entry.glyphId));
    const current = numeric.filter(entry => entry.familyId === familyId && !entry.middleLegs);
    assert.deepEqual(current.map(entry => entry.glyphId), previous.map(entry => entry.glyphId), familyId);
  }
});

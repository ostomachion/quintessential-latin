"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { gunzipSync } = require("node:zlib");
const test = require("node:test");
const { canonicalName, nameParts, formatParts } = require("./canonical_glyph_names.js");

// These fixtures encode the specification's component connections, independently
// of the font's current appearance and of the allocation's existing labels.
const stem = (upper = "none", lower = "none") => ({ kind: "stem", upper, lower });
const leg = (lower = "none", middle = false) => ({ kind: "leg", upper: "none", lower, middle });
const arm = (upper = "none", middle = false) => ({ kind: "arm", upper, lower: "none", middle });
const bowl = () => ({ kind: "bowl" });
const longBowl = (closingNeighbor, closingEnd, returnContact = true) => ({
  kind: "bowl", long: true, closingNeighbor, closingEnd, returnContact
});
const spine = (long = false) => ({ kind: "spine", long });
const body = kind => ({ kind });
const allocation = JSON.parse(fs.readFileSync(path.join(__dirname, "../resources/quintessential-latin-allocation.json"), "utf8"));

function freeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

function cases(fixtures) {
  for (const [parts, expected] of fixtures) {
    const original = structuredClone(parts);
    freeze(parts);
    assert.equal(nameParts(parts), expected, JSON.stringify(original));
    assert.equal(nameParts(parts), expected, "Repeated naming must be deterministic.");
    assert.deepEqual(parts, original, "Naming must retain the full component geometry.");
  }
}

test("all nine stem primitives and the ordinary body vocabulary", () => {
  const names = [
    ["stem", "ascender", "hook"],
    ["descender", "long stem", "long hook"],
    ["tail", "long tail", "long spine"]
  ];
  const extensions = ["none", "straight", "curved"];
  const fixtures = [];
  for (const [lowerIndex, lower] of extensions.entries()) {
    for (const [upperIndex, upper] of extensions.entries()) {
      fixtures.push([[stem(upper, lower)], names[lowerIndex][upperIndex]]);
    }
  }
  fixtures.push([[spine()], "spine"], [[spine(true)], "long spine"], [[bowl()], "bowl"],
    [[body("double bowl")], "double bowl"]);
  cases(fixtures);
});

test("Section 4 short-form examples preserve left-to-right connection roles", () => {
  cases([
    [[stem(), body("shoulder")], "stem with shoulder"],
    [[body("hip"), stem()], "hip with stem"],
    [[stem(), leg()], "stem with leg"],
    [[arm(), stem()], "arm with stem"],
    [[stem("straight"), leg()], "ascender with leg"],
    [[stem("straight"), bowl()], "ascender with bowl"],
    [[bowl(), stem("straight")], "bowl with ascender"],
    [[stem("none", "straight"), bowl()], "descender with bowl"],
    [[bowl(), stem("none", "straight")], "bowl with descender"],
    [[bowl()], "bowl"],
    [[bowl(), stem("none", "curved")], "bowl with tail"],
    [[spine(), stem()], "spine with stem"],
    [[stem(), spine()], "stem with spine"],
    [[stem("straight"), leg("straight")], "ascender with long leg"],
    [[arm("straight"), stem("none", "straight")], "long arm with descender"],
    [[stem("curved"), longBowl(0, "lower")], "hook with long open bowl"],
    [[longBowl(1, "upper"), stem("none", "curved")], "long open bowl with tail"]
  ]);
});

test("upward bowls omit only the straight upper extension that actually closes them", () => {
  cases([
    [[longBowl(1, "upper"), stem()], "long open bowl with stem"],
    [[longBowl(1, "upper"), stem("straight")], "long bowl with stem"],
    [[longBowl(1, "upper"), stem("straight", "straight")], "long bowl with descender"],
    [[longBowl(1, "upper"), stem("straight", "curved")], "long bowl with tail"],
    [[longBowl(1, "upper"), stem("curved")], "long open bowl with hook"],
    [[longBowl(1, "upper"), stem("curved", "curved")], "long open bowl with long spine"],
    [[longBowl(1, "upper", false), stem("straight")], "long open bowl with ascender"]
  ]);
});

test("downward bowls omit only the straight lower extension that actually closes them", () => {
  cases([
    [[stem(), longBowl(0, "lower")], "stem with long open bowl"],
    [[stem("none", "straight"), longBowl(0, "lower")], "stem with long bowl"],
    [[stem("straight", "straight"), longBowl(0, "lower")], "ascender with long bowl"],
    [[stem("curved", "straight"), longBowl(0, "lower")], "hook with long bowl"],
    [[stem("none", "curved"), longBowl(0, "lower")], "tail with long open bowl"],
    [[stem("curved", "curved"), longBowl(0, "lower")], "long spine with long open bowl"],
    [[stem("none", "straight"), longBowl(0, "lower", false)], "descender with long open bowl"]
  ]);
});

test("all closed-neighbor requirements are collected before naming a shared upright", () => {
  const parts = [longBowl(1, "upper"), stem("straight", "straight"), longBowl(1, "lower")];
  cases([[parts, "long bowl with stem and long bowl"]]);
  assert.equal(parts[1].upper, "straight");
  assert.equal(parts[1].lower, "straight");
});

test("interior branches use upright primitives and retain terminal branch names", () => {
  cases([
    [[stem(), leg("none", true), leg()], "two stems with leg"],
    [[stem("straight"), leg("none", true), leg()], "ascender with stem and leg"],
    [[stem(), leg("straight", true), leg("straight")], "stem with descender and long leg"],
    [[arm(), arm("none", true), stem()], "arm with two stems"],
    [[arm("straight"), arm("straight", true), stem()], "long arm with ascender and stem"],
    [[stem(), leg("straight", true), leg()], "stem with descender and leg"],
    [[stem(), leg("none", true), leg("straight")], "two stems with long leg"],
    [[arm(), arm("straight", true), stem()], "arm with ascender and stem"],
    [[arm("straight"), arm("none", true), stem()], "long arm with two stems"],
    [[stem(), leg("none", true), body("shoulder")], "two stems with shoulder"],
    [[body("hip"), arm("none", true), stem()], "hip with two stems"],
    [[stem(), leg("none", true), bowl()], "two stems with bowl"],
    [[bowl(), arm("none", true), stem()], "bowl with two stems"]
  ]);
});

test("count rules combine equal adjacent uprights without crossing a body", () => {
  cases([
    [[stem(), leg("none", true), leg("none", true)], "three stems"],
    [[arm("none", true), arm("none", true), stem()], "three stems"],
    [[stem(), leg("none", true), spine(), leg()], "two stems with spine and leg"],
    [[arm(), spine(), arm("none", true), stem()], "arm with spine and two stems"],
    [[stem(), leg("none", true), leg("none", true), leg()], "three stems with leg"],
    [[arm(), arm("none", true), arm("none", true), stem()], "arm with three stems"]
  ]);
});

test("Section 6 final long bowls close against the immediate interior upright", () => {
  cases([
    [[stem(), leg("none", true), longBowl(1, "lower")], "two stems with long open bowl"],
    [[stem("none", "straight"), leg("none", true), longBowl(1, "lower")], "descender with stem and long open bowl"],
    [[stem(), leg("straight", true), longBowl(1, "lower")], "two stems with long bowl"],
    [[stem("none", "straight"), leg("straight", true), longBowl(1, "lower")], "descender with stem and long bowl"]
  ]);
});

test("Section 6 initial long bowls close against the immediate interior upright", () => {
  cases([
    [[longBowl(1, "upper"), arm("none", true), stem()], "long open bowl with two stems"],
    [[longBowl(1, "upper"), arm("none", true), stem("straight")], "long open bowl with stem and ascender"],
    [[longBowl(1, "upper"), arm("straight", true), stem()], "long bowl with two stems"],
    [[longBowl(1, "upper"), arm("straight", true), stem("straight")], "long bowl with stem and ascender"]
  ]);
});

test("changing every distant main-upright extension leaves interior-neighbor closure local", () => {
  for (const upper of ["none", "straight", "curved"]) {
    for (const lower of ["none", "straight", "curved"]) {
      for (const middleExtension of ["none", "straight"]) {
        const final = freeze([stem(upper, lower), leg(middleExtension, true), longBowl(1, "lower")]);
        const initial = freeze([longBowl(1, "upper"), arm(middleExtension, true), stem(upper, lower)]);
        const expected = middleExtension === "straight" ? "long bowl" : "long open bowl";
        assert.ok(nameParts(final).endsWith(expected));
        assert.ok(nameParts(initial).startsWith(`${expected} with `));
        assert.equal(final[1].lower, middleExtension, "Closure omission must preserve the middle descent.");
        assert.equal(initial[1].upper, middleExtension, "Closure omission must preserve the middle ascent.");
      }
    }
  }
});

test("one-sided and two-sided spines retain attachment features and never acquire opening qualifiers", () => {
  cases([
    [[spine(), stem()], "spine with stem"],
    [[stem(), spine()], "stem with spine"],
    [[stem(), spine(), stem()], "stem with spine and stem"],
    [[stem("straight"), spine(), stem("none", "straight")], "ascender with spine and descender"],
    [[stem(), spine(true), stem()], "stem with long spine and stem"],
    [[stem("curved", "straight"), spine(true), stem("straight", "curved")], "long hook with long spine and long tail"]
  ]);
});

test("formatting uses one with and any remaining and separators after abbreviation", () => {
  const fixtures = [
    [["stem"], "stem"],
    [["stem", "leg"], "stem with leg"],
    [["two stems", "long open bowl"], "two stems with long open bowl"],
    [["stem", "spine", "stem"], "stem with spine and stem"],
    [["arm", "two stems"], "arm with two stems"],
    [["A", "B", "C", "D"], "A with B and C and D"]
  ];
  for (const [terms, expected] of fixtures) assert.equal(formatParts(freeze(terms)), expected);
  assert.throws(() => formatParts([]));
  assert.throws(() => nameParts([]));
});

test("default extensions and explicit absent extensions name the same structure", () => {
  cases([
    [[{ kind: "stem" }, { kind: "leg", middle: true }, { kind: "leg" }], "two stems with leg"],
    [[{ kind: "arm" }, { kind: "arm", middle: true }, { kind: "stem" }], "arm with two stems"]
  ]);
  assert.equal(nameParts([{ kind: "stem" }]), nameParts([stem()]));
});


test("all 1216 neutral structures retain unique canonical names without mutation", () => {
  assert.equal(allocation.entries.length, 1216);
  assert.equal(allocation.namingVersion, 3);
  const seen = new Set();
  for (const entry of allocation.entries) {
    assert.ok(!("model" in entry) && !("language" in entry) && !("role" in entry));
    const parts = freeze(structuredClone(entry.parts));
    const original = structuredClone(parts);
    assert.equal(canonicalName(parts), entry.canonicalName, entry.glyphId);
    assert.equal(entry.name, `QUINTESSENTIAL LATIN LETTER ${entry.canonicalName.toUpperCase()}`, entry.glyphId);
    assert.doesNotMatch(entry.canonicalName, /middle (?:arm|leg)/);
    assert.deepEqual(parts, original);
    assert.ok(!seen.has(entry.canonicalName), entry.glyphId);
    seen.add(entry.canonicalName);
  }
});

test("all two-middle constructions include every independent extension state", () => {
  const byId = new Map(allocation.entries.map(entry => [entry.glyphId, entry]));
  const bases = allocation.entries.filter(entry => !entry.middleLegs && entry.parts.filter(part => part.middle).length === 2);
  assert.equal(bases.length, 192);
  assert.equal(new Set(bases.map(entry => entry.familyId)).size, 10);
  assert.equal(allocation.entries.filter(entry => entry.middleLegExtensions).length, 384);
  for (const base of bases) {
    const variants = allocation.entries.filter(entry => entry.glyphId === base.glyphId || entry.baseGlyphId === base.glyphId);
    assert.equal(variants.length, 4, base.glyphId);
    const states = variants.map(entry => entry.parts.filter(part => part.middle)
      .map(part => part[part.kind === "leg" ? "lower" : "upper"] === "straight"));
    assert.deepEqual(states.map(state => state.map(Number).join("")).sort(), ["00", "01", "10", "11"], base.glyphId);
    for (const [index, side] of ["left", "right"].entries()) {
      const entry = byId.get(`${base.glyphId}-extended-${side}-middle-leg`);
      assert.ok(entry, base.glyphId);
      assert.deepEqual(entry.middleLegExtensions, [index === 0, index === 1]);
      assert.equal(entry.recipeCodePoint, base.recipeCodePoint);
      assert.equal(entry.glyphName, `${base.glyphName}.middle${side === "left" ? "Left" : "Right"}`);
      assert.equal(entry.familyId, `${base.familyId}-extended-middle-legs`);
      assert.deepEqual(entry.postures, ["Roman", "Italic"]);
      assert.equal(entry.oldCodePoint, null);
      let middleIndex = 0;
      for (const [partIndex, part] of entry.parts.entries()) {
        const prior = base.parts[partIndex];
        if (part.middle) {
          const end = part.kind === "leg" ? "lower" : "upper";
          const expected = entry.middleLegExtensions[middleIndex++] ? "straight" : "none";
          assert.deepEqual(part, {...prior, [end]: expected}, entry.glyphId);
        } else if (part.kind === "bowl" && part.long) {
          const neighbor = entry.parts[part.closingNeighbor];
          assert.deepEqual(part, {...prior, returnContact: neighbor[part.closingEnd] === "straight"}, entry.glyphId);
        } else assert.deepEqual(part, prior, entry.glyphId);
      }
    }
  }
});

test("independent additions preserve every prior allocation identity and display order", () => {
  const baseline = JSON.parse(gunzipSync(fs.readFileSync(path.join(__dirname, "../resources/provenance/italic-completion-baseline.json.gz"))));
  assert.equal(baseline.entries.length, 832);
  const withoutPostures = ({postures, ...identity}) => identity;
  assert.deepEqual(allocation.entries.slice(0, 832).map(withoutPostures), baseline.entries.map(withoutPostures));
  assert.deepEqual(allocation.entries.slice(832).map(entry => entry.legacyIndex), Array.from({length:384}, (_, index) => 832 + index));
  assert.deepEqual(allocation.entries.slice(832).map(entry => entry.codePoint), Array.from({length:384}, (_, index) => 0xF2E00 + index));
  assert.equal(new Set(allocation.entries.map(entry => entry.glyphName)).size, 1216);
  assert.equal(new Set(allocation.displayOrder).size, 1216);
  assert.equal(allocation.displayOrder.length, 1216);
  const previousIds = new Set(baseline.entries.map(entry => entry.glyphId));
  const priorByCode = [...baseline.entries].sort((a, b) => a.codePoint - b.codePoint).map(entry => entry.glyphId);
  assert.deepEqual(allocation.displayOrder.filter(id => previousIds.has(id)), priorByCode);
  assert.deepEqual([allocation.version, allocation.previousVersion], ["0.240", "0.220"]);
  assert.equal(allocation.blocks.find(block => block.id === "quintessential-latin-extensions").end, 0xF2FFF);
});

test("mixed middle states name visual sides and close only against the selected adjacent upright", () => {
  const expected = {
    "triple-arch-extended-left-middle-leg": "stem with descender and stem and leg",
    "triple-arch-extended-right-middle-leg": "two stems with descender and leg",
    "turned-triple-arch-extended-left-middle-leg": "arm with ascender and two stems",
    "turned-triple-arch-extended-right-middle-leg": "arm with stem and ascender and stem",
    "double-arched-opposed-bowls-0-0-extended-left-middle-leg": "stem with descender and spine and two stems",
    "double-arched-opposed-bowls-0-0-extended-right-middle-leg": "two stems with spine and ascender and stem",
    "triple-arch-right-tail-extended-left-middle-leg": "stem with descender and stem and long open bowl",
    "triple-arch-right-tail-extended-right-middle-leg": "three stems with long bowl",
    "turned-triple-arch-left-hook-extended-left-middle-leg": "long bowl with three stems",
    "turned-triple-arch-left-hook-extended-right-middle-leg": "long open bowl with stem and ascender and stem"
  };
  for (const [id, name] of Object.entries(expected)) {
    assert.equal(nameParts(allocation.entries.find(entry => entry.glyphId === id).parts), name, id);
  }
});
test("requested code points use uniform letter names and simplified upright counts", () => {
  const expected = new Map([
    [0xF2A61, "QUINTESSENTIAL LATIN LETTER HIP WITH TWO ASCENDERS"],
    [0xF2AA9, "QUINTESSENTIAL LATIN LETTER LONG ARM WITH TWO ASCENDERS"],
    [0xF2C00, "QUINTESSENTIAL LATIN LETTER THREE STEMS WITH SHOULDER"],
    [0xF2A7C, "QUINTESSENTIAL LATIN LETTER TWO STEMS WITH LEG"]
  ]);
  for (const [codePoint, name] of expected) {
    assert.equal(allocation.entries.find(entry => entry.codePoint === codePoint)?.name, name);
  }
  cases([
    [[body("hip"), arm("straight", true), stem("straight")], "hip with two ascenders"],
    [[arm("straight"), arm("straight", true), stem("straight")], "long arm with two ascenders"],
    [[stem(), leg("none", true), leg("none", true), body("shoulder")], "three stems with shoulder"],
    [[stem("none", "straight"), leg("straight", true), leg("straight")], "two descenders with long leg"],
    [[body("hip"), arm("straight", true), arm("straight", true), stem("straight")], "hip with three ascenders"]
  ]);
});
test("Special names and adjacent interior closures remain explicit structural fixtures", () => {
  const expected = {
    "special-ring":"bowl", "special-closed-double-bowl":"double bowl",
    "special-open-bowl":"open bowl", "special-turned-open-bowl":"turned open bowl",
    "special-double-open-bowl":"double open bowl", "special-turned-double-open-bowl":"turned double open bowl",
    "special-spine":"spine",
    "triple-arch-right-tail-extended-middle-legs":"stem with descender and stem and long bowl",
    "turned-triple-arch-left-hook-extended-middle-legs":"long bowl with stem and ascender and stem"
  };
  for (const [id, name] of Object.entries(expected)) {
    const entry = allocation.entries.find(e => e.glyphId === id);
    assert.equal(nameParts(entry.parts), name, id);
  }
});
test("unsupported long bowl adjacency and spine opening states fail", () => {
  assert.throws(() => nameParts([stem(), leg("straight", true), longBowl(0, "lower")]));
  assert.throws(() => nameParts([stem(), {kind:"bowl",long:true}]));
  assert.throws(() => nameParts([{kind:"spine",open:true}]));
  assert.throws(() => nameParts([{kind:"spine",closed:true}]));
});

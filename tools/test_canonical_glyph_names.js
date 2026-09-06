"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
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

test("middle roles and the four exact count abbreviations are preserved", () => {
  cases([
    [[stem(), leg("none", true), leg()], "stem with two legs"],
    [[stem("straight"), leg("none", true), leg()], "ascender with two legs"],
    [[stem(), leg("straight", true), leg("straight")], "stem with two long legs"],
    [[arm(), arm("none", true), stem()], "two arms with stem"],
    [[arm("straight"), arm("straight", true), stem()], "two long arms with stem"],
    [[stem(), leg("straight", true), leg()], "stem with long middle leg and leg"],
    [[stem(), leg("none", true), leg("straight")], "stem with middle leg and long leg"],
    [[arm(), arm("straight", true), stem()], "arm with long middle arm and stem"],
    [[arm("straight"), arm("none", true), stem()], "long arm with middle arm and stem"],
    [[stem(), leg("none", true), body("shoulder")], "stem with middle leg and shoulder"],
    [[body("hip"), arm("none", true), stem()], "hip with middle arm and stem"],
    [[stem(), leg("none", true), bowl()], "stem with middle leg and bowl"],
    [[bowl(), arm("none", true), stem()], "bowl with middle arm and stem"]
  ]);
});

test("count rules require adjacent matching terminal and middle roles", () => {
  cases([
    [[stem(), leg("none", true), leg("none", true)], "stem with middle leg and middle leg"],
    [[arm("none", true), arm("none", true), stem()], "middle arm with middle arm and stem"],
    [[stem(), leg("none", true), spine(), leg()], "stem with middle leg and spine and leg"],
    [[arm(), spine(), arm("none", true), stem()], "arm with spine and middle arm and stem"],
    [[stem(), leg("none", true), leg("none", true), leg()], "stem with middle leg and two legs"],
    [[arm(), arm("none", true), arm("none", true), stem()], "two arms with middle arm and stem"]
  ]);
});

test("Section 8 final long bowls close against the immediate middle leg", () => {
  cases([
    [[stem(), leg("none", true), longBowl(1, "lower")], "stem with middle leg and long open bowl"],
    [[stem("none", "straight"), leg("none", true), longBowl(1, "lower")], "descender with middle leg and long open bowl"],
    [[stem(), leg("straight", true), longBowl(1, "lower")], "stem with middle leg and long bowl"],
    [[stem("none", "straight"), leg("straight", true), longBowl(1, "lower")], "descender with middle leg and long bowl"]
  ]);
});

test("Section 8 initial long bowls close against the immediate middle arm", () => {
  cases([
    [[longBowl(1, "upper"), arm("none", true), stem()], "long open bowl with middle arm and stem"],
    [[longBowl(1, "upper"), arm("none", true), stem("straight")], "long open bowl with middle arm and ascender"],
    [[longBowl(1, "upper"), arm("straight", true), stem()], "long bowl with middle arm and stem"],
    [[longBowl(1, "upper"), arm("straight", true), stem("straight")], "long bowl with middle arm and ascender"]
  ]);
});

test("changing every distant main-upright extension leaves middle-neighbor closure local", () => {
  for (const upper of ["none", "straight", "curved"]) {
    for (const lower of ["none", "straight", "curved"]) {
      for (const middleExtension of ["none", "straight"]) {
        const final = freeze([stem(upper, lower), leg(middleExtension, true), longBowl(1, "lower")]);
        const initial = freeze([longBowl(1, "upper"), arm(middleExtension, true), stem(upper, lower)]);
        const expected = middleExtension === "straight" ? "long bowl" : "long open bowl";
        assert.ok(nameParts(final).endsWith(` and ${expected}`));
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
    [["stem", "middle leg", "long open bowl"], "stem with middle leg and long open bowl"],
    [["stem", "spine", "stem"], "stem with spine and stem"],
    [["two arms", "stem"], "two arms with stem"],
    [["A", "B", "C", "D"], "A with B and C and D"]
  ];
  for (const [terms, expected] of fixtures) assert.equal(formatParts(freeze(terms)), expected);
  assert.throws(() => formatParts([]));
  assert.throws(() => nameParts([]));
});

test("default extensions and explicit absent extensions name the same structure", () => {
  cases([
    [[{ kind: "stem" }, { kind: "leg", middle: true }, { kind: "leg" }], "stem with two legs"],
    [[{ kind: "arm" }, { kind: "arm", middle: true }, { kind: "stem" }], "two arms with stem"]
  ]);
  assert.equal(nameParts([{ kind: "stem" }]), nameParts([stem()]));
});


test("all 832 neutral structures retain unique canonical names without mutation", () => {
  assert.equal(allocation.entries.length, 832);
  const seen = new Set();
  for (const entry of allocation.entries) {
    assert.ok(!("model" in entry) && !("language" in entry) && !("role" in entry));
    const parts = freeze(structuredClone(entry.parts));
    const original = structuredClone(parts);
    assert.equal(canonicalName(parts), entry.canonicalName, entry.glyphId);
    assert.deepEqual(parts, original);
    assert.ok(!seen.has(entry.canonicalName), entry.glyphId);
    seen.add(entry.canonicalName);
  }
});
test("Special names and adjacent middle closures remain explicit structural fixtures", () => {
  const expected = {
    "special-ring":"bowl", "special-closed-double-bowl":"double bowl",
    "special-open-bowl":"open bowl", "special-turned-open-bowl":"turned open bowl",
    "special-double-open-bowl":"double open bowl", "special-turned-double-open-bowl":"turned double open bowl",
    "special-spine":"spine",
    "triple-arch-right-tail-extended-middle-legs":"stem with long middle leg and middle leg and long bowl",
    "turned-triple-arch-left-hook-extended-middle-legs":"long bowl with middle arm and long middle arm and stem"
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

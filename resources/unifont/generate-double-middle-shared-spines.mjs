import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const directory = path.dirname(fileURLToPath(import.meta.url));
const allocation = JSON.parse(fs.readFileSync(path.join(directory, "../quintessential-latin-allocation.json"), "utf8"));
const families = ["left-double-arched-opposed-bowls", "right-double-arched-opposed-bowls"];
const blank = "........";

// Literal body drawings. The narrow spine retains the approved row-9 crossover.
// Its outward stave retains a native head/foot connection at the cell boundary.
const bodies = {
  left: [".##.#.##", ".#.#.#.#", ".#.#.#.#", ".#.#.###", ".#.#.#.#", ".#.#.#.#", ".#.#.#.#", ".#.#.###"],
  right: [".###.#.#", ".#.#.#.#", ".#.#.#.#", ".###.#.#", ".#.#.#.#", ".#.#.#.#", ".#.#.#.#", ".##.#.##"],
};

function regions(rows, ink, diagonal) {
  const visited = new Set();
  const result = [];
  const steps = diagonal
    ? [-1, 0, 1].flatMap(dy => [-1, 0, 1].filter(dx => dx || dy).map(dx => [dx, dy]))
    : [[-1, 0], [1, 0], [0, -1], [0, 1]];
  for (let y = 0; y < 16; y++) for (let x = 0; x < 8; x++) {
    if ((rows[y][x] === "#") !== ink || visited.has(`${x},${y}`)) continue;
    const queue = [[x, y]];
    const points = [];
    visited.add(`${x},${y}`);
    while (queue.length) {
      const [px, py] = queue.pop();
      points.push([px, py]);
      for (const [dx, dy] of steps) {
        const nx = px + dx, ny = py + dy, key = `${nx},${ny}`;
        if (nx < 0 || nx > 7 || ny < 0 || ny > 15 || visited.has(key) || (rows[ny][nx] === "#") !== ink) continue;
        visited.add(key);
        queue.push([nx, ny]);
      }
    }
    result.push({ points, exterior: points.some(([px, py]) => px === 0 || px === 7 || py === 0 || py === 15) });
  }
  return result;
}

function draw(entry, side) {
  const rows = [...Array(6).fill(blank), ...bodies[side], blank, blank].map(row => row.split(""));
  const put = coordinates => coordinates.forEach(([x, y]) => { rows[y][x] = "#"; });
  const outerMasks = [];
  const outer = (partIndex, pixels) => { put(pixels); outerMasks.push({ partIndex, pixels }); };
  const left = entry.parts[0], right = entry.parts.at(-1);
  if (left.upper === "straight") outer(0, [[1, 3], [1, 4], [1, 5]]);
  if (left.upper === "curved") outer(0, [[2, 3], [1, 4], [3, 4], [1, 5]]);
  if (left.lower === "straight") outer(0, [[1, 14], [1, 15]]);
  if (right.upper === "straight") outer(4, [[7, 3], [7, 4], [7, 5]]);
  if (right.lower === "straight") outer(4, [[7, 14], [7, 15]]);
  if (right.lower === "curved") outer(4, [[7, 14], [5, 15], [6, 15]]);
  const middle = entry.parts.map((part, partIndex) => ({ ...part, partIndex })).filter(part => part.middle);
  const extensionState = middle.map(part => part.lower === "straight" || part.upper === "straight");
  const extensionPixels = [];
  const components = middle.map((part, index) => {
    const x = 3 + 2 * index;
    const extension = side === "left" ? [[x, 14], [x, 15]] : [[x, 3], [x, 4], [x, 5]];
    if (extensionState[index]) { put(extension); extensionPixels.push(...extension); }
    return { partIndex: part.partIndex, kind: part.kind, column: x, extended: extensionState[index], pixels: extension };
  });
  return { rows: rows.map(row => row.join("")), extensionState, extensionPixels, components, outerMasks };
}

const result = {
  schemaVersion: 1,
  sourceReferences: ["generate-double-middle-shared-spines.mjs"],
  layoutTemplates: Object.fromEntries(families.map(family => [family, { bodyRows: [...Array(6).fill(blank), ...bodies[family.startsWith("left-") ? "left" : "right"], blank, blank] }])),
  groups: [], glyphs: [],
};
for (const familyId of families) {
  const side = familyId.startsWith("left-") ? "left" : "right";
  const entries = allocation.entries.filter(entry => entry.familyId === familyId).sort((a, b) => a.codePoint - b.codePoint);
  if (entries.length !== 144) throw new Error(`Unexpected allocation for ${familyId}`);
  for (let groupStart = 0; groupStart < entries.length; groupStart += 4) {
    const quartet = entries.slice(groupStart, groupStart + 4);
    const base = draw(quartet[0], side);
    const groupId = quartet[0].glyphId;
    result.groups.push({ id: groupId, title: quartet[0].canonicalName, glyphIds: quartet.map(entry => entry.glyphId), notes: "Neither, left only, right only, and both middle extensions, in current visual part order. All body and outer-terminal pixels are fixed within this quartet." });
    for (const entry of quartet) {
      const drawing = draw(entry, side);
      const foreground = regions(drawing.rows, true, true);
      const counters = regions(drawing.rows, false, false).filter(region => !region.exterior);
      if (foreground.length !== 1) throw new Error(`Disconnected drawing: ${entry.glyphId}`);
      const coreX = side === "left" ? 6 : 2;
      const spineSeeds = [[coreX, 7], [coreX, 10]];
      const coreCounters = spineSeeds.map(([x, y]) => counters.find(region => region.points.some(([px, py]) => px === x && py === y)));
      if (coreCounters.some((region, index) => !region || region.points.length !== [2, 3][index])) throw new Error(`Spine counter damaged: ${entry.glyphId}`);
      const contact = side === "left"
        ? entry.parts.at(-1).lower === "curved" && drawing.extensionState[1]
        : entry.parts[0].upper === "curved" && drawing.extensionState[0];
      if (counters.length !== (contact ? 3 : 2)) throw new Error(`Unexpected terminal topology: ${entry.glyphId}`);
      const notes = [
        "Keep four one-pixel staves at columns 1, 3, 5 and 7, with column 0 blank.",
        side === "left" ? "Two compressed native-m arches enter a shared spine between columns 5 and 7." : "A shared spine between columns 1 and 3 exits through two compressed native-u hips.",
        "The approved row-9 crossover retains a two-pixel upper counter and a three-pixel lower counter.",
        side === "left" ? "The outward right stave retains its baseline terminal at (7,13)." : "The outward left stave retains its head at (1,6).",
        "Simple upper hooks and lower tails use the approved narrow native-terminal masks. Independent middle extensions add only pixels above or below the unchanged body.",
      ];
      if (contact) notes.push("The compact hook meets the adjacent independently extended stave, producing a small terminal counter. The hooked ending remains distinct from a straight ending; no long-bowl return contact is declared by this allocation.");
      const glyph = {
        glyphId: entry.glyphId, width: 8, rows: drawing.rows,
        donors: ["0061", "0250", "006D", "026F", "0075", "0066", "014B"],
        notes: notes.join(" "),
        expected: { components: 1, counters: counters.length },
        reviewNotes: contact ? ["Inspect the compact hook contact with the adjacent extended stave; the additional terminal counter is separate from both unchanged shared-spine counters."] : [],
        groupId, extensionState: drawing.extensionState, extensionPixels: drawing.extensionPixels,
        layout: { templateId: familyId, familyId, staveColumns: [1, 3, 5, 7], spineColumns: side === "left" ? [5, 6, 7] : [1, 2, 3], crossoverRow: 9, bodyRows: [6, 13], middleParts: drawing.components, outerMasks: drawing.outerMasks },
        structuralChecks: { counterSeeds: spineSeeds, counterAreas: [2, 3], terminalContact: contact ? { position: side === "left" ? "lower-right" : "upper-left", neighborPartIndex: side === "left" ? 2 : 2, counterSeed: side === "left" ? [6, 14] : [2, 4], allocationReturnContact: false } : null },
      };
      if (entry.glyphId !== quartet[0].glyphId) {
        const addPixels = [];
        for (let y = 0; y < 16; y++) for (let x = 0; x < 8; x++) {
          if (base.rows[y][x] === "#" && drawing.rows[y][x] !== "#") throw new Error("Extension removed a body pixel");
          if (base.rows[y][x] !== drawing.rows[y][x]) addPixels.push([x, y]);
        }
        glyph.recipe = { baseGlyphId: quartet[0].glyphId, addPixels, removePixels: [], joinPixels: [] };
      }
      result.glyphs.push(glyph);
    }
  }
}

const output = path.join(directory, "double-middle-shared-spines.json");
const serialized = `${JSON.stringify(result, null, 2)}\n`;
if (process.argv.includes("--check")) {
  if (fs.readFileSync(output, "utf8") !== serialized) throw new Error("Generated sources differ");
} else fs.writeFileSync(output, serialized);
console.log(`${result.glyphs.length} drawings; ${result.groups.length} independent-extension quartets; ${result.glyphs.filter(glyph => glyph.structuralChecks.terminalContact).length} compact hook contacts.`);

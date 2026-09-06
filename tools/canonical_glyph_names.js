"use strict";

// Canonical naming v2 for neutral structural component arrays.
// Components describe visible construction independently of any language.
const EXTENSIONS = ["none", "straight", "curved"];
const PRIMITIVES = [
  ["stem", "ascender", "hook"],
  ["descender", "long stem", "long hook"],
  ["tail", "long tail", "long spine"]
];

function formatParts(terms) {
  if (!Array.isArray(terms) || !terms.length || terms.some(term => typeof term !== "string" || !term.trim())) {
    throw new Error("Cannot name an empty construction or component.");
  }
  return terms.length === 1 ? terms[0] : `${terms[0]} with ${terms.slice(1).join(" and ")}`;
}

function extension(part, end) {
  const value = part[end] ?? "none";
  if (!EXTENSIONS.includes(value)) throw new Error(`Unsupported ${end} extension: ${value}`);
  return value;
}

function nameParts(parts) {
  if (!Array.isArray(parts) || !parts.length) throw new Error("Cannot name an empty construction.");
  for (const part of parts) {
    if (["leg", "arm"].includes(part.kind)) {
      const free = extension(part, part.kind === "leg" ? "lower" : "upper");
      const joined = extension(part, part.kind === "leg" ? "upper" : "lower");
      if (free === "curved" || joined !== "none") throw new Error("Unsupported branch extension in full geometry.");
    }
  }
  const implied = parts.map(() => new Set());
  // Evaluate all returns against the full geometry before omitting anything.
  const closed = parts.map((part, index) => {
    if (part.kind !== "bowl" || !part.long) return false;
    const neighbor = parts[part.closingNeighbor];
    if (!neighbor || Math.abs(part.closingNeighbor - index) !== 1
      || !["stem", "leg", "arm"].includes(neighbor.kind)
      || !["upper", "lower"].includes(part.closingEnd)
      || part.closingEnd !== (part.closingNeighbor > index ? "upper" : "lower")
      || typeof part.returnContact !== "boolean") {
      throw new Error("A long bowl requires its actual adjacent closing upright and return contact.");
    }
    const contact = part.returnContact && extension(neighbor, part.closingEnd) === "straight";
    if (contact) implied[part.closingNeighbor].add(part.closingEnd);
    return contact;
  });
  const named = parts.map((part, index) => {
    const upper = implied[index].has("upper") ? "none" : extension(part, "upper");
    const lower = implied[index].has("lower") ? "none" : extension(part, "lower");
    let text;
    switch (part.kind) {
      case "stem": text = PRIMITIVES[EXTENSIONS.indexOf(lower)][EXTENSIONS.indexOf(upper)]; break;
      case "leg":
      case "arm": {
        const free = part.kind === "leg" ? lower : upper;
        const joined = part.kind === "leg" ? upper : lower;
        if (free === "curved" || joined !== "none") throw new Error("Unsupported branch extension; returning branches use the long-bowl constructor.");
        text = `${free === "straight" ? "long " : ""}${part.middle ? "middle " : ""}${part.kind}`;
        break;
      }
      case "bowl": text = part.long ? `long ${closed[index] ? "" : "open "}bowl` : `${part.turnedSpecial ? "turned " : ""}${part.open ? "open " : ""}bowl`; break;
      case "spine":
        if (part.open !== undefined || part.closed !== undefined) throw new Error("Spines have no opening state.");
        text = `${part.long ? "long " : ""}spine`; break;
      case "shoulder": case "hip": text = part.kind; break;
      case "double bowl": text = `${part.turnedSpecial ? "turned " : ""}double ${part.open ? "open " : ""}bowl`; break;
      default: throw new Error(`Unsupported semantic component: ${part.kind}`);
    }
    return { kind: part.kind, middle: Boolean(part.middle), text };
  });
  const terms = [];
  for (let index = 0; index < named.length; index += 1) {
    const left = named[index], right = named[index + 1];
    const legPair = left.kind === "leg" && left.middle && right?.kind === "leg" && !right.middle;
    const armPair = left.kind === "arm" && !left.middle && right?.kind === "arm" && right.middle;
    const sameLength = right && left.text.startsWith("long ") === right.text.startsWith("long ");
    if ((legPair || armPair) && sameLength) {
      terms.push(`two ${left.text.startsWith("long ") ? "long " : ""}${left.kind}s`);
      index += 1;
    } else terms.push(left.text);
  }
  return formatParts(terms);
}


function canonicalName(parts) { return nameParts(parts); }
module.exports = { canonicalName, nameParts, formatParts };

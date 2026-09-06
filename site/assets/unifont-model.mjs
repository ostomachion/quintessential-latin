import {escapeHtml as esc, code, anchor} from './model.mjs';
import {typeGuidesMarkup} from './type-guides.mjs';

// Row boundaries in the pinned 16px Latin design: capitals occupy rows 4–13,
// the x-height body rows 6–13, and descenders continue through row 15.
const BITMAP_METRICS = [
  {id:'cap', label:'Cap height', row:4},
  {id:'xheight', label:'x-height', row:6},
  {id:'baseline', label:'Baseline', row:14},
  {id:'descender', label:'Descender', row:16},
];

// Roman Czyborra's Unifont format: one scalar and 16 rows of MSB-first bits.
export function parseHex(source) {
  const glyphs = new Map();
  for (const [index, line] of source.trim().split(/\r?\n/).entries()) {
    const match = line.match(/^([0-9A-F]{4}|[0-9A-F]{6}):([0-9A-F]{32}|[0-9A-F]{64})$/);
    if (!match) throw new Error(`Invalid Unifont .hex line ${index + 1}`);
    const point = parseInt(match[1], 16), bits = match[2];
    if (point > 0x10FFFF || (point >= 0xD800 && point <= 0xDFFF) || glyphs.has(point)) {
      throw new Error(`Invalid or duplicate Unifont scalar on line ${index + 1}`);
    }
    if (match[1].length !== (point > 0xFFFF ? 6 : 4)) throw new Error(`Noncanonical Unifont scalar on line ${index + 1}`);
    const width = bits.length / 4;
    const rows = Array.from({length:16}, (_, y) => parseInt(bits.slice(y * width / 4, (y + 1) * width / 4), 16));
    glyphs.set(point, {point, width, rows, line});
  }
  return glyphs;
}

export function inspectorMarkup(glyph){
  return `<article class="bitmap-card" id="bitmap-${glyph.codePoint.toString(16)}" tabindex="-1"><p class="code">${code(glyph.codePoint)} · ${glyph.width} × 16</p><h3>${esc(glyph.canonicalName)}</h3><p class="bitmap-review-status">${glyph.reviewStatus==='inspected'?'Agent inspected · awaiting your review':'Drawing · inspection pending'}</p><div class="bitmap-proof"><div class="bitmap-paper">${bitmapGuideProof(glyph)}</div><div class="bitmap-native"><span>Actual size</span>${bitmapSvg(glyph)}<span>2×</span>${bitmapSvg(glyph,2)}</div></div><p class="bitmap-guides">Rows 6–13: x-height body. Column 0: spacing. Guides follow pixel boundaries.</p><div class="inspector-outline"><span>Quintessential Serif</span>${outlineGuideProof(glyph)}</div><p class="drawing-note">${esc(glyph.notes)}</p><details class="bitmap-source"><summary>HEX data &amp; pixel checks</summary><code>${glyph.line}</code><p>${glyph.assessment.components} connected body · ${glyph.assessment.counters} enclosed spaces</p><p>${glyph.assessment.flagCount??glyph.assessment.flags.length} pixel flags recorded for review.</p></details><p><a class="bitmap-reference" href="unifont/proofs/${esc(glyph.familyId)}.html#bitmap-${glyph.codePoint.toString(16)}">Full proof &amp; native donors →</a></p><a class="bitmap-reference" href="charts.html#${anchor(glyph.codePoint)}">Outline character details →</a></article>`;
}

export function bitmapGuideProof(glyph, scale = 8) {
  return `<div class="bitmap-guided-proof" style="--bitmap-proof-width:${glyph.width*scale}px">${bitmapSvg(glyph,scale,true)}${BITMAP_METRICS.map(metric=>`<span class="bitmap-guide-label bitmap-guide-${metric.id}" style="top:${metric.row/16*100}%">${metric.label}</span>`).join('')}</div>`;
}

export function outlineGuideProof(glyph) {
  return `<span class="type-study bitmap-outline-study">${typeGuidesMarkup()}<span class="outline-reference" aria-hidden="true">${String.fromCodePoint(glyph.codePoint)}</span></span>`;
}

function bitmapPath(glyph, offset = 0) {
  const {width, rows} = glyph;
  let pixels = '';
  for (let y = 0; y < 16; y++) for (let x = 0; x < width; x++) {
    if (rows[y] & (1 << (width - x - 1))) pixels += `M${offset+x} ${y}h1v1h-1z`;
  }
  return pixels;
}

// A continuous run needs a single SVG paint origin. Separate SVG roots can
// each round differently during scrolling, even with correct layout advances.
export function bitmapSequenceSvg(glyphs, scale = 1) {
  let width = 0, pixels = '';
  for (const glyph of glyphs) {
    pixels += bitmapPath(glyph, width);
    width += glyph.width;
  }
  return `<svg class="bitmap bitmap-run" data-bitmap-width="${width}" data-bitmap-scale="${scale}" xmlns="http://www.w3.org/2000/svg" width="${width*scale}" height="${16*scale}" viewBox="0 0 ${width} 16" aria-hidden="true" shape-rendering="crispEdges"><path fill="currentColor" d="${pixels}"/></svg>`;
}

export function bitmapSvg(glyph, scale = 1, guides = false) {
  const {width} = glyph, pixels = bitmapPath(glyph);
  const grid = guides ? `<path class="bitmap-grid" d="${Array.from({length:width+1}, (_,x)=>`M${x} 0V16`).join('')}${Array.from({length:17}, (_,y)=>`M0 ${y}H${width}`).join('')}"/>${BITMAP_METRICS.map(metric=>`<path class="bitmap-metrics bitmap-metric-${metric.id}" data-metric="${metric.id}" d="M0 ${metric.row}H${width}"/>`).join('')}` : '';
  return `<svg class="bitmap${guides?' bitmap-enlarged':''}" data-bitmap-width="${width}" data-bitmap-scale="${scale}" xmlns="http://www.w3.org/2000/svg" width="${width*scale}" height="${16*scale}" viewBox="0 0 ${width} 16" aria-hidden="true" shape-rendering="crispEdges"><path fill="currentColor" d="${pixels}"/>${grid}</svg>`;
}

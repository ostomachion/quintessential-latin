export const VERSION = '0.220';
export const code = value => `U+${Number(value).toString(16).toUpperCase().padStart(5, '0')}`;
export const anchor = value => `u-${Number(value).toString(16).toLowerCase()}`;
export const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
export function normalizeSettings(value) {
  return {weight: Math.min(700, Math.max(400, Number(value?.weight) || 400)), italic: value?.italic === true};
}
export function available(entry, italic) { return entry.postures.includes(italic ? 'Italic' : 'Roman'); }
export function searchEntries(entries, query, family = '') {
  const words = query.trim().toLowerCase().replace(/^u\+/, '').split(/\s+/).filter(Boolean);
  return entries.filter(entry => (!family || entry.familyId === family) && words.every(word => `${entry.name} ${entry.canonicalName} ${entry.codePoint.toString(16)} ${String.fromCodePoint(entry.codePoint)}`.toLowerCase().includes(word)));
}
export function glyphSize(entry, availableWidth = 48, maximum = 32) {
  const advances = Object.values(entry.metrics || {}).map(metric => Math.max(metric.advance, metric.bounds?.[2] || 0) - Math.min(0, metric.bounds?.[0] || 0));
  return Math.min(maximum, availableWidth * 1000 / Math.max(1000, ...advances));
}
export function chartCode(start, row, column) { return start + column * 16 + row; }
export function printableSheets(blocks) {
  return blocks.flatMap(block => Array.from({length:(block.end - block.start + 1) / 128}, (_, index) => ({block, start:block.start + index * 128, end:block.start + index * 128 + 127})));
}

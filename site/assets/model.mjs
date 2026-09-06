export const VERSION = '0.250';
export const code = value => `U+${Number(value).toString(16).toUpperCase().padStart(5, '0')}`;
export const anchor = value => `u-${Number(value).toString(16).toLowerCase()}`;
export const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
export function normalizeSettings(value) {
  return {weight: Math.min(700, Math.max(400, Number(value?.weight) || 400)), italic: value?.italic === true};
}
export function available(entry, italic) { return entry.postures.includes(italic ? 'Italic' : 'Roman'); }
export function searchEntries(entries, query, family = '') {
  const words = query.trim().toLowerCase().replace(/^u\+/, '').split(/\s+/).filter(Boolean);
  return entries.filter(entry => (!family || entry.familyId === family) && words.every(word => `${entry.name} ${entry.canonicalName} ${entry.codePoint.toString(16)} ${String.fromCodePoint(entry.codePoint)}`.toLowerCase().includes(word))).sort((a,b)=>a.codePoint-b.codePoint);
}
export function glyphSize(entry, availableWidth = 48, maximum = 32) {
  const advances = Object.values(entry.metrics || {}).map(metric => Math.max(metric.advance, metric.bounds?.[2] || 0) - Math.min(0, metric.bounds?.[0] || 0));
  return Math.min(maximum, availableWidth * 1000 / Math.max(1000, ...advances));
}
export function chartCode(start, row, column) { return start + column * 16 + row; }
export function printableSheets(blocks) {
  return blocks.flatMap(block => Array.from({length:Math.ceil((block.end - block.start + 1) / 256)}, (_, index) => ({block, start:block.start + index * 256, end:Math.min(block.end,block.start + index * 256 + 255)})));
}
export function chartChunks(sheet, maximumColumns = 16) {
  const count = maximumColumns * 16;
  return Array.from({length:Math.ceil((sheet.end-sheet.start+1)/count)}, (_,index) => {
    const start=sheet.start+index*count, end=Math.min(sheet.end,start+count-1);
    return {...sheet,start,end,columns:(end-start+1)/16};
  });
}

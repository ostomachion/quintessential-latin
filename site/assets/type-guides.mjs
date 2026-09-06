// Decorative rules share their positions with the font-metric CSS in style.css.
// Labels are shown once per study, rather than repeated on every small glyph.
export function typeGuidesMarkup(labels = false) {
  return [['cap','Cap height'],['xheight','x-height'],['baseline','Baseline'],['descender','Descender']]
    .map(([metric,label])=>`<span class="type-rule" data-metric="${metric}" aria-hidden="true">${labels?`<span>${label}</span>`:''}</span>`).join('');
}

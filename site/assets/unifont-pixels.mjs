// SVG crispEdges alone rounds each edge separately. Give every source pixel
// the same whole number of device pixels, then align the cell's screen origin.
// Keep the SVG paths as the static/no-script and print representation.
const selector = 'svg.bitmap[data-bitmap-scale]';
const cells = new Map(), visible = new Set(), ownStyles = new WeakMap();
let frame = 0, density = 0, printing = false;

function style(element, property, value) {
  if (element.style.getPropertyValue(property) === value) return;
  element.style.setProperty(property, value);
  ownStyles.set(element, element.getAttribute('style'));
}

function screenGrid() {
  const viewport = window.visualViewport;
  return {ratio: window.devicePixelRatio * (viewport?.scale || 1),
    left: viewport?.offsetLeft || 0, top: viewport?.offsetTop || 0};
}

function resizeCell(svg, state, ratio) {
  const pixel = Math.max(1, Math.round(state.scale * ratio)) / ratio;
  style(svg, 'width', `${state.width * pixel}px`);
  style(svg, 'height', `${16 * pixel}px`);
  if (state.target !== svg) {
    style(state.target, '--bitmap-proof-width', `${state.width * pixel}px`);
    style(state.target, '--bitmap-pixel', `${pixel}px`);
  }
}

function schedule() {
  if (!frame && !printing) frame = requestAnimationFrame(align);
}

const intersections = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (!cells.has(entry.target)) continue;
    if (entry.isIntersecting) visible.add(entry.target);
    else visible.delete(entry.target);
  }
  schedule();
}, {rootMargin:'200px'});
const sizes = new ResizeObserver(schedule);

function collect(root) {
  const added = root.matches?.(selector) ? [root] : [...(root.querySelectorAll?.(selector) || [])];
  for (const svg of added) {
    if (cells.has(svg)) continue;
    const target = svg.closest('.coordinate-proof, .bitmap-guided-proof') || svg;
    const state = {width:Number(svg.dataset.bitmapWidth), scale:Number(svg.dataset.bitmapScale), target, dx:0, dy:0};
    cells.set(svg, state);
    resizeCell(svg, state, screenGrid().ratio);
    intersections.observe(svg);
    sizes.observe(target.parentElement);
    // Align visible first-paint content without waiting for intersection delivery.
    visible.add(svg);
  }
}

function align() {
  frame = 0;
  const grid = screenGrid();
  if (grid.ratio !== density) {
    density = grid.ratio;
    for (const [svg, state] of cells) resizeCell(svg, state, density);
  }
  // Batch reads before writes. Relative offsets preserve the layout slots.
  // CSS transforms can move an already-snapped SVG painting a second time,
  // giving the right bounding box but the wrong ink origin in Chromium.
  const moves = [], viewports = [], sequences = new Map();
  function sequencePosition(svg) {
    const parent = svg.parentElement;
    if (!parent.matches('.bitmap-sequence')) return null;
    if (!sequences.has(parent)) {
      const positions = new Map();
      const siblings = [...parent.children].filter(child => cells.has(child));
      const first = siblings[0], state = cells.get(first), rect = first.getBoundingClientRect();
      let x = Math.round((rect.left - state.dx - grid.left) * density);
      const bottom = Math.round((rect.bottom - state.dy - grid.top) * density);
      const gap = Math.round((parseFloat(getComputedStyle(parent).columnGap) || 0) * density);
      // CSS app-unit widths can accumulate to a missing device pixel. Keep
      // repeated/mixed characters on one common physical advance and baseline.
      for (const child of siblings) {
        const item = cells.get(child), step = Math.max(1, Math.round(item.scale * density));
        positions.set(child, {x, y:bottom - 16 * step});
        x += item.width * step + gap;
      }
      sequences.set(parent, positions);
    }
    return sequences.get(parent).get(svg);
  }
  for (const svg of visible) {
    if (!svg.isConnected) continue;
    const state = cells.get(svg), rect = svg.getBoundingClientRect();
    if (!rect.width || !rect.height) continue; // Closed chart sheets.
    // CSS width and height round independently to layout units. Compensate in
    // SVG coordinates so every source pixel still has an exact device step;
    // a nearly integral scale can otherwise give one row an extra screen pixel.
    const step = Math.max(1, Math.round(state.scale * density));
    viewports.push([svg, `0 0 ${rect.width * density / step} ${rect.height * density / step}`]);
    const x = (rect.left - state.dx - grid.left) * density;
    const y = (rect.top - state.dy - grid.top) * density;
    const destination = sequencePosition(svg) || {x:Math.round(x), y:Math.round(y)};
    // Layout offsets have finite precision. Keep them on CSS layout units so
    // subtracting the previous correction cannot accumulate rounding drift.
    const offset = value => Math.round(value * 64) / 64;
    moves.push([state, offset((destination.x-x)/density), offset((destination.y-y)/density)]);
  }
  for (const [svg, viewBox] of viewports) {
    if (svg.getAttribute('viewBox') !== viewBox) svg.setAttribute('viewBox', viewBox);
  }
  for (const [state, dx, dy] of moves) {
    state.dx = dx; state.dy = dy;
    style(state.target, '--bitmap-snap-x', `${dx}px`);
    style(state.target, '--bitmap-snap-y', `${dy}px`);
  }
}

collect(document);
sizes.observe(document.body);
new MutationObserver(records => {
  let changed = false;
  for (const record of records) {
    if (record.type === 'attributes' && record.attributeName === 'style' &&
        ownStyles.get(record.target) === record.target.getAttribute('style')) continue;
    changed = true;
    for (const node of record.addedNodes) if (node.nodeType === 1) collect(node);
  }
  if (!changed) return;
  for (const [svg, state] of cells) if (!svg.isConnected) {
    intersections.unobserve(svg);
    // Shared parent observations are retained until the parent is detached.
    if (!state.target.parentElement?.isConnected) sizes.unobserve(state.target.parentElement || state.target);
    cells.delete(svg); visible.delete(svg);
  }
  schedule();
}).observe(document.body, {childList:true, subtree:true, attributes:true,
  attributeFilter:['style','class','open','hidden']});

// Scroll capture covers the horizontal chart scrollers as well as the page.
document.addEventListener('scroll', schedule, {capture:true, passive:true});
document.addEventListener('toggle', schedule, true);
window.addEventListener('resize', schedule);
window.addEventListener('pageshow', schedule);
window.visualViewport?.addEventListener('resize', schedule);
window.visualViewport?.addEventListener('scroll', schedule);
document.fonts.ready.then(schedule);
document.fonts.addEventListener('loadingdone', schedule);

// A move between monitors can change density without changing CSS dimensions.
let resolution;
function watchResolution() {
  resolution?.removeEventListener('change', watchResolution);
  resolution = matchMedia(`(resolution: ${devicePixelRatio}dppx)`);
  resolution.addEventListener('change', watchResolution);
  schedule();
}
watchResolution();

window.addEventListener('beforeprint', () => {
  printing = true;
  cancelAnimationFrame(frame); frame = 0;
  for (const [svg, state] of cells) {
    resizeCell(svg, state, 1);
    svg.setAttribute('viewBox', `0 0 ${state.width} 16`);
    state.dx = state.dy = 0;
    style(state.target, '--bitmap-snap-x', '0px');
    style(state.target, '--bitmap-snap-y', '0px');
  }
});
window.addEventListener('afterprint', () => { printing = false; density = 0; schedule(); });

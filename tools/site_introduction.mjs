// Editorial specimens use stable identities. Names, code points, characters,
// and coverage always come from the generated catalogue supplied by the build.
export const introductionExamples = [
  ['arch', 'arch-ascender', 'arch-descender'],
  ['bowl-ascender', 'turned-bowl-ascender', 'bowl-descender'],
  ['special-spine', 'turned-bowled-spine', 'opposed-bowls-0-0'],
];

// These are instructional centreline diagrams, not replacement glyph outlines
// or a normative ductus. Each d has one moveto and one continuous subpath.
// Their topology follows the indicated catalogue parts; the guides express
// the baseline/x-height relationship without claiming font-outline metrics.
const writingStudies = [
  {
    id: 'arch',
    parts: [{kind:'stem', lower:'none', upper:'none'}, {kind:'leg', lower:'none', middle:false, upper:'none'}],
    path: 'M100 140 L100 65 L100 86 C112 57 154 57 156 89 L156 140',
    start: [100,140],
    description: 'An n-like construction: a stem from baseline to x-height, joined near its top to an arch and a descending right leg.',
    trace: 'Trace up the stem, return partway down it, then follow the arch and leg to the baseline.',
  },
  {
    id: 'bowl-ascender',
    parts: [{kind:'stem', lower:'none', upper:'straight'}, {kind:'bowl'}],
    path: 'M100 28 L100 140 L100 75 C117 57 160 58 160 101 C160 144 119 151 100 130',
    start: [100,28],
    description: 'A b-like construction: an upright extends above x-height, with a closed rounded bowl on its right in the baseline-to-x-height region.',
    trace: 'Trace down the ascender, back up to the bowl’s upper join, around the bowl, and back to the upright.',
  },
  {
    id: 'special-spine',
    parts: [{kind:'spine'}],
    path: 'M154 76 C144 56 102 59 100 82 C97 108 158 98 157 123 C157 145 111 147 99 128',
    start: [154,76],
    description: 'An s-like spine: one continuous curved body occupying the baseline-to-x-height region.',
    trace: 'Follow the s-shaped curve from its upper terminal to its lower terminal.',
  },
];

export function renderIntroduction({catalogue, glyph, scriptLink, code, anchor, esc}) {
  const byId = new Map(catalogue.entries.map(entry => [entry.glyphId, entry]));
  const entry = id => {
    const found = byId.get(id);
    if (!found) throw new Error(`Missing introduction example: ${id}`);
    return found;
  };
  // A construction edit must trigger a review of the corresponding diagram.
  for (const study of writingStudies) {
    if (JSON.stringify(entry(study.id).parts) !== JSON.stringify(study.parts)) {
      throw new Error(`Introduction diagram no longer matches catalogue parts: ${study.id}`);
    }
  }
  const label = id => esc(entry(id).canonicalName);
  const specimen = (id, relation) => {
    const value = entry(id);
    return `<figure class="intro-character" data-introduction-example="${esc(id)}">${scriptLink(value,110,94,'intro-character-link')}<figcaption><span class="intro-character-name">${esc(value.canonicalName)}</span><span class="code">${code(value.codePoint)}</span>${relation ? `<span class="intro-character-relation">${relation}</span>` : ''}</figcaption></figure>`;
  };
  const study = index => {
    const value = writingStudies[index];
    return `<figure class="intro-writing-study"><svg viewBox="0 0 230 175" role="img" aria-labelledby="writing-${value.id}-title writing-${value.id}-desc" data-writing-example="${value.id}"><title id="writing-${value.id}-title">Illustrative writing path: ${label(value.id)}</title><desc id="writing-${value.id}-desc">${esc(value.description)} ${esc(value.trace)} An open circle marks this example’s starting point.</desc><g class="intro-writing-guides" aria-hidden="true"><path d="M72 65 H210 M72 140 H210"/><text x="6" y="68">x-height</text><text x="6" y="143">baseline</text></g><path class="intro-writing-path" d="${value.path}"/><circle class="intro-writing-start" cx="${value.start[0]}" cy="${value.start[1]}" r="4"/></svg><figcaption>${esc(value.trace)}</figcaption></figure>`;
  };
  const emblem = entry('opposed-bowls-0-0');
  const total = catalogue.entries.length.toLocaleString('en-US');
  return `<section class="intro-hero intro-opening"><div><p class="eyebrow">Letterforms from a shared vocabulary</p><h1>Quintessential Latin</h1><p class="lead">Familiar Latin forms, taken apart and built into a consistent system.</p><p>Quintessential Latin begins with recurring structures in Latin typography, especially lowercase letters. It uses those structures to construct a repertoire of familiar and unfamiliar letterforms, each designed to be writable in one continuous stroke.</p><div class="inline-links"><a href="#the-idea">See how it works ↓</a><a href="charts.html">Explore the characters →</a></div></div><a class="project-emblem" href="charts.html#${anchor(emblem.codePoint)}" data-glyph="${esc(emblem.glyphId)}" aria-label="${code(emblem.codePoint)} ${esc(emblem.name)}"><span class="emblem-glyph">${glyph(emblem,200,330)}</span><span class="emblem-caption"><span>${esc(emblem.canonicalName)}</span><span>A construction from the repertoire</span></span></a></section>

<section class="section-rule intro-section" id="the-idea"><p class="eyebrow">The idea</p><h2>A vocabulary of forms, beyond an inherited alphabet</h2><p>Why do <span class="latin-comparison">b</span>, <span class="latin-comparison">h</span>, and <span class="latin-comparison">n</span> look related? Their uprights, curves, and joins suggest reusable building parts. Quintessential Latin turns that observation into a deliberate design abstraction: identify useful structural features, give their combinations consistent rules, and build a repertoire from them.</p><p>The aim is a coherent vocabulary of Latin-like forms, extending beyond the particular combinations inherited by existing alphabets. This is one design informed by Latin typography, rather than a claim to the uniquely correct analysis of Latin letters or a replacement for the historical alphabet.</p><ol class="intro-progression" aria-label="The design progression"><li><strong>Familiar forms</strong><span>Start with lowercase Latin shapes.</span></li><li><strong>Recurring components</strong><span>Identify uprights, branches, and bodies.</span></li><li><strong>Consistent rules</strong><span>Specify their extensions and connections.</span></li><li><strong>A coherent repertoire</strong><span>Give each included construction an identity.</span></li></ol></section>

<section class="section-rule intro-section" id="single-stroke"><p class="eyebrow">A writing principle</p><h2>One continuous pen movement</h2><p>Each character’s underlying form is designed to be writable without lifting the pen. A font renders that form with filled outlines, contrast, serifs, and other stylistic choices. Those outlines are not the pen’s writing path.</p><p>The diagrams below show possible continuous paths through three real constructions. They are <strong>illustrative skeletons</strong>, not a prescribed handwriting standard. The first two retrace part of an upright. The principle does not require a unique starting point, forbid retracing or intersections, or require an entire word to be written in one stroke.</p><p class="intro-study-key">Open circle: one possible start. Guides: x-height and baseline. The static diagrams stay upright; the neighboring font specimens respond to the weight and Italic controls.</p></section>

<section class="intro-worked-example" id="uprights-and-branches"><div class="intro-example-heading"><span class="intro-example-number" aria-hidden="true">01</span><div><h2>Keep the connection; change the upright</h2><p>A <strong>stem</strong> spans the baseline to x-height. In the n-like <em>${label('arch')}</em>, the <strong>leg</strong> is the complete right branch, including its upper connecting arch. Extend the upright upward and it becomes an <strong>ascender</strong>; extend it downward and it becomes a <strong>descender</strong>. The same leg connection works with each.</p></div></div><div class="intro-example-demonstration">${study(0)}<div class="intro-character-row">${specimen('arch','Compare Latin n')}${specimen('arch-ascender','Compare Latin h')}${specimen('arch-descender','The same rule, extending downward')}</div></div></section>

<section class="intro-worked-example" id="uprights-and-bowls"><div class="intro-example-heading"><span class="intro-example-number" aria-hidden="true">02</span><div><h2>Keep the bowl; change its neighbor</h2><p>A <strong>bowl</strong> is a closed rounded body. In the b-like <em>${label('bowl-ascender')}</em>, it sits to the right of the upright. The d-like construction puts the bowl first; the p-like construction gives its upright a downward extension. Component order and extension are structural distinctions, so these are separate repertoire entries.</p></div></div><div class="intro-example-demonstration">${study(1)}<div class="intro-character-row">${specimen('bowl-ascender','Compare Latin b')}${specimen('turned-bowl-ascender','Compare Latin d')}${specimen('bowl-descender','Compare Latin p')}</div></div></section>

<section class="intro-worked-example" id="spines-and-attachments"><div class="intro-example-heading"><span class="intro-example-number" aria-hidden="true">03</span><div><h2>Let a familiar curve make unfamiliar forms</h2><p>A <strong>spine</strong> is an s-shaped body. It can stand alone, join an upright on one side, or connect uprights on both sides. The a-like <em>${label('turned-bowled-spine')}</em> and the two-sided construction share this structural vocabulary. The project’s emblem is itself the latter character.</p></div></div><div class="intro-example-demonstration">${study(2)}<div class="intro-character-row">${specimen('special-spine','Compare Latin s')}${specimen('turned-bowled-spine','Compare double-storey Latin a')}${specimen('opposed-bowls-0-0','Uprights on both sides')}</div></div><p class="intro-comparison-note">Latin comparisons here describe visual relationships. They assign no sounds and do not establish equivalence to existing Unicode characters. These examples are typographic specimens, with no assigned linguistic meaning.</p></section>

<section class="section-rule intro-section" id="construction-principles"><p class="eyebrow">The rules continue</p><h2>Consistent construction gives the repertoire its coherence</h2><p>The full vocabulary includes <strong>shoulders</strong> (short, free-ended upper branches), their lower counterparts called <strong>hips</strong>, <strong>arms</strong> (complete left branches with a lower connecting arch), and curved upper and lower extensions called <strong>hooks</strong> and <strong>tails</strong>. Repeated arches add interior uprights. Long bowls follow specific rules for where their returns meet an adjacent upright.</p><p>Names describe the construction from left to right. In <em>${label('turned-bowl-ascender')}</em>, the bowl precedes the upright. That naming order is distinct from both construction order and the movement of a pen. A font’s weight, posture, and serif treatment are styling choices for the same character identity.</p><p>The current catalogue identifies ${total} characters. It records the implemented repertoire; that count is not a claim that every theoretically possible combination has been enumerated. The detailed reference explains the vocabulary, connections, and naming rules.</p><div class="inline-links"><a href="construction.html">Read the construction reference →</a><a href="charts.html">Browse the complete current repertoire →</a></div></section>

<section class="section-rule intro-section" id="using-the-repertoire"><p class="eyebrow">From forms to writing systems</p><h2>Choose the letters; decide what they mean</h2><p>The repertoire supplies structurally defined letterforms, independent of any particular language, pronunciation system, or orthography. An adopting writing system can select a subset and assign its own linguistic functions.</p><ul class="intro-uses"><li><strong>Extend a Latin-based orthography.</strong> Choose additional letters whose structures fit its visual conventions.</li><li><strong>Construct a Latin-like script.</strong> Build an alphabet from a related set of forms with consistent features.</li><li><strong>Write a constructed language.</strong> Assign the selected characters sound values or other functions in your own documented system.</li></ul><p>Adoption does not require using one enormous alphabet or accepting predefined sounds. Quintessential Latin defines the forms; an orthography defines their meaning. Quintessential Serif and the Unifont study are font implementations of the repertoire.</p></section>

<section class="section-rule intro-section" id="start-using"><p class="eyebrow">A practical route</p><h2>Inspect, copy, and use a character</h2><ol class="intro-use-steps"><li><strong>Find a form.</strong> Select any example above or search the <a href="charts.html">code charts</a> by structural name or code point.</li><li><strong>Identify it.</strong> Character details show its canonical name, draft code point, and permanent link. Use <em>Copy character</em> to copy the actual private-use character.</li><li><strong>Get a font.</strong> Obtain <a href="downloads.html#serif-font">Quintessential Serif</a> for Roman and Italic rendering, or inspect the <a href="unifont.html">Unifont study</a>. A compatible font is needed to display the characters.</li><li><strong>Share the convention.</strong> Document your chosen subset and linguistic values, and supply the allocation version and compatible font. Private-use text depends on agreement between sender and recipient; the same code points can mean something else in another system.</li></ol><p class="intro-draft-note">The assignments are a draft proposal for the Under-ConScript Unicode Registry (UCSUR). They are not standardized Unicode characters or a registered allocation. Read the <a href="proposal.html">self-contained proposal</a> for the encoding model, boundaries, sources, and open review questions; use <a href="downloads.html">Downloads</a> for fonts, printable charts, names lists, machine-readable data, and licenses.</p><p class="byline">Designed and maintained by Josh Hufford.</p></section>`;
}

export const introStyles = `
/* Introduction: a short illustrated reading path within the reference layout. */
.intro-opening{grid-template-columns:minmax(0,1fr) 175px;gap:26px;margin-bottom:32px}
.intro-opening h1{font-size:34px;line-height:1.12;margin-bottom:15px}
.intro-opening .lead{font-size:20px;line-height:1.3;color:var(--ink);margin-bottom:18px}
.intro-opening .project-emblem{padding:0;gap:8px}
.intro-opening .emblem-glyph{--mark-size:145px}
.intro-opening .emblem-caption{max-width:175px;font-size:13px;line-height:1.35}
.intro-opening .emblem-caption>span+span{font-size:12px;color:var(--muted)}
.intro-section{scroll-margin-top:90px}
.intro-section h2{max-width:580px;line-height:1.25}
.intro-section>p,.intro-example-heading p{line-height:1.55}
.latin-comparison{font-family:Georgia,'Times New Roman',serif;font-size:1.2em}
.intro-progression{list-style:none;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;padding:20px 0 2px;margin:18px 0 24px;border-top:1px solid var(--rule)}
.intro-progression li{position:relative;min-width:0;font-size:14px;line-height:1.4}
.intro-progression li:not(:last-child)::after{content:'→';position:absolute;right:-16px;top:0;color:var(--muted)}
.intro-progression strong,.intro-progression span{display:block}
.intro-progression strong{margin-bottom:7px;font-size:14px;line-height:1.35}
.intro-progression span{color:var(--muted);font-size:13px}
.intro-study-key,.intro-comparison-note{font-size:13px;color:var(--muted);line-height:1.5}
.intro-worked-example{border-top:1px solid var(--rule);padding-top:24px;margin-top:28px;scroll-margin-top:90px}
.intro-example-heading{display:grid;grid-template-columns:34px minmax(0,1fr);gap:10px}
.intro-example-number{font-size:14px;color:var(--muted);padding-top:4px;font-variant-numeric:tabular-nums}
.intro-example-heading h2{font-size:22px;line-height:1.25}
.intro-example-heading p{margin-bottom:12px}
.intro-example-demonstration{display:grid;grid-template-columns:180px minmax(0,1fr);gap:22px;align-items:start;margin:8px 0 16px}
.intro-writing-study,.intro-character{margin:0;min-width:0}
.intro-writing-study svg{display:block;width:100%;height:auto;max-width:230px;margin-inline:auto;overflow:visible}
.intro-writing-guides path{fill:none;stroke:#aeb9bd;stroke-width:1;stroke-dasharray:3 4}
.intro-writing-guides text{font:14px 'Source Sans 3',Arial,sans-serif;fill:#526067}
.intro-writing-path{stroke:#182a33;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;fill:none}
.intro-writing-start{fill:#fff;stroke:#182a33;stroke-width:1.8}
.intro-writing-study figcaption{font-size:12px;line-height:1.5;color:var(--muted);padding:3px 0 0 4px}
.intro-character-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;min-width:0;padding-top:7px}
.intro-character-link{height:126px;display:flex;align-items:center;justify-content:center;text-decoration:none}
.intro-character figcaption{font-size:13px;line-height:1.35;overflow-wrap:anywhere;text-align:center}
.intro-character figcaption>span{display:block}
.intro-character-name{font-weight:600;margin-bottom:4px}
.intro-character .code{font-size:12px;color:var(--muted)}
.intro-character-relation{font-size:12px;color:var(--muted);margin-top:7px}
.intro-comparison-note{border-top:1px solid var(--rule);padding-top:13px;margin:19px 0 0}
.intro-uses,.intro-use-steps{padding-left:22px;margin-block:18px}
.intro-uses li,.intro-use-steps li{padding-left:4px;margin-bottom:12px;line-height:1.5}
.intro-draft-note{font-size:14px;border-top:1px solid var(--rule);padding-top:16px;margin-top:23px}
@media(max-width:620px){
  .intro-opening{grid-template-columns:1fr;gap:18px}
  .intro-opening h1{font-size:32px}
  .intro-opening .project-emblem{flex-direction:row;justify-content:flex-start;gap:22px;max-width:100%}
  .intro-opening .emblem-glyph{--mark-size:104px;flex:none}
  .intro-opening .emblem-caption{text-align:left;max-width:180px}
  .intro-progression{grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 28px}
  .intro-progression li:nth-child(2)::after{content:none}
  .intro-example-demonstration{grid-template-columns:1fr;gap:12px}
  .intro-writing-study{display:grid;grid-template-columns:minmax(0,200px) minmax(0,1fr);gap:12px;align-items:center}
  .intro-character-row{gap:10px;padding-top:0}
  .intro-character-link{height:124px}
  .intro-example-heading{grid-template-columns:25px minmax(0,1fr);gap:8px}
}
@media(max-width:380px){
  .intro-writing-study{grid-template-columns:1fr}
  .intro-writing-study svg{width:215px;max-width:100%}
  .intro-writing-study figcaption{padding:0 4px;text-align:left}
  .intro-character-link .glyph{font-size:min(var(--glyph-size),27vw)}
  .intro-character-link{height:115px}
  .intro-character-name{font-size:12px}
}
@media print{
  .intro-opening{grid-template-columns:minmax(0,1fr) 140px;gap:20px}
  .intro-opening .emblem-glyph{--mark-size:110px}
  .intro-opening .project-emblem{flex-direction:column}
  .intro-opening .emblem-caption{text-align:center}
  .intro-section,.intro-worked-example{scroll-margin-top:0}
  .intro-worked-example{break-inside:avoid;padding-top:16px;margin-top:20px}
  .intro-example-demonstration{grid-template-columns:155px minmax(0,1fr);gap:18px}
  .intro-writing-study{display:block}
  .intro-character-link{height:105px}
  .intro-character-link .glyph{font-size:80px}
  .intro-progression{grid-template-columns:repeat(4,minmax(0,1fr))}
  .intro-use-steps li,.intro-uses li{break-inside:avoid}
}`;

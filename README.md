<p><img src="site/assets/project-icon.svg" width="88" height="88" alt="Quintessential Latin project emblem, U+F2ADC, stem with spine and stem"></p>

# Quintessential Latin

A systematic repertoire of 1,216 Latin-derived constructions, with a reference
font, code charts, and a draft proposal for the Under-ConScript Unicode Registry.

**Author:** Josh Hufford  
**Website:** https://ostomachion.github.io/quintessential-latin/  
**Discussion:** https://github.com/ostomachion/quintessential-latin/issues

Quintessential Serif 0.250 contains all 1,216 forms in both Roman and native
Italic, across weights 400–700.
These are proposed private-use assignments, not Unicode or UCSUR registrations.
The [independent middle extensions](docs/independent-middle-extensions.md) add
left-only and right-only extensions wherever two middle components occur.
Version 0.250 places all forms in one [gapless construction order](docs/logical-allocation.md),
with each extension state beside its base. Earlier numeric assignments are replaced
without compatibility aliases.

U+F2ADC, stem with spine and stem, is the project mark. Its reviewed joins and paired spine curves are the
basis of the [shared-spine refinement](docs/shared-spine-optical-design.md),
covering all 396 related Roman constructions, including ending, arch, and
extended-middle-leg variants. The [initial emblem review](docs/f2b18-optical-design.md)
records the design decisions that established this treatment.
The [connection proofs](docs/images/shared-spine-connections/index.html) show
each join class at close range, with the exact compiled-font revision visible.

| Block | Range | Assigned |
| --- | --- | ---: |
| Quintessential Latin | U+F2A00–U+F2ABF | 192 |
| Quintessential Latin Extended-A | U+F2AC0–U+F2BBF | 256 |
| Quintessential Latin Extended-B | U+F2BC0–U+F2EBF | 768 |

## Website development

Install Node.js 22 or later. The checked-in fonts, compact catalogue and PDF
downloads make the site build independent of the font-development environment.

```sh
npm ci
npm run build
npm test
npm run dev
```

Open http://localhost:8767/quintessential-latin/. The preview also serves the
root path. All site URLs work beneath the GitHub Pages project prefix.

The four pages introduce the construction system, present numeric charts and
names lists, explain the draft proposal, and offer
font/data/PDF downloads. Weight and native Italic preferences are shared across
the pages, including both project marks. The marks follow the same native
posture coverage as the charts; the favicon stays at Roman 500.
No language-specific transcription or backend is required.

Browser tests use Playwright Chromium:

```sh
npx playwright install chromium
npm run test:browser
```

## Editable sources and fonts

The authoritative masters are four UFOs and two designspaces under
`fonts/QuintessentialSerif/`. Pinned STIX Two Text 2.13 b171 donor inputs are
under `resources/fonts/STIXTwoText/`; do not replace them during routine builds.

Create a Python 3.13 virtual environment, activate it, then run:

```sh
python -m pip install -r tools/requirements-fonts.txt
python tools/build_quintessential_font.py
python tools/test_fonts.py
```

The font build regenerates the detailed proof file locally. The plain JSON is
excluded from Git and the website. A small, checksummed gzip copy lets the full
test runner restore the preserved proof in a fresh checkout without rebuilding. The complete acceptance checks can take
substantial time because they enumerate 14,786,560 ordered-pair samples.
See [font development](docs/font-development.md) for preservation boundaries and
[Italic completion](docs/italic-completion.md) for the construction and proof inventory.

## Catalogue and proposal

`resources/quintessential-latin-allocation.json` is the explicit allocation.
It preserves stable construction identities separately from numeric codes,
internal font glyph names, and presentation order. Structural component data
drives canonical naming without prescribing pronunciation.

```sh
node tools/export_glyph_catalogue.js
node tools/export_glyph_catalogue.js --check
```

Commit allocation and generated data together. The compact browser catalogue
uses verified compiled-font coverage, not assumed coverage. Individual names
follow [canonical naming version 3](docs/quintessential-latin-canonical-naming-spec-v3.md).

`docs/proposal.json` supplies the website and PDF proposal from one text source.
The proposed repertoire remains subject to registry review; publishing the
website does not submit the proposal.

## PDF publication

Install the PDF-specific requirements in a Python environment, then generate
and check all five publication PDFs:

```sh
python -m pip install -r tools/requirements-pdfs.txt
python tools/build_pdfs.py
python tools/test_pdfs.py
```

Outputs are in `output/pdf/`: three block charts, a combined catalogue, and
the proposal. Reference charts use Roman 400, embedded fonts, and vector text.
The five grid sheets contain 192, 256, 256, 256, and 256 positions, followed by numeric
two-column names lists with family subheadings. Source Sans 3 supplies the
publication text. Grid geometry, running headers, diagonal vacancy hatching,
and compact names follow the official Unicode code-chart format.
The responsive page presents 16, 8, or 4 hexadecimal columns according to its
available width. Its Letter-sized print view reflects the selected posture
and weight. Poppler is used for visual PDF review.

## GitHub Pages

The Pages workflow validates and builds the static site, then deploys only
`dist/`. Select **GitHub Actions** as the repository's Pages publishing source.
The checked-in PDF downloads are deployed with the site; the font sources,
regression fixtures, and development dependencies are not.

The manual font-validation workflow rebuilds fonts and runs the expensive
font and preservation checks separately from ordinary site deployment.

## Licensing and status

Original project code and documentation are MIT-licensed. Font software remains
under SIL OFL 1.1. See [third-party notices](THIRD_PARTY_NOTICES.md) and the notices
distributed with the fonts.

Engineering results and visual review are recorded in
[verification](docs/verification.md). User visual acceptance remains distinct
from automated verification and publication.

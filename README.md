# Quintessential Latin

A systematic repertoire of 832 Latin-derived constructions, with a reference
font, code charts, and a draft proposal for the Under-ConScript Unicode Registry.

**Author:** Josh Hufford  
**Website:** https://ostomachion.github.io/quintessential-latin/  
**Discussion:** https://github.com/ostomachion/quintessential-latin/issues

Quintessential Serif 0.220 contains all 832 forms in Roman and 232 in native
Italic, across weights 400–700. The 600 remaining Italic forms are pending.
These are proposed private-use assignments, not Unicode or UCSUR registrations.

| Block | Range | Assigned |
| --- | --- | ---: |
| Quintessential Latin | U+F2A00–U+F2AFF | 196 |
| Quintessential Latin Extended-A | U+F2B00–U+F2BFF | 252 |
| Quintessential Latin Extended-B | U+F2C00–U+F2DFF | 384 |

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

The five pages introduce the construction system, present numeric charts and
names lists, provide editable specimens, explain the draft proposal, and offer
font/data/PDF downloads. Weight and native Italic preferences are shared across
the pages. No language-specific transcription or backend is required.

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
substantial time because they enumerate 3,730,240 ordered-pair samples.
See [font development](docs/font-development.md) for preservation boundaries.

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
follow [canonical naming version 2](docs/quintessential-latin-canonical-naming-spec-v2.md).

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
The eight grid sheets each contain 128 positions, followed by numeric
two-column names lists. The website's print view reflects the selected posture
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

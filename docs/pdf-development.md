# PDF development and visual review

The publication builder reads the neutral catalogue and the shared proposal text.
It writes three block PDFs, the complete catalogue, and the UCSUR proposal under
`output/pdf/`. Reference charts use Quintessential Serif 0.220, Roman 400, with
embedded vector fonts. The original variable fonts remain unchanged.

## Build and automated checks

Use the same Python 3.13 virtual environment as the font tools, or a separate PDF
environment. The pinned requirements use fontTools 4.64.0, matching the font build.

```sh
python -m pip install -r tools/requirements-pdfs.txt
python tools/build_pdfs.py
python tools/test_pdfs.py
```

Build before testing: the builder creates `.tmp/pdf-layout-audit.json`, including
page inventories and measured glyph placement. Tests bind that evidence to the
current font and PDF hashes, then independently inspect PDF text and embedded
fonts. They check all assigned characters and names, supplementary-plane copying,
numeric ordering, page bounds, and proposal sections and references.

Static font instances and placement evidence are regenerable scratch files in
`.tmp/`. They are not required to read the checked-in publication PDFs or to build
the static website. Rebuild all five PDFs after changing the catalogue, proposal,
font inputs, or publication layout.

## Render for visual inspection

Install Poppler separately from the Python requirements. Its `pdftoppm` executable
must be on `PATH`, or supplied as a file or directory with `--poppler-bin`.
For example, the package is `poppler-utils` on Debian/Ubuntu and `poppler` with
Homebrew. On Windows, use the `bin` directory of an installed Poppler distribution.

Render every publication:

```sh
python tools/render_pdf_review.py
```

Render one publication with an explicitly selected Poppler installation:

```sh
python tools/render_pdf_review.py output/pdf/quintessential-latin.pdf --poppler-bin /path/to/poppler/bin
```

The helper writes one PNG per page, four-page contact sheets, and `manifest.json`
under `.tmp/pdf-review/`. The manifest lists only PDFs selected for the current
invocation, with relative output paths, page counts, PDF and PNG hashes, resolution,
and the Poppler version. Existing scratch renders outside that selection may
remain, but they are not included in the invocation manifest. The default is
110 dpi; use `--dpi 150` for closer inspection or `--output` for another scratch
folder. Running the helper does not modify PDF files or recorded acceptance.

Inspect every page, using the contact sheets to verify pagination and native-size
page PNGs to inspect dense names, wide forms, headers, footers, and references.
Check for clipped glyphs, overlapping labels, omitted characters, broken tables,
and awkward section transitions. Rendering by itself does not establish that
these checks have passed.

## Publication freshness manifest

Every PDF build also writes `output/pdf/build-manifest.json`. It binds the raw
SHA-256 hashes of the catalogue, proposal text, Roman reference and interface
font sources, builder, and pinned PDF requirements to all five output PDF hashes,
byte sizes, and page counts. Commit this generated manifest with the PDFs.

The Node website build validates the manifest before changing `dist/`, so edits
to a catalogue, proposal, font source, or PDF build input cannot silently publish
older reference PDFs. If that check reports stale publications, regenerate and
validate them with `python tools/build_pdfs.py` and `python tools/test_pdfs.py`,
then run the website build again. A hash match establishes freshness; it does not
replace optical review of changed PDF bytes.

## Durable verification evidence

The committed [PDF review record](../resources/verification/pdf-review.json)
binds the completed review to the five exact PDF files and reference font. It
records all 68 reviewed pages, the complete engineering checks, reproducibility,
and the distinction between agent review and pending user visual acceptance.
The corresponding [test log](../resources/verification/pdf-tests.log) is retained.

The record's temporary image references identify regenerable review material;
those PNGs are intentionally excluded from Git. It preserves the hashes of the
images actually reviewed. A different Poppler or Pillow version may generate
different PNG bytes from the same PDF, so a new rendering is not automatically
equivalent to the archived optical review. Record a fresh review when publication
PDF bytes change. Do not overwrite the archived acceptance record merely because
the renderer or automated checks ran successfully.

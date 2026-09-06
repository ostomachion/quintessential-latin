# Licenses and attribution

Original website code, project tooling, repertoire data, and documentation:
Copyright 2026 Josh Hufford, MIT License (see LICENSE).

## Font software

The Quintessential Serif font binaries, UFO masters, designspaces, and preserved
font fixtures are distributed under the SIL Open Font License 1.1. The STIX Two
Text donor fonts remain under their existing SIL Open Font License 1.1.

The outlined project mark and favicon in `site/assets/` are exported from
Quintessential Serif's stem with spine and stem (stable identity
`opposed-bowls-0-0`, currently U+F2ADC). They preserve the font's STIX attribution and
SIL Open Font License 1.1 notice in their SVG descriptions.

Preserve the OFL, FONTLOG, and TRADEMARKS notices alongside font distributions:
- resources/fonts/QuintessentialSerif/OFL.txt
- resources/fonts/QuintessentialSerif/FONTLOG.txt
- resources/fonts/QuintessentialSerif/TRADEMARKS.txt
- resources/fonts/STIXTwoText/OFL.txt
- resources/fonts/SourceSans3/OFL.txt

Original STIX font attribution: Copyright 2001-2021 The STIX Fonts Project Authors
(https://github.com/stipub/stixfonts), with Reserved Font Name "TM Math".
STIX Fonts is a trademark of The Institute of Electrical and Electronics Engineers, Inc.
Quintessential Serif is the modified font family; no STIX endorsement is implied.

The website and code charts use Source Sans 3 version 3.052, Copyright 2010-2022 Adobe,
under the SIL Open Font License 1.1. Four unmodified TTF and WOFF2 faces are
pinned to the upstream `3.052R` release. Their original download URLs and
SHA-256 hashes are recorded in `resources/fonts/SourceSans3/source-manifest.json`.
Source: https://github.com/adobe-fonts/source-sans/tree/3.052R

## Bitmap font software

Quintessential Latin Unifont and the project bitmap drawings derive from GNU
Unifont 17.0.05 and are distributed under SIL OFL 1.1. They are independent
project fonts, not an official GNU Unifont release. Preserve the contributor
attribution and complete license in `resources/unifont/OFL.txt` and the copy in
`resources/fonts/QuintessentialUnifont/OFL.txt` with redistributed font software.
The MIT license for project code and documentation does not replace these
font licenses.

## Development dependencies

Playwright is licensed under Apache-2.0. It is used for development tests and is
not included in the deployed website. Python font-building and PDF tools retain
their own licenses; install the pinned requirement files through the package
manager, which supplies their license metadata.

The project website bundles no third-party JavaScript runtime. Unicode and UCSUR
documents are cited as references; their publications are not relicensed here.

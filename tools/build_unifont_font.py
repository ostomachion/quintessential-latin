"""Compile the reviewed Unifont cells into installable TTF and web WOFF2."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables import E_B_D_T_, E_B_L_C_
from fontTools.ttLib.tables.BitmapGlyphMetrics import BigGlyphMetrics

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path('resources/fonts/QuintessentialUnifont')
FAMILY = 'Quintessential Latin Unifont'
STEM = 'QuintessentialUnifont-Regular'
VERSION = '0.250'
UPM, PIXEL, ASCENT, DESCENT, ADVANCE = 1024, 64, 896, -128, 512
FONT_TIMESTAMP = 1788652800 + 2082844800  # 2026-09-06, OpenType's 1904 epoch.
COMPANION_SHA256 = '0ec8a4f2f3fda7f6ed4d0db9358099bb522eeb65df51e5cb2d5fc0dba56c0090'
NOTDEF = bytes([0, 0, 0, 126, 66, 66, 66, 66, 66, 66, 66, 66, 66, 126, 0, 0])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_hex(data: bytes) -> dict[int, bytes]:
    result = {}
    for line in data.decode('ascii').splitlines():
        code, pixels = line.split(':')
        point, rows = int(code, 16), bytes.fromhex(pixels)
        if point in result or len(rows) != 16 or not (0 <= point <= 0x10ffff) or 0xd800 <= point <= 0xdfff:
            raise ValueError(f'Invalid or duplicate 8x16 HEX entry: {line}')
        canonical = f'{point:06X}' if point > 0xffff else f'{point:04X}'
        if code != canonical:
            raise ValueError(f'Noncanonical HEX code: {code}')
        result[point] = rows
    return result


def load_cells(root: Path = ROOT):
    base = root / 'resources/unifont'
    custom = parse_hex((base / 'quintessential-latin.hex').read_bytes())
    allocation = json.loads((root / 'resources/quintessential-latin-allocation.json').read_text(encoding='utf8'))
    metadata = json.loads((base / 'glyphs.json').read_text(encoding='utf8'))
    if set(custom) != {entry['codePoint'] for entry in allocation['entries']} or len(custom) != 1216:
        raise ValueError('The font requires exactly the current 1216-character allocation')
    if len(metadata['glyphs']) != 1216:
        raise ValueError('Incomplete bitmap metadata')
    for glyph in metadata['glyphs']:
        if custom[glyph['codePoint']] != bytes(glyph['rows']) or not any(glyph['rows']):
            raise ValueError(f'Stale or blank bitmap: {glyph["glyphId"]}')
    companion_data = (base / 'font-companions.hex').read_bytes()
    companion_info = json.loads((base / 'font-companions.json').read_text(encoding='utf8'))
    if sha256(companion_data) != COMPANION_SHA256 or companion_info['subsetSha256'] != COMPANION_SHA256:
        raise ValueError('Pinned native companion pixels changed')
    companions = parse_hex(companion_data)
    if len(companions) != 214 or set(companions) != {int(p, 16) for p in companion_info['codePoints']} or custom.keys() & companions.keys():
        raise ValueError('Invalid companion coverage')
    for point, rows in parse_hex((base / 'donors.hex').read_bytes()).items():
        if companions.get(point) != rows:
            raise ValueError(f'Native donor changed at U+{point:04X}')
    return {**companions, **custom}


def draw_outline(rows: bytes):
    """One clockwise rectangle per horizontal ink run; no smoothing or hints."""
    pen = TTGlyphPen(None)
    for y, row in enumerate(rows):
        x = 0
        while x < 8:
            if not row & (128 >> x):
                x += 1
                continue
            start = x
            while x < 8 and row & (128 >> x):
                x += 1
            x0, x1 = start * PIXEL, x * PIXEL
            y0, y1 = (13 - y) * PIXEL, (14 - y) * PIXEL
            pen.moveTo((x0, y0))
            pen.lineTo((x0, y1))
            pen.lineTo((x1, y1))
            pen.lineTo((x1, y0))
            pen.closePath()
    return pen.glyph()


def add_bitmap_strike(font, drawings: dict[str, bytes]):
    """OpenType EBDT format 5, one fixed 8x16 monochrome cell per glyph."""
    ebdt, eblc = newTable('EBDT'), newTable('EBLC')
    ebdt.version = eblc.version = 2.0
    strike = E_B_L_C_.Strike()
    size = strike.bitmapSizeTable
    size.colorRef, size.ppemX, size.ppemY, size.bitDepth, size.flags = 0, 16, 16, 1, 1
    for direction in ('hori', 'vert'):
        metrics = E_B_L_C_.SbitLineMetrics()
        for field, value in dict(ascender=14, descender=-2, widthMax=8, caretSlopeNumerator=1, caretSlopeDenominator=0, caretOffset=0, minOriginSB=0, minAdvanceSB=0, maxBeforeBL=14, minAfterBL=-2, pad1=0, pad2=0).items():
            setattr(metrics, field, value)
        setattr(size, direction, metrics)
    subtable = E_B_L_C_.eblc_index_sub_table_2(None, font)
    subtable.indexFormat, subtable.imageFormat, subtable.imageSize = 2, 5, 16
    subtable.names = font.getGlyphOrder()
    subtable.metrics = BigGlyphMetrics()
    for field, value in dict(height=16, width=8, horiBearingX=0, horiBearingY=14, horiAdvance=8, vertBearingX=-4, vertBearingY=0, vertAdvance=16).items():
        setattr(subtable.metrics, field, value)
    strike.indexSubTables = [subtable]
    eblc.strikes = [strike]
    ebdt.strikeData = [{name: E_B_D_T_.ebdt_bitmap_format_5(rows, font) for name, rows in drawings.items()}]
    font['EBDT'], font['EBLC'] = ebdt, eblc


def make_font(cells: dict[int, bytes], license_text: str):
    cmap = {point: f'u{point:04X}' for point in sorted(cells)}
    drawings = {'.notdef': NOTDEF, **{cmap[p]: cells[p] for p in sorted(cells)}}
    builder = FontBuilder(UPM, isTTF=True)
    builder.setupGlyphOrder(list(drawings))
    builder.setupCharacterMap(cmap)
    unicode_full = copy.deepcopy(next(t for t in builder.font['cmap'].tables if t.format == 12))
    unicode_full.platformID, unicode_full.platEncID = 0, 4
    builder.font['cmap'].tables.append(unicode_full)
    glyphs = {name: draw_outline(rows) for name, rows in drawings.items()}
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (ADVANCE, glyph.xMin if glyph.numberOfContours else 0) for name, glyph in glyphs.items()})
    builder.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
    builder.setupNameTable({
        'familyName': FAMILY, 'styleName': 'Regular', 'typographicFamily': FAMILY, 'typographicSubfamily': 'Regular',
        'uniqueFontIdentifier': f'Josh Hufford:{STEM}:{VERSION}', 'fullName': FAMILY + ' Regular',
        'psName': STEM, 'version': f'Version {VERSION}',
        'copyright': license_text.split('This Font Software')[0].strip(),
        'manufacturer': 'Josh Hufford', 'designer': 'Josh Hufford; GNU Unifont contributors',
        'description': '1216 Quintessential Latin characters and 214 native GNU Unifont Latin companions. Pixel outlines with an exact 16-ppem monochrome bitmap strike.',
        'licenseDescription': 'Licensed under the SIL Open Font License, Version 1.1. See the accompanying OFL.txt.',
        'licenseInfoURL': 'https://openfontlicense.org/',
    })
    builder.setupOS2(version=4, sTypoAscender=ASCENT, sTypoDescender=DESCENT, sTypoLineGap=0,
                     usWinAscent=ASCENT, usWinDescent=-DESCENT, sxHeight=512, sCapHeight=640,
                     usWeightClass=400, usWidthClass=5, fsType=0, fsSelection=0xC0,
                     xAvgCharWidth=ADVANCE, usDefaultChar=0, usBreakChar=32)
    builder.setupPost(isFixedPitch=1, underlinePosition=-64, underlineThickness=64)
    builder.setupMaxp()
    builder.font['head'].created = builder.font['head'].modified = FONT_TIMESTAMP
    builder.font['head'].fontRevision = float(VERSION)
    builder.font['head'].lowestRecPPEM = 16
    builder.font.recalcTimestamp = False
    # A rasterizer preference, not a promise that every application honors it.
    gasp = newTable('gasp')
    gasp.version, gasp.gaspRange = 1, {65535: 0}
    builder.font['gasp'] = gasp
    add_bitmap_strike(builder.font, drawings)
    return builder.font


def compile_outputs(root: Path = ROOT) -> dict[str, bytes]:
    cells = load_cells(root)
    license_bytes = (root / 'resources/unifont/OFL.txt').read_bytes()
    font = make_font(cells, license_bytes.decode('utf8'))
    ttf = io.BytesIO()
    font.save(ttf)
    font.flavor = 'woff2'
    woff = io.BytesIO()
    font.save(woff)
    font.close()
    return {STEM+'.ttf': ttf.getvalue(), STEM+'.woff2': woff.getvalue(), 'OFL.txt': license_bytes}


def build(root: Path = ROOT, check: bool = False):
    outputs = compile_outputs(root)
    inputs = ['tools/build_unifont_font.py', 'tools/requirements-unifont.txt', 'resources/unifont/quintessential-latin.hex', 'resources/unifont/font-companions.hex', 'resources/unifont/font-companions.json', 'resources/unifont/OFL.txt', 'resources/quintessential-latin-allocation.json']
    manifest = {'schemaVersion': 1, 'family': FAMILY, 'version': VERSION, 'customCharacters': 1216,
                'nativeCompanions': 214, 'encodedCharacters': 1430, 'glyphs': 1431,
                'unitsPerEm': UPM, 'advance': ADVANCE, 'ascent': ASCENT, 'descent': DESCENT,
                'bitmapStrikePpem': 16, 'license': 'OFL-1.1',
                'dependencies': {name: importlib.metadata.version(name) for name in ('fonttools', 'brotli')},
                'sources': {name: sha256((root/name).read_bytes()) for name in inputs},
                'outputs': {name: {'sha256': sha256(data), 'bytes': len(data)} for name, data in outputs.items()}}
    outputs['manifest.json'] = (json.dumps(manifest, indent=2)+'\n').encode('utf8')
    destination = root / OUTPUT
    if not check:
        destination.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        if check:
            if (destination/name).read_bytes() != data:
                raise ValueError(f'Stale Unifont font artifact: {name}; run npm run build:unifont:font')
        else:
            (destination/name).write_bytes(data)
    print(f'{"Verified" if check else "Built"} {FAMILY}: TTF + WOFF2, 1216 custom + 214 native characters, exact 16px strike.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare deterministic outputs without writing files')
    build(check=parser.parse_args().check)

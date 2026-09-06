"""Verify the compiled font containers, actual outlines and native rasterization."""
import io
import json
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from build_unifont_font import ROOT, OUTPUT, STEM, FAMILY, NOTDEF, load_cells, compile_outputs, build


class UnifontFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = load_cells()
        cls.files = {ext: (ROOT/OUTPUT/f'{STEM}.{ext}').read_bytes() for ext in ('ttf', 'woff2')}
        cls.fonts = {ext: TTFont(io.BytesIO(data), recalcTimestamp=False) for ext, data in cls.files.items()}

    @classmethod
    def tearDownClass(cls):
        for font in cls.fonts.values():
            font.close()

    def test_repertoire_names_metrics_and_supplementary_cmaps(self):
        for font in self.fonts.values():
            self.assertEqual(set(font.getBestCmap()), set(self.cells))
            self.assertEqual(len(font.getGlyphOrder()), 1431)
            self.assertEqual(font['name'].getDebugName(1), FAMILY)
            self.assertEqual(font['name'].getDebugName(2), 'Regular')
            self.assertEqual(font['name'].getDebugName(6), STEM)
            self.assertEqual(font['head'].unitsPerEm, 1024)
            self.assertEqual((font['hhea'].ascent, font['hhea'].descent, font['hhea'].lineGap), (896, -128, 0))
            self.assertEqual(font['OS/2'].version, 4)
            self.assertEqual(font['OS/2'].fsType, 0)
            self.assertEqual(font['OS/2'].fsSelection, 0xc0)
            self.assertEqual(font['post'].isFixedPitch, 1)
            self.assertEqual({advance for advance, _ in font['hmtx'].metrics.values()}, {512})
            for platform, encoding in ((3, 10), (0, 4)):
                full = font['cmap'].getcmap(platform, encoding)
                self.assertEqual(full.format, 12)
                self.assertEqual(set(full.cmap), set(self.cells))

    def test_every_binary_outline_reconstructs_the_original_cell(self):
        for font in self.fonts.values():
            drawings = {'.notdef': NOTDEF, **{font.getBestCmap()[p]: rows for p, rows in self.cells.items()}}
            for name, expected in drawings.items():
                glyph = font['glyf'][name]
                rows = [0]*16
                if glyph.numberOfContours:
                    coordinates, ends, flags = glyph.getCoordinates(font['glyf'])
                    self.assertTrue(all(flag & 1 for flag in flags), name)
                    start = 0
                    for end in ends:
                        points = list(coordinates[start:end+1]); start = end+1
                        self.assertEqual(len(points), 4, name)
                        xs, ys = sorted({x for x, _ in points}), sorted({y for _, y in points})
                        self.assertEqual((len(xs), len(ys)), (2, 2), name)
                        self.assertTrue(all(value % 64 == 0 for value in xs+ys), name)
                        self.assertEqual(set(points), {(x, y) for x in xs for y in ys})
                        self.assertEqual(ys[1]-ys[0], 64)
                        row = 13 - ys[0]//64
                        self.assertTrue(0 <= row < 16 and 0 <= xs[0] < xs[1] <= 512)
                        for x in range(xs[0]//64, xs[1]//64):
                            self.assertFalse(rows[row] & (128 >> x), (name, 'overlapping contour'))
                            rows[row] |= 128 >> x
                self.assertEqual(bytes(rows), expected, name)
                self.assertEqual(font['hmtx'][name][1], glyph.xMin if glyph.numberOfContours else 0)

    def test_both_containers_retain_every_exact_embedded_bitmap(self):
        for font in self.fonts.values():
            self.assertEqual(len(font['EBLC'].strikes), 1)
            strike = font['EBLC'].strikes[0]
            self.assertEqual((strike.bitmapSizeTable.ppemX, strike.bitmapSizeTable.ppemY, strike.bitmapSizeTable.bitDepth), (16, 16, 1))
            sub = strike.indexSubTables[0]
            self.assertEqual((sub.indexFormat, sub.imageFormat, sub.imageSize), (2, 5, 16))
            self.assertEqual((sub.metrics.width, sub.metrics.height, sub.metrics.horiBearingX, sub.metrics.horiBearingY, sub.metrics.horiAdvance), (8, 16, 0, 14, 8))
            for point, expected in self.cells.items():
                self.assertEqual(font['EBDT'].strikeData[0][font.getBestCmap()[point]].imageData, expected)
            self.assertEqual(font['EBDT'].strikeData[0]['.notdef'].imageData, NOTDEF)

    def test_freetype_renders_every_character_pixel_exactly_at_native_size(self):
        font = ImageFont.truetype(io.BytesIO(self.files['ttf']), 16, layout_engine=ImageFont.Layout.BASIC)
        for point, expected in self.cells.items():
            image = Image.new('L', (8, 16))
            ImageDraw.Draw(image).text((0, 14), chr(point), font=font, fill=255, anchor='ls')
            self.assertEqual(image.tobytes(), bytes(255 if row & (128 >> x) else 0 for row in expected for x in range(8)), f'U+{point:04X}')
            self.assertEqual(font.getlength(chr(point)), 8)

    def test_woff2_preserves_outlines_and_metrics(self):
        ttf, web = self.fonts['ttf'], self.fonts['woff2']
        self.assertEqual(ttf.getBestCmap(), web.getBestCmap())
        self.assertEqual(ttf['hmtx'].metrics, web['hmtx'].metrics)
        for name in ttf.getGlyphOrder():
            self.assertEqual(ttf['glyf'][name].getCoordinates(ttf['glyf']), web['glyf'][name].getCoordinates(web['glyf']))

    def test_repeat_build_is_byte_identical_and_manifest_is_current(self):
        again = compile_outputs()
        for ext, original in self.files.items():
            self.assertEqual(again[f'{STEM}.{ext}'], original)
        build(check=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)

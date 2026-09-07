#!/usr/bin/env python3
"""Validate the three approved two-bulb Specials without relaxing other ink.

The revision is confined to stable identities, irrespective of their encoding.
All advances and pairs stay fixed. Actual filled-outline collision checks cover
both ordering directions against the complete catalogue at five weights.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import unittest
import hip_tail_revision

import pyclipper
from fontTools.ttLib import TTFont
from ufoLib2 import Font

from font_geometry_helpers import effective_pairs, outline, polygons_from_recording, ZERO_PAIR

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
BASELINE = ROOT / "resources/provenance/stemless-terminals-geometry-baseline.json.gz"
BASELINE_SHA256 = "5d939d0a40f92d4c87ca0e1370412d5f1e93d12d1f51a49e2c25809a5ba2d296"
TARGET_IDS = frozenset(("special-spine", "special-turned-open-bowl", "special-turned-double-open-bowl"))
TARGET_NAMES = frozenset(("uF2B03", "special-turned-open-bowl", "special-turned-double-open-bowl"))
WEIGHTS = (400, 500, 550, 600, 700)
STYLES = {"Regular": (False, 400), "Bold": (False, 700),
          "Italic": (True, 400), "BoldItalic": (True, 700)}
COMPILED_FACES = None


def assert_preserved_outlines(test, actual, captured, context, *, source=False, instantiated=False):
    """Permit only the three approved outline edits; protect every advance."""
    test.assertEqual(set(actual), set(captured), context)
    for name, old in captured.items():
        test.assertEqual(actual[name][0], old[0], (context, name, "Advance changed"))
        if name not in TARGET_NAMES:
            historical = hip_tail_revision.historical_outline(context, name, actual[name], source=source, instantiated=instantiated)
            test.assertEqual(historical, old, (context, name, "Unrelated outline changed"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def recorded_outlines(glyphs, names):
    return {name: [float(glyphs[name].width), digest(
        [(op, [[float(v) for v in p] for p in points]) for op, points in outline(glyphs, name)])]
        for name in names}


def pairs_digest(pairs):
    return digest(sorted([left, right, *value] for (left, right), value in pairs.items()
                         if tuple(value) != ZERO_PAIR))


def target_pair_values(font, normalized_location, target_names=TARGET_NAMES):
    """Resolve actual GPOS VariationIndex values only for the affected pairs."""
    from fontTools.varLib.varStore import VarStoreInstancer
    from test_quintessential_font import dflt_kern_lookups
    variation = VarStoreInstancer(font["GDEF"].table.VarStore, font["fvar"].axes, normalized_location)
    result = {}
    for lookup in dflt_kern_lookups(font):
        assert lookup.LookupType in (2, 9)
        for wrapper in lookup.SubTable:
            table = wrapper.ExtSubTable if lookup.LookupType == 9 else wrapper
            assert table.Format == 1
            for left, pair_set in zip(table.Coverage.glyphs, table.PairSet):
                for record in pair_set.PairValueRecord:
                    right = record.SecondGlyph
                    if left not in target_names and right not in target_names:
                        continue
                    assert record.Value2 is None or not any(vars(record.Value2).values())
                    value = record.Value1
                    assert set(vars(value)) <= {"XAdvance", "XAdvDevice"}, (left, right, vars(value))
                    adjustment = getattr(value, "XAdvance", 0)
                    device = getattr(value, "XAdvDevice", None)
                    if device:
                        assert device.DeltaFormat == 0x8000
                        adjustment += variation[(device.StartSize << 16) | device.EndSize]
                    result[left, right] = result.get((left, right), 0) + adjustment
    return result


def capture(folder, target_names=TARGET_NAMES):
    """Capture actual pre-edit files, independently of the construction code."""
    entries = json.loads((folder / "quintessential-latin-allocation.json").read_text())["entries"]
    result = {"schemaVersion": 1, "revision": "stemless-two-bulbs-1", "weights": WEIGHTS,
              "entries": entries, "sourceFiles": {}, "sources": {}, "compiled": {}}
    for path in (folder / "sources").rglob("*"):
        if path.is_file():
            result["sourceFiles"][path.relative_to(folder / "sources").as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for style in STYLES:
        with Font.open(folder / "sources" / f"QuintessentialSerif-{style}.ufo") as source:
            names = source.lib["public.glyphOrder"]
            result["sources"][style] = {"outlines": recorded_outlines(source, names), "order": names,
                "pairs": pairs_digest({pair: (0, 0, value, 0, 0, 0, 0, 0) for pair, value in source.kerning.items()}),
                "cmap": {name: source[name].unicodes for name in names},
                "targets": {name: {"recording": outline(source, name), "lib": source[name].lib} for name in target_names}}
        with TTFont(folder / "compiled" / f"QuintessentialSerif-{style}.otf") as font:
            result["compiled"][style] = {"outlines": recorded_outlines(font.getGlyphSet(), names),
                "pairs": pairs_digest(effective_pairs(font)), "order": font.getGlyphOrder(), "hmtx": font["hmtx"].metrics}
    for italic in (False, True):
        filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
        for weight in WEIGHTS:
            with TTFont(folder / "compiled" / filename) as variable:
                glyphs = variable.getGlyphSet(location={"wght": weight})
                result["compiled"][f"{'Italic' if italic else 'Roman'}-{weight}"] = {
                    "outlines": recorded_outlines(glyphs, variable.getGlyphOrder()),
                    "pairTables": {tag: hashlib.sha256(variable.getTableData(tag)).hexdigest()
                                   for tag in ("GPOS", "GDEF") if tag in variable}, "order": variable.getGlyphOrder(),
                    "hmtx": variable["hmtx"].metrics}
    return result


class StemlessTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if BASELINE.exists():
            assert hashlib.sha256(BASELINE.read_bytes()).hexdigest() == BASELINE_SHA256, "The immutable pre-terminal geometry baseline changed"
        cls.entries = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text())["entries"]
        cls.targets = {entry["glyphId"]: entry["glyphName"] for entry in cls.entries if entry["glyphId"] in TARGET_IDS}
        assert set(cls.targets.values()) == TARGET_NAMES, "Stable terminal glyph identity changed"

    def test_every_unrelated_source_byte_and_all_advances_pairs_and_mappings_are_preserved(self):
        baseline = json.loads(gzip.decompress(BASELINE.read_bytes()))
        self.assertEqual(self.entries, baseline["entries"])
        allowed = set()
        import plistlib
        for style in STYLES:
            folder = SOURCES / f"QuintessentialSerif-{style}.ufo"
            contents = plistlib.loads((folder / "glyphs/contents.plist").read_bytes())
            allowed.update((folder / "glyphs" / contents[name]).relative_to(SOURCES).as_posix() for name in TARGET_NAMES)
            with Font.open(folder) as source:
                captured = baseline["sources"][style]
                names = source.lib["public.glyphOrder"]
                self.assertEqual(names, captured["order"], style)
                assert_preserved_outlines(self, recorded_outlines(source, names), captured["outlines"], style, source=True)
                self.assertEqual(pairs_digest({pair: (0, 0, value, 0, 0, 0, 0, 0)
                    for pair, value in hip_tail_revision.historical_source_pairs(source).items()}), captured["pairs"], style)
                self.assertEqual({name: source[name].unicodes for name in names}, captured["cmap"], style)
                for name in TARGET_NAMES:
                    self.assertNotEqual(recorded_outlines(source, [name])[name], captured["outlines"][name], (style, name))
        self.assertEqual(len(allowed), 12)
        actual_files = {path.relative_to(SOURCES).as_posix() for path in SOURCES.rglob("*") if path.is_file()}
        self.assertEqual(actual_files, set(baseline["sourceFiles"]))
        for relative, expected in baseline["sourceFiles"].items():
            if relative not in allowed:
                self.assertEqual(hashlib.sha256(hip_tail_revision.historical_source_bytes(SOURCES / relative)).hexdigest(), expected, relative)

    def test_all_unrelated_compiled_ink_and_all_advances_pairs_and_gid_orders_are_preserved(self):
        baseline = json.loads(gzip.decompress(BASELINE.read_bytes()))
        if COMPILED_FACES is not None:
            self.assertTrue(COMPILED_FACES <= set(baseline["compiled"]), "Unknown selected compiled face")
        for face, captured in baseline["compiled"].items():
            if COMPILED_FACES is not None and face not in COMPILED_FACES:
                continue
            if "-" in face:
                posture, weight = face.split("-")
                filename = "QuintessentialSerif-Italic-Variable.ttf" if posture == "Italic" else "QuintessentialSerif-Variable.ttf"
            else:
                filename, weight = f"QuintessentialSerif-{face}.otf", None
            with TTFont(OUTPUT / filename) as font:
                if weight is not None:
                    glyphs = font.getGlyphSet(location={"wght": int(weight)})
                else:
                    glyphs = font.getGlyphSet()
                names = font.getGlyphOrder()
                self.assertEqual(names, captured["order"], face)
                self.assertEqual(set(font["hmtx"].metrics), set(captured["hmtx"]), face)
                for name, old in captured["hmtx"].items():
                    metrics = font["hmtx"][name]
                    self.assertEqual(metrics[0], old[0], (face, name, "Advance changed"))
                    if name not in TARGET_NAMES:
                        self.assertEqual(list(hip_tail_revision.historical_metrics(face, name, metrics)), old, (face, name, "Unrelated sidebearing changed"))
                assert_preserved_outlines(self, recorded_outlines(glyphs, names), captured["outlines"], face)
                if weight is None:
                    self.assertEqual(pairs_digest(hip_tail_revision.historical_pairs(effective_pairs(font), face)), captured["pairs"], face)
                else:
                    self.assertEqual(hip_tail_revision.historical_pair_tables(face, {tag: hashlib.sha256(font.getTableData(tag)).hexdigest()
                                      for tag in ("GPOS", "GDEF") if tag in font}), captured["pairTables"], face)
                print(f"terminal preservation {face}: {len(names) - len(TARGET_NAMES)} unrelated outlines/sidebearings; all advances/pairs", flush=True)

    def test_both_pair_directions_clear_the_complete_catalogue_at_five_weights(self):
        from test_quintessential_font import polygons
        for italic in (False, True):
            filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
            names = [entry["glyphName"] for entry in self.entries if ("Italic" if italic else "Roman") in entry["postures"]]
            for weight in WEIGHTS:
                with TTFont(OUTPUT / filename) as font:
                    glyphs = font.getGlyphSet(location={"wght": weight})
                    pairs = target_pair_values(font, glyphs.location)
                    shapes = {name: polygons(glyphs, name) for name in names}
                    self.assert_pairs_clear(shapes, {name: glyphs[name].width for name in names}, pairs, (italic, weight, "compiled"))

    def assert_pairs_clear(self, shapes, widths, pairs, context):
        from test_quintessential_font import outlines_overlap
        bounds = {name: (min(x for path in paths for x, _ in path), max(x for path in paths for x, _ in path))
                  for name, paths in shapes.items()}
        checked = exact = 0
        selected = {(target, name) for target in TARGET_NAMES for name in shapes}
        selected.update((name, target) for target in TARGET_NAMES for name in shapes)
        for left, right in sorted(selected):
            advance = widths[left] + pairs.get((left, right), 0)
            checked += 1
            offset = round(advance * 64)
            if bounds[left][1] <= bounds[right][0] + offset or bounds[right][1] + offset <= bounds[left][0]:
                continue
            exact += 1
            self.assertFalse(outlines_overlap(shapes[left], shapes[right], advance),
                             (context, left, right, pairs.get((left, right), 0), "Filled ink collision"))
        print(f"terminal pairs {context}: {checked} ordered pairs; {exact} exact filled intersections", flush=True)

    def test_source_pair_directions_clear_at_five_weights(self):
        from test_additions_font import interpolate_recordings, interpolation_factor
        for italic in (False, True):
            first, second = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
            names = [entry["glyphName"] for entry in self.entries if ("Italic" if italic else "Roman") in entry["postures"]]
            with Font.open(SOURCES / f"QuintessentialSerif-{first}.ufo") as light, Font.open(SOURCES / f"QuintessentialSerif-{second}.ufo") as bold:
                recordings = {name: (outline(light, name), outline(bold, name)) for name in names}
                for weight in WEIGHTS:
                    factor = interpolation_factor(weight)
                    shapes = {name: polygons_from_recording(interpolate_recordings(*recordings[name], factor)) for name in names}
                    widths = {name: light[name].width + factor * (bold[name].width - light[name].width) for name in names}
                    pairs = {pair: light.kerning.get(pair, 0) + factor * (bold.kerning.get(pair, 0) - light.kerning.get(pair, 0))
                             for pair in light.kerning.keys() | bold.kerning.keys()}
                    self.assert_pairs_clear(shapes, widths, pairs, (italic, weight, "source"))

    def test_two_bulb_sources_interpolate_as_one_open_nonintersecting_contour(self):
        from test_additions_font import interpolate_recordings, interpolation_factor
        for italic in (False, True):
            light_style, bold_style = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
            with Font.open(SOURCES / f"QuintessentialSerif-{light_style}.ufo") as light, Font.open(SOURCES / f"QuintessentialSerif-{bold_style}.ufo") as bold:
                for name in TARGET_NAMES:
                    for weight in WEIGHTS:
                        recording = interpolate_recordings(outline(light, name), outline(bold, name), interpolation_factor(weight))
                        self.assert_open_contour(recording, (italic, weight, name, "source"))
            filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
            with TTFont(OUTPUT / filename) as font:
                for weight in WEIGHTS:
                    glyphs = font.getGlyphSet(location={"wght": weight})
                    for name in TARGET_NAMES:
                        self.assert_open_contour(outline(glyphs, name), (italic, weight, name, "compiled"))

    def assert_open_contour(self, recording, context):
        paths = polygons_from_recording(recording)
        self.assertEqual(len(paths), 1, (context, "Contour count"))
        original_area = abs(pyclipper.Area(paths[0])) / 4096
        simplified = pyclipper.SimplifyPolygon(paths[0], pyclipper.PFT_NONZERO)
        self.assertEqual(len(simplified), 1, (context, "Self-intersection or closed opening"))
        self.assertLessEqual(abs(original_area - abs(pyclipper.Area(simplified[0])) / 4096), .1,
                             (context, "Self-intersection"))

    def test_native_bodies_and_both_complete_bulb_runs_survive_sources_and_compilation(self):
        from test_additions_font import (recording_quadratics, translated_quadratics,
            interpolate_points, interpolation_factor)
        from test_quintessential_font import (DONORS, DONOR_FILES, instantiated,
            quadratic_segments, assert_contains_quadratics)
        baseline = json.loads(gzip.decompress(BASELINE.read_bytes()))
        regions = {}
        for style, (italic, weight) in STYLES.items():
            with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source, instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                native, cmap = donor.getGlyphSet(), donor.getBestCmap()
                epsilon = outline(native, cmap[0x25B])
                for glyph_id, name in self.targets.items():
                    metadata = source[name].lib["org.quintessential.construction"]
                    self.assertEqual(metadata["terminalDesign"], "upper-and-lower-bulbs", (style, name))
                    self.assertEqual(metadata["counterCount"], 0, (style, name))
                    if glyph_id == "special-spine":
                        body = outline(native, cmap[0x73])
                        dx = baseline["sources"][style]["targets"][name]["lib"]["org.quintessential.construction"]["bodyOffsetX"]
                        self.assertAlmostEqual(metadata["bodyOffsetX"], dx, places=6)
                        indices = (*range(9, 12), *range(20, 23)) if italic else (*range(5, 8), *range(16, 19))
                        expected = translated_quadratics(recording_quadratics(body, indices), dx)
                        top, bottom = (11, 22) if italic else (7, 18)
                        anchor = epsilon[5][1][-1]
                        upper, lower = body[top][1][-1], body[bottom][1][-1]
                        bulb = recording_quadratics(epsilon, range(6, 11 if italic else 9))
                        expected += translated_quadratics(bulb, upper[0] - anchor[0] + dx, upper[1] - anchor[1])
                        expected += translated_quadratics(bulb, lower[0] + anchor[0] + dx, lower[1] + anchor[1],
                                                         reflected=True, reflected_y=True)
                        self.assertEqual(metadata["lowerTerminalDonorCodePoint"], 0x25B)
                    elif glyph_id == "special-turned-double-open-bowl" and not italic:
                        body = outline(native, cmap[0x25C])
                        expected = recording_quadratics(body, range(5, 19))
                        anchor, target = epsilon[5][1][-1], body[0][1][0]
                        expected += translated_quadratics(recording_quadratics(epsilon, range(6, 9)),
                            target[0] + anchor[0], target[1] + anchor[1], reflected=True, reflected_y=True)
                    else:
                        double = glyph_id == "special-turned-double-open-bowl"
                        code = 0x25C if double else 0x254
                        body = outline(native, cmap[code])
                        lower_end = 3 if double or not italic else 5
                        inner = 10 if double else (7 if italic else 5)
                        outer = 13 if double else (10 if italic else 8)
                        # Protect every unchanged native curve, including the
                        # complete lower bulb, side stress and middle spur.
                        expected = recording_quadratics(body, (*range(1, inner), *range(outer + 1, len(body) - 1)))
                        shear = -2 * math.tan(math.radians(-donor["post"].italicAngle))
                        anchor, target = body[0][1][0], body[outer][1][-1]
                        upper = [tuple((x + shear * (y - anchor[1]) + target[0] - anchor[0], target[1] + anchor[1] - y)
                                       for x, y in reversed(segment))
                                 for segment in recording_quadratics(body, range(1, lower_end + 1))]
                        expected += upper
                        self.assertAlmostEqual(metadata["upperTerminalShearX"], shear, places=6)
                        self.assertEqual(metadata["upperTerminalDonorCodePoint"], code)
                        self.assertEqual(metadata["lowerTerminalDonorCodePoint"], code)
                    assert_contains_quadratics(self, quadratic_segments(source, name), expected, 1e-5, (style, name, "Native source body and bulbs"))
                    regions[italic, weight, name] = expected
        for italic in (False, True):
            filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
            for weight in WEIGHTS:
                with TTFont(OUTPUT / filename) as font:
                    for name in TARGET_NAMES:
                        first, second = (regions[italic, endpoint, name] for endpoint in (400, 700))
                        self.assertEqual(len(first), len(second))
                        expected = [interpolate_points(a, b, interpolation_factor(weight)) for a, b in zip(first, second)]
                        assert_contains_quadratics(self, quadratic_segments(font.getGlyphSet(location={"wght": weight}), name), expected, .75,
                                                   (italic, weight, name, "Compiled native body and bulbs"))

    def test_revised_static_glyphs_match_the_variable_endpoints(self):
        from test_quintessential_font import polygons, symmetric_difference_area
        for style, (italic, weight) in STYLES.items():
            filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
            with TTFont(OUTPUT / f"QuintessentialSerif-{style}.otf") as static, TTFont(OUTPUT / filename) as variable:
                first, second = static.getGlyphSet(), variable.getGlyphSet(location={"wght": weight})
                for name in TARGET_NAMES:
                    self.assertEqual(first[name].width, second[name].width, (style, name, "Static advance"))
                    for steps in (192, 384, 768):
                        for scale in (64, 4096, 65536):
                            area = symmetric_difference_area(polygons(first, name, steps=steps, scale=scale),
                                polygons(second, name, steps=steps, scale=scale), scale=scale)
                            if area <= 1.0:
                                break
                        if area <= 1.0:
                            break
                    self.assertLessEqual(area, 1.0, (style, name, "Static target differs from variable", area))


def main():
    global BASELINE, COMPILED_FACES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--capture-from", type=Path, default=ROOT / ".tmp/stemless-terminals-baseline")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--compiled-faces", help="Comma-separated faces for a staged compiled-preservation check")
    args, rest = parser.parse_known_args()
    BASELINE = args.baseline
    COMPILED_FACES = set(args.compiled_faces.split(",")) if args.compiled_faces else None
    if args.capture:
        if args.capture.exists():
            raise SystemExit(f"Refusing to overwrite {args.capture}")
        data = gzip.compress(json.dumps(capture(args.capture_from), sort_keys=True, separators=(",", ":")).encode(), mtime=0)
        args.capture.write_bytes(data)
        print(hashlib.sha256(data).hexdigest())
        return
    unittest.main(argv=[__file__, *rest])


if __name__ == "__main__":
    main()

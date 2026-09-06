#!/usr/bin/env python3
"""Preserve 0.210 semantic identities through the 0.220 allocation migration.

The pre-change capture supplies the old identity registry independently of the
new construction code. Internal glyph names and their GID prefix stay fixed;
only assigned characters move. The authorized s correction is the only old
metrics and pair exception. The later shared-spine optical revision permits the
396 Roman forms with an internal spine to change their body counters and
explicitly reviewed local joins, while retaining advances, metrics, effective
pairs, and every other native region.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import unittest

import pyclipper
from fontTools.misc.fixedTools import floatToFixedToFloat
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.varLib.models import piecewiseLinearMap
from ufoLib2 import Font

from font_geometry_helpers import counter_recordings, interpolate_points, polygons_from_recording, shift
from font_geometry_helpers import effective_pairs, outline, ZERO_PAIR
from verify_logical_allocation import historical_entry
from test_quintessential_font import (
    ALLOCATION, ALLOCATION_BY_ID, ALLOCATION_BY_NAME, ALLOCATION_ENTRIES,
    DONORS, DONOR_FILES, EXPECTED_AVAR, MAIN_SCRIPT_CMAP, OUTPUT, POSTURE_CMAPS, ROOT,
    SAMPLE_WEIGHTS, SOURCES, STATIC_FACES, VARIABLE_FILES, instantiated,
    QuadraticSegmentPen, assert_contains_quadratics, filled_counter_paths,
    filled_shape_paths, filled_scanline_intervals, outlines_overlap, quadratic_segments, native_contour_edges,
)


BASELINE = ROOT / "tests/baselines/0.210"
BASELINE_0150 = ROOT / "tests/baselines/0.150"
CHANGED_ID = "special-spine"
CHANGED_NAME = "uF2B03"
OPTICAL_REVISION_ID = "opposed-bowls-0-0"
OPTICAL_REVISION_NAME = "uF2B1C"


def has_internal_spine(entry):
    """Select the structure independently of the production recipe dispatch."""
    kinds = [part["kind"] for part in entry["parts"]]
    return "spine" in kinds and 0 < kinds.index("spine") < len(kinds) - 1


# This historical increment required every internal end to extend together.
# Mixed states have their own independent geometry/preservation suite.
HISTORICAL_ENTRIES = tuple(entry for entry in ALLOCATION_ENTRIES if "middleLegExtensions" not in entry)
SHARED_SPINE_ENTRIES = tuple(entry for entry in HISTORICAL_ENTRIES if has_internal_spine(entry))
SHARED_SPINE_NAMES = frozenset(entry["glyphName"] for entry in SHARED_SPINE_ENTRIES)
OLD_CMAPS = {
    False: {**MAIN_SCRIPT_CMAP,
            **{code: f"u{code:X}" for code in range(0xF2B00, 0xF2BA0)},
            **{code: f"u{code:X}" for code in range(0xF2C00, 0xF2CC0)}},
    True: {**MAIN_SCRIPT_CMAP,
           **{code: f"u{code:X}" for code in range(0xF2B00, 0xF2B04)},
           **{code: f"u{code:X}" for code in range(0xF2B10, 0xF2B1C)},
           **{code: f"u{code:X}" for code in range(0xF2B4C, 0xF2B58)}},
}
OLD_NAMES = {italic: (".notdef", "space", *cmap.values()) for italic, cmap in OLD_CMAPS.items()}
MAIN_NAMES = (".notdef", "space", *MAIN_SCRIPT_CMAP.values())
COMPILED = True

SPECIAL_DONORS = {
    "special-ring": 0x6F,
    "special-open-bowl": 0x63,
    "special-turned-open-bowl": 0x254,
    "special-double-open-bowl": 0x25B,
    "special-turned-double-open-bowl": 0x25C,
}
SPECIAL_IDS = (*SPECIAL_DONORS, "special-closed-double-bowl", "special-spine")


def interpolation_factor(weight):
    return floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)


def interpolate_recordings(first, second, factor):
    if [(op, len(points)) for op, points in first] != [(op, len(points)) for op, points in second]:
        raise AssertionError("Source endpoints are not compatible")
    return [(op, interpolate_points(points, other, factor))
            for (op, points), (_, other) in zip(first, second)]


def recording_bounds(recording):
    pen = BoundsPen(None)
    replayRecording(recording, pen)
    return pen.bounds


def recording_quadratics(recording, indices=None):
    pen = QuadraticSegmentPen()
    if indices is None:
        replayRecording(recording, pen)
    else:
        for index in indices:
            operation, points = recording[index]
            if operation == "qCurveTo":
                replayRecording([("moveTo", (recording[index - 1][1][-1],)),
                                 (operation, points), ("endPath", ())], pen)
    return pen.segments


def translated_quadratics(segments, dx=0, dy=0, reflected=False, reflected_y=False, reversed_run=False):
    sign = -1 if reflected else 1
    sign_y = -1 if reflected_y else 1
    return [tuple((sign * x + dx, sign_y * y + dy) for x, y in (reversed(segment) if reversed_run else segment))
            for segment in segments]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# The independent old recipe identities define every eligible companion, without
# using the production dispatch table or the new catalogue's middle-leg flags.
MIDDLE_FAMILIES = (
    (0xF2A45, 12, 1, "arm"), (0xF2A51, 12, 1, "arch"),
    (0xF2A5D, 12, 1, "bowl"), (0xF2A69, 12, 1, "arch"),
    (0xF2A75, 12, 1, "arch"), (0xF2B40, 12, 1, "double-bowl"),
    (0xF2B4C, 12, 1, "spine"), (0xF2B58, 36, 1, "left"),
    (0xF2B7C, 36, 1, "right"), (0xF2C00, 12, 2, "arm"),
    (0xF2C0C, 12, 2, "arch"), (0xF2C18, 12, 2, "bowl"),
    (0xF2C24, 12, 2, "arch"), (0xF2C30, 12, 2, "arch"),
    (0xF2C3C, 12, 2, "double-bowl"), (0xF2C48, 12, 2, "spine"),
    (0xF2C54, 36, 2, "left"), (0xF2C78, 36, 2, "right"),
    (0xF2C9C, 36, 2, "both"),
)
MIDDLE_RECIPES = {code: (start, count, kind)
                  for start, length, count, kind in MIDDLE_FAMILIES
                  for code in range(start, start + length)}


def middle_directions(recipe):
    first, count, kind = MIDDLE_RECIPES[recipe]
    if kind == "both":
        return ("descender", "ascender")
    turned = kind == "right" if kind in ("left", "right") else (recipe - first) % 4 >= 2
    return ("ascender" if turned else "descender",) * count


def middle_counter_reference(recipe):
    first, _, kind = MIDDLE_RECIPES[recipe]
    if kind in ("left", "right", "both"):
        left, right = divmod(recipe - first, 6)
        left = 3 if kind in ("left", "both") else left
        right = 1 if kind in ("right", "both") else right
        return 0xF2B1C + 6 * left + right
    return recipe


class AdditionsBaselineTests(unittest.TestCase):
    def test_capture_and_independent_semantic_registry_are_intact(self):
        for version, root in (("0.210", BASELINE), ("0.150", BASELINE_0150)):
            manifest = json.loads((root / "fixture-manifest.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(manifest["version"], version)
            self.assertEqual(manifest["kind"], "font-only-preservation-subset")
            self.assertEqual(len(manifest["files"]), manifest["fileCount"])
            actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
                      and p.name != "fixture-manifest.json"}
            self.assertEqual(actual, set(manifest["files"]))
            for filename, record in manifest["files"].items():
                self.assertEqual(sha256(root / filename), record["sha256"], filename)
                self.assertEqual((root / filename).stat().st_size, record["bytes"])
        capture = json.loads((BASELINE / "fixture-manifest.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(capture["sourceCaptureSha256"], "ef560a02788d28ecf617ab73fc468015b01e72bb41dd627cdc39b1560ecb6b1b")
        self.assertEqual(capture["sourceSemanticRegistrySha256"], "839074a1950724cf4864b4d2cc9dbb10638631cf4e697a89813e2f94ecaa0efb")

    def test_semantic_migration_keeps_all_old_identities_names_and_postures(self):
        captured = json.loads((BASELINE / "semantic-identities.json").read_text(encoding="utf-8"))
        self.assertEqual((captured["version"], captured["romanGlyphs"], captured["italicGlyphs"]),
                         ("0.210", 481, 157))
        self.assertEqual(len(captured["entries"]), 481)
        self.assertEqual(len({entry["glyphId"] for entry in captured["entries"]}), 481)
        self.assertEqual({italic: len(cmap) for italic, cmap in OLD_CMAPS.items()}, {False: 481, True: 157})
        expected_by_code = {entry["oldCodePoint"]: entry["oldGlyphName"] for entry in captured["entries"]}
        self.assertEqual(expected_by_code, OLD_CMAPS[False])
        self.assertEqual({entry["oldCodePoint"]: entry["oldGlyphName"] for entry in captured["entries"]
                          if "Italic" in entry["postures"]}, OLD_CMAPS[True])
        for before in captured["entries"]:
            current = ALLOCATION_BY_ID[before["glyphId"]]
            with self.subTest(glyphId=before["glyphId"]):
                self.assertEqual(current["glyphName"], before["oldGlyphName"])
                self.assertEqual(current["oldCodePoint"], before["oldCodePoint"])
                self.assertEqual(current["recipeCodePoint"], before["oldCodePoint"])
                self.assertTrue(set(before["postures"]) <= set(current["postures"]))
                self.assertEqual(current["postures"], ["Roman", "Italic"])
                self.assertEqual(current["parts"], before["parts"])
                self.assertEqual(historical_entry(current)["familyId"], before["familyId"])
                self.assertEqual(current["legacyIndex"], before["legacyIndex"])
                self.assertFalse(current["middleLegs"])
        self.assertEqual(ALLOCATION_BY_ID[CHANGED_ID]["glyphName"], CHANGED_NAME)
        revised = historical_entry(ALLOCATION_BY_ID[OPTICAL_REVISION_ID])
        self.assertEqual((revised["codePoint"], revised["glyphName"], revised["recipeCodePoint"],
                          revised["postures"]),
                         (0xF2B18, OPTICAL_REVISION_NAME, 0xF2B1C, ["Roman", "Italic"]))
        self.assertEqual(len(SHARED_SPINE_ENTRIES), 396)
        self.assertEqual(len(SHARED_SPINE_NAMES), 396)
        self.assertEqual(sum(entry["middleLegs"] for entry in SHARED_SPINE_ENTRIES), 180)
        self.assertTrue(all(entry["postures"] == ["Roman", "Italic"] for entry in SHARED_SPINE_ENTRIES))
        historic_internal = {entry["glyphId"] for entry in captured["entries"] if has_internal_spine(entry)}
        current_internal = {entry["glyphId"] for entry in SHARED_SPINE_ENTRIES if entry["oldCodePoint"] is not None}
        self.assertEqual(len(historic_internal), 216)
        self.assertEqual(current_internal, historic_internal)
        self.assertTrue(all(entry["baseGlyphId"] in historic_internal
                            for entry in SHARED_SPINE_ENTRIES if entry["middleLegs"]))
        self.assertEqual(sum(entry["middleLegs"] for entry in HISTORICAL_ENTRIES), 348)
        self.assertEqual(sum(entry["middleLegs"] and "Italic" in entry["postures"]
                             for entry in HISTORICAL_ENTRIES), 348)
        self.assertEqual(sum(entry["oldCodePoint"] is None and not entry["middleLegs"]
                             for entry in ALLOCATION_ENTRIES), 3)
        self.assertEqual((ALLOCATION["version"], ALLOCATION["previousVersion"]), ("0.250", "0.240"))

    def assert_pairs_preserved(self, before, after, names, zero, changed_name=CHANGED_NAME):
        for left in names:
            for right in names:
                if changed_name in (left, right):
                    continue
                pair = left, right
                self.assertEqual(before.get(pair, zero), after.get(pair, zero), pair)

    def connection_metadata(self, name, weight):
        from reviewed_spine_connections import interpolate_connection_metadata
        if not hasattr(self, "_connection_masters"):
            self._connection_masters = {}
            for style, endpoint in (("Regular", 400), ("Bold", 700)):
                source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
                self._connection_masters[endpoint] = {
                    glyph: dict(source[glyph].lib["org.quintessential.construction"])
                    for glyph in SHARED_SPINE_NAMES}
                source.close()
        return interpolate_connection_metadata(self._connection_masters[400][name],
                                               self._connection_masters[700][name], weight)

    def test_all_prior_source_outlines_advances_and_semantic_pairs_are_preserved(self):
        for style, (_weight, italic) in STATIC_FACES.items():
            filename = f"QuintessentialSerif-{style}.ufo"
            before = Font.open(BASELINE / "fonts/QuintessentialSerif" / filename)
            after = Font.open(SOURCES / filename)
            try:
                self.assertEqual(tuple(before.glyphOrder), OLD_NAMES[italic])
                self.assertEqual(tuple(after.glyphOrder[:len(before.glyphOrder)]), tuple(before.glyphOrder))
                self.assertEqual(set(before.kerning), {(left, right) for left in OLD_CMAPS[italic].values()
                                                      for right in OLD_CMAPS[italic].values()})
                for name in OLD_NAMES[italic]:
                    with self.subTest(style=style, glyph=name):
                        if name != CHANGED_NAME:
                            if italic or name not in SHARED_SPINE_NAMES:
                                self.assertEqual(outline(after, name), outline(before, name))
                            else:
                                from reviewed_spine_connections import assert_preserved_connections
                                assert_preserved_connections(outline(before, name), outline(after, name),
                                                             ALLOCATION_BY_NAME[name], after[name].lib["org.quintessential.construction"])
                            self.assertEqual(after[name].width, before[name].width)
                        expected = [ALLOCATION_BY_NAME[name]["codePoint"]] if name in ALLOCATION_BY_NAME else before[name].unicodes
                        self.assertEqual(after[name].unicodes, expected)
                self.assert_pairs_preserved(before.kerning, after.kerning, OLD_NAMES[italic], 0)
            finally:
                before.close()
                after.close()

    def assert_compiled_preserved(self, before, after, italic, weight):
        self.assertEqual(before.getBestCmap(), {0x20: "space", **OLD_CMAPS[italic]})
        self.assertEqual(after.getBestCmap(), {0x20: "space", **POSTURE_CMAPS[italic]})
        self.assertEqual(tuple(after.getGlyphOrder()[:len(OLD_NAMES[italic])]), OLD_NAMES[italic])
        original, current = before.getGlyphSet(), after.getGlyphSet()
        for name in OLD_NAMES[italic]:
            if name != CHANGED_NAME:
                if italic or name not in SHARED_SPINE_NAMES:
                    self.assertEqual(outline(current, name), outline(original, name), name)
                else:
                    from reviewed_spine_connections import assert_preserved_connections
                    assert_preserved_connections(outline(original, name), outline(current, name),
                                                 ALLOCATION_BY_NAME[name], self.connection_metadata(name, weight),
                                                 tolerance=1 / 64)
                self.assertEqual(after["hmtx"][name], before["hmtx"][name], name)
        self.assert_pairs_preserved(effective_pairs(before), effective_pairs(after), OLD_NAMES[italic], ZERO_PAIR)

    def test_all_prior_static_outlines_metrics_and_semantic_pairs_are_preserved(self):
        if not COMPILED:
            self.skipTest("--sources-only requested")
        for style, (_weight, italic) in STATIC_FACES.items():
            filename = f"QuintessentialSerif-{style}.otf"
            with self.subTest(style=style), TTFont(BASELINE / "resources/fonts/QuintessentialSerif" / filename) as before, \
                    TTFont(OUTPUT / filename) as after:
                self.assert_compiled_preserved(before, after, italic, _weight)

    def test_all_prior_variable_outlines_metrics_and_semantic_pairs_at_five_weights(self):
        if not COMPILED:
            self.skipTest("--sources-only requested")
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(BASELINE / "resources/fonts/QuintessentialSerif" / filename, weight) as before, \
                        instantiated(OUTPUT / filename, weight) as after:
                    self.assert_compiled_preserved(before, after, italic, weight)

    def test_variable_axis_and_nonlinear_mapping_remain_unchanged(self):
        if not COMPILED:
            self.skipTest("--sources-only requested")
        for filename in VARIABLE_FILES.values():
            with TTFont(BASELINE / "resources/fonts/QuintessentialSerif" / filename) as before, \
                    TTFont(OUTPUT / filename) as after:
                fields = ("axisTag", "minValue", "defaultValue", "maxValue", "flags")
                self.assertEqual([tuple(getattr(axis, field) for field in fields) for axis in after["fvar"].axes],
                                 [tuple(getattr(axis, field) for field in fields) for axis in before["fvar"].axes])
                self.assertEqual(after["avar"].segments, before["avar"].segments)
                self.assertEqual(after["avar"].segments["wght"], EXPECTED_AVAR)


class StemlessSpecialGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {(italic, weight): Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
                       for style, (weight, italic) in STATIC_FACES.items()}

    @classmethod
    def tearDownClass(cls):
        for source in cls.sources.values():
            source.close()

    def test_seven_special_assignments_and_posture_specific_native_direct_forms(self):
        self.assertEqual({entry["glyphId"] for entry in ALLOCATION_ENTRIES if entry["stemless"]},
                         set(SPECIAL_IDS))
        for (italic, weight), source in self.sources.items():
            with instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                native, cmap = donor.getGlyphSet(), donor.getBestCmap()
                for glyph_id in SPECIAL_IDS:
                    entry = ALLOCATION_BY_ID[glyph_id]
                    name = entry["glyphName"]
                    metadata = source[name].lib["org.quintessential.construction"]
                    self.assertEqual(source[name].unicodes, [entry["codePoint"]])
                    self.assertEqual(metadata["family"], "stemless-specials")
                    self.assertEqual(metadata["glyphId"], glyph_id)
                    self.assertEqual(metadata["posture"], "Italic" if italic else "Roman")
                    self.assertEqual(source[name].width, round(metadata["advanceWidth"], 6))
                    if glyph_id in SPECIAL_DONORS and (italic or glyph_id != "special-turned-double-open-bowl"):
                        code = SPECIAL_DONORS[glyph_id]
                        self.assertEqual(metadata["bodyDonorCodePoint"], code)
                        self.assertEqual(outline(source, name), outline(native, cmap[code]))
                        self.assertEqual(source[name].width, donor["hmtx"][cmap[code]][0])
        if not COMPILED:
            return
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    current, native, cmap = font.getGlyphSet(), donor.getGlyphSet(), donor.getBestCmap()
                    for glyph_id, code in SPECIAL_DONORS.items():
                        if not italic and glyph_id == "special-turned-double-open-bowl":
                            continue
                        name = ALLOCATION_BY_ID[glyph_id]["glyphName"]
                        self.assertEqual(outline(current, name), outline(native, cmap[code]), (italic, weight, name))
                        self.assertEqual(font["hmtx"][name], donor["hmtx"][cmap[code]], (italic, weight, name))

    def assert_special_geometry(self, recording, glyph_id, advance, context):
        paths = polygons_from_recording(recording)
        clipper = pyclipper.Pyclipper()
        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
        self.assertEqual(len(tree.Childs), 1, (context, "disconnected stemless form"))
        counters = filled_counter_paths(paths)
        expected = 2 if glyph_id == "special-closed-double-bowl" else int(glyph_id == "special-ring")
        self.assertEqual(len(counters), expected, (context, "unexpected stemless counters"))
        for counter in counters:
            self.assertGreater(abs(pyclipper.Area(counter)) / 4096, 1000, (context, "collapsed counter"))
        self.assertFalse(outlines_overlap(paths, paths, advance), (context, "unkerned self collision"))
        if glyph_id == "special-closed-double-bowl":
            bounds = sorted((min(y for _, y in path) / 64, max(y for _, y in path) / 64)
                            for path in counters)
            self.assertGreater(bounds[1][0] - bounds[0][1], 5, (context, "collapsed closed-bowl waist"))

    def test_all_specials_keep_connected_counters_and_native_spacing_at_five_weights(self):
        for italic in (False, True):
            for glyph_id in SPECIAL_IDS:
                name = ALLOCATION_BY_ID[glyph_id]["glyphName"]
                light, bold = (outline(self.sources[italic, weight], name) for weight in (400, 700))
                for weight in SAMPLE_WEIGHTS:
                    factor = interpolation_factor(weight)
                    recording = interpolate_recordings(light, bold, factor)
                    advance = self.sources[italic, 400][name].width + factor * (
                        self.sources[italic, 700][name].width - self.sources[italic, 400][name].width)
                    self.assert_special_geometry(recording, glyph_id, advance, (italic, weight, name, "source"))
        if not COMPILED:
            return
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font:
                    glyphs = font.getGlyphSet()
                    for glyph_id in SPECIAL_IDS:
                        name = ALLOCATION_BY_ID[glyph_id]["glyphName"]
                        self.assert_special_geometry(outline(glyphs, name), glyph_id, font["hmtx"][name][0],
                                                     (italic, weight, name, "compiled"))

    def test_composed_special_bodies_and_orientation_specific_terminals_remain_native(self):
        references, selected = {}, {}
        for (italic, weight), source in self.sources.items():
            with instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                native, cmap = donor.getGlyphSet(), donor.getBestCmap()
                epsilon = outline(native, cmap[0x25B])
                reversed_epsilon = outline(native, cmap[0x25C])
                spine = outline(native, cmap[0x73])
                targets = ("special-closed-double-bowl", "special-spine", *(() if italic else ("special-turned-double-open-bowl",)))
                for glyph_id in targets:
                    name = ALLOCATION_BY_ID[glyph_id]["glyphName"]
                    metadata = source[name].lib["org.quintessential.construction"]
                    actual = quadratic_segments(source, name)
                    if glyph_id == "special-closed-double-bowl":
                        self.assertEqual((metadata["leftDonorCodePoint"], metadata["rightDonorCodePoint"]), (0x25B, 0x25C))
                        dx = epsilon[5][1][-1][0] - reversed_epsilon[13][1][-1][0]
                        self.assertAlmostEqual(metadata["rightDonorOffsetX"], dx, places=5)
                        expected = [*recording_quadratics(epsilon, range(2, 5)),
                                    *translated_quadratics(recording_quadratics(reversed_epsilon, range(15, 18)), dx)]
                        right_bearing = donor["hmtx"][cmap[0x25C]][0] - recording_bounds(reversed_epsilon)[2]
                        self.assertAlmostEqual(source[name].width - recording_bounds(outline(source, name))[2],
                                               right_bearing, places=4)
                    elif glyph_id == "special-turned-double-open-bowl":
                        self.assertEqual(metadata["bodyDonorCodePoint"], 0x25C)
                        self.assertEqual(metadata["upperTerminalDonorCodePoint"], 0x25C)
                        self.assertEqual(metadata["lowerTerminalDonorCodePoint"], 0x25B)
                        self.assertTrue(metadata["upperTerminalReflectedY"])
                        self.assertTrue(metadata["upperTerminalReversed"])
                        self.assertTrue(metadata["lowerTerminalTurned"])
                        self.assertEqual(source[name].width, donor["hmtx"][cmap[0x25C]][0])
                        expected = recording_quadratics(reversed_epsilon, (*range(5, 10), *range(14, 19)))
                        expected += translated_quadratics(recording_quadratics(reversed_epsilon, range(1, 4)),
                            metadata["upperTerminalOffsetX"], metadata["upperTerminalOffsetY"],
                            reflected_y=True, reversed_run=True)
                        expected += translated_quadratics(recording_quadratics(epsilon, range(6, 9)),
                            metadata["lowerTerminalOffsetX"], metadata["lowerTerminalOffsetY"],
                            reflected=True, reflected_y=True)
                    else:
                        self.assertEqual(metadata["bodyDonorCodePoint"], 0x73)
                        self.assertEqual(metadata["upperTerminalDonorCodePoint"], 0x25B)
                        self.assertEqual(metadata["lowerTerminalDonorCodePoint"], 0x25B if italic else 0x25C)
                        self.assertEqual(metadata["lowerTerminalReflectedX"], italic)
                        dx = metadata["bodyOffsetX"]
                        self.assertGreaterEqual(dx, 0)
                        self.assertAlmostEqual(source[name].width, donor["hmtx"][cmap[0x73]][0] + dx, places=5)
                        native_left = recording_bounds(spine)[0]
                        current_left = recording_bounds(outline(source, name))[0]
                        self.assertAlmostEqual(current_left, native_left, places=4)
                        body_indices = (*range(9, 12), *range(20, 23)) if italic else (*range(5, 8), *range(16, 19))
                        expected = translated_quadratics(recording_quadratics(spine, body_indices), dx)
                        expected += translated_quadratics(recording_quadratics(epsilon, range(6, 11 if italic else 9)),
                            metadata["upperTerminalOffsetX"], metadata["upperTerminalOffsetY"])
                        lower_native = epsilon if italic else reversed_epsilon
                        lower_indices = range(18, 21) if italic else range(1, 4)
                        expected += translated_quadratics(recording_quadratics(lower_native, lower_indices),
                            metadata["lowerTerminalOffsetX"], metadata["lowerTerminalOffsetY"],
                            reflected=italic, reversed_run=italic)
                    assert_contains_quadratics(self, actual, expected, 1e-5, (italic, weight, name, "native source region"))
                    indices = set()
                    for segment in expected:
                        errors = [max(abs(a - b) for p, q in zip(part, segment) for a, b in zip(p, q)) for part in actual]
                        self.assertLessEqual(min(errors), 1e-5)
                        indices.update(index for index, error in enumerate(errors) if error <= 1e-5)
                    references[italic, weight, name] = actual
                    selected[italic, weight, name] = indices
        for italic in (False, True):
            targets = ("special-closed-double-bowl", "special-spine", *(() if italic else ("special-turned-double-open-bowl",)))
            for glyph_id in targets:
                name = ALLOCATION_BY_ID[glyph_id]["glyphName"]
                light, bold = (references[italic, endpoint, name] for endpoint in (400, 700))
                self.assertEqual(len(light), len(bold))
                indices = selected[italic, 400, name] | selected[italic, 700, name]
                for weight in SAMPLE_WEIGHTS:
                    factor = interpolation_factor(weight)
                    expected = [interpolate_points(light[index], bold[index], factor) for index in sorted(indices)]
                    recording = interpolate_recordings(outline(self.sources[italic, 400], name),
                                                       outline(self.sources[italic, 700], name), factor)
                    assert_contains_quadratics(self, recording_quadratics(recording), expected, 1e-5,
                                               (italic, weight, name, "source interpolated native region"))
        if not COMPILED:
            return
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                factor = interpolation_factor(weight)
                with instantiated(OUTPUT / filename, weight) as font:
                    glyphs = font.getGlyphSet()
                    targets = ("special-closed-double-bowl", "special-spine", *(() if italic else ("special-turned-double-open-bowl",)))
                    for glyph_id in targets:
                        name = ALLOCATION_BY_ID[glyph_id]["glyphName"]
                        light, bold = (references[italic, endpoint, name] for endpoint in (400, 700))
                        self.assertEqual(len(light), len(bold))
                        indices = selected[italic, 400, name] | selected[italic, 700, name]
                        expected = [interpolate_points(light[index], bold[index], factor) for index in sorted(indices)]
                        assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected, .75,
                                                   (italic, weight, name, "compiled native region"))
                        expected_advance = self.sources[italic, 400][name].width + factor * (
                            self.sources[italic, 700][name].width - self.sources[italic, 400][name].width)
                        self.assertLessEqual(abs(font["hmtx"][name][0] - expected_advance), 1.0)


class MiddleLegGeometryTests(unittest.TestCase):
    """Check new free ends against the independent 0.210 parents and donors."""

    @classmethod
    def setUpClass(cls):
        cls.sources, cls.baseline = {}, {}
        for style, (weight, italic) in STATIC_FACES.items():
            filename = f"QuintessentialSerif-{style}.ufo"
            cls.sources[italic, weight] = Font.open(SOURCES / filename)
            cls.baseline[italic, weight] = Font.open(BASELINE / "fonts/QuintessentialSerif" / filename)
        cls.entries = {italic: [entry for entry in HISTORICAL_ENTRIES
                                if entry["middleLegs"] and (not italic or entry["recipeCodePoint"] in OLD_CMAPS[True])]
                       for italic in (False, True)}
        cls.native_stems, cls.native_stem_recordings, cls.native_stem_samples = {}, {}, {}
        for italic in (False, True):
            for weight in (400, 700):
                with instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    for code in (0x64, 0x6C, 0x70):
                        recording = outline(donor.getGlyphSet(), donor.getBestCmap()[code])
                        cls.native_stem_recordings[italic, weight, code] = recording
                        cls.native_stems[italic, weight, code] = filled_shape_paths(polygons_from_recording(recording))

    @classmethod
    def tearDownClass(cls):
        for font in (*cls.sources.values(), *cls.baseline.values()):
            font.close()

    def assert_counters(self, recording, reference, tolerance, context):
        actual_filled = filled_counter_paths(polygons_from_recording(recording))
        native_filled = filled_counter_paths(polygons_from_recording(reference))
        translations = []
        remaining = list(actual_filled)
        for native in native_filled:
            old_bounds = (min(x for x, _ in native), min(y for _, y in native),
                          max(x for x, _ in native), max(y for _, y in native))
            matches = []
            for index, candidate in enumerate(remaining):
                bounds = (min(x for x, _ in candidate), min(y for _, y in candidate),
                          max(x for x, _ in candidate), max(y for _, y in candidate))
                error = max(abs(bounds[1] - old_bounds[1]), abs(bounds[3] - old_bounds[3]),
                            abs((bounds[2] - bounds[0]) - (old_bounds[2] - old_bounds[0]))) / 64
                dx = round((bounds[0] + bounds[2] - old_bounds[0] - old_bounds[2]) / 2)
                shifted = [(x + dx, y) for x, y in native]
                clipper = pyclipper.Pyclipper()
                clipper.AddPath(candidate, pyclipper.PT_SUBJECT, True)
                clipper.AddPath(shifted, pyclipper.PT_CLIP, True)
                xor = clipper.Execute(pyclipper.CT_XOR, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                # Clipper returns nested holes with opposite winding; retain
                # that subtraction when two rounded counters form an annulus.
                area = abs(sum(pyclipper.Area(path) for path in xor)) / 4096
                matches.append((error, area, index, dx))
            self.assertTrue(matches, (context, "missing filled native body counter"))
            error, area, index, dx = min(matches)
            self.assertLessEqual(error, 2 * tolerance + 1 / 16, (context, "native filled counter bounds changed"))
            perimeter = sum(math.hypot(x - a, y - b) for (x, y), (a, b) in zip(native, [*native[1:], native[0]])) / 64
            self.assertLessEqual(area, max(1, perimeter * (tolerance + 1 / 32)),
                                 (context, "native filled counter shape changed"))
            translations.append(dx / 64)
            remaining.pop(index)
        if translations:
            self.assertLessEqual(max(translations) - min(translations), 2 * tolerance + 1 / 16,
                                 (context, "native body counter spacing changed"))
        actual, expected = counter_recordings(recording), counter_recordings(reference)
        self.assertGreaterEqual(len(actual), len(expected), (context, "native counter count"))
        if not expected:
            return
        # One common rigid translation preserves body width and the spacing
        # between native counters, including compact terminal counters.
        shifts = []
        for before in expected:
            matches = []
            for index, after in enumerate(actual):
                if [(op, len(points)) for op, points in after] != [(op, len(points)) for op, points in before]:
                    continue
                deltas = [x - old_x for (_, points), (_, old_points) in zip(after, before)
                          for (x, _), (old_x, _) in zip(points, old_points)]
                dx = (max(deltas) + min(deltas)) / 2
                error = max(abs(a - b) for (_, points), (_, old_points) in zip(after, shift(before, dx))
                            for point, old_point in zip(points, old_points) for a, b in zip(point, old_point))
                matches.append((error, index, dx))
            self.assertTrue(matches, (context, "missing native raw counter topology"))
            error, index, dx = min(matches)
            self.assertLessEqual(error, tolerance, (context, "native counter geometry or body width changed"))
            shifts.append(dx)
            actual.pop(index)
        self.assertLessEqual(max(shifts) - min(shifts), 2 * tolerance,
                             (context, "native raw counter spacing changed"))

    def native_shaft_bands(self, italic, weight, name):
        recipe = ALLOCATION_BY_NAME[name]["recipeCodePoint"]
        first, _, kind = MIDDLE_RECIPES[recipe]
        endpoints = []
        for endpoint in (400, 700):
            metadata = self.sources[italic, endpoint][name].lib["org.quintessential.construction"]
            turned = kind == "right" if kind in ("left", "right") else (recipe - first) % 4 >= 2
            arch_shift = -metadata["terminalOffsetX"] if turned and kind not in ("arch", "both") else 0
            bands = []
            for leg in metadata["extendedMiddleLegs"]:
                code = leg["donorCodePoint"]
                paths = self.native_stems[italic, endpoint, code]
                height = 600.37 if leg["direction"] == "ascender" else -100.37
                if "terminalOffsetX" in leg:
                    dx = leg["terminalOffsetX"] + arch_shift
                elif leg.get("owner") == "terminal" and ("freeLegOffsetX" in metadata or
                                                         ("upperOffsetX" if turned else "lowerOffsetX") in metadata):
                    key = "upperOffsetX" if turned else "lowerOffsetX"
                    dx = metadata["freeLegOffsetX"] if "freeLegOffsetX" in metadata else metadata.get(key, 0)
                    dx += 0 if turned else metadata["terminalOffsetX"]
                else:
                    # Unannotated terminal-owned legs use the native straight
                    # shaft at y250; curved Italic m has its explicit offset.
                    native250 = filled_scanline_intervals(paths, 250)[-1 if code == 0x64 else 0]
                    dx = leg["centerX"] - sum(native250) / 2
                clipped = None
                if any(join["middleStemCenterX"] == leg["centerX"] for join in metadata.get("middleHookJoins", [])):
                    # The hook clips a slanted native shaft at a changing y.
                    # Constrain both endpoint lines against the donor before
                    # interpolating their compatible clipped endpoints.
                    def crossing_lines(recording, scan_y):
                        result, current = [], None
                        for index, (operation, points) in enumerate(recording):
                            if operation == "lineTo" and min(current[1], points[-1][1]) < scan_y < max(current[1], points[-1][1]):
                                result.append((index, current, points[-1]))
                            if points:
                                current = points[-1]
                        return result
                    native_edges = crossing_lines(self.native_stem_recordings[italic, endpoint, code],
                                                  550 if height > 0 else -50)
                    self.assertEqual(len(native_edges), 2)
                    source_edges = crossing_lines(outline(self.sources[italic, endpoint], name), height)
                    clipped = []
                    for _, a, b in native_edges:
                        slope = (b[0] - a[0]) / (b[1] - a[1])
                        matches = [edge for edge in source_edges
                                   if max(abs(x - a[0] - dx - slope * (y - a[1])) for x, y in edge[1:]) <= 1e-5]
                        self.assertEqual(len(matches), 1, (italic, endpoint, name, "native clipped shaft line"))
                        clipped.append(matches[0])
                bands.append((code, height, dx, clipped))
            endpoints.append(bands)
        self.assertEqual([band[:2] for band in endpoints[0]], [band[:2] for band in endpoints[1]])
        factor = interpolation_factor(weight)
        result = []
        for (code, height, light_dx, light_clipped), (_, _, bold_dx, bold_clipped) in zip(*endpoints):
            if light_clipped is not None:
                self.assertIsNotNone(bold_clipped)
                self.assertEqual([edge[0] for edge in light_clipped], [edge[0] for edge in bold_clipped])
                crossings = []
                for a, b in zip(light_clipped, bold_clipped):
                    start, end = interpolate_points(a[1:], b[1:], factor)
                    self.assertLess(min(start[1], end[1]), height)
                    self.assertGreater(max(start[1], end[1]), height)
                    crossings.append(start[0] + (end[0] - start[0]) * (height - start[1]) / (end[1] - start[1]))
                result.append((height, *sorted(crossings)))
                continue
            key = italic, weight, code
            if key not in self.native_stem_samples:
                recording = interpolate_recordings(self.native_stem_recordings[italic, 400, code],
                                                   self.native_stem_recordings[italic, 700, code], factor)
                self.native_stem_samples[key] = filled_shape_paths(polygons_from_recording(recording))
            profile = filled_scanline_intervals(self.native_stem_samples[key], height)
            self.assertEqual(len(profile), 1, (italic, weight, code, "native free shaft band"))
            dx = light_dx + factor * (bold_dx - light_dx)
            result.append((height, *(x + dx for x in profile[0])))
        return result

    def hook_closure_references(self, donor, italic, endpoint, name, metadata):
        """Derive the closing quarters from pinned b/d and the old hook body.

        The affine constraint preserves the donor's vertical profile, the
        receiving native shaft's slope, and the independently retained hook
        anchor. No construction helper supplies the reference outline.
        """
        recipe = ALLOCATION_BY_NAME[name]["recipeCodePoint"]
        first, _, _ = MIDDLE_RECIPES[recipe]
        turned = (recipe - first) % 4 >= 2
        glyphs, cmap = donor.getGlyphSet(), donor.getBestCmap()
        context = italic, endpoint, name
        joins = metadata["middleHookJoins"]
        self.assertEqual(len(joins), 1, context)
        join = joins[0]
        old = self.baseline[italic, endpoint][f"u{recipe:X}"].lib["org.quintessential.construction"]
        offset = old["leftUpperOffsetX"] if turned else old.get("outerRibbonOffsetX", 0)
        self.assertEqual(join["hookOffsetX"], offset, (context, "hook body must not move"))
        self.assertEqual(join["direction"], "upper" if turned else "lower")
        self.assertEqual(join["donorCodePoint"], 0x64 if turned else 0x62)
        self.assertEqual(join["hookDonorCodePoint"], 0x266 if turned else 0x271)
        self.assertEqual(join["removedTerminalDonorCodePoint"], 0x6C if turned else 0x70)
        legs = metadata["extendedMiddleLegs"]
        leg = (min if turned else max)(legs, key=lambda item: item["centerX"])
        self.assertEqual(join["middleStemCenterX"], leg["centerX"])

        def edges(code, contour=0):
            return native_contour_edges(glyphs, cmap[code], contour)

        def moved(edge, dx):
            start, operation, points = edge
            return ((start[0] + dx, start[1]), operation, tuple((x + dx, y) for x, y in points))

        def slope(edge):
            start, operation, points = edge
            self.assertEqual(operation, "lineTo")
            return (points[-1][0] - start[0]) / (points[-1][1] - start[1])

        def fit(edge, shaft, receiver, anchor, anchor_first):
            start, operation, points = edge
            source_anchor, corner = (start, points[-1]) if anchor_first else (points[-1], start)
            dy = anchor[1] - source_anchor[1]
            source_slope, target_slope = slope(shaft), slope(receiver)
            corner_x = receiver[0][0] + target_slope * (corner[1] + dy - receiver[0][1])
            scale = ((anchor[0] - corner_x - target_slope * (source_anchor[1] - corner[1]))
                     / (source_anchor[0] - corner[0] - source_slope * (source_anchor[1] - corner[1])))
            self.assertGreater(scale, 0, (context, "closing quarter is reversed"))
            shear = target_slope - scale * source_slope
            dx = corner_x - scale * corner[0] - shear * corner[1]
            transform = lambda point: (scale * point[0] + shear * point[1] + dx, point[1] + dy)
            return transform(start), operation, tuple(transform(point) for point in points)

        hook = [moved(edge, offset) for edge in edges(0x266 if turned else 0x271,
                                                     0 if turned or italic else 1)]
        anchors = ((hook[2 if italic else 4][2][-1], hook[6 if italic else 8][0]) if turned
                   else (hook[0][0], hook[2][2][-1]))
        for key, anchor in zip(("outerAnchor", "innerAnchor"), anchors):
            self.assertLessEqual(max(abs(a - b) for a, b in zip(join[key], anchor)), 1e-5, context)
        free_edges = edges(0x6C if turned else 0x70, 0 if turned or not italic else 1)
        cut = 550 if turned else -50
        receivers = [moved(edge, leg["terminalOffsetX"]) for edge in free_edges
                     if edge[1] == "lineTo" and min(edge[0][1], edge[2][-1][1]) < cut < max(edge[0][1], edge[2][-1][1])]
        self.assertEqual(len(receivers), 2, (context, "native receiving shaft edges"))
        matched = []
        for key in ("outerJoin", "innerJoin"):
            point = join[key]
            errors = [(abs(point[0] - edge[0][0] - slope(edge) * (point[1] - edge[0][1])), index)
                      for index, edge in enumerate(receivers)]
            error, index = min(errors)
            self.assertLessEqual(error, 1e-5, (context, key, "closure left its native receiving shaft"))
            matched.append(receivers[index])
        self.assertNotEqual(matched[0], matched[1])
        outer, inner = edges(0x64 if turned else 0x62), edges(0x64 if turned else 0x62, 1)
        fitted = ([fit(outer[2], outer[4], matched[0], anchors[0], True),
                   fit(inner[2], outer[4], matched[1], anchors[1], False)] if turned else
                  [fit(outer[0 if italic else 6], outer[1 if italic else 7], matched[0], anchors[0], True),
                   fit(inner[4 if italic else 1], inner[3 if italic else 0], matched[1], anchors[1], False)])
        removed = hook[3 if italic else 5:6 if italic else 8] if turned else hook[:3]

        def segments(sequence):
            pen = QuadraticSegmentPen()
            for start, operation, points in sequence:
                replayRecording([("moveTo", (start,)), (operation, points), ("endPath", ())], pen)
            return pen.segments

        return segments(fitted), segments(removed), leg["centerX"]

    def assert_removed_curves_absent(self, actual, removed, tolerance, context):
        self.assertTrue(removed, (context, "missing old ball reference"))
        for segment in removed:
            error = min(max(abs(a - b) for p, q in zip(candidate, segment) for a, b in zip(p, q))
                        for candidate in actual)
            self.assertGreater(error, tolerance, (context, "facing hook ball survives inside the new closure"))

    def assert_middle_geometry(self, recording, parent, counter_reference, recipe, context, tolerance, foot_joins=0):
        paths = polygons_from_recording(recording)
        clipper = pyclipper.Pyclipper()
        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
        self.assertEqual(len(tree.Childs), 1, (context, "disconnected middle leg"))
        counters = filled_counter_paths(paths)
        hook_enclosure = int(MIDDLE_RECIPES[recipe][0] in (0xF2A75, 0xF2C30))
        native_count = len(filled_counter_paths(polygons_from_recording(counter_reference)))
        self.assertEqual(len(counters), native_count + foot_joins + hook_enclosure,
                         (context, "unintended filled enclosure"))
        for counter in counters:
            self.assertGreater(abs(pyclipper.Area(counter)) / 4096, 1000, (context, "collapsed native counter"))
        self.assert_counters(recording, counter_reference, tolerance, context)
        filled = filled_shape_paths(paths)
        for height, left, right in self.native_shaft_bands(*context[:3]):
            intervals = filled_scanline_intervals(filled, height)
            self.assertTrue(any(a <= left + tolerance + 1 / 32 and b >= right - tolerance - 1 / 32
                                for a, b in intervals),
                            (context, height, (left, right), intervals, "native extended shaft band is missing"))

    def test_every_eligible_parent_has_the_required_free_internal_legs(self):
        self.assertEqual(len(MIDDLE_RECIPES), 348)
        self.assertEqual({entry["recipeCodePoint"] for entry in self.entries[False]}, set(MIDDLE_RECIPES))
        expected_italic = {code for code in MIDDLE_RECIPES if code in MAIN_SCRIPT_CMAP
                           or 0xF2B4C <= code < 0xF2B58}
        self.assertEqual({entry["recipeCodePoint"] for entry in self.entries[True]}, expected_italic)
        self.assertEqual(len(expected_italic), 72)
        for (italic, weight), source in self.sources.items():
            with instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                native_p = outline(donor.getGlyphSet(), donor.getBestCmap()[0x70])
                floor, top = native_p[1][1][-1][1], native_p[2][1][-1][1]
            for entry in self.entries[italic]:
                recipe, name = entry["recipeCodePoint"], entry["glyphName"]
                metadata = source[name].lib["org.quintessential.construction"]
                self.assertEqual(source[name].unicodes, [entry["codePoint"]])
                self.assertEqual(metadata["recipeCodePoint"], recipe)
                self.assertEqual(metadata["middleLegs"], "extended")
                legs = sorted(metadata["extendedMiddleLegs"], key=lambda leg: leg["centerX"])
                directions = middle_directions(recipe)
                self.assertEqual(metadata["middleLegCount"], len(directions))
                self.assertEqual(tuple(leg["direction"] for leg in legs), directions)
                self.assertEqual(len({leg["centerX"] for leg in legs}), len(legs))
                for leg in legs:
                    self.assertIn(leg["donorCodePoint"], (0x64, 0x6C) if leg["direction"] == "ascender" else (0x70,))
                joins = metadata["middleFootJoins"]
                if italic:
                    self.assertEqual(joins, [])
                contours, contour = [], []
                for operation in outline(source, name):
                    contour.append(operation)
                    if operation[0] == "closePath":
                        contours.append(contour)
                        contour = []
                hook_expected = MIDDLE_RECIPES[recipe][0] in (0xF2A75, 0xF2C30)
                self.assertEqual(len(metadata["middleHookJoins"]), int(hook_expected))
                splits = metadata["middleFootContourSplits"]
                self.assertEqual(len(splits), int(not italic and recipe in (0xF2A4E, 0xF2C31, 0xF2C35, 0xF2C39)))
                for split in splits:
                    self.assertEqual((split["donorCodePoint"], split["bodyCutY"], split["footTopY"]), (0x70, -50, 20))
                    leg = next(leg for leg in legs if leg["centerX"] == split["middleStemCenterX"])
                    self.assertEqual(leg["direction"], "descender")
                    native250 = filled_scanline_intervals(self.native_stems[italic, weight, 0x70], 250)[0]
                    dx = leg.get("terminalOffsetX", leg["centerX"] - sum(native250) / 2)
                    for height in (-25.37, 10.37):
                        left, right = filled_scanline_intervals(self.native_stems[italic, weight, 0x70], height)[0]
                        overlap = sum(any(a <= left + dx + 1 / 32 and b >= right + dx - 1 / 32
                                          for a, b in filled_scanline_intervals(
                                              filled_shape_paths(polygons_from_recording(contour)), height))
                                      for contour in contours)
                        self.assertGreaterEqual(overlap, 2, (italic, weight, name, "native body/foot overlap is missing"))
                rectangles = []
                for join in joins:
                    self.assertEqual((join["floor"], join["top"]), (floor, top))
                    self.assertEqual(floor, -220)
                    left, right = join["leftCenterX"], join["rightCenterX"]
                    self.assertLess(left, right)
                    rectangle = [("moveTo", ((round(right, 6), floor),)),
                                 ("lineTo", ((round(left, 6), floor),)),
                                 ("lineTo", ((round(left, 6), top),)),
                                 ("lineTo", ((round(right, 6), top),)), ("closePath", ())]
                    self.assertIn(rectangle, contours, (italic, weight, name, "missing native-foot bridge"))
                    rectangles.append(rectangle)
                bars = []
                for contour in contours:
                    if contour in rectangles:
                        continue
                    for previous, (operation, points) in zip(contour, contour[1:]):
                        if operation == "lineTo" and previous[1] and previous[1][-1][1] == points[-1][1] == floor:
                            left, right = sorted((previous[1][-1][0], points[-1][0]))
                            if right - left > 100:
                                bars.append((left, right))
                bars.sort()
                for join in joins:
                    indices = [next((index for index, bar in enumerate(bars)
                                     if abs(sum(bar) / 2 - join[key]) < 1e-5), None)
                               for key in ("leftCenterX", "rightCenterX")]
                    self.assertNotIn(None, indices, (italic, weight, name, "bridge must end inside native foot bars"))
                    first, second = (bars[index] for index in indices)
                    self.assertEqual(indices[1] - indices[0], 1, (italic, weight, name, "bridge skipped a native foot"))
                    self.assertLessEqual(second[0] - first[1], 80)
                    self.assertTrue(any(leg["direction"] == "descender" and
                                        (first[0] < leg["centerX"] < first[1] or second[0] < leg["centerX"] < second[1])
                                        for leg in legs), (italic, weight, name, "bridge needs an extended middle foot"))
                other = self.sources[italic, 1100 - weight][name].lib["org.quintessential.construction"]
                self.assertEqual(len(joins), len(other["middleFootJoins"]), (italic, name, "bridge topology changed"))
                self.assertEqual(source[name].width, self.baseline[italic, weight][f"u{recipe:X}"].width,
                                 (italic, weight, name, "parent advance changed"))
                _, _, kind = MIDDLE_RECIPES[recipe]
                if kind in ("left", "right", "both"):
                    reference = middle_counter_reference(recipe)
                    self.assertEqual(metadata["middleTerminalSourceCodePoint"], reference)
                    self.assertEqual(metadata["sigmoidAdvanceWidth"], self.baseline[italic, weight][f"u{reference:X}"].width)

    def test_source_interpolations_keep_native_counters_and_extend_every_free_end(self):
        for italic in (False, True):
            for entry in self.entries[italic]:
                recipe, name = entry["recipeCodePoint"], entry["glyphName"]
                counter_name = f"u{middle_counter_reference(recipe):X}"
                # Shared-spine companions must contain the newly reviewed
                # base's counters. All other families retain their independent
                # historical counter reference, and all native shaft/arch tests
                # below continue to use the historical baseline.
                counter_sources = self.sources if name in SHARED_SPINE_NAMES else self.baseline
                recordings = [tuple(outline(collection[italic, endpoint], key) for endpoint in (400, 700))
                              for collection, key in ((self.sources, name), (self.baseline, f"u{recipe:X}"),
                                                      (counter_sources, counter_name))]
                for weight in SAMPLE_WEIGHTS:
                    values = [interpolate_recordings(*endpoints, interpolation_factor(weight)) for endpoints in recordings]
                    joins = self.sources[italic, 400][name].lib["org.quintessential.construction"]["middleFootJoins"]
                    self.assert_middle_geometry(*values, recipe, (italic, weight, name, "source"), 1e-5, len(joins))

    def test_compiled_five_weights_keep_native_counters_and_extend_every_free_end(self):
        if not COMPILED:
            self.skipTest("--sources-only requested")
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font, \
                        instantiated(BASELINE / "resources/fonts/QuintessentialSerif" / filename, weight) as baseline:
                    current, original = font.getGlyphSet(), baseline.getGlyphSet()
                    for entry in self.entries[italic]:
                        recipe, name = entry["recipeCodePoint"], entry["glyphName"]
                        reference = middle_counter_reference(recipe)
                        counter_set = current if name in SHARED_SPINE_NAMES else original
                        joins = self.sources[italic, 400][name].lib["org.quintessential.construction"]["middleFootJoins"]
                        self.assert_middle_geometry(outline(current, name), outline(original, f"u{recipe:X}"),
                            outline(counter_set, f"u{reference:X}"), recipe, (italic, weight, name, "compiled"), .75, len(joins))
                        self.assertEqual(font["hmtx"][name][0], baseline["hmtx"][f"u{recipe:X}"][0])

    def test_added_terminals_and_retained_arch_regions_use_rigid_native_curves(self):
        selected, references, removed_references = {}, {}, {}
        for (italic, endpoint), source in self.sources.items():
            with instantiated(DONORS / DONOR_FILES[italic], endpoint) as donor:
                donor_set, cmap = donor.getGlyphSet(), donor.getBestCmap()
                native = {code: quadratic_segments(donor_set, cmap[code]) for code in (0x64, 0x6C, 0x70)}
                for entry in self.entries[italic]:
                    recipe, name = entry["recipeCodePoint"], entry["glyphName"]
                    context = italic, endpoint, name
                    actual = quadratic_segments(source, name)
                    metadata = source[name].lib["org.quintessential.construction"]
                    expected = []
                    first, _, kind = MIDDLE_RECIPES[recipe]
                    hooked = first in (0xF2A75, 0xF2C30)
                    joined_center = None
                    if hooked:
                        closure, removed, joined_center = self.hook_closure_references(donor, italic, endpoint, name, metadata)
                        expected.extend(closure)
                        self.assert_removed_curves_absent(actual, removed, 1e-5, context)
                        removed_references[italic, endpoint, name] = removed
                    for leg in metadata["extendedMiddleLegs"]:
                        if leg["centerX"] == joined_center:
                            # This free tip is replaced by the b/d closure,
                            # whose two quarters are constrained above.
                            continue
                        above = leg["direction"] == "ascender"
                        shared = False
                        if kind in ("left", "right", "both"):
                            pair = (("stemRightInnerX", "stemRightX") if above else
                                    ("stemLeftX", "stemLeftInnerX"))
                            center = sum(metadata[key] for key in pair) / 2 + metadata["sigmoidOffsetX"]
                            shared = abs(leg["centerX"] - center) < 1e-5
                        if shared:
                            # The captured prepared sigmoid already contains
                            # the accepted compact p/d terminal return.
                            curves = quadratic_segments(self.baseline[italic, endpoint],
                                                        f"u{middle_counter_reference(recipe):X}")
                            divider = sum(metadata[key] for key in
                                          ("stemLeftX", "stemLeftInnerX", "stemRightInnerX", "stemRightX")) / 4
                            curves = [segment for segment in curves
                                      if (min(y for _, y in segment) > 550 if above else
                                          max(y for _, y in segment) < -30)
                                      and (min(x for x, _ in segment) > divider if above else
                                           max(x for x, _ in segment) < divider)]
                            self.assertTrue(curves, (context, "captured compact terminal reference"))
                            translated = translated_quadratics(curves, metadata["sigmoidOffsetX"])
                            if name in SHARED_SPINE_NAMES:
                                from reviewed_spine_connections import is_reviewed_connection_segment
                                translated = [segment for segment in translated
                                              if not is_reviewed_connection_segment(segment, entry, metadata)]
                            expected.extend(translated)
                            continue
                        curves = [segment for segment in native[leg["donorCodePoint"]]
                                  if (min(y for _, y in segment) > 550 if above else max(y for _, y in segment) < -30)]
                        self.assertTrue(curves, (context, "independent native terminal selection"))
                        candidates = []
                        for segment in actual:
                            dx = segment[0][0] - curves[0][0][0]
                            translated = translated_quadratics(curves, dx)
                            if all(any(max(abs(a - b) for p, q in zip(part, desired) for a, b in zip(p, q)) <= 1e-5
                                       for part in actual) for desired in translated):
                                center = sum(x for curve in translated for x, _ in curve) / (3 * len(translated))
                                candidates.append((abs(center - leg["centerX"]), dx, translated))
                        self.assertTrue(candidates, (context, leg, "new free terminal is not a rigid native region"))
                        distance, _, translated = min(candidates, key=lambda item: item[0])
                        self.assertLess(distance, 250, (context, "terminal detached from its internal shaft"))
                        expected.extend(translated)
                    # The half of each native arch opposite its newly extended
                    # free cap is independently retained from the old parent.
                    directions = set(middle_directions(recipe))
                    old_curves = quadratic_segments(self.baseline[italic, endpoint], f"u{recipe:X}")
                    if name in SHARED_SPINE_NAMES:
                        # The old height-only selection also included parts of
                        # the edited body counters. Exclude those contours and
                        # the explicitly reviewed local connection curves;
                        # retain the historical arch and terminal requirements.
                        old_counters = counter_recordings(outline(self.baseline[italic, endpoint], f"u{recipe:X}"))
                        self.assertEqual(len(old_counters), 2, (context, "shared-spine body counters"))
                        revised_curves = [segment for contour in old_counters
                                          for segment in recording_quadratics(contour)]
                        old_curves = [segment for segment in old_curves if segment not in revised_curves]
                        from reviewed_spine_connections import is_reviewed_connection_segment
                        old_curves = [segment for segment in old_curves
                                      if not is_reviewed_connection_segment(segment, entry, metadata)]
                    if len(directions) == 1:
                        above = "descender" in directions
                        retained = [segment for segment in old_curves
                                    if (min(y for _, y in segment) > 300 if above else max(y for _, y in segment) < 200)]
                        self.assertTrue(retained, (context, "independent preserved arch selection"))
                        expected.extend(retained)
                    else:
                        left, right = sorted(leg["centerX"] for leg in metadata["extendedMiddleLegs"])
                        upper = [segment for segment in old_curves
                                 if max(x for x, _ in segment) < left - 80 and min(y for _, y in segment) > 300]
                        lower = [segment for segment in old_curves
                                 if min(x for x, _ in segment) > right + 80 and max(y for _, y in segment) < 200]
                        self.assertTrue(upper, (context, "independent left arch roof selection"))
                        self.assertTrue(lower, (context, "independent right turned-arch roof selection"))
                        expected.extend((*upper, *lower))
                    assert_contains_quadratics(self, actual, expected, 1e-5, (context, "native source regions"))
                    references[italic, endpoint, name] = actual
                    indices = set()
                    for wanted in expected:
                        indices.update(index for index, segment in enumerate(actual)
                                       if max(abs(a - b) for p, q in zip(segment, wanted) for a, b in zip(p, q)) <= 1e-5)
                    selected[italic, endpoint, name] = indices
        # Union indices in the complete compatible topology before selecting,
        # so endpoint geometry thresholds cannot pair unrelated curve indices.
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                font = instantiated(OUTPUT / VARIABLE_FILES[italic], weight) if COMPILED else None
                try:
                    glyphs = font.getGlyphSet() if font else None
                    factor = interpolation_factor(weight)
                    for entry in self.entries[italic]:
                        name = entry["glyphName"]
                        light, bold = (references[italic, endpoint, name] for endpoint in (400, 700))
                        self.assertEqual(len(light), len(bold))
                        indices = selected[italic, 400, name] | selected[italic, 700, name]
                        expected = [interpolate_points(light[index], bold[index], factor) for index in sorted(indices)]
                        source = interpolate_recordings(outline(self.sources[italic, 400], name),
                                                        outline(self.sources[italic, 700], name), factor)
                        assert_contains_quadratics(self, recording_quadratics(source), expected, 1e-5,
                                                   (italic, weight, name, "source native regions"))
                        if glyphs:
                            assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected, .75,
                                                       (italic, weight, name, "compiled native regions"))
                        if (italic, 400, name) in removed_references:
                            old_light, old_bold = (removed_references[italic, endpoint, name] for endpoint in (400, 700))
                            self.assertEqual(len(old_light), len(old_bold))
                            removed = [interpolate_points(a, b, factor) for a, b in zip(old_light, old_bold)]
                            self.assert_removed_curves_absent(recording_quadratics(source), removed, 1e-5,
                                                             (italic, weight, name, "source"))
                            if glyphs:
                                self.assert_removed_curves_absent(quadratic_segments(glyphs, name), removed, .75,
                                                                 (italic, weight, name, "compiled"))
                finally:
                    if font:
                        font.close()


class IndependentMain0150Tests(unittest.TestCase):
    """Retain the separately captured 129-glyph main baseline by stable name."""

    def assert_pairs(self, before, after):
        for left in MAIN_NAMES:
            for right in MAIN_NAMES:
                self.assertEqual(before.get((left, right), ZERO_PAIR), after.get((left, right), ZERO_PAIR),
                                 (left, right))

    def test_main_129_source_outlines_advances_and_16641_pairs(self):
        self.assertEqual(len(MAIN_SCRIPT_CMAP) ** 2, 16641)
        for style in STATIC_FACES:
            filename = f"QuintessentialSerif-{style}.ufo"
            before, after = Font.open(BASELINE_0150 / "sources" / filename), Font.open(SOURCES / filename)
            try:
                self.assertEqual(tuple(before.glyphOrder), MAIN_NAMES)
                self.assertEqual(set(before.kerning), {(left, right) for left in MAIN_SCRIPT_CMAP.values()
                                                      for right in MAIN_SCRIPT_CMAP.values()})
                for name in MAIN_NAMES:
                    self.assertEqual(outline(after, name), outline(before, name), (style, name))
                    self.assertEqual(after[name].width, before[name].width)
                    expected = [ALLOCATION_BY_NAME[name]["codePoint"]] if name in ALLOCATION_BY_NAME else before[name].unicodes
                    self.assertEqual(after[name].unicodes, expected)
                for pair, value in before.kerning.items():
                    self.assertEqual(after.kerning.get(pair, 0), value, (style, pair))
            finally:
                before.close()
                after.close()

    def assert_compiled_main(self, before, after):
        self.assertEqual(before.getBestCmap(), {0x20: "space", **MAIN_SCRIPT_CMAP})
        current_cmap = after.getBestCmap()
        self.assertEqual({ALLOCATION_BY_NAME[name]["codePoint"]: current_cmap.get(ALLOCATION_BY_NAME[name]["codePoint"])
                          for name in MAIN_SCRIPT_CMAP.values()},
                         {ALLOCATION_BY_NAME[name]["codePoint"]: name for name in MAIN_SCRIPT_CMAP.values()})
        original, current = before.getGlyphSet(), after.getGlyphSet()
        for name in MAIN_NAMES:
            self.assertEqual(outline(current, name), outline(original, name), name)
            self.assertEqual(after["hmtx"][name], before["hmtx"][name], name)
        self.assert_pairs(effective_pairs(before), effective_pairs(after))

    def test_main_129_static_outlines_metrics_and_all_pairs(self):
        if not COMPILED:
            self.skipTest("--sources-only requested")
        for style in STATIC_FACES:
            filename = f"QuintessentialSerif-{style}.otf"
            with self.subTest(style=style), TTFont(BASELINE_0150 / "outputs" / filename) as before, TTFont(OUTPUT / filename) as after:
                self.assert_compiled_main(before, after)

    def test_main_129_variable_outlines_metrics_and_all_pairs_at_five_weights(self):
        if not COMPILED:
            self.skipTest("--sources-only requested")
        for filename in VARIABLE_FILES.values():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(filename=filename, weight=weight), \
                        instantiated(BASELINE_0150 / "outputs" / filename, weight) as before, \
                        instantiated(OUTPUT / filename, weight) as after:
                    self.assert_compiled_main(before, after)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--baseline-0150", type=Path, default=BASELINE_0150)
    parser.add_argument("--sources", type=Path, default=SOURCES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--sources-only", action="store_true")
    arguments, remaining = parser.parse_known_args()
    BASELINE = arguments.baseline.resolve()
    BASELINE_0150 = arguments.baseline_0150.resolve()
    SOURCES, OUTPUT = arguments.sources.resolve(), arguments.output.resolve()
    COMPILED = not arguments.sources_only
    unittest.main(argv=[__file__, *remaining])

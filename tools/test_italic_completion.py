#!/usr/bin/env python3
"""Independent completion and exact pre-increment outline/pair preservation checks.

The immutable capture records the actual 0.220 sources and compiled outlines,
independently of production recipes. New Italic forms must fill the existing
Roman allocation; every previous advance and effective pair survives. The three
subsequently approved stemless terminal outlines have their own focused suite.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import unittest

import pyclipper

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from font_geometry_helpers import effective_pairs, ZERO_PAIR, outline, polygons_from_recording, counter_recordings
from verify_logical_allocation import historical_entry, current_unicode_map
from test_stemless_terminals import assert_preserved_outlines

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
BASELINE = ROOT / "resources/provenance/italic-completion-baseline.json.gz"
WEIGHTS = (400, 500, 550, 600, 700)


def expected_counter_count(entry):
    """Read enclosure obligations from neutral structural parts, not recipes."""
    parts = entry["parts"]
    total = sum({"bowl": int(part.get("returnContact", True)), "double bowl": 2}.get(part["kind"], 0)
                for part in parts)
    for index, part in enumerate(parts):
        if part["kind"] != "spine":
            continue
        if index == 0 or index == len(parts) - 1:
            total += 1
            continue
        total += 2
        left, right = parts[index - 1], parts[index + 1]
        # Facing hooks or paired descenders close locally across the spine.
        total += int(left["kind"] == "stem" and left.get("upper") == "curved"
                     and right.get("upper") == "straight")
        total += int(left.get("lower") == "straight" and right["kind"] == "stem"
                     and right.get("lower") in ("straight", "curved"))
    return total


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def outlines(glyph_set, names):
    result = {}
    for name in names:
        pen = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(pen)
        # Keep exact numeric equality, without treating 1 and 1.0 differently.
        recording = [(op, [[float(v) for v in point] for point in points]) for op, points in pen.value]
        result[name] = [float(glyph_set[name].width), digest(recording)]
    return result


def pair_digest(pairs, names):
    names = set(names)
    return digest(sorted([left, right, *value] for (left, right), value in pairs.items()
                         if left in names and right in names and tuple(value) != ZERO_PAIR))


def source_pair_digest(source, names):
    # This project's editable kerning has explicit glyph pairs, no classes.
    assert not source.groups
    return pair_digest({pair: (0, 0, value, 0, 0, 0, 0, 0)
                        for pair, value in source.kerning.items()}, names)


def previous_order(entries, posture):
    entries = [entry for entry in entries if posture in entry["postures"]]
    original = sorted((entry for entry in entries if entry["oldCodePoint"] is not None),
                      key=lambda entry: entry["oldCodePoint"])
    added = sorted((entry for entry in entries if entry["oldCodePoint"] is None),
                   key=lambda entry: entry["codePoint"])
    return [".notdef", "space", *[entry["glyphName"] for entry in (*original, *added)]]


def snapshot():
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text())
    result = {"version": "0.220", "weights": WEIGHTS, "entries": allocation["entries"], "sources": {}, "compiled": {}}
    for style in ("Regular", "Bold", "Italic", "BoldItalic"):
        with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source:
            names = source.lib["public.glyphOrder"]
            result["sources"][style] = {"outlines": outlines(source, names), "pairs": source_pair_digest(source, names),
                                        "cmap": {name: source[name].unicodes for name in names}}
        with TTFont(OUTPUT / f"QuintessentialSerif-{style}.otf") as font:
            result["compiled"][style] = {"outlines": outlines(font.getGlyphSet(), names),
                                          "pairs": pair_digest(effective_pairs(font), names)}
    for italic in (False, True):
        filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
        for weight in WEIGHTS:
            with TTFont(OUTPUT / filename) as variable:
                font = instantiateVariableFont(variable, {"wght": weight}, inplace=True)
                names = font.getGlyphOrder()
                result["compiled"][f"{'Italic' if italic else 'Roman'}-{weight}"] = {
                    "outlines": outlines(font.getGlyphSet(), names), "pairs": pair_digest(effective_pairs(font), names)}
    return result


class ItalicCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = BASELINE.read_bytes()
        if hashlib.sha256(data).hexdigest() != "52289d17a64771b131661d5d64646fcd90377c3975592843f39549818a8d5940":
            raise AssertionError("The immutable pre-increment outline and pair capture changed")
        cls.baseline = json.loads(gzip.decompress(data))
        cls.all_entries = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text())["entries"]
        cls.entries = [entry for entry in cls.all_entries if "middleLegExtensions" not in entry]

    def test_full_coverage_changes_only_posture_availability(self):
        self.assertEqual(len(self.entries), 832)
        self.assertEqual(len(self.baseline["entries"]), 832)
        self.assertEqual(sum("Italic" in item["postures"] for item in self.baseline["entries"]), 232)
        self.assertEqual(sum("Italic" not in item["postures"] for item in self.baseline["entries"]), 600)
        by_id = {entry["glyphId"]: entry for entry in self.entries}
        for old in self.baseline["entries"]:
            current = historical_entry(by_id[old["glyphId"]])
            self.assertEqual(current["postures"], ["Roman", "Italic"])
            self.assertEqual({key: value for key, value in old.items() if key != "postures"},
                             {key: value for key, value in current.items() if key != "postures"})
        expected = {0x20: "space", **{entry["codePoint"]: entry["glyphName"] for entry in self.all_entries}}
        for path in OUTPUT.glob("QuintessentialSerif-*.*"):
            if path.suffix not in (".ttf", ".otf", ".woff2"):
                continue
            with TTFont(path) as font, self.subTest(file=path.name):
                self.assertEqual(font.getBestCmap(), expected)
                self.assertEqual(len(font.getGlyphOrder()), len(expected) + 1)

    def test_all_prior_editable_outlines_advances_and_pairs_are_exact(self):
        for style, captured in self.baseline["sources"].items():
            with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source:
                names = tuple(captured["outlines"])
                order = previous_order(self.baseline["entries"], "Italic" if "Italic" in style else "Roman")
                self.assertEqual(source.lib["public.glyphOrder"][:len(order)], order, style)
                assert_preserved_outlines(self, outlines(source, names), captured["outlines"], style)
                self.assertEqual(source_pair_digest(source, names), captured["pairs"], style)
                self.assertEqual({name: source[name].unicodes for name in names}, current_unicode_map(captured["cmap"]), style)

    def test_all_prior_static_and_variable_outlines_advances_and_pairs_are_exact(self):
        for face, captured in self.baseline["compiled"].items():
            names = tuple(captured["outlines"])
            if "-" in face:
                posture, weight = face.split("-")
                filename = "QuintessentialSerif-Italic-Variable.ttf" if posture == "Italic" else "QuintessentialSerif-Variable.ttf"
            else:
                filename, weight = f"QuintessentialSerif-{face}.otf", None
            with TTFont(OUTPUT / filename) as font, self.subTest(face=face):
                if weight is not None:
                    font = instantiateVariableFont(font, {"wght": int(weight)}, inplace=True)
                order = previous_order(self.baseline["entries"], "Italic" if "Italic" in face else "Roman")
                self.assertEqual(font.getGlyphOrder()[:len(order)], order, face)
                assert_preserved_outlines(self, outlines(font.getGlyphSet(), names), captured["outlines"], face)
                self.assertEqual(pair_digest(effective_pairs(font), names), captured["pairs"], face)

    def test_new_italic_endpoints_are_compatible_and_differ_from_roman(self):
        new = [entry for entry in self.baseline["entries"] if "Italic" not in entry["postures"]]
        fonts = {style: Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
                 for style in ("Regular", "Bold", "Italic", "BoldItalic")}
        try:
            for entry in new:
                name = entry["glyphName"]
                first, second = (fonts[style][name] for style in ("Italic", "BoldItalic"))
                self.assertGreater(first.width, 0, name)
                self.assertEqual([[(point.type) for point in contour.points] for contour in first.contours],
                                 [[(point.type) for point in contour.points] for contour in second.contours], name)
                self.assertNotEqual(outlines(fonts["Regular"], [name]), outlines(fonts["Italic"], [name]), name)
                for glyph in (first, second):
                    bounds = BoundsPen(None)
                    glyph.draw(bounds)
                    self.assertIsNotNone(bounds.bounds, name)
                    self.assertGreater(bounds.bounds[2] - bounds.bounds[0], 20, name)
                    self.assertGreater(bounds.bounds[3] - bounds.bounds[1], 100, name)
        finally:
            for source in fonts.values():
                source.close()

    def test_new_italic_shapes_have_connected_ink_and_open_counters_at_five_weights(self):
        entries = [entry for entry in self.baseline["entries"] if "Italic" not in entry["postures"]]
        for weight in WEIGHTS:
            with TTFont(OUTPUT / "QuintessentialSerif-Italic-Variable.ttf") as font:
                font = instantiateVariableFont(font, {"wght": weight}, inplace=True)
                glyphs = font.getGlyphSet()
                for entry in entries:
                    name = entry["glyphName"]
                    with self.subTest(weight=weight, glyph=name):
                        paths = polygons_from_recording(outline(glyphs, name))
                        clipper = pyclipper.Pyclipper()
                        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
                        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                        self.assertEqual(len(tree.Childs), 1, "Detached ink component")
                        self.assertEqual(len(tree.Childs[0].Childs), expected_counter_count(entry),
                                         "A required counter opened or an unintended enclosure formed")
                        for counter in tree.Childs[0].Childs:
                            self.assertTrue(counter.IsHole)
                            self.assertGreater(abs(pyclipper.Area(counter.Contour)) / 4096, 1000,
                                               "Collapsed or unintended small enclosure")

    def test_new_italics_retain_rigid_native_italic_curves(self):
        from test_quintessential_font import quadratic_segments

        # Translation-normalized curved segments distinguish native component
        # reuse from slanting a Roman outline. Donor choice is independent of
        # the production metadata and recipe dispatch.
        donor_codes = (0x62, 0x64, 0x70, 0x71, 0x6C, 0x6D, 0x6E, 0x75,
                       0x26F, 0x271, 0x73, 0x72, 0x279, 0x131,
                       0x251, 0x250, 0x253, 0x25B, 0x25C, 0x266, 0x261)
        def signature(segment):
            origin = segment[0]
            return tuple((round(x - origin[0], 4), round(y - origin[1], 4)) for x, y in segment)
        def meaningful(segment):
            xs, ys = zip(*segment)
            return max(xs) - min(xs) > 10 and max(ys) - min(ys) > 10
        new = [entry["glyphName"] for entry in self.baseline["entries"] if "Italic" not in entry["postures"]]
        for style, weight in (("Italic", 400), ("BoldItalic", 700)):
            with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source, \
                    TTFont(ROOT / "resources/fonts/STIXTwoText/STIXTwoText-Italic-VariableFont_wght.ttf") as donor:
                donor = instantiateVariableFont(donor, {"wght": weight}, inplace=True)
                native = {signature(segment) for code in donor_codes
                          for segment in quadratic_segments(donor.getGlyphSet(), donor.getBestCmap()[code])
                          if meaningful(segment)}
                for name in new:
                    actual = {signature(segment) for segment in quadratic_segments(source, name) if meaningful(segment)}
                    self.assertGreaterEqual(len(native & actual), 2, (style, name, "Native Italic curves were transformed"))

    def test_new_middle_companions_keep_parent_advances_and_extend_every_internal_end(self):
        from test_additions_font import middle_directions, middle_counter_reference
        from test_quintessential_font import filled_scanline_intervals, filled_shape_paths

        added = [entry for entry in self.baseline["entries"]
                 if "Italic" not in entry["postures"] and entry["middleLegs"]]
        self.assertEqual(len(added), 276)
        for style, weight in (("Italic", 400), ("BoldItalic", 700)):
            with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source, \
                    TTFont(ROOT / "resources/fonts/STIXTwoText/STIXTwoText-Italic-VariableFont_wght.ttf") as donor:
                donor = instantiateVariableFont(donor, {"wght": weight}, inplace=True)
                native_bands = {}
                for code, height in ((0x70, -100), (0x64, 600), (0x6C, 600)):
                    shape = filled_shape_paths(polygons_from_recording(outline(donor.getGlyphSet(), donor.getBestCmap()[code])))
                    bands = filled_scanline_intervals(shape, height)
                    self.assertEqual(len(bands), 1, (style, code, "Expected one native free-end shaft"))
                    native_bands[code] = height, bands[0]
                for entry in added:
                    name, recipe = entry["glyphName"], entry["recipeCodePoint"]
                    with self.subTest(style=style, glyph=name):
                        metadata = source[name].lib["org.quintessential.construction"]
                        self.assertEqual(source[name].width, source[f"u{recipe:X}"].width)
                        legs = sorted(metadata["extendedMiddleLegs"], key=lambda item: item["centerX"])
                        directions = middle_directions(recipe)
                        self.assertEqual(tuple(leg["direction"] for leg in legs), directions)
                        self.assertEqual(metadata["middleLegCount"], len(directions))
                        self.assertEqual(len({leg["centerX"] for leg in legs}), len(legs))
                        shape = filled_shape_paths(polygons_from_recording(outline(source, name)))
                        for leg in legs:
                            self.assertIn(leg["donorCodePoint"],
                                          (0x64, 0x6C) if leg["direction"] == "ascender" else (0x70,))
                            if "terminalOffsetX" in leg:
                                dx = leg["terminalOffsetX"] + metadata.get("archOffsetX", 0)
                            elif "sigmoidOffsetX" in metadata:
                                # Outer arch endings have identically named
                                # offsets. Read the unchanged narrow body's
                                # native donor offset before adding its shift.
                                body = source[f"u{metadata['middleTerminalSourceCodePoint']:X}"].lib["org.quintessential.construction"]
                                dx = body["leftLowerOffsetX" if leg["direction"] == "descender" else "rightUpperOffsetX"]
                                dx += metadata["sigmoidOffsetX"]
                            else:
                                key = "lowerOffsetX" if leg["direction"] == "descender" else "upperOffsetX"
                                dx = metadata.get("freeLegOffsetX", metadata.get(key))
                                self.assertIsNotNone(dx, "Missing native free-end translation")
                                if leg["direction"] == "descender":
                                    dx += metadata["terminalOffsetX"]
                            height, (left, right) = native_bands[leg["donorCodePoint"]]
                            bands = filled_scanline_intervals(shape, height)
                            closed = any(abs(join["middleStemCenterX"] - leg["centerX"]) < 1e-5
                                         for join in metadata.get("middleHookJoins", []))
                            if "terminalOffsetX" not in leg and "sigmoidOffsetX" in metadata:
                                closed |= bool(metadata.get("joinedLower" if leg["direction"] == "descender" else "joinedUpper"))
                            if closed:
                                # A closed hook replaces the free donor edge
                                # with a fitted quarter. Protect the complete
                                # central half of its receiving shaft here;
                                # the independent enclosure gate also requires
                                # its intended closed counter. Unjoined ends
                                # must retain the donor's entire shaft band.
                                inset = (right - left) / 4
                                left, right = left + inset, right - inset
                            missing = min(max(0, a - left - dx, right + dx - b) for a, b in bands)
                            self.assertTrue(any(a <= left + dx + 1 / 32 and b >= right + dx - 1 / 32 for a, b in bands),
                                            (name, leg, height, missing, "Required native free-end shaft is missing"))
                        # Counter contours are translated rigidly from each
                        # current native Italic base, with identical curve data.
                        def normalized(contour):
                            x = min(point[0] for _, points in contour for point in points)
                            return [(op, [[px - x, py] for px, py in points])
                                    for op, points in contour]
                        expected = counter_recordings(outline(source, f"u{middle_counter_reference(recipe):X}"))
                        actual = [normalized(contour) for contour in counter_recordings(outline(source, name))]
                        for counter in expected:
                            wanted = normalized(counter)
                            compatible = [candidate for candidate in actual
                                          if [(op, len(points)) for op, points in candidate] ==
                                             [(op, len(points)) for op, points in wanted]]
                            errors = [max(abs(a - b) for (_, first), (_, second) in zip(candidate, wanted)
                                          for p, q in zip(first, second) for a, b in zip(p, q))
                                      for candidate in compatible]
                            self.assertTrue(errors and min(errors) <= 1e-5,
                                            (name, "Native body counter changed", min(errors, default=None)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, help="Capture before modifying any sources or output")
    args, rest = parser.parse_known_args()
    if args.capture:
        if args.capture.exists():
            raise SystemExit(f"Refusing to overwrite baseline {args.capture}")
        result = snapshot()
        args.capture.parent.mkdir(parents=True, exist_ok=True)
        args.capture.write_bytes(gzip.compress(json.dumps(result, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
        print(f"Captured {len(result['sources'])} source masters and {len(result['compiled'])} compiled faces in {args.capture}")
    else:
        unittest.main(argv=[__file__, *rest])

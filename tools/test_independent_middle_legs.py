#!/usr/bin/env python3
"""Verify independent middle ends against preserved outlines and visible ink.

The pre-increment capture pins all 832 prior identities, editable GLIF bytes,
outlines, advances, effective pairs, and GID order. Mixed constructions must
fill the two missing states for each of the 192 two-middle-component bases.
The three later stemless terminal edits are validated by their focused suite;
their advances and pairs remain subject to this historical preservation gate.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import unittest

import pyclipper
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from font_geometry_helpers import effective_pairs, outline, polygons_from_recording
from test_additions_font import interpolation_factor, middle_directions
from test_italic_completion import expected_counter_count, outlines, pair_digest, source_pair_digest
from test_quintessential_font import PolygonPen, filled_scanline_intervals
from verify_logical_allocation import historical_entry, historical_source_sha, current_unicode_map
from test_stemless_terminals import assert_preserved_outlines
import hip_tail_revision

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
BASELINE = ROOT / "resources/provenance/independent-middle-legs-baseline.json.gz"
BASELINE_SHA256 = "4a6cbca062740f26cdefbc0a8399ceca8f2f707af6f4ecf159be7959d72997b8"
WEIGHTS = (400, 500, 550, 600, 700)
STYLES = {"Regular": (False, 400), "Bold": (False, 700),
          "Italic": (True, 400), "BoldItalic": (True, 700)}
COMPILED = True


def filled_tree(recording):
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(polygons_from_recording(recording), pyclipper.PT_SUBJECT, True)
    return clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)


def extra_intervals(extended, short):
    """Find visible scanline spans present only in the pinned extended form."""
    result = []
    for first, last in extended:
        position = first
        for left, right in short:
            if right <= position or left >= last:
                continue
            if left > position:
                result.append((position, min(left, last)))
            position = max(position, right)
            if position >= last:
                break
        if position < last:
            result.append((position, last))
    return result


def expected_mixed_counters(entry, italic):
    total = expected_counter_count(entry)
    if not italic:
        # Native Roman p serif bars join neighboring descending shafts.
        # This accepted bar adds one enclosure beneath their unchanged arch.
        # Italic p feet have no horizontal serif bar and remain independent.
        total += sum(left.get("lower") == right.get("lower") == "straight"
                     and (left.get("middle", False) or right.get("middle", False))
                     for left, right in zip(entry["parts"], entry["parts"][1:]))
    return total


class IndependentMiddleLegTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = BASELINE.read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE_SHA256:
            raise AssertionError("The immutable independent-middle-leg baseline changed")
        cls.baseline = json.loads(gzip.decompress(data))
        cls.entries = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text())["entries"]
        cls.added = [entry for entry in cls.entries if "middleLegExtensions" in entry]
        cls.by_id = {entry["glyphId"]: entry for entry in cls.entries}
        cls.sources = {style: Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") for style in STYLES}

    @classmethod
    def tearDownClass(cls):
        for source in cls.sources.values():
            source.close()

    def test_every_two_middle_base_has_all_four_independent_states(self):
        self.assertEqual(len(self.baseline["entries"]), 832)
        self.assertEqual(len(self.entries), 1216)
        self.assertEqual(len(self.added), 384)
        self.assertEqual(len({entry["codePoint"] for entry in self.entries}), len(self.entries))
        self.assertEqual(len({entry["glyphName"] for entry in self.entries}), len(self.entries))
        for before in self.baseline["entries"]:
            self.assertEqual(historical_entry(self.by_id[before["glyphId"]]), before, before["glyphId"])
        for code in range(0xF2C00, 0xF2CC0):
            entries = [entry for entry in self.entries if entry["recipeCodePoint"] == code]
            states = {tuple(entry.get("middleLegExtensions", (entry["middleLegs"],) * 2)): entry
                      for entry in entries}
            self.assertEqual(len(entries), 4, hex(code))
            self.assertEqual(set(states), {(False, False), (True, False), (False, True), (True, True)})
            for flags, entry in states.items():
                self.assertEqual(entry["postures"], ["Roman", "Italic"])
                parts = [part for part in entry["parts"] if part.get("middle")]
                self.assertEqual(len(parts), 2, entry["glyphId"])
                actual = tuple(part.get("upper") == "straight" or part.get("lower") == "straight"
                               for part in parts)
                self.assertEqual(actual, flags, entry["glyphId"])
                if entry in self.added:
                    self.assertEqual(entry["baseGlyphId"], states[False, False]["glyphId"])

    def test_every_prior_source_byte_outline_advance_pair_and_gid_is_exact(self):
        self.assertEqual(len(self.baseline["sourceFiles"]), 3336)
        for relative, digest in self.baseline["sourceFiles"].items():
            self.assertEqual(historical_source_sha(ROOT / relative), digest, relative)
        for style, captured in self.baseline["sources"].items():
            source = self.sources[style]
            names = tuple(captured["outlines"])
            self.assertEqual(source.lib["public.glyphOrder"][:len(captured["order"])], captured["order"], style)
            assert_preserved_outlines(self, outlines(source, names), captured["outlines"], style, source=True)
            self.assertEqual(source_pair_digest(source, names), captured["pairs"], style)
            self.assertEqual({name: source[name].unicodes for name in names}, current_unicode_map(captured["cmap"]), style)

    def reference_legs(self, recipe, italic, weight):
        """Read the old both-extended GLIF, pinned apart from its assigned Unicode."""
        first, second = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
        legs = [sorted(self.sources[style][f"u{recipe:X}.middle"].lib[
            "org.quintessential.construction"]["extendedMiddleLegs"], key=lambda leg: leg["centerX"])
            for style in (first, second)]
        factor = interpolation_factor(weight)
        return [{"centerX": a["centerX"] + factor * (b["centerX"] - a["centerX"]),
                 "centerY": a.get("centerY", 250) + factor * (b.get("centerY", 250) - a.get("centerY", 250))}
                for a, b in zip(*legs)]

    def assert_shape(self, glyphs, entry, italic, weight, references):
        name, recipe = entry["glyphName"], entry["recipeCodePoint"]
        flags = entry["middleLegExtensions"]
        recording = outline(glyphs, name)
        paths = polygons_from_recording(recording)
        winding = tuple(pyclipper.Area(path) > 0 for path in paths)
        if weight == 400:
            self.winding[italic, name] = winding
        else:
            self.assertEqual(winding, self.winding[italic, name], "A contour reversed during interpolation")
        for index, path in enumerate(paths):
            area = abs(pyclipper.Area(path)) / 4096
            self.assertGreater(area, 1, (name, index, "Collapsed contour"))
            simple = pyclipper.SimplifyPolygon(path, pyclipper.PFT_NONZERO)
            resolved_area = sum(abs(pyclipper.Area(part)) for part in simple) / 4096
            if abs(area - resolved_area) > .1:
                # Use the primary suite's refinement gate for acute corners;
                # intentional overlap between separate contours remains valid.
                pen = PolygonPen(None)
                replayRecording(recording, pen)
                for scale in (256, 1024, 4096):
                    refined = [(round(x * scale), round(y * scale)) for x, y in pen.paths[index]]
                    area = abs(pyclipper.Area(refined)) / scale ** 2
                    resolved_area = sum(abs(pyclipper.Area(part)) for part in
                                        pyclipper.SimplifyPolygon(refined, pyclipper.PFT_NONZERO)) / scale ** 2
            self.assertLessEqual(abs(area - resolved_area), .1,
                                 (name, index, "Self-intersection", area, resolved_area))
        tree = filled_tree(recording)
        self.assertEqual(len(tree.Childs), 1, "Detached ink component")
        self.assertEqual(len(tree.Childs[0].Childs), expected_mixed_counters(entry, italic),
                         "A required counter opened or an unintended enclosure formed")
        for counter in tree.Childs[0].Childs:
            self.assertTrue(counter.IsHole)
            self.assertGreater(abs(pyclipper.Area(counter.Contour)) / 4096, 1000,
                               "Collapsed or unintended small counter")
        actual = pyclipper.PolyTreeToPaths(tree)
        if recipe not in references:
            references[recipe] = [pyclipper.PolyTreeToPaths(filled_tree(outline(glyphs, suffix)))
                                  for suffix in (f"u{recipe:X}", f"u{recipe:X}.middle")]
        short, both = references[recipe]
        legs = self.reference_legs(recipe, italic, weight)
        for direction, leg, extend in zip(middle_directions(recipe), legs, flags):
            height = -100 if direction == "descender" else 600
            difference = extra_intervals(filled_scanline_intervals(both, height),
                                         filled_scanline_intervals(short, height))
            # The old shaft center locates its neighborhood. The actual test
            # points come from visible ink added to the pinned short outline,
            # independently of new construction metadata or donor dispatch.
            expected_x = leg["centerX"] + (0.21256 * (height - leg["centerY"]) if italic else 0)
            candidates = [(left, right) for left, right in difference if right - left > 8]
            self.assertTrue(candidates, (name, direction, "Missing reference extension"))
            left, right = min(candidates, key=lambda band: abs(sum(band) / 2 - expected_x))
            self.assertLess(abs((left + right) / 2 - expected_x), 100, "Reference shaft is ambiguous")
            bands = filled_scanline_intervals(actual, height)
            for fraction in (.35, .5, .65):
                x = left + (right - left) * fraction
                self.assertEqual(any(a - 1 / 32 <= x <= b + 1 / 32 for a, b in bands), extend,
                                 (name, direction, height, x, "Wrong visible middle-leg state"))

    def test_all_1536_new_source_glyphs_are_compatible_and_keep_only_selected_ends(self):
        self.winding = {}
        for italic in (False, True):
            styles = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
            for entry in self.added:
                name = entry["glyphName"]
                first, second = (self.sources[style][name] for style in styles)
                self.assertEqual([[(point.type) for point in contour.points] for contour in first.contours],
                                 [[(point.type) for point in contour.points] for contour in second.contours], name)
        for style, (italic, weight) in STYLES.items():
            source, references = self.sources[style], {}
            for entry in self.added:
                name, recipe = entry["glyphName"], entry["recipeCodePoint"]
                with self.subTest(style=style, glyph=name):
                    self.assertEqual(source[name].width, source[f"u{recipe:X}"].width)
                    self.assertEqual(source[name].unicodes, [entry["codePoint"]])
                    metadata = source[name].lib["org.quintessential.construction"]
                    self.assertEqual(metadata["middleLegExtensions"], entry["middleLegExtensions"])
                    self.assertEqual(metadata["middleLegCount"], 2)
                    self.assertEqual(len(metadata["extendedMiddleLegs"]), 1)
                    if 0xF2C30 <= recipe < 0xF2C3C:
                        adjacent = 0 if (recipe - 0xF2C30) % 4 >= 2 else 1
                        self.assertEqual(len(metadata["middleHookJoins"]), int(entry["middleLegExtensions"][adjacent]))
                    self.assert_shape(source, entry, italic, weight, references)

    def test_compiled_preservation_and_all_384_additions_at_five_weights_in_both_postures(self):
        if not COMPILED:
            self.skipTest("Source-only run")
        expected_cmap = {0x20: "space", **{entry["codePoint"]: entry["glyphName"] for entry in self.entries}}
        self.winding = {}
        for face, captured in self.baseline["compiled"].items():
            italic = "Italic" in face
            if "-" in face:
                _, weight_text = face.split("-")
                weight = int(weight_text)
                filename = "QuintessentialSerif-Italic-Variable.ttf" if italic else "QuintessentialSerif-Variable.ttf"
            else:
                filename, weight = f"QuintessentialSerif-{face}.otf", None
            with TTFont(OUTPUT / filename) as font, self.subTest(face=face):
                if weight is not None:
                    font = instantiateVariableFont(font, {"wght": weight}, inplace=True)
                names = tuple(captured["outlines"])
                style = "Italic" if italic else "Regular"
                order = self.baseline["sources"][style]["order"]
                self.assertEqual(font.getGlyphOrder()[:len(order)], order)
                self.assertEqual(font.getBestCmap(), expected_cmap)
                self.assertEqual(len(font.getGlyphOrder()), 1218)
                glyphs = font.getGlyphSet()
                assert_preserved_outlines(self, outlines(glyphs, names), captured["outlines"], face, instantiated=weight is not None)
                self.assertEqual(pair_digest(hip_tail_revision.historical_pairs(effective_pairs(font), face), names), captured["pairs"], face)
                if weight is None:
                    continue
                references = {}
                for entry in self.added:
                    with self.subTest(face=face, glyph=entry["glyphName"]):
                        self.assertEqual(glyphs[entry["glyphName"]].width, glyphs[f"u{entry['recipeCodePoint']:X}"].width)
                        self.assert_shape(glyphs, entry, italic, weight, references)


def main():
    global COMPILED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-only", action="store_true")
    args, rest = parser.parse_known_args()
    COMPILED = not args.sources_only
    unittest.main(argv=[__file__, *rest])


if __name__ == "__main__":
    main()

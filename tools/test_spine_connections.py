"""Check the reviewed receiving quarters and lower-hook closure against STIX.

These checks complement the complete family inventory and preservation audit.
They measure the actual source/compiled curves, independently of their builders.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import plistlib
import unittest

from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from ufoLib2 import Font

from font_geometry_helpers import outline
from reviewed_spine_connections import _nonbody_segments, interpolate_connection_metadata
from test_project_glyph import (
    WEIGHTS, interpolated, filled_tree, bounds, vertical_interval,
    distance_to_outline, stix_reference,
)
from test_quintessential_font import ALLOCATION_ENTRIES, DONORS, DONOR_FILES, OUTPUT, ROOT, SOURCES, PolygonPen

COMPILED = True
REPORT = []
INPUTS = {}
RECIPES = (0xF2B1D, 0xF2B22, 0xF2B26, 0xF2B3F)
ENTRIES = {e["recipeCodePoint"]: e for e in ALLOCATION_ENTRIES
           if e["recipeCodePoint"] in RECIPES and not e["middleLegs"]}


def _angle(points, at_end=False, vertical=False):
    first, second = points[-2:] if at_end else points[:2]
    dx, dy = abs(second[0] - first[0]), abs(second[1] - first[1])
    return math.degrees(math.atan2(dx, dy) if vertical else math.atan2(dy, dx))


def _filled(recording):
    pen = PolygonPen(None)
    replayRecording(recording, pen)
    paths = [[(round(x * 64), round(y * 64)) for x, y in path] for path in pen.paths]
    tree = filled_tree(paths)
    assert len(tree.Childs) == 1, "Connection must form one filled body"
    return tree.Childs[0]


def receiving_profile(recording, metadata, upper):
    segments = _nonbody_segments(recording)
    left, right = metadata["stemLeftInnerX"], metadata["stemRightInnerX"]
    factor = ((left - metadata["stemLeftX"]) - 83) / 60
    entry_y = (400 + 2 * factor if upper else
               64 - 5 * factor if metadata["rightVariant"] // 2 == 0 else 63 - 7 * factor)
    wanted = [(i, points) for i, (operation, points) in enumerate(segments)
              if operation != "line" and abs(points[0][1] - entry_y) < .76
              and (left + 1 <= points[0][0] <= left + 5 if upper else right - 3 <= points[0][0] <= right + 1)]
    assert len(wanted) == 1, (upper, wanted, "Unique receiving-quarter entrance")
    index, points = wanted[0]
    entry_angle = _angle(points)
    while index + 1 < len(segments):
        operation, current = segments[index]
        following_op, following = segments[index + 1]
        if (operation != "line" and following_op != "line" and current[-1] == following[0]
                and abs(current[-1][1] - current[-2][1]) < 1e-5
                and abs(following[1][1] - following[0][1]) < 1e-5):
            peak = current[-1]
            break
        index += 1
    else:
        raise AssertionError("Receiving quarters need a common horizontal extremum")
    index += 1
    while index + 1 < len(segments) and segments[index + 1][0] != "line":
        index += 1
    span = abs(segments[index][1][-1][0] - peak[0])
    body = _filled(recording)
    holes = [h for h in body.Childs if bounds(h.Contour)[1] >= 0 and bounds(h.Contour)[3] <= 500]
    assert len(holes) == 2
    own = max(holes, key=lambda h: bounds(h.Contour)[1]) if upper else min(holes, key=lambda h: bounds(h.Contour)[1])
    counter = own.Contour
    boundaries = [body.Contour, *(hole.Contour for hole in body.Childs if hole is not own)]
    x0, _, x1, _ = bounds(counter)
    widths = []
    for i in range(31):
        x = x0 + (x1 - x0) * (.02 + .96 * i / 30)
        y = vertical_interval(counter, x)[1 if upper else 0]
        widths.append(min(distance_to_outline((x, y), boundary) for boundary in boundaries))
    return {"entryAngle": entry_angle, "receivingSpan": span,
            "stem": left - metadata["stemLeftX"], "minimumInk": min(widths)}


def closure_profile(recording, metadata):
    segments = _nonbody_segments(recording)
    outer, inner = metadata["lowerClosureOuterJoin"], metadata["lowerClosureInnerJoin"]
    near = lambda a, b: max(abs(x - y) for x, y in zip(a, b)) < .76
    outside = [points for op, points in segments if op != "line" and near(points[-1], outer)]
    inside = [points for op, points in segments if op != "line" and near(points[0], inner)]
    assert len(outside) == len(inside) == 1, "Unique lower closure quarters"
    body = _filled(recording)
    holes = [hole for hole in body.Childs if bounds(hole.Contour)[1] < -100]
    assert len(holes) == 1, "The closed tail must retain one open enclosure"
    boundaries = [body.Contour, *(hole.Contour for hole in body.Childs if hole is not holes[0])]
    widths = [min(distance_to_outline((x / 64, y / 64), boundary) for boundary in boundaries)
              for x, y in holes[0].Contour]
    return {"outerShaftAngle": _angle(outside[0], at_end=True, vertical=True),
            "innerShaftAngle": _angle(inside[0], vertical=True), "minimumRibbon": min(widths)}


class SpineConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.metadata, cls.old = {}, {}, {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            source_path = SOURCES / f"QuintessentialSerif-{style}.ufo"
            source = Font.open(source_path)
            filenames = plistlib.loads((source_path / "glyphs/contents.plist").read_bytes())
            old = Font.open(ROOT / f"tests/baselines/0.210/fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo")
            for recipe, entry in ENTRIES.items():
                name = entry["glyphName"]
                cls.sources[weight, recipe] = outline(source, name)
                cls.metadata[weight, recipe] = dict(source[name].lib["org.quintessential.construction"])
                cls.old[weight, recipe] = outline(old, name)
                path = source_path / "glyphs" / filenames[name]
                INPUTS[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            source.close()
            old.close()
        cls.donor = TTFont(DONORS / DONOR_FILES[False])
        cls.addClassCleanup(cls.donor.close)
        for path in (DONORS / DONOR_FILES[False], Path(__file__), ROOT / "tools/reviewed_spine_connections.py"):
            INPUTS[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        if COMPILED:
            path = OUTPUT / "QuintessentialSerif-Variable.ttf"
            cls.font = TTFont(path)
            INPUTS[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            cls.addClassCleanup(cls.font.close)

    def check_recording(self, recording, metadata, entry, weight, kind):
        native = self.donor.getGlyphSet(location={"wght": weight})
        reference = stix_reference(self.donor, weight)
        row = {"weight": weight, "glyphId": entry["glyphId"], "kind": kind}
        for upper, extended, donor_code, operation_index in (
            (True, metadata["rightVariant"] % 2, 0x62, 4),
            (False, metadata["leftVariant"] % 2, 0x61, 23),
        ):
            if extended:
                metrics = receiving_profile(recording, metadata, upper)
                donor = outline(native, self.donor.getBestCmap()[donor_code])
                donor_points = (donor[operation_index - 1][1][-1], *donor[operation_index][1])
                native_angle = _angle(donor_points)
                # Native b/a remain the stress reference. A 22-degree limit
                # permits the compact body but rejects the old Bold collapse
                # (28 and 32 degrees steeper than its native entry respectively).
                self.assertLessEqual(metrics["entryAngle"], native_angle + 22)
                self.assertGreaterEqual(metrics["receivingSpan"], metrics["stem"] * .2)
                self.assertGreaterEqual(metrics["minimumInk"], reference["hairline"] * .6)
                row["upper" if upper else "lower"] = {**metrics, "nativeEntryAngle": native_angle}
        if metadata.get("joinedLower") == "hook":
            metrics = closure_profile(recording, metadata)
            self.assertLessEqual(metrics["outerShaftAngle"], 1)
            self.assertLessEqual(metrics["innerShaftAngle"], 1)
            self.assertGreaterEqual(metrics["minimumRibbon"], reference["hairline"] * .6)
            row["lowerHook"] = metrics
        REPORT.append(row)

    def test_source_connections_at_seven_weights(self):
        for weight in WEIGHTS:
            for recipe, entry in ENTRIES.items():
                with self.subTest(weight=weight, glyph=entry["glyphId"]):
                    recording = interpolated(self.sources[400, recipe], self.sources[700, recipe], weight)
                    metadata = interpolate_connection_metadata(self.metadata[400, recipe], self.metadata[700, recipe], weight)
                    self.check_recording(recording, metadata, entry, weight, "source")

    def test_compiled_connections_at_seven_weights(self):
        if not COMPILED:
            self.skipTest("Source-only run")
        for weight in WEIGHTS:
            glyphs = self.font.getGlyphSet(location={"wght": weight})
            for recipe, entry in ENTRIES.items():
                with self.subTest(weight=weight, glyph=entry["glyphId"]):
                    metadata = interpolate_connection_metadata(self.metadata[400, recipe], self.metadata[700, recipe], weight)
                    self.check_recording(outline(glyphs, entry["glyphName"]), metadata, entry, weight, "compiled")

    def test_checks_reject_the_previous_compressed_and_cornered_connections(self):
        native = self.donor.getGlyphSet(location={"wght": 700})
        for recipe, upper, code, index in ((0xF2B1D, True, 0x62, 4), (0xF2B22, False, 0x61, 23)):
            metrics = receiving_profile(self.old[700, recipe], self.metadata[700, recipe], upper)
            donor = outline(native, self.donor.getBestCmap()[code])
            native_angle = _angle((donor[index - 1][1][-1], *donor[index][1]))
            self.assertGreater(metrics["entryAngle"], native_angle + 22)
        old_closure = closure_profile(self.old[700, 0xF2B26], self.metadata[700, 0xF2B26])
        self.assertGreater(old_closure["outerShaftAngle"], 10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-only", action="store_true")
    parser.add_argument("--report", type=Path)
    args, unittest_args = parser.parse_known_args()
    COMPILED = not args.sources_only
    result = unittest.main(argv=[__file__, *unittest_args], exit=False)
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in INPUTS.items()), "Regression inputs changed during this run"
    if args.report:
        args.report.write_text(json.dumps({"status": "passed" if result.result.wasSuccessful() else "failed",
                                          "inputSha256": dict(sorted(INPUTS.items())),
                                          "connectionBoundaryHelperSha256": INPUTS["tools/reviewed_spine_connections.py"],
                                          "compiledChecks": COMPILED,
                                          "measurements": REPORT}, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(not result.result.wasSuccessful())

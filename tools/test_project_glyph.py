#!/usr/bin/env python3
"""Independent optical regression for the Roman project emblem.

Measure the filled outline, without importing its construction recipe. The
immutable 0.210 glyph supplies the old silhouette, advance, and defect profile;
STIX Two Text o and b supply weight-specific stroke and shoulder references.
These are engineering guardrails, not a substitute for visual acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import unittest

import pyclipper
from fontTools.misc.fixedTools import floatToFixedToFloat
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.varLib.models import piecewiseLinearMap
from ufoLib2 import Font

from font_geometry_helpers import outline, polygons_from_recording
from test_quintessential_font import (
    ALLOCATION_BY_NAME, DONORS, DONOR_FILES, EXPECTED_AVAR, OUTPUT, ROOT, SOURCES, VARIABLE_FILES,
    PolygonPen, filled_scanline_intervals, polygons, symmetric_difference_area,
)

NAME = "uF2B1C"  # Stable internal recipe name, independent of current encoding.
CODE_POINT = ALLOCATION_BY_NAME[NAME]["codePoint"]
WEIGHTS = (400, 450, 500, 550, 600, 650, 700)
BASELINE = ROOT / "tests/baselines/0.210"
COMPILED = True
MEASUREMENTS = []
STATIC_MEASUREMENTS = []


def contours(recording):
    result, current = [], []
    for item in recording:
        current.append(item)
        if item[0] == "closePath":
            result.append(current)
            current = []
    assert not current, "Open outline"
    return result


def interpolated(first, second, weight):
    assert [(op, len(points)) for op, points in first] == [
        (op, len(points)) for op, points in second], "Incompatible source contours"
    factor = floatToFixedToFloat(
        piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
    return [(op, tuple((x + factor * (bx - x), y + factor * (by - y))
                       for (x, y), (bx, by) in zip(points, other)))
            for (op, points), (_, other) in zip(first, second)]


def bounds(path):
    return (min(x for x, _ in path) / 64, min(y for _, y in path) / 64,
            max(x for x, _ in path) / 64, max(y for _, y in path) / 64)


def vertical_interval(path, x):
    intervals = filled_scanline_intervals([[(y, px) for px, y in path]], x)
    assert len(intervals) == 1, ("Counter does not have a single vertical section", x)
    return intervals[0]


def distance_to_outline(point, path):
    """Shortest point-to-segment distance approximates perpendicular ink width."""
    px, py = point
    closest = math.inf
    for (ax, ay), (bx, by) in zip(path, [*path[1:], path[0]]):
        ax, ay, bx, by = ax / 64, ay / 64, bx / 64, by / 64
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length)) if length else 0
        closest = min(closest, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return closest


def filled_tree(paths):
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    return clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)


def parts(paths):
    tree = filled_tree(paths)
    assert len(tree.Childs) == 1, "Glyph must be one connected body"
    body = tree.Childs[0]
    assert not body.IsHole and len(body.Childs) == 2, "Glyph must have exactly two counters"
    assert all(hole.IsHole and not hole.Childs for hole in body.Childs), "Nested or intersecting counters"
    lower, upper = sorted((hole.Contour for hole in body.Childs), key=lambda p: bounds(p)[1])
    return body.Contour, lower, upper


def normal_spine_profile(outer, lower, upper):
    """Cast from both facing counter edges into the ink, over their full span.

    A ray ending at the opposing counter measures the shared spine. A ray that
    exits the exterior crosses a native shaft merge, where the unchanged outer
    contour can add ink; report that separately rather than calling it an even
    stroke. The production construction recipe is not used here.
    """
    segments = []
    for label, path in (("outer", outer), ("lower", lower), ("upper", upper)):
        for (ax, ay), (bx, by) in zip(path, [*path[1:], path[0]]):
            segments.append((label, ax / 64, ay / 64, (bx - ax) / 64, (by - ay) / 64))

    def first_exit(origin, normal):
        ox, oy = origin
        nx, ny = normal
        hits = []
        for label, ax, ay, dx, dy in segments:
            denominator = nx * dy - ny * dx
            if abs(denominator) < 1e-10:
                continue
            ax, ay = ax - ox, ay - oy
            distance = (ax * dy - ay * dx) / denominator
            along_segment = (ax * ny - ay * nx) / denominator
            if distance > 0.01 and -1e-6 <= along_segment <= 1 + 1e-6:
                hits.append((distance, label))
        assert hits, "Normal ray did not leave the closed glyph"
        return min(hits)

    shared, merged, profiles, slopes, curvatures = [], [], {}, [], []
    for edge, path, section_index, opposite in (("upper", upper, 0, "lower"),
                                                ("lower", lower, 1, "upper")):
        left, _, right, _ = bounds(path)
        # Estimate the tangent across half a scan step. A sub-grid window on
        # the flattened 1/64-unit contour amplifies quantization into fake
        # normal-direction jumps, especially in the heavier master.
        h = (right - left) / 200
        samples, reported = [], []
        for i in range(1, 100):
            x = left + (right - left) * i / 100
            y = vertical_interval(path, x)[section_index]
            slope = (vertical_interval(path, x + h)[section_index]
                     - vertical_interval(path, x - h)[section_index]) / (2 * h)
            normal = (-slope, 1) if section_index else (slope, -1)
            length = math.hypot(*normal)
            width, boundary = first_exit((x, y), tuple(value / length for value in normal))
            assert boundary in (opposite, "outer"), "Spine normal folds back into its originating counter"
            is_shared = boundary == opposite
            (shared if is_shared else merged).append(width)
            samples.append((x, width, is_shared))
            if i == 1 or i == 99 or i % 5 == 0:
                reported.append([i / 100, round(width, 3), "counter" if is_shared else "shaft merge"])
        profiles[edge] = reported
        for first, second in zip(samples, samples[1:]):
            if first[2] and second[2]:
                slopes.append(abs(second[1] - first[1]) / (second[0] - first[0]))
        for first, second, third in zip(samples, samples[1:], samples[2:]):
            if first[2] and second[2] and third[2]:
                curvatures.append(abs(third[1] - 2 * second[1] + first[1]) / (second[0] - first[0]) ** 2)
    assert shared and merged, "Missing shared spine or native shaft transition"
    return {
        "sharedNormalMin": min(shared), "sharedNormalMax": max(shared),
        "sharedNormalMedian": statistics.median(shared),
        "sharedNormalRatio": max(shared) / min(shared), "sharedSamples": len(shared),
        "sharedMaxSlope": max(slopes), "sharedMaxCurvature": max(curvatures),
        "shaftMergeRayMin": min(merged), "shaftMergeRayMax": max(merged),
        "normalProfiles": profiles,
    }


def profile(paths, scale=64):
    outer, lower, upper = parts(paths)
    # Counter-normal measurements are sensitive to the tangent, so use a much
    # finer clipping grid than the separate coarse topology/preservation tests.
    if scale != 64:
        outer, lower, upper = [[(x * 64 / scale, y * 64 / scale) for x, y in path]
                               for path in (outer, lower, upper)]
    left, _, right, _ = bounds(upper)
    shoulder = []
    for i in range(41):
        x = left + (right - left) * (0.01 + 0.44 * i / 40)
        shoulder.append(distance_to_outline((x, vertical_interval(upper, x)[1]), outer))
    return {
        "shoulderMin": min(shoulder),
        "shoulderMax": max(shoulder),
        **normal_spine_profile(outer, lower, upper),
    }


def source_profile(recording):
    pen = PolygonPen(None)
    replayRecording(recording, pen)
    scale = 65536
    return profile([[(round(x * scale), round(y * scale)) for x, y in path]
                    for path in pen.paths], scale=scale)


def stix_reference(font, weight):
    glyph_set = font.getGlyphSet(location={"wght": weight})
    paths = polygons(glyph_set, font.getBestCmap()[0x6F])
    outer, = filled_tree(paths).Childs
    x0, y0, x1, y1 = bounds(outer.Contour)
    vertical = filled_scanline_intervals([[(y, x) for x, y in p] for p in paths], (x0 + x1) / 2)
    horizontal = filled_scanline_intervals(paths, (y0 + y1) / 2)
    assert len(vertical) == len(horizontal) == 2
    b_body, = filled_tree(polygons(glyph_set, font.getBestCmap()[0x62])).Childs
    b_counter, = b_body.Childs
    left, _, right, _ = bounds(b_counter.Contour)
    shoulder = []
    for i in range(41):
        x = left + (right - left) * (0.01 + 0.44 * i / 40)
        shoulder.append(distance_to_outline(
            (x, vertical_interval(b_counter.Contour, x)[1]), b_body.Contour))
    return {"hairline": statistics.mean(b - a for a, b in vertical),
            "stem": statistics.mean(b - a for a, b in horizontal),
            "bShoulderMin": min(shoulder)}


class ProjectGlyphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.old_sources = [], []
        for style in ("Regular", "Bold"):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            old = Font.open(BASELINE / "fonts/QuintessentialSerif" / f"QuintessentialSerif-{style}.ufo")
            cls.sources.append((outline(source, NAME), source[NAME].width))
            cls.old_sources.append((outline(old, NAME), old[NAME].width))
        cls.donor = TTFont(DONORS / DONOR_FILES[False])
        cls.addClassCleanup(cls.donor.close)
        if COMPILED:
            cls.font = TTFont(OUTPUT / VARIABLE_FILES[False])
            cls.old_font = TTFont(BASELINE / "resources/fonts/QuintessentialSerif" / VARIABLE_FILES[False])
            cls.addClassCleanup(cls.font.close)
            cls.addClassCleanup(cls.old_font.close)

    def test_source_compatibility_and_preserved_silhouette(self):
        for weight in WEIGHTS:
            with self.subTest(weight=weight):
                recording = interpolated(self.sources[0][0], self.sources[1][0], weight)
                parts(polygons_from_recording(recording))
                self.assertTrue(all(math.isfinite(value) for _, points in recording
                                    for point in points for value in point))
        for (recording, width), (old, old_width) in zip(self.sources, self.old_sources):
            self.assertEqual(width, old_width)
            self.assertEqual(contours(recording)[0], contours(old)[0])

    def test_optical_profiles_across_weight_axis(self):
        for weight in WEIGHTS:
            with self.subTest(weight=weight):
                reference = stix_reference(self.donor, weight)
                before = source_profile(interpolated(
                    self.old_sources[0][0], self.old_sources[1][0], weight))
                sources = source_profile(interpolated(
                    self.sources[0][0], self.sources[1][0], weight))
                row = {"weight": weight, "stix": reference, "before": before, "source": sources}
                if COMPILED:
                    self.assertEqual(self.font.getBestCmap()[CODE_POINT], NAME)
                    row["compiled"] = profile(polygons(
                        self.font.getGlyphSet(location={"wght": weight}), NAME, scale=65536), scale=65536)
                MEASUREMENTS.append(row)
                for kind in ("source", "compiled") if COMPILED else ("source",):
                    actual = row[kind]
                    # A diagonal join can be finer than an o crown: compare it
                    # primarily with STIX b's shoulder, with an o-based floor.
                    self.assertGreaterEqual(actual["shoulderMin"], reference["bShoulderMin"] * 0.7, (kind, row))
                    self.assertGreaterEqual(actual["shoulderMin"], reference["hairline"] * 0.6, (kind, row))
                    self.assertGreater(actual["shoulderMin"], before["shoulderMin"] * 1.5, (kind, row))
                    # The shared spine should have steady optical weight with
                    # natural curvature and modest contrast against the shafts.
                    # Bound both the original pinched waist and the subsequent
                    # overly heavy draft without freezing a chosen coordinate.
                    self.assertGreaterEqual(actual["sharedSamples"], 100, (kind, row))
                    self.assertGreaterEqual(actual["sharedNormalMin"], reference["stem"] * 0.58, (kind, row))
                    self.assertLessEqual(actual["sharedNormalMax"], reference["stem"] * 0.9, (kind, row))
                    self.assertLessEqual(actual["sharedNormalRatio"], 1.2, (kind, row))
                    self.assertGreaterEqual(actual["shaftMergeRayMin"], actual["sharedNormalMin"] * 0.95, (kind, row))
                    # Reject both a fragile waist and short rounded-control-point
                    # ripples; widened native shaft intersections remain valid.
                    self.assertLess(actual["sharedMaxSlope"], 0.75, (kind, row))
                    self.assertLess(actual["sharedMaxCurvature"], 0.1, (kind, row))

    def test_compiled_advance_and_outer_contour_preserved(self):
        if not COMPILED:
            self.skipTest("Source-only run")
        self.assertEqual(self.font["hmtx"][NAME], self.old_font["hmtx"][NAME])
        for weight in WEIGHTS:
            with self.subTest(weight=weight):
                current_set = self.font.getGlyphSet(location={"wght": weight})
                old_set = self.old_font.getGlyphSet(location={"wght": weight})
                self.assertEqual(current_set[NAME].width, old_set[NAME].width)
                current_outline, old_outline = contours(outline(current_set, NAME))[0], contours(outline(old_set, NAME))[0]
                self.assertEqual([(op, len(points)) for op, points in current_outline],
                                 [(op, len(points)) for op, points in old_outline])
                maximum_delta = max(abs(a - b) for (_, points), (_, old_points) in zip(current_outline, old_outline)
                                    for point, old_point in zip(points, old_points) for a, b in zip(point, old_point))
                # Inspect raw variable coordinates: rounding a static instance
                # can hide fractional drift introduced by sparse gvar/IUP data.
                self.assertLessEqual(maximum_delta, 1 / 64)
                current_outer = parts(polygons(current_set, NAME))[0]
                old_outer = parts(polygons(old_set, NAME))[0]
                self.assertLessEqual(symmetric_difference_area([current_outer], [old_outer]), 1.0)

    def test_static_faces_match_variable_endpoints_geometrically(self):
        if not COMPILED:
            self.skipTest("Source-only run")
        for style, weight in (("Regular", 400), ("Bold", 700)):
            with self.subTest(style=style), TTFont(OUTPUT / f"QuintessentialSerif-{style}.otf") as static:
                variable_set = self.font.getGlyphSet(location={"wght": weight})
                static_set = static.getGlyphSet()
                self.assertEqual(variable_set[NAME].width, static_set[NAME].width)
                parts(polygons(static_set, NAME))
                # Match the repository's full-font geometric acceptance method:
                # refine flattening and integer clipping precision independently
                # so cubic/quadratic subdivision cannot create a false mismatch.
                for steps in (192, 384, 768):
                    for scale in (64, 4096, 65536):
                        area = symmetric_difference_area(
                            polygons(variable_set, NAME, steps=steps, scale=scale),
                            polygons(static_set, NAME, steps=steps, scale=scale), scale=scale)
                        if area <= 1.0:
                            break
                    if area <= 1.0:
                        break
                STATIC_MEASUREMENTS.append({"style": style, "weight": weight,
                                            "symmetricDifferenceArea": area,
                                            "subdivisionSteps": steps, "clippingScale": scale})
                self.assertLessEqual(area, 1.0, (style, area))


def main():
    global COMPILED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-only", action="store_true")
    parser.add_argument("--report", type=str, help="Write successful measurements as JSON")
    args, remaining = parser.parse_known_args()
    COMPILED = not args.sources_only
    result = unittest.main(argv=[__file__, *remaining], exit=False).result
    if result.wasSuccessful() and args.report:
        from pathlib import Path
        destination = Path(args.report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        inputs = [SOURCES / f"QuintessentialSerif-{style}.ufo/glyphs/uF_2B_1C_.glif"
                  for style in ("Regular", "Bold")]
        if COMPILED:
            inputs.append(OUTPUT / VARIABLE_FILES[False])
            inputs.extend(OUTPUT / f"QuintessentialSerif-{style}.otf" for style in ("Regular", "Bold"))
        destination.write_text(json.dumps({
            "character": f"U+{CODE_POINT:X}", "reference": "STIX Two Text o and b",
            "units": "font units; shoulder nearest-boundary distance and spine normal-ray ink width",
            "normalProfileColumns": ["fraction of counter x span", "ink width", "exit boundary"],
            "shaftMergeNote": "Exterior-exit rays include native shaft ink and are not constant-width claims.",
            "inputSha256": {str(path.relative_to(ROOT)).replace("\\", "/"):
                            hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs},
            "compiled": COMPILED, "weights": MEASUREMENTS, "staticGeometry": STATIC_MEASUREMENTS,
        }, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()

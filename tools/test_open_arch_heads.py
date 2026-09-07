"""Verify native-u caps independently in generators, UFOs and compiled fonts.

The frozen cap inventory supplies locations, not expected new outlines. Shape
references come directly from the pinned u donor. Native left/right roles are
identified uniquely in each source master and retained in compiled fragments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from fontTools.misc.fixedTools import floatToFixedToFloat
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.ttLib import TTFont
from fontTools.varLib.models import piecewiseLinearMap
from ufoLib2 import Font

import import_stix_foundation as foundation
from quintessential_font import MASTERS, OUTPUT, ROOT, SOURCES, glyphs_for_posture


WEIGHTS = (400, 500, 550, 600, 700)
INVENTORY = ROOT / "resources/serif-consistency-targets.json"
RESULTS = {}


class Segments(BasePen):
    """Expose elementary curves, independent of qCurveTo grouping."""
    def __init__(self):
        super().__init__(None)
        self.contours = []
        self.current = []
        self.first = None

    def _moveTo(self, point):
        self.current, self.first = [], point

    def _lineTo(self, point):
        self.current.append(("line", (self._getCurrentPoint(), point)))

    def _qCurveToOne(self, control, point):
        start = self._getCurrentPoint()
        # The exact cubic equivalent also permits comparison with CFF output.
        first = tuple(a + 2 * (b - a) / 3 for a, b in zip(start, control))
        second = tuple(a + 2 * (b - a) / 3 for a, b in zip(point, control))
        self.current.append(("curve", (start, first, second, point)))

    def _curveToOne(self, first, second, point):
        self.current.append(("curve", (self._getCurrentPoint(), first, second, point)))

    def _closePath(self):
        if self._getCurrentPoint() != self.first:
            self._lineTo(self.first)
        self._endPath()

    def _endPath(self):
        self.contours.append(self.current)


def segments(recording):
    pen = Segments()
    replayRecording(recording, pen)
    return pen.contours


def glyph_segments(glyph):
    pen = RecordingPen()
    glyph.draw(pen)
    return segments(pen.value)


def translate(fragment, dx):
    return [(op, tuple((x + dx, y) for x, y in points)) for op, points in fragment]


def maximum_delta(first, second):
    if [(op, len(points)) for op, points in first] != [(op, len(points)) for op, points in second]:
        return float("inf")
    return max(abs(a - b) for (_, ps), (_, qs) in zip(first, second)
               for p, q in zip(ps, qs) for a, b in zip(p, q))


def nearest_fragment(contours, expected):
    best, fragment = float("inf"), None
    for contour in contours:
        reverse = [(op, tuple(reversed(points))) for op, points in reversed(contour)]
        for ordered in (contour, reverse):
            for index in range(len(ordered)):
                candidate = [ordered[(index + offset) % len(ordered)] for offset in range(len(expected))]
                delta = maximum_delta(candidate, expected)
                if delta < best:
                    best, fragment = delta, candidate
    return best, fragment


def fragment_delta(contours, expected):
    return nearest_fragment(contours, expected)[0]


def native_heads(donor):
    recording = foundation.decomposed_recording(donor, donor.getBestCmap()[0x75])
    result = {}
    for side, first in (("left", 2), ("right", 10)):
        cap = recording[first:first + 5]
        result[side] = segments([("moveTo", cap[0][1]), *cap[1:], ("endPath", ())])[0]
    return result


def donor_at(posture, weight):
    with TTFont(foundation.donor_paths_from_manifest()[posture]) as variable:
        return foundation.instantiateVariableFont(variable, {"wght": weight}, inplace=False, optimize=True)


def build(donor, spec):
    if spec.stemless:
        from stix_stemless import stemless_outline
        return stemless_outline(donor, spec.glyph_id)[0]
    if spec.middle_legs:
        from stix_middle_legs import middle_legs_outline
        return middle_legs_outline(donor, spec.recipe_code_point, spec.middle_leg_extensions)[0]
    return foundation.legacy_outline(donor, spec)[0]


class OpenArchHeadTests(unittest.TestCase):
    def test_native_heads_keep_u_curves_and_every_other_donor_operation(self):
        count, largest = 0, 0
        for weight in WEIGHTS:
            with donor_at("Roman", weight) as donor:
                references = native_heads(donor)
                for code, slots in ((0x265, ((6, "left"), (15, "right"))),
                                    (0x26F, ((2, "left"), (11, "right"), (29, "left")))):
                    before = foundation.decomposed_recording(donor, donor.getBestCmap()[code])
                    after = foundation.open_arch_recording(donor, code)
                    self.assertEqual(len(before), len(after))
                    changed_slots = {i for first, _ in slots for i in range(first, first + 6)}
                    self.assertTrue(all(before[i] == after[i] for i in range(len(before)) if i not in changed_slots))
                    for first, side in slots:
                        cap = after[first:first + 6]
                        actual = segments([("moveTo", cap[0][1]), *cap[1:], ("endPath", ())])[0]
                        reference = references[side]
                        reference = translate(reference, actual[0][1][0][0] - reference[0][1][0][0])
                        delta = maximum_delta(actual, reference)
                        self.assertLessEqual(delta, 0.000001, (weight, code, side))
                        if weight in (400, 700):
                            self.assertLessEqual(delta, 0.0000000001, (weight, code, side))
                        largest, count = max(largest, delta), count + 1
        RESULTS["nativeDonorHeads"] = {"heads": count, "maximumCoordinateDelta": largest,
                                       "endpointCurveTolerance": 0.0000000001, "nonCapOperationsExact": True}

    def test_generator_changes_exactly_the_independent_target_inventory(self):
        expected = {row["glyphName"] for row in json.loads(INVENTORY.read_bytes())["entries"]}
        results = []
        for master in MASTERS:
            changed, count = set(), 0
            with donor_at(master.posture, master.weight) as donor:
                def original(font, code):
                    return foundation.decomposed_recording(font, font.getBestCmap()[code])
                for spec in glyphs_for_posture(master.italic):
                    with patch.object(foundation, "open_arch_recording", original):
                        before = build(donor, spec)
                    if before != build(donor, spec):
                        changed.add(spec.glyph_name)
                    count += 1
            self.assertEqual(changed, set() if master.italic else expected, master.style)
            results.append({"master": master.style, "glyphs": count, "changed": len(changed)})
        RESULTS["generatorDependencyClosure"] = results

    def test_all_source_and_compiled_caps_match_the_correct_native_u_side(self):
        rows = json.loads(INVENTORY.read_bytes())["entries"]
        # The independently frozen old cap's leading x is 69/77 units left
        # of its receiving shaft. No production cap-location helper is used.
        references = {}
        roles = {}
        source_count = 0
        for style, weight, shaft_offset in (("Regular", 400, 69), ("Bold", 700, 77)):
            references[style] = {}
            with donor_at("Roman", weight) as donor, Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source:
                heads = native_heads(donor)
                for row in rows:
                    contours = glyph_segments(source[row["glyphName"]])
                    prepared = []
                    for index, (entrance_x, _) in enumerate(row["headEntrancePositions"][style]):
                        candidates = {side: translate(head, entrance_x + shaft_offset - head[0][1][0][0])
                                      for side, head in heads.items()}
                        matches = [side for side, head in candidates.items() if fragment_delta(contours, head) <= 0.000002]
                        self.assertEqual(len(matches), 1, (style, row["glyphName"], index, matches))
                        key = row["glyphName"], index
                        self.assertEqual(roles.setdefault(key, matches[0]), matches[0], (key, "Head side changes across masters"))
                        prepared.append(candidates[matches[0]])
                        source_count += 1
                    references[style][row["glyphName"]] = prepared

        measured = []
        for style in ("Regular", "Bold"):
            path = OUTPUT / f"QuintessentialSerif-{style}.otf"
            with TTFont(path) as font, TTFont(OUTPUT / "QuintessentialSerif-Variable.ttf") as variable:
                glyphs, maximum = font.getGlyphSet(), 0
                endpoints = variable.getGlyphSet(location={"wght": 400 if style == "Regular" else 700})
                for row in rows:
                    contours = glyph_segments(glyphs[row["glyphName"]])
                    compiled_endpoint = glyph_segments(endpoints[row["glyphName"]])
                    for cap in references[style][row["glyphName"]]:
                        # Static CFF is built from the canonical rounded TTF
                        # endpoint. Check the donor allowance once, then require
                        # CFF to retain that same compiled fragment precisely.
                        source_delta, endpoint_cap = nearest_fragment(compiled_endpoint, cap)
                        self.assertLessEqual(source_delta, 1.01, (style, row["glyphName"], "Rounded endpoint head"))
                        delta = fragment_delta(contours, endpoint_cap)
                        self.assertLessEqual(delta, 0.0001, (style, row["glyphName"], "CFF head"))
                        maximum = max(maximum, delta)
                measured.append({"face": style, "heads": len(roles), "maximumCoordinateDelta": maximum,
                                 "fontSha256": hashlib.sha256(path.read_bytes()).hexdigest()})

        path = OUTPUT / "QuintessentialSerif-Variable.ttf"
        with TTFont(path) as font:
            for weight in WEIGHTS:
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, font["avar"].segments["wght"]), 14)
                glyphs, maximum = font.getGlyphSet(location={"wght": weight}), 0
                for row in rows:
                    name = row["glyphName"]
                    contours = glyph_segments(glyphs[name])
                    for regular, bold in zip(references["Regular"][name], references["Bold"][name]):
                        cap = [(op, tuple(tuple(a + factor * (b - a) for a, b in zip(p, q)) for p, q in zip(ps, qs)))
                               for (op, ps), (_, qs) in zip(regular, bold)]
                        delta = fragment_delta(contours, cap)
                        self.assertLessEqual(delta, 1.01, (weight, name, "TrueType head differs beyond integer rounding"))
                        maximum = max(maximum, delta)
                measured.append({"face": f"Roman-{weight}", "heads": len(roles), "maximumCoordinateDelta": maximum,
                                 "fontSha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        RESULTS["sourceAndCompiledCaps"] = {"sourceHeads": source_count, "uniqueHeadsPerFace": len(roles),
                                             "compiled": measured, "trueTypeCoordinateTolerance": 1.01,
                                             "cffVersusQuantizedEndpointTolerance": 0.0001}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--report", type=Path)
    args, remaining = parser.parse_known_args()
    result = unittest.main(argv=[sys.argv[0], *remaining], exit=False).result
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"passed": result.wasSuccessful(), "weights": WEIGHTS,
                                           "inventorySha256": hashlib.sha256(INVENTORY.read_bytes()).hexdigest(),
                                           **RESULTS}, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)

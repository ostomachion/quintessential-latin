#!/usr/bin/env python3
"""Verify the refined spine throughout its independently allocated family.

The allocation's structural parts select every interior spine, including arch
and extended-middle-leg companions. The construction recipe is not imported.
Rigid counter congruence transfers the emblem's measured normal-width profile
to every member; full filled outlines are separately checked for lost joins,
collapsed counters, and closed arch openings. Optional --before checks all
geometry outside the reviewed connection segments against a pre-revision checkout.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import plistlib
import unittest

import pyclipper
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from ufoLib2 import Font

from font_geometry_helpers import outline
from reviewed_spine_connections import (
    assert_preserved_connections, interpolate_connection_metadata,
)
from test_project_glyph import (
    NAME, WEIGHTS, contours, interpolated, source_profile, stix_reference,
    filled_tree, bounds, vertical_interval, distance_to_outline,
)
from test_quintessential_font import (
    ALLOCATION_ENTRIES, DONORS, DONOR_FILES, OUTPUT, ROOT, SOURCES,
    VARIABLE_FILES, PolygonPen,
)

ENTRIES = tuple(e for e in ALLOCATION_ENTRIES
                if "middleLegExtensions" not in e
                and any(p["kind"] == "spine" for p in e["parts"][1:-1]))
COMPILED = True
BEFORE = ROOT / "tests/baselines/0.210"
REPORT = {"familySize": len(ENTRIES), "weights": [], "sourcePreservation": [],
          "compiledPreservation": []}


def signature(recording):
    return [(op, len(points)) for op, points in recording]


def delta(first, second, dx=0):
    assert signature(first) == signature(second), "Contour topology changed"
    return max((max(abs(x - bx - dx), abs(y - by))
                for (_, points), (_, other) in zip(first, second)
                for (x, y), (bx, by) in zip(points, other)), default=0)


def counter_indices(recording, references):
    """Locate the two counters by shape, allowing only a rigid x translation."""
    found, offsets = [], []
    for reference in references:
        matches = []
        for index, contour in enumerate(contours(recording)):
            if signature(contour) != signature(reference):
                continue
            dx = contour[0][1][0][0] - reference[0][1][0][0]
            if delta(contour, reference, dx) <= 1.1e-6:
                matches.append((index, dx))
        assert len(matches) == 1, ("Missing or ambiguous shared counter", matches)
        found.append(matches[0][0])
        offsets.append(matches[0][1])
    assert len(set(found)) == 2 and abs(offsets[0] - offsets[1]) <= 1e-6
    return tuple(found), offsets[0]


def paths(recording, steps=48):
    pen = PolygonPen(None, steps=steps)
    replayRecording(recording, pen)
    return [[(round(x * 64), round(y * 64)) for x, y in path] for path in pen.paths]


def topology(recording, body_indices=None):
    flattened = paths(recording)
    tree = filled_tree(flattened)
    assert len(tree.Childs) == 1, "Disconnected shaft, arch, or terminal"
    body = tree.Childs[0]
    assert all(h.IsHole and not h.Childs for h in body.Childs), "Nested enclosure"
    for hole in body.Childs:
        assert abs(pyclipper.Area(hole.Contour)) / 4096 > 1000, "Collapsed enclosure"
        left, bottom, right, top = bounds(hole.Contour)
        assert min(right - left, top - bottom) > 10, "Fragile enclosure"
    if body_indices is None:
        return len(body.Childs)
    # Arches change the exterior beside the shared counter. Check the actual
    # filled shoulder in every member instead of inferring it from congruence.
    shoulders = []
    for upper, index in ((True, body_indices[0]), (False, body_indices[1])):
        counter = flattened[index]
        left, _, right, _ = bounds(counter)
        own = [hole for hole in body.Childs
               if max(abs(a - b) for a, b in zip(bounds(counter), bounds(hole.Contour))) < 1 / 64]
        assert len(own) == 1, "Each body counter must remain intact"
        # Closed hooks and tails can put another white enclosure beside a
        # shoulder. Check all non-own boundaries and both opposing joins.
        boundaries = [body.Contour, *(hole.Contour for hole in body.Childs if hole is not own[0])]
        positions = [(.01 + .44*i/8) if upper else (1 - .01 - .44*i/8) for i in range(9)]
        shoulders.append(min(distance_to_outline((x, vertical_interval(counter, x)[1 if upper else 0]), boundary)
                             for boundary in boundaries
                             for x in (left + (right-left) * t for t in positions)))
    return len(body.Childs), min(shoulders)


class SharedSpineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.old_sources, cls.indices, cls.offsets, cls.metadata = {}, {}, {}, {}, {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            font = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            previous = Font.open(BEFORE / "fonts/QuintessentialSerif" / f"QuintessentialSerif-{style}.ufo")
            references = contours(outline(font, NAME))[1:3]
            for entry in ENTRIES:
                name = entry["glyphName"]
                recording = outline(font, name)
                cls.sources[weight, name] = (recording, font[name].width)
                cls.metadata[weight, name] = dict(font[name].lib["org.quintessential.construction"])
                indices, dx = counter_indices(recording, references)
                cls.indices[weight, name] = indices
                cls.offsets[weight, name] = dx
                if name in previous:
                    cls.old_sources[weight, name] = (outline(previous, name), previous[name].width)
        cls.donor = TTFont(DONORS / DONOR_FILES[False])
        cls.addClassCleanup(cls.donor.close)
        if COMPILED:
            cls.font = TTFont(OUTPUT / VARIABLE_FILES[False])
            cls.previous = TTFont(BEFORE / "resources/fonts/QuintessentialSerif" / VARIABLE_FILES[False])
            cls.addClassCleanup(cls.font.close)
            cls.addClassCleanup(cls.previous.close)

    def assert_optical_profile(self, optical, stix):
        self.assertGreaterEqual(optical["shoulderMin"], stix["bShoulderMin"] * .7)
        self.assertGreaterEqual(optical["shoulderMin"], stix["hairline"] * .6)
        self.assertGreaterEqual(optical["sharedNormalMin"], stix["stem"] * .58)
        self.assertLessEqual(optical["sharedNormalMax"], stix["stem"] * .9)
        self.assertLessEqual(optical["sharedNormalRatio"], 1.2)
        self.assertGreaterEqual(optical["shaftMergeRayMin"], optical["sharedNormalMin"] * .95)
        self.assertGreaterEqual(optical["sharedSamples"], 100)
        self.assertLess(optical["sharedMaxSlope"], .75)
        self.assertLess(optical["sharedMaxCurvature"], .1)

    def test_source_family_closure_and_localized_connection_preservation(self):
        self.assertEqual(len(ENTRIES), 396)
        self.assertEqual(sum(e["middleLegs"] for e in ENTRIES), 180)
        self.assertTrue(all(e["postures"] == ["Roman", "Italic"] for e in ENTRIES))
        for weight in (400, 700):
            preserved = 0
            for entry in ENTRIES:
                name = entry["glyphName"]
                with self.subTest(weight=weight, glyph=name):
                    self.assertEqual(self.indices[400, name], self.indices[700, name])
                    first, second = (self.sources[w, name][0] for w in (400, 700))
                    self.assertEqual(signature(first), signature(second))
                    if (weight, name) in self.old_sources:
                        current, width = self.sources[weight, name]
                        old, old_width = self.old_sources[weight, name]
                        self.assertEqual(width, old_width)
                        assert_preserved_connections(old, current, entry,
                                                     self.metadata[weight, name], tolerance=1.1e-6)
                        preserved += 1
            REPORT["sourcePreservation"].append({"weight": weight,
                "glyphsWithExactUnreviewedSegments": preserved})

    def test_every_source_weight_has_shared_counters_and_open_enclosures(self):
        for weight in WEIGHTS:
            exemplar = interpolated(self.sources[400, NAME][0], self.sources[700, NAME][0], weight)
            references = contours(exemplar)[1:3]
            optical = source_profile(exemplar)
            stix = stix_reference(self.donor, weight)
            self.assert_optical_profile(optical, stix)
            counts, maximum, shoulder_minimum = Counter(), 0, float("inf")
            for entry in ENTRIES:
                name = entry["glyphName"]
                with self.subTest(weight=weight, glyph=name):
                    recording = interpolated(self.sources[400, name][0], self.sources[700, name][0], weight)
                    indices, dx = counter_indices(recording, references)
                    self.assertEqual(indices, self.indices[400, name])
                    for index, reference in zip(indices, references):
                        maximum = max(maximum, delta(contours(recording)[index], reference, dx))
                    holes, shoulder = topology(recording, indices)
                    self.assertGreaterEqual(shoulder, max(stix["bShoulderMin"] * .7, stix["hairline"] * .6))
                    shoulder_minimum = min(shoulder_minimum, shoulder)
                    self.assertGreaterEqual(holes, 2)
                    counts[holes] += 1
                    if (400, name) in self.old_sources:
                        old = interpolated(self.old_sources[400, name][0], self.old_sources[700, name][0], weight)
                        self.assertEqual(holes, topology(old), "Changed arch or terminal enclosure")
            REPORT["weights"].append({"weight": weight, "sourceCounterMaximumDelta": maximum,
                                       "sourceGlyphs": len(ENTRIES), "sourceEnclosureCounts": dict(counts),
                                       "allMemberShoulderMinimum": shoulder_minimum,
                                       "inheritedOpticalProfile": optical, "stixReference": stix})

    def test_every_compiled_weight_keeps_counter_congruence_and_original_geometry(self):
        if not COMPILED:
            self.skipTest("Source-only run")
        for weight in WEIGHTS:
            current = self.font.getGlyphSet(location={"wght": weight})
            old_set = self.previous.getGlyphSet(location={"wght": weight})
            references = contours(outline(current, NAME))[1:3]
            optical = source_profile(outline(current, NAME))
            self.assert_optical_profile(optical, stix_reference(self.donor, weight))
            max_counter, preserved, counts = 0, 0, Counter()
            shoulder_minimum = float("inf")
            stix = stix_reference(self.donor, weight)
            for entry in ENTRIES:
                name = entry["glyphName"]
                with self.subTest(weight=weight, glyph=name):
                    recording = outline(current, name)
                    pieces = contours(recording)
                    indices = self.indices[400, name]
                    offsets = []
                    for index, reference in zip(indices, references):
                        dx = pieces[index][0][1][0][0] - reference[0][1][0][0]
                        offsets.append(dx)
                        error = delta(pieces[index], reference, dx)
                        self.assertLessEqual(error, 1 / 64, "Shared counter changed with its ending")
                        max_counter = max(max_counter, error)
                    self.assertLessEqual(abs(offsets[0] - offsets[1]), 1 / 64)
                    holes, shoulder = topology(recording, indices)
                    self.assertGreaterEqual(shoulder, max(stix["bShoulderMin"] * .7, stix["hairline"] * .6))
                    shoulder_minimum = min(shoulder_minimum, shoulder)
                    counts[holes] += 1
                    self.assertGreaterEqual(holes, 2)
                    if name in old_set:
                        old = outline(old_set, name)
                        self.assertEqual(current[name].width, old_set[name].width)
                        self.assertEqual(self.font["hmtx"][name], self.previous["hmtx"][name])
                        self.assertEqual(holes, topology(old), "Changed arch or terminal enclosure")
                        metadata = interpolate_connection_metadata(
                            self.metadata[400, name], self.metadata[700, name], weight)
                        # Compare the actual native segments outside the
                        # reviewed joins. Raw interpolation must remain exact
                        # before instance rounding can conceal IUP drift.
                        assert_preserved_connections(old, recording, entry, metadata,
                                                     tolerance=1 / 64)
                        preserved += 1
            REPORT["compiledPreservation"].append({"weight": weight, "glyphs": len(ENTRIES),
                "counterMaximumDelta": max_counter,
                "unreviewedSegmentsPreserved": True,
                "preservedGlyphs": preserved, "enclosureCounts": dict(counts),
                "allMemberShoulderMinimum": shoulder_minimum,
                "inheritedOpticalProfile": optical})


def main():
    global BEFORE, COMPILED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-only", action="store_true")
    parser.add_argument("--before", type=Path, default=BEFORE)
    parser.add_argument("--report", type=Path)
    args, rest = parser.parse_known_args()
    BEFORE, COMPILED = args.before.resolve(), not args.sources_only
    result = unittest.main(argv=[__file__, *rest], exit=False).result
    if result.wasSuccessful() and args.report:
        REPORT["before"] = str(BEFORE.relative_to(ROOT)).replace("\\", "/")
        REPORT["compiled"] = COMPILED
        REPORT["selection"] = "An interior spine in the independent allocation's structural parts"
        REPORT["opticalInheritance"] = "Every counter pair is congruent to the independently measured emblem. Its full ray profile separately labels native shaft merges, which are specific to the emblem exterior. Both opposing shoulders in every member are measured against all non-own filled boundaries, including terminal enclosures."
        inputs = [ROOT / "resources/quintessential-latin-allocation.json"]
        for style in ("Regular", "Bold"):
            folder = SOURCES / f"QuintessentialSerif-{style}.ufo/glyphs"
            filenames = plistlib.loads((folder / "contents.plist").read_bytes())
            inputs.extend(folder / filenames[e["glyphName"]] for e in ENTRIES)
        if COMPILED:
            inputs.append(OUTPUT / VARIABLE_FILES[False])
        REPORT["inputSha256"] = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(REPORT, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()

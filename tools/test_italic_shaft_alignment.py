"""Check the visible axis across each assembled Italic stem and arm shaft.

Measurements isolate each base construction's independent shaft contour. This
excludes overlapping companion contours and samples straight donor shafts
outside the splice, so a smooth connector alone cannot conceal a change of
slope between halves. Descendants must retain the corrected shaft exactly.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import readGlyphFromString
import pyclipper
from ufoLib2 import Font

from quintessential_font import OUTPUT, ROOT, SOURCES
from test_quintessential_font import PolygonPen


DIRECT_TARGETS = (
    "uF2A02", "uF2A03", "uF2A04", "uF2A05", "uF2A07",
    "uF2A0A", "uF2A0C", "uF2A0D", "uF2A0E", "uF2A0F",
    "uF2A10", "uF2A11", "uF2A12", "uF2A13", "uF2A14",
)
# These are actual retained shaft dependencies, checked by marking the outer
# shaft in each of the three arch recipes and comparing final recordings.
# A repeated arch call whose output is discarded would not enter this set.
ARCH_SHAFT_BASES = {}
for _base, _singles, _left, _double in (
    ("uF2A16", (0xF2A46, 0xF2A5E, 0xF2B4D, 0xF2B41), 0xF2B5E, 0xF2CA2),
    ("uF2A1A", (0xF2A4A, 0xF2A62, 0xF2B51, 0xF2B45), 0xF2B6A, 0xF2CAE),
    ("uF2A1E", (0xF2A4E, 0xF2A66, 0xF2B55, 0xF2B49), 0xF2B76, 0xF2CBA),
):
    ARCH_SHAFT_BASES[_base] = _base
    for _code in (*_singles, *range(_left, _left + 6), *range(_double, _double + 6)):
        for _suffix in ("", ".middle"):
            ARCH_SHAFT_BASES[f"u{_code:X}{_suffix}"] = _base
    for _code in range(_double, _double + 6):
        for _suffix in (".middleLeft", ".middleRight"):
            ARCH_SHAFT_BASES[f"u{_code:X}{_suffix}"] = _base
ARCH_BASE_TARGETS = ("uF2A16", "uF2A1A", "uF2A1E")
BASE_TARGETS = (*DIRECT_TARGETS, *ARCH_BASE_TARGETS)
TARGETS = (*DIRECT_TARGETS, *ARCH_SHAFT_BASES)
assert len(TARGETS) == len(set(TARGETS)) == 150
WEIGHTS = (400, 500, 550, 600, 700)
VARIABLE = "QuintessentialSerif-Italic-Variable"
MAX_ANGLE_DIFFERENCE = 0.15
MAX_JOIN_DEVIATION = 0.3
SOURCE_DIRECTORY = SOURCES
FONT_DIRECTORY = OUTPUT
MEASUREMENTS = []
PAIR_MEASUREMENTS = []
COMPILED_MEASUREMENTS = []
DEPENDENCY_AUDIT = {}


def lower_cut(name):
    # Turned-r's rising baseline finish needs the higher cut. The two g
    # terminals are attached above their complete descending hook.
    return 220 if name == "uF2A0C" else 50 if name in ("uF2A13", "uF2A14", *ARCH_BASE_TARGETS) else 150


def path_crossings(path, y):
    crossings = []
    for first, second in zip(path, (*path[1:], path[0])):
        if (first[1] <= y < second[1]) or (second[1] <= y < first[1]):
            t = (y - first[1]) / (second[1] - first[1])
            crossings.append(first[0] + t * (second[0] - first[0]))
    return sorted(crossings)


def shaft_center(path, y):
    crossings = path_crossings(path, y)
    if len(crossings) != 2:
        raise AssertionError(f"Expected two shaft crossings at {y}: {crossings}")
    return sum(crossings) / 2


def measure(glyph_set, name):
    pen = PolygonPen(glyph_set, steps=192)
    glyph_set[name].draw(pen)
    path = pen.paths[1 if name in ("uF2A16", "uF2A1A") else 0]
    cut = lower_cut(name)
    upper_cut = 150 if name in ARCH_BASE_TARGETS else 300
    # 330 is below the shortest upper donor's first curved head (r at 333
    # in Bold). A long sample to y440 incorrectly includes the Bold hook.
    upper_ys = (upper_cut + 10.37, upper_cut + 30.37)
    # Both boundaries are straight immediately below every defined cut;
    # lower samples would include the dotless-i foot or turned-r sweep.
    lower_ys = (cut - 4.63, cut - 0.63)
    upper_xs = [shaft_center(path, y) for y in upper_ys]
    lower_xs = [shaft_center(path, y) for y in lower_ys]
    upper_slope = (upper_xs[1] - upper_xs[0]) / (upper_ys[1] - upper_ys[0])
    lower_slope = (lower_xs[1] - lower_xs[0]) / (lower_ys[1] - lower_ys[0])
    upper_angle, lower_angle = [math.degrees(math.atan(slope))
                                for slope in (upper_slope, lower_slope)]
    deviations = []
    for step in range(1, 31):
        y = cut + (upper_cut - cut) * step / 31
        expected = lower_xs[1] + lower_slope * (y - lower_ys[1])
        deviations.append(abs(shaft_center(path, y) - expected))
    return {"glyphName": name, "upperAngleDegrees": upper_angle,
            "lowerAngleDegrees": lower_angle,
            "angleDifferenceDegrees": abs(upper_angle - lower_angle),
            "maximumJoinDeviationUnits": max(deviations)}


def recording(glyph_set, name):
    pen = RecordingPen()
    glyph_set[name].draw(pen)
    return pen.value


class ItalicShaftAlignmentTests(unittest.TestCase):
    def test_descending_arch_dependency_inventory_is_exhaustive(self):
        import import_stix_foundation as foundation
        from fontTools.varLib.instancer import instantiateVariableFont
        from quintessential_font import glyphs_for_posture
        from stix_middle_legs import middle_legs_outline

        original = foundation.arch_outline
        calls = []
        arch_codes = (0xF2A16, 0xF2A1A, 0xF2A1E)

        def tracked(donor, code):
            if code in arch_codes:
                calls.append(code)
            return original(donor, code)

        def marked(donor, code):
            result, metadata = original(donor, code)
            if code in arch_codes:
                contours = list(foundation.native_recording_contours(result))
                index = 0 if code == 0xF2A1E else 1
                contours[index] = [(op, tuple((x + 0.03125, y) for x, y in points))
                                   for op, points in contours[index]]
                result = sum(contours, [])
            return result, metadata

        def generate(donor, spec):
            if spec.stemless:
                from stix_stemless import stemless_outline
                return stemless_outline(donor, spec.glyph_id)[0]
            if spec.middle_legs:
                return middle_legs_outline(donor, spec.recipe_code_point, spec.middle_leg_extensions)[0]
            return foundation.legacy_outline(donor, spec, True)[0]

        retained, discarded = {}, []
        specs = glyphs_for_posture(True)
        with TTFont(foundation.donor_paths_from_manifest()["Italic"]) as variable:
            donor = instantiateVariableFont(variable, {"wght": 400}, inplace=False)
            for spec in specs:
                calls.clear()
                with patch.object(foundation, "arch_outline", tracked):
                    before = generate(donor, spec)
                if not calls:
                    continue
                used = set(calls)
                self.assertEqual(len(used), 1, spec.glyph_name)
                with patch.object(foundation, "arch_outline", marked):
                    after = generate(donor, spec)
                if before != after:
                    retained[spec.glyph_name] = f"u{next(iter(used)):X}"
                else:
                    discarded.append(spec.glyph_name)
            donor.close()
        self.assertEqual(retained, ARCH_SHAFT_BASES)
        self.assertEqual(discarded, [])
        inventory = json.loads((ROOT / "resources/italic-shaft-targets.json").read_text(encoding="utf-8"))["targets"]
        self.assertEqual({row["glyphName"] for row in inventory}, set(TARGETS))
        inputs = [Path(__file__), ROOT / "tools/import_stix_foundation.py", ROOT / "tools/quintessential_font.py",
                  ROOT / "resources/quintessential-latin-allocation.json", ROOT / "resources/italic-shaft-targets.json",
                  *sorted((ROOT / "tools").glob("stix_*.py"))]
        DEPENDENCY_AUDIT.update(currentItalicConstructions=len(specs), retainedShafts=len(retained),
                                discardedCalls=discarded,
                                sourceSha256={path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                              for path in inputs})

    def inspect(self, glyph_set, label):
        failures = []
        for name in BASE_TARGETS:
            result = {"artifact": label, **measure(glyph_set, name)}
            MEASUREMENTS.append(result)
            if (result["angleDifferenceDegrees"] > MAX_ANGLE_DIFFERENCE
                    or result["maximumJoinDeviationUnits"] > MAX_JOIN_DEVIATION):
                failures.append(f'{name}: upper {result["upperAngleDegrees"]:.4f}°, '
                                f'lower {result["lowerAngleDegrees"]:.4f}°, '
                                f'join {result["maximumJoinDeviationUnits"]:.4f} units')
        self.assertFalse(failures, label + "\n" + "\n".join(failures))

    def test_source_masters(self):
        for style in ("Italic", "BoldItalic"):
            with self.subTest(style=style):
                source = Font.open(SOURCE_DIRECTORY / f"QuintessentialSerif-{style}.ufo")
                self.inspect(source, f"source-{style}")

    def test_arch_descendants_retain_the_corrected_source_shaft(self):
        from font_geometry_helpers import outline
        from import_stix_foundation import native_recording_contours

        def relative(contour):
            origin = contour[0][1][0][0]
            return [(op, tuple((x - origin, y) for x, y in points)) for op, points in contour]

        def matches(first, second):
            return ([(op, len(points)) for op, points in first] == [(op, len(points)) for op, points in second]
                    and all(abs(a - b) <= 0.000003
                            for (_, first_points), (_, second_points) in zip(first, second)
                            for first_point, second_point in zip(first_points, second_points)
                            for a, b in zip(first_point, second_point)))

        for style in ("Italic", "BoldItalic"):
            with Font.open(SOURCE_DIRECTORY / f"QuintessentialSerif-{style}.ufo") as source:
                references = {name: relative(list(native_recording_contours(outline(source, name)))[
                    1 if name in ("uF2A16", "uF2A1A") else 0]) for name in ARCH_BASE_TARGETS}
                for name, base in ARCH_SHAFT_BASES.items():
                    contours = [relative(contour) for contour in native_recording_contours(outline(source, name))]
                    with self.subTest(style=style, glyph=name, base=base):
                        self.assertTrue(any(matches(references[base], contour) for contour in contours),
                                        "The inherited shaft differs beyond a rigid horizontal translation")

    def test_only_the_shaft_changes_inside_each_affected_source_glyph(self):
        from font_geometry_helpers import outline
        from import_stix_foundation import native_recording_contours, native_region
        import italic_shaft_revision

        before = italic_shaft_revision.load_baseline()
        for style in ("Italic", "BoldItalic"):
            old = Font()
            for path, captured in before["sourceGlyphs"].items():
                if f"QuintessentialSerif-{style}.ufo/" in path:
                    glyph = old.newGlyph(captured["name"])
                    readGlyphFromString(base64.b64decode(captured["base64"]), glyph, glyph.getPointPen())
            with Font.open(SOURCE_DIRECTORY / f"QuintessentialSerif-{style}.ufo") as source:
                for name in TARGETS:
                    old_contours = list(native_recording_contours(outline(old, name)))
                    new_contours = list(native_recording_contours(outline(source, name)))
                    with self.subTest(style=style, glyph=name):
                        self.assertEqual(len(old_contours), len(new_contours))
                        changed = [index for index, (first, second) in enumerate(zip(old_contours, new_contours))
                                   if first != second]
                        self.assertEqual(len(changed), 1, "A companion arm, arch, bowl, or spine contour changed")
                        index = changed[0]
                        base = ARCH_SHAFT_BASES.get(name, name)
                        cut = lower_cut(base)
                        old_lower = native_region(old_contours[index], cut, False)
                        new_lower = native_region(new_contours[index], cut, False)
                        offset = new_lower.start[0] - old_lower.start[0]
                        translated = old_lower.translated(offset)
                        self.assertEqual([(op, len(points)) for op, points in translated.operations],
                                         [(op, len(points)) for op, points in new_lower.operations])
                        maximum_delta = max(abs(a - b)
                            for (_, first_points), (_, second_points) in zip(translated.operations, new_lower.operations)
                            for first_point, second_point in zip(first_points, second_points)
                            for a, b in zip(first_point, second_point))
                        self.assertLessEqual(maximum_delta, 0.000003,
                                             "The native lower terminal changed beyond rigid horizontal translation")
                        if name in BASE_TARGETS:
                            old_pen, new_pen = PolygonPen(old, steps=192), PolygonPen(source, steps=192)
                            old[name].draw(old_pen)
                            source[name].draw(new_pen)
                            old_path, new_path = old_pen.paths[index], new_pen.paths[index]
                            upper_cut = 150 if name in ARCH_BASE_TARGETS else 300
                            shear = source[name].lib["org.quintessential.construction"]["upperShear"]
                            top = min(max(y for _, y in old_path), max(y for _, y in new_path))
                            for step in range(1, 41):
                                y = upper_cut + (top - upper_cut) * step / 41
                                previous = path_crossings(old_path, y)
                                current = path_crossings(new_path, y)
                                self.assertEqual(len(previous), len(current), (name, y))
                                for first, second in zip(previous, current):
                                    self.assertLessEqual(abs(second - first - shear * (y - upper_cut)), 0.003,
                                        (name, y, "Upper width or shape changed beyond the small documented shear"))

    def test_variable_all_sampled_weights(self):
        with TTFont(FONT_DIRECTORY / f"{VARIABLE}.ttf") as font:
            for weight in WEIGHTS:
                with self.subTest(weight=weight):
                    self.inspect_compiled(font.getGlyphSet(location={"wght": weight}), weight, f"variable-{weight}")

    def test_static_endpoints(self):
        for style in ("Italic", "BoldItalic"):
            with self.subTest(style=style), TTFont(FONT_DIRECTORY / f"QuintessentialSerif-{style}.otf") as font:
                self.inspect_compiled(font.getGlyphSet(), 400 if style == "Italic" else 700, f"static-{style}")

    @classmethod
    def interpolated_sources(cls, weight):
        from font_geometry_helpers import outline, polygons_from_recording
        from test_additions_font import interpolate_recordings, interpolation_factor
        if not hasattr(cls, "source_recordings"):
            with Font.open(SOURCE_DIRECTORY / "QuintessentialSerif-Italic.ufo") as light, \
                    Font.open(SOURCE_DIRECTORY / "QuintessentialSerif-BoldItalic.ufo") as bold:
                cls.source_recordings = {name: (outline(light, name), outline(bold, name)) for name in TARGETS}
        factor = interpolation_factor(weight)
        return {name: polygons_from_recording(interpolate_recordings(*values, factor))
                for name, values in cls.source_recordings.items()}

    def inspect_compiled(self, glyph_set, weight, label):
        """Require all compiled ink to remain within 0.75 units of the source.

        Integer rounding makes a tangent measured across a four-unit terminal
        cut unstable. Comparing both complete filled outlines to independently
        interpolated masters checks the actual visible result without treating
        those tiny quantized segments as new design angles.
        """
        from test_quintessential_font import polygons

        def united(paths):
            clipper = pyclipper.Pyclipper()
            clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
            return clipper.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

        def outside_tolerance(first, second):
            offset = pyclipper.PyclipperOffset()
            offset.AddPaths(united(second), pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
            expanded = offset.Execute(0.75 * 64)
            clipper = pyclipper.Pyclipper()
            clipper.AddPaths(first, pyclipper.PT_SUBJECT, True)
            clipper.AddPaths(expanded, pyclipper.PT_CLIP, True)
            remaining = clipper.Execute(pyclipper.CT_DIFFERENCE, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
            return sum(abs(pyclipper.Area(path)) for path in remaining) / 64**2

        failures = []
        for name, expected in self.interpolated_sources(weight).items():
            actual = polygons(glyph_set, name)
            excess = max(outside_tolerance(actual, expected), outside_tolerance(expected, actual))
            if excess:
                failures.append((name, excess))
        COMPILED_MEASUREMENTS.append({"artifact": label, "glyphCount": len(TARGETS),
                                      "outlineToleranceUnits": 0.75, "failures": failures})
        self.assertEqual(len(failures), 0, (label, failures[:20]))

    def test_webfont_outlines_match_desktop_outlines(self):
        stems = (VARIABLE, "QuintessentialSerif-Italic", "QuintessentialSerif-BoldItalic")
        for stem in stems:
            suffix = "ttf" if stem == VARIABLE else "otf"
            with TTFont(FONT_DIRECTORY / f"{stem}.{suffix}") as desktop, \
                    TTFont(FONT_DIRECTORY / f"{stem}.woff2") as web:
                for weight in WEIGHTS if stem == VARIABLE else (None,):
                    location = {"wght": weight} if weight is not None else None
                    desktop_set = desktop.getGlyphSet(location=location)
                    web_set = web.getGlyphSet(location=location)
                    for name in TARGETS:
                        with self.subTest(font=stem, weight=weight, glyph=name):
                            self.assertEqual(recording(desktop_set, name), recording(web_set, name))

    def assert_pairs_clear(self, shapes, widths, pairs, context):
        from test_quintessential_font import outlines_overlap, pair_projections, projections_are_disjoint
        projections = {name: pair_projections(paths) for name, paths in shapes.items()}
        selected = {(target, name) for target in TARGETS for name in shapes}
        selected.update((name, target) for target in TARGETS for name in shapes)
        exact, collisions = 0, []
        for left, right in sorted(selected):
            advance = widths[left] + pairs.get((left, right), 0)
            offset = round(advance * 64)
            if projections_are_disjoint(projections[left], projections[right], offset):
                continue
            exact += 1
            if outlines_overlap(shapes[left], shapes[right], advance):
                collisions.append((left, right, pairs.get((left, right), 0)))
        PAIR_MEASUREMENTS.append({"artifact": context, "orderedPairs": len(selected),
                                  "projectionSeparationCertificates": len(selected) - exact,
                                  "filledOutlineFallbacks": exact, "collisions": collisions})
        self.assertEqual(len(collisions), 0, (context, len(collisions), collisions[:20]))
        print(f"shaft pairs {context}: {len(selected)} ordered pairs; {exact} filled-outline fallbacks; no collisions", flush=True)

    def test_source_target_pairs_clear_at_all_five_weights(self):
        from font_geometry_helpers import outline, polygons_from_recording
        from test_additions_font import interpolate_recordings, interpolation_factor
        allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
        names = [entry["glyphName"] for entry in allocation["entries"]]
        with Font.open(SOURCE_DIRECTORY / "QuintessentialSerif-Italic.ufo") as light, \
                Font.open(SOURCE_DIRECTORY / "QuintessentialSerif-BoldItalic.ufo") as bold:
            recordings = {name: (outline(light, name), outline(bold, name)) for name in names}
            for weight in WEIGHTS:
                factor = interpolation_factor(weight)
                shapes = {name: polygons_from_recording(interpolate_recordings(*recordings[name], factor)) for name in names}
                widths = {name: light[name].width + factor * (bold[name].width - light[name].width) for name in names}
                pairs = {pair: light.kerning.get(pair, 0) + factor * (bold.kerning.get(pair, 0) - light.kerning.get(pair, 0))
                         for pair in light.kerning.keys() | bold.kerning.keys()}
                with self.subTest(weight=weight):
                    self.assert_pairs_clear(shapes, widths, pairs, f"source-{weight}")

    def test_compiled_target_pairs_clear_at_all_five_weights(self):
        from test_quintessential_font import polygons
        from test_stemless_terminals import target_pair_values
        allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
        names = [entry["glyphName"] for entry in allocation["entries"]]
        with TTFont(FONT_DIRECTORY / f"{VARIABLE}.ttf") as font:
            for weight in WEIGHTS:
                glyphs = font.getGlyphSet(location={"wght": weight})
                shapes = {name: polygons(glyphs, name) for name in names}
                with self.subTest(weight=weight):
                    self.assert_pairs_clear(shapes, {name: glyphs[name].width for name in names},
                                            target_pair_values(font, glyphs.location, set(TARGETS)),
                                            f"compiled-{weight}")


def main():
    global SOURCE_DIRECTORY, FONT_DIRECTORY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=SOURCES)
    parser.add_argument("--fonts", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path)
    args, remaining = parser.parse_known_args()
    SOURCE_DIRECTORY, FONT_DIRECTORY = args.sources, args.fonts
    result = unittest.main(argv=[__file__, *remaining], exit=False).result
    if args.report:
        font = FONT_DIRECTORY / f"{VARIABLE}.ttf"
        allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
        code_points = {entry["glyphName"]: f'U+{entry["codePoint"]:X}' for entry in allocation["entries"]}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({
            "passed": result.wasSuccessful(), "testsRun": result.testsRun,
            "variableFontSha256": hashlib.sha256(font.read_bytes()).hexdigest(),
            "maximumAngleDifferenceDegrees": MAX_ANGLE_DIFFERENCE,
            "maximumJoinDeviationUnits": MAX_JOIN_DEVIATION,
            "targets": [{"glyphName": name, "codePoint": code_points[name]} for name in TARGETS],
            "measurements": MEASUREMENTS,
            "pairMeasurements": PAIR_MEASUREMENTS,
            "compiledMeasurements": COMPILED_MEASUREMENTS,
            "dependencyAudit": DEPENDENCY_AUDIT,
        }, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()

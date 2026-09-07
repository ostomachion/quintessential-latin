#!/usr/bin/env python3
"""Preserve the catalogue while widening only the two tails below hips."""
from __future__ import annotations

import argparse
import base64
import gzip
import json
from pathlib import Path
import plistlib
import unittest
import pyclipper

from fontTools.ttLib import TTFont
from ufoLib2 import Font

import hip_tail_revision as revision
from font_geometry_helpers import outline, polygons_from_recording
from test_stemless_terminals import (capture as capture_geometry, recorded_outlines,
    pairs_digest, target_pair_values, WEIGHTS, STYLES, digest)
from font_geometry_helpers import effective_pairs

ROOT = revision.ROOT
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
TARGET_IDS, TARGET_NAMES = revision.TARGET_IDS, revision.TARGET_NAMES


def capture(folder):
    result = capture_geometry(folder, TARGET_NAMES)
    result.update(revision="hip-wide-tail-1", glyphIds=sorted(TARGET_IDS), sourceGlyphs={}, tables={})
    for style in STYLES:
        directory = folder / "sources" / f"QuintessentialSerif-{style}.ufo"
        contents = plistlib.loads((directory / "glyphs/contents.plist").read_bytes())
        for name in TARGET_NAMES:
            path = directory / "glyphs" / contents[name]
            relative = "fonts/QuintessentialSerif/" + path.relative_to(folder / "sources").as_posix()
            data = path.read_bytes()
            result["sourceGlyphs"][relative] = {"name": name, "sha256": revision.digest(data),
                                               "base64": base64.b64encode(data).decode()}
    for path in sorted((folder / "compiled").iterdir()):
        if path.suffix in (".ttf", ".otf", ".woff2"):
            result["tables"][path.name] = revision.normalized_tables(path)
    assert len(result["tables"]) == 12
    result = capture_pair_evidence(result, folder)
    result["instances"] = capture_instance_outlines(folder / "compiled")
    return result


def compiled_target_pairs(path, weight=None):
    from fontTools.misc.roundTools import otRound
    with TTFont(path) as font:
        if weight is not None:
            glyphs = font.getGlyphSet(location={"wght": weight})
            values = target_pair_values(font, glyphs.location, TARGET_NAMES)
        else:
            from test_quintessential_font import dflt_kern_lookups
            values = {}
            for lookup in dflt_kern_lookups(font):
                for wrapper in lookup.SubTable:
                    table = wrapper.ExtSubTable if lookup.LookupType == 9 else wrapper
                    assert table.Format == 1
                    for left, pair_set in zip(table.Coverage.glyphs, table.PairSet):
                        for record in pair_set.PairValueRecord:
                            right = record.SecondGlyph
                            if left in TARGET_NAMES or right in TARGET_NAMES:
                                assert record.Value2 is None
                                values[left, right] = values.get((left, right), 0) + getattr(record.Value1, "XAdvance", 0)
        return {f"{left}/{right}": otRound(value) for (left, right), value in values.items()}


def capture_pair_evidence(result, folder):
    result.update(kerning={}, targetPairs={}, nonTargetPairs={})
    for style in STYLES:
        path = folder / "sources" / f"QuintessentialSerif-{style}.ufo/kerning.plist"
        data = path.read_bytes()
        relative = "fonts/QuintessentialSerif/" + path.relative_to(folder / "sources").as_posix()
        pairs = revision.target_source_pairs(data)
        result["kerning"][relative] = {"sha256": revision.digest(data), "pairs": pairs}
        result["targetPairs"][f"source-{style}"] = pairs
    for face in result["compiled"]:
        filename, weight = face_location(face)
        result["targetPairs"][face] = compiled_target_pairs(folder / "compiled" / filename, weight)
        if weight is not None:
            with TTFont(folder / "compiled" / filename) as font:
                result["nonTargetPairs"][face] = non_target_pair_digest(font, font.getGlyphSet(location={"wght": weight}).location)
    return result


def capture_instance_outlines(folder):
    from fontTools.varLib.instancer import instantiateVariableFont
    cache = ROOT / ".tmp/hip-tail-current-instances.json"
    hashes = {path.name: revision.digest(path.read_bytes()) for path in folder.glob("*Variable.ttf")}
    if folder == OUTPUT and cache.exists():
        cached = json.loads(cache.read_text())
        if cached["fonts"] == hashes:
            return cached["outlines"]
    result = {}
    for italic in (False, True):
        for weight in WEIGHTS:
            face = f"{'Italic' if italic else 'Roman'}-{weight}"
            filename, _ = face_location(face)
            with TTFont(folder / filename) as font:
                instance = instantiateVariableFont(font, {"wght": weight}, inplace=True)
                result[face] = recorded_outlines(instance.getGlyphSet(), TARGET_NAMES)
            print(f"hip-tail instance evidence {face}", flush=True)
    if folder == OUTPUT:
        cache.write_text(json.dumps({"fonts": hashes, "outlines": result}, sort_keys=True), encoding="utf-8")
    return result


def non_target_pair_digest(font, location):
    """Resolve every non-target positioning record, including its variation."""
    from fontTools.varLib.varStore import VarStoreInstancer
    from test_quintessential_font import dflt_kern_lookups
    variation = VarStoreInstancer(font["GDEF"].table.VarStore, font["fvar"].axes, location)
    values = {}
    for lookup in dflt_kern_lookups(font):
        assert lookup.LookupType in (2, 9)
        for wrapper in lookup.SubTable:
            table = wrapper.ExtSubTable if lookup.LookupType == 9 else wrapper
            assert table.Format == 1
            for left, pair_set in zip(table.Coverage.glyphs, table.PairSet):
                if left in TARGET_NAMES:
                    continue
                for record in pair_set.PairValueRecord:
                    right = record.SecondGlyph
                    if right in TARGET_NAMES:
                        continue
                    assert record.Value2 is None or not any(vars(record.Value2).values())
                    value = record.Value1
                    assert set(vars(value)) <= {"XAdvance", "XAdvDevice"}
                    amount = getattr(value, "XAdvance", 0)
                    device = getattr(value, "XAdvDevice", None)
                    if device:
                        assert device.DeltaFormat == 0x8000
                        amount += variation[(device.StartSize << 16) | device.EndSize]
                    values[left, right] = values.get((left, right), 0) + amount
    return digest(sorted([left, right, value] for (left, right), value in values.items() if value))


def current_revision():
    before = revision.load_baseline()
    result = {"schemaVersion": 1, "revision": "hip-wide-tail-1", "glyphIds": sorted(TARGET_IDS),
              "baselineSha256": revision.BASELINE_SHA256, "sourceGlyphs": {}, "tables": {}, "geometry": {}, "kerning": {}}
    for relative in before["sourceGlyphs"]:
        result["sourceGlyphs"][relative] = revision.digest((ROOT / relative).read_bytes())
    for relative in before["kerning"]:
        result["kerning"][relative] = revision.digest((ROOT / relative).read_bytes())
    for filename, old in before["tables"].items():
        actual = revision.normalized_tables(OUTPUT / filename)
        assert set(actual) == set(old)
        result["tables"][filename] = {tag: value for tag, value in actual.items() if value != old[tag]}
        assert result["tables"][filename] and set(result["tables"][filename]) <= revision.REVISED_TABLES, (filename, result["tables"][filename])
        revision.verify_aggregate_metrics(OUTPUT / filename)
    for style in STYLES:
        with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source:
            records = recorded_outlines(source, TARGET_NAMES)
            result["geometry"][f"source-{style}"] = {name: {"outline": records[name]} for name in TARGET_NAMES}
            result["geometry"][f"source-{style}"]["pairs"] = revision.target_source_pairs((SOURCES / f"QuintessentialSerif-{style}.ufo/kerning.plist").read_bytes())
    for face in before["compiled"]:
        filename, weight = face_location(face)
        with TTFont(OUTPUT / filename) as font:
            glyphs = font.getGlyphSet(location={"wght": weight}) if weight is not None else font.getGlyphSet()
            records = recorded_outlines(glyphs, TARGET_NAMES)
            result["geometry"][face] = {name: {"outline": records[name], "metrics": font["hmtx"][name]} for name in TARGET_NAMES}
        result["geometry"][face]["pairs"] = compiled_target_pairs(OUTPUT / filename, weight)
    result["instances"] = capture_instance_outlines(OUTPUT)
    result["targetPairChanges"] = {style: sum(value != before["targetPairs"][f"source-{style}"][pair]
        for pair, value in result["geometry"][f"source-{style}"]["pairs"].items()) for style in STYLES}
    return result


def face_location(face):
    if "-" in face:
        posture, weight = face.split("-")
        return ("QuintessentialSerif-Italic-Variable.ttf" if posture == "Italic" else "QuintessentialSerif-Variable.ttf"), int(weight)
    return f"QuintessentialSerif-{face}.otf", None


class HipTailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = revision.load_baseline()
        cls.entries = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text())["entries"]
        assert {row["glyphName"] for row in cls.entries if row["glyphId"] in TARGET_IDS} == TARGET_NAMES

    def assert_outlines_preserved(self, actual, before, face):
        self.assertEqual(set(actual), set(before), face)
        for name, old in before.items():
            self.assertEqual(actual[name][0], old[0], (face, name, "Advance changed"))
            if name not in TARGET_NAMES:
                self.assertEqual(actual[name], old, (face, name, "Unrelated outline changed"))
            else:
                self.assertNotEqual(actual[name][1], old[1], (face, name, "Tail revision absent"))

    def test_only_eight_target_glyph_sources_and_target_pairs_change_with_advances_and_mappings_fixed(self):
        self.assertEqual(self.entries, self.before["entries"])
        allowed = {Path(path).relative_to("fonts/QuintessentialSerif").as_posix() for path in self.before["sourceGlyphs"]}
        allowed.update(Path(path).relative_to("fonts/QuintessentialSerif").as_posix() for path in self.before["kerning"])
        actual_files = {path.relative_to(SOURCES).as_posix() for path in SOURCES.rglob("*") if path.is_file()}
        self.assertEqual(actual_files, set(self.before["sourceFiles"]))
        for relative, expected in self.before["sourceFiles"].items():
            if relative not in allowed:
                self.assertEqual(revision.digest((SOURCES / relative).read_bytes()), expected, relative)
        for style in STYLES:
            with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source:
                old = self.before["sources"][style]
                names = source.lib["public.glyphOrder"]
                self.assertEqual(names, old["order"])
                self.assertEqual({name: source[name].unicodes for name in names}, old["cmap"])
                restored = dict(source.kerning)
                restored.update({tuple(pair.split("/")): value for pair, value in self.before["targetPairs"][f"source-{style}"].items()})
                self.assertEqual(pairs_digest({pair: (0, 0, value, 0, 0, 0, 0, 0) for pair, value in restored.items()}), old["pairs"])
                self.assert_outlines_preserved(recorded_outlines(source, names), old["outlines"], style)
            path = f"fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/kerning.plist"
            revision.restore_kerning_bytes((ROOT / path).read_bytes(), self.before["kerning"][path])

    def test_non_target_compiled_outlines_pairs_and_all_advances_order_and_cmap_are_preserved(self):
        for face, old in self.before["compiled"].items():
            filename, weight = face_location(face)
            with TTFont(OUTPUT / filename) as font:
                names = font.getGlyphOrder()
                self.assertEqual(names, old["order"], face)
                self.assertEqual(font.getBestCmap(), {0x20: "space", **{row["codePoint"]: row["glyphName"] for row in self.entries}})
                glyphs = font.getGlyphSet(location={"wght": weight}) if weight is not None else font.getGlyphSet()
                self.assert_outlines_preserved(recorded_outlines(glyphs, names), old["outlines"], face)
                for name, metrics in old["hmtx"].items():
                    self.assertEqual(font["hmtx"][name][0], metrics[0], (face, name, "Advance"))
                    if name not in TARGET_NAMES:
                        self.assertEqual(list(font["hmtx"][name]), metrics, (face, name, "Unrelated metrics"))
                if weight is None:
                    restored = dict(effective_pairs(font))
                    for pair in list(restored):
                        if any(name in TARGET_NAMES for name in pair):
                            del restored[pair]
                    restored.update({tuple(pair.split("/")): (0, 0, value, 0, 0, 0, 0, 0) for pair, value in self.before["targetPairs"][face].items()})
                    self.assertEqual(pairs_digest(restored), old["pairs"], face)
                else:
                    # Source pair matrices were restored byte-for-byte above;
                    # independently compare all non-target variable records and
                    # their variation deltas against the pinned old table data.
                    self.assertEqual(non_target_pair_digest(font, glyphs.location), self.before["nonTargetPairs"][face], face)
            print(f"hip-tail preservation {face}: {len(names) - 2} unchanged outlines; all advances/mappings and unrelated pairs", flush=True)

    def assert_pairs_clear(self, shapes, widths, pairs, context):
        from test_quintessential_font import outlines_overlap
        bounds = {name: (min(x for path in paths for x, _ in path), max(x for path in paths for x, _ in path)) for name, paths in shapes.items()}
        selected = {(target, name) for target in TARGET_NAMES for name in shapes}
        selected.update((name, target) for target in TARGET_NAMES for name in shapes)
        exact, collisions = 0, []
        for left, right in sorted(selected):
            advance = widths[left] + pairs.get((left, right), 0)
            offset = round(advance * 64)
            if bounds[left][1] < bounds[right][0] + offset or bounds[right][1] + offset < bounds[left][0]:
                continue
            exact += 1
            if outlines_overlap(shapes[left], shapes[right], advance):
                collisions.append((left, right, pairs.get((left, right), 0)))
        self.assertEqual(len(collisions), 0, (context, len(collisions), collisions[:20]))
        print(f"hip-tail pairs {context}: {len(selected)} ordered pairs; {exact} exact filled intersections", flush=True)

    def test_compiled_target_pairs_clear_at_all_five_weights(self):
        from test_quintessential_font import polygons
        for italic in (False, True):
            for weight in WEIGHTS:
                filename, _ = face_location(f"{'Italic' if italic else 'Roman'}-{weight}")
                with TTFont(OUTPUT / filename) as font:
                    glyphs = font.getGlyphSet(location={"wght": weight})
                    names = [row["glyphName"] for row in self.entries if ("Italic" if italic else "Roman") in row["postures"]]
                    shapes = {name: polygons(glyphs, name) for name in names}
                    self.assert_pairs_clear(shapes, {name: glyphs[name].width for name in names},
                                            target_pair_values(font, glyphs.location, TARGET_NAMES), (italic, weight, "compiled"))

    def test_source_target_pairs_clear_at_all_five_weights(self):
        from test_additions_font import interpolate_recordings, interpolation_factor
        for italic in (False, True):
            first, second = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
            names = [row["glyphName"] for row in self.entries if ("Italic" if italic else "Roman") in row["postures"]]
            with Font.open(SOURCES / f"QuintessentialSerif-{first}.ufo") as light, Font.open(SOURCES / f"QuintessentialSerif-{second}.ufo") as bold:
                recordings = {name: (outline(light, name), outline(bold, name)) for name in names}
                for weight in WEIGHTS:
                    factor = interpolation_factor(weight)
                    shapes = {name: polygons_from_recording(interpolate_recordings(*recordings[name], factor)) for name in names}
                    widths = {name: light[name].width + factor * (bold[name].width - light[name].width) for name in names}
                    pairs = {pair: light.kerning.get(pair, 0) + factor * (bold.kerning.get(pair, 0) - light.kerning.get(pair, 0)) for pair in light.kerning.keys() | bold.kerning.keys()}
                    self.assert_pairs_clear(shapes, widths, pairs, (italic, weight, "source"))

    def test_revised_static_glyphs_match_variable_endpoints(self):
        from test_quintessential_font import polygons, symmetric_difference_area
        for style, (italic, weight) in STYLES.items():
            filename, _ = face_location(f"{'Italic' if italic else 'Roman'}-{weight}")
            with TTFont(OUTPUT / f"QuintessentialSerif-{style}.otf") as static, TTFont(OUTPUT / filename) as variable:
                first, second = static.getGlyphSet(), variable.getGlyphSet(location={"wght": weight})
                for name in TARGET_NAMES:
                    area = symmetric_difference_area(polygons(first, name, steps=384, scale=65536),
                        polygons(second, name, steps=384, scale=65536), scale=65536)
                    self.assertLessEqual(area, 1.0, (style, name, "Static/variable ink difference", area))

    def test_complete_native_g_tail_and_unchanged_hip_and_head_curves_survive_compilation(self):
        from test_additions_font import (recording_quadratics, translated_quadratics,
                                         interpolate_points, interpolation_factor)
        from test_quintessential_font import (DONORS, DONOR_FILES, instantiated,
                                              quadratic_segments, assert_contains_quadratics)
        regions = {}
        for style, (italic, weight) in STYLES.items():
            with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source, instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                native = outline(donor.getGlyphSet(), donor.getBestCmap()[0x261])
                # The whole native lower g sweep wraps the first outer contour;
                # its bowl/counter quadratics are outside this explicit run.
                tail = recording_quadratics(native, (1, 2, 3, 4, 15 if italic else 14))
                self.assertGreaterEqual(len(tail), 14)
                for name in TARGET_NAMES:
                    metadata = source[name].lib["org.quintessential.construction"]
                    self.assertEqual(metadata["lowerDonorCodePoint"], 0x261, (style, name))
                    old = self.before["sources"][style]["targets"][name]["recording"]
                    # The native hip bottom is at y=-12; every former j-tail
                    # curve extends below -20. This captures the entire hip
                    # and upper-head curve runs independently of recipe indices.
                    if italic:
                        split = next(index for index, (op, _) in enumerate(old[1:], 1) if op == "moveTo")
                        upper = recording_quadratics(old[split:])
                        upper += [segment for segment in recording_quadratics(old[:split]) if min(y for _, y in segment) >= 300]
                    else:
                        upper = [segment for segment in recording_quadratics(old) if min(y for _, y in segment) >= -20]
                    self.assertGreaterEqual(len(upper), 10)
                    expected = upper + translated_quadratics(tail, metadata["lowerOffsetX"])
                    assert_contains_quadratics(self, quadratic_segments(source, name), expected, 1e-5, (style, name, "Source native tail and preserved hip/head"))
                    regions[italic, weight, name] = expected
        for italic in (False, True):
            filename, _ = face_location(f"{'Italic' if italic else 'Roman'}-400")
            with TTFont(OUTPUT / filename) as font:
                for weight in WEIGHTS:
                    glyphs = font.getGlyphSet(location={"wght": weight})
                    for name in TARGET_NAMES:
                        first, second = (regions[italic, endpoint, name] for endpoint in (400, 700))
                        self.assertEqual(len(first), len(second))
                        expected = [interpolate_points(a, b, interpolation_factor(weight)) for a, b in zip(first, second)]
                        assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected, .75,
                                                   (italic, weight, name, "Compiled native tail and preserved hip/head"))

    def test_targets_keep_simple_contours_one_connected_filled_shape_and_no_holes(self):
        from test_additions_font import interpolate_recordings, interpolation_factor
        def check(recording, before, context):
            paths, old_paths = polygons_from_recording(recording), polygons_from_recording(before)
            self.assertEqual(len(paths), len(old_paths), (context, "Contour count"))
            self.assertEqual([pyclipper.Area(path) > 0 for path in paths],
                             [pyclipper.Area(path) > 0 for path in old_paths], (context, "Winding"))
            for path in paths:
                simplified = pyclipper.SimplifyPolygon(path, pyclipper.PFT_NONZERO)
                self.assertEqual(len(simplified), 1, (context, "Self-intersection"))
                self.assertLessEqual(abs(abs(pyclipper.Area(path)) - abs(pyclipper.Area(simplified[0]))) / 4096, .1, (context, "Self-intersection area"))
            clipper = pyclipper.Pyclipper()
            clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
            tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
            self.assertEqual(len(tree.Childs), 1, (context, "Disconnected filled ink"))
            self.assertFalse(tree.Childs[0].Childs, (context, "Unexpected hole"))
        for italic in (False, True):
            first, second = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
            filename, _ = face_location(f"{'Italic' if italic else 'Roman'}-400")
            with Font.open(SOURCES / f"QuintessentialSerif-{first}.ufo") as light, Font.open(SOURCES / f"QuintessentialSerif-{second}.ufo") as bold, TTFont(OUTPUT / filename) as font:
                for weight in WEIGHTS:
                    glyphs = font.getGlyphSet(location={"wght": weight})
                    for name in TARGET_NAMES:
                        before = self.before["sources"][first]["targets"][name]["recording"]
                        check(interpolate_recordings(outline(light, name), outline(bold, name), interpolation_factor(weight)), before, (italic, weight, name, "source"))
                        check(outline(glyphs, name), before, (italic, weight, name, "compiled"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-from", type=Path)
    parser.add_argument("--seal", action="store_true")
    args, rest = parser.parse_known_args()
    if args.capture_from:
        assert not revision.BASELINE.exists(), "Refusing to overwrite frozen baseline"
        data = gzip.compress(json.dumps(capture(args.capture_from), sort_keys=True, separators=(",", ":")).encode(), mtime=0)
        revision.BASELINE.write_bytes(data)
        print(revision.digest(data))
    elif args.seal:
        assert not revision.REVISION.exists(), "Refusing to overwrite sealed revision"
        data = (json.dumps(current_revision(), sort_keys=True, indent=2) + "\n").encode()
        revision.REVISION.write_bytes(data)
        print(revision.digest(data))
    else:
        unittest.main(argv=[__file__, *rest])


if __name__ == "__main__":
    main()

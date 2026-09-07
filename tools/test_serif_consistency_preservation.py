"""Independent preservation and scope checks for the Roman u-head revision."""
from __future__ import annotations

import base64
import copy
import json
import plistlib
import unittest
import xml.etree.ElementTree as ET

from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.ttLib import TTFont
from ufoLib2 import Font
import pyclipper

from font_geometry_helpers import outline
import serif_consistency_revision as revision
from test_quintessential_font import polygons, symmetric_difference_area


def old_target_font(style):
    result = Font()
    for relative, captured in revision.load_baseline()["sourceGlyphs"].items():
        if f"QuintessentialSerif-{style}.ufo/" in relative:
            glyph = result.newGlyph(captured["name"])
            readGlyphFromString(base64.b64decode(captured["base64"]), glyph, glyph.getPointPen())
    return result


def semantic_metadata(data):
    element = ET.fromstring(data)
    lib = plistlib.loads(b'<plist version="1.0">' + ET.tostring(element.find("lib/dict")) + b"</plist>")
    fields = [(child.tag, child.attrib, child.text) for child in element if child.tag not in ("outline", "lib")]
    return element.attrib, fields, lib


def donor_references(value):
    if isinstance(value, dict):
        return {item for key, item in value.items() if key.endswith("CodePoint") and item in (0x265, 0x26F)} | set().union(
            *(donor_references(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(donor_references(item) for item in value))
    return set()


def old_head_positions(recording, deltas):
    """Identify the frozen donor's three straight cap edges, without recipes."""
    contours, segments = [], []
    first = previous = None
    for operation, points in recording:
        if operation == "moveTo":
            first = previous = points[0]
            segments = []
        elif operation == "closePath":
            if previous != first:
                segments.append((previous, "lineTo", (first,)))
            contours.append(segments)
        else:
            segments.append((previous, operation, points))
            previous = points[-1]
    found = []
    for contour in contours:
        for index, segment in enumerate(contour):
            selected = [contour[(index + offset) % len(contour)] for offset in range(3)]
            if all(operation == "lineTo" and len(points) == 1 for _, operation, points in selected):
                actual = [[round(points[0][axis] - start[axis], 6) for axis in (0, 1)]
                          for start, _, points in selected]
                if actual == deltas:
                    found.append([round(value, 6) for value in segment[0]])
    return sorted(found)


def outside_caps(paths, positions):
    masks = [[(round(x * 64), round(y * 64)) for x, y in (
        (entrance_x - 12, 350), (entrance_x + 230, 350),
        (entrance_x + 230, 490), (entrance_x - 12, 490))] for entrance_x, _ in positions]
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    clipper.AddPaths(masks, pyclipper.PT_CLIP, True)
    return clipper.Execute(pyclipper.CT_DIFFERENCE, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)


class SerifConsistencyPreservationTests(unittest.TestCase):
    def test_all_unrelated_source_bytes_including_italic_and_kerning_are_frozen(self):
        self.assertEqual(revision.verify_sources(), 656)

    def test_every_font_preserves_unrelated_ink_all_advances_mappings_and_positioning(self):
        self.assertEqual(revision.verify_compiled(), 12)

    def test_only_local_caps_and_two_explicit_provenance_keys_change(self):
        before = revision.load_baseline()
        rows = {row["glyphName"]: row for row in revision.target_rows()}
        for relative, captured in before["sourceGlyphs"].items():
            previous = semantic_metadata(base64.b64decode(captured["base64"]))
            actual = semantic_metadata((revision.ROOT / relative).read_bytes())
            actual = copy.deepcopy(actual)
            construction = actual[2]["org.quintessential.construction"]
            self.assertEqual(construction.pop("openArchHeadDonorCodePoint"), 0x75, relative)
            self.assertEqual(construction.pop("openArchHeadDesign"), "native-u-left-arm-right-stem-1", relative)
            self.assertEqual(actual, previous, (relative, "Non-outline GLIF data changed"))
        for style in revision.STYLES:
            old = old_target_font(style)
            with Font.open(revision.SOURCES / f"QuintessentialSerif-{style}.ufo") as current:
                for name, row in rows.items():
                    self.assertFalse(current[name].components, (style, name))
                    self.assertEqual(len(old[name].contours), len(current[name].contours), (style, name))
                    positions = row["headEntrancePositions"][style]
                    previous = outside_caps(polygons(old, name), positions)
                    actual = outside_caps(polygons(current, name), positions)
                    self.assertEqual(symmetric_difference_area(previous, actual), 0,
                                     (style, name, "Ink outside the local y350..490 caps changed"))
            print(f"serif source scope {style}: 328 exact local edits; all lower bodies and companions preserved", flush=True)

    def test_frozen_inventory_exhausts_visible_old_h_and_m_heads(self):
        inventory = json.loads(revision.TARGETS_FILE.read_bytes())
        rows = {row["glyphName"]: row for row in revision.target_rows()}
        for style in revision.STYLES:
            old = old_target_font(style)
            deltas = inventory["matcher"][f"{style.lower()}Deltas"]
            found = {}
            with Font.open(revision.SOURCES / f"QuintessentialSerif-{style}.ufo") as current:
                for name in current.lib["public.glyphOrder"]:
                    source = old if name in old else current
                    references = donor_references(source[name].lib)
                    if not references:
                        continue
                    positions = old_head_positions(outline(source, name), deltas)
                    if positions:
                        found[name] = positions
                        self.assertEqual(references, set(rows[name]["oldHeadDonorCodePoints"]), (style, name))
            expected = {name: sorted(row["headEntrancePositions"][style]) for name, row in rows.items()}
            self.assertEqual(found, expected, (style, "Visible old cap inventory differs"))
            self.assertEqual(sum(len(positions) for positions in found.values()), 483, style)

    def test_revised_caps_clear_every_catalogue_neighbor_in_both_directions_at_five_weights(self):
        from test_stemless_terminals import target_pair_values
        from test_quintessential_font import outlines_overlap

        entries = json.loads((revision.ROOT / "resources/quintessential-latin-allocation.json").read_text())["entries"]
        names = [row["glyphName"] for row in entries if "Roman" in row["postures"]]
        targets = revision.target_names()
        with TTFont(revision.OUTPUT / "QuintessentialSerif-Variable.ttf") as font:
            for weight in revision.WEIGHTS:
                glyphs = font.getGlyphSet(location={"wght": weight})
                pairs = target_pair_values(font, glyphs.location, targets)
                shapes = {name: polygons(glyphs, name) for name in names}
                bounds = {name: (min(x for path in paths for x, _ in path),
                                 max(x for path in paths for x, _ in path)) for name, paths in shapes.items()}
                widths = {name: glyphs[name].width for name in names}
                checked = exact = 0
                failures = []
                for left in names:
                    for right in (names if left in targets else sorted(targets)):
                        checked += 1
                        advance = widths[left] + pairs.get((left, right), 0)
                        offset = round(advance * 64)
                        if bounds[left][1] < bounds[right][0] + offset or bounds[right][1] + offset < bounds[left][0]:
                            continue
                        exact += 1
                        if outlines_overlap(shapes[left], shapes[right], advance):
                            failures.append((left, right, pairs.get((left, right), 0)))
                self.assertEqual(checked, (2 * len(names) - len(targets)) * len(targets))
                self.assertEqual(failures, [], (weight, "Filled cap collision", len(failures), failures[:20]))
                print(f"serif compiled pairs Roman-{weight}: {checked} ordered pairs; {exact} filled-intersection checks", flush=True)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate all 832 Roman catalogue glyphs and the native Italic subset."""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import unittest

import pyclipper
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen, replayRecording
from fontTools.misc.fixedTools import floatToFixedToFloat
from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import decompress
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.varLib.models import piecewiseLinearMap
from ufoLib2 import Font


ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
DONORS = ROOT / "resources/fonts/STIXTwoText"
VERSION = "0.220"

MAIN_SCRIPT_CMAP = {code: f"u{code:X}" for code in range(0xF2A00, 0xF2A81)}
SPECIAL_CMAP = {code: f"u{code:X}" for code in range(0xF2B00, 0xF2B04)}
DOUBLE_BOWL_CMAP = {code: f"u{code:X}" for code in range(0xF2B04, 0xF2B10)}
DOUBLE_BOWL_GLYPHS = tuple(DOUBLE_BOWL_CMAP.values())
ARCHED_DOUBLE_BOWL_CMAP = {code: f"u{code:X}" for code in range(0xF2B40, 0xF2B4C)}
ARCHED_DOUBLE_BOWL_GLYPHS = tuple(ARCHED_DOUBLE_BOWL_CMAP.values())
DOUBLE_BOWL_FAMILY_CMAP = {**DOUBLE_BOWL_CMAP, **ARCHED_DOUBLE_BOWL_CMAP}
DOUBLE_BOWL_FAMILY_GLYPHS = tuple(DOUBLE_BOWL_FAMILY_CMAP.values())
BOWLED_SPINE_CMAP = {code: f"u{code:X}" for code in range(0xF2B10, 0xF2B1C)}
ARCHED_BOWLED_SPINE_CMAP = {code: f"u{code:X}" for code in range(0xF2B4C, 0xF2B58)}
BOWLED_SPINE_FAMILY_CMAP = {**BOWLED_SPINE_CMAP, **ARCHED_BOWLED_SPINE_CMAP}
BOWLED_SPINE_FAMILY_GLYPHS = tuple(BOWLED_SPINE_FAMILY_CMAP.values())
OPPOSED_BOWL_CMAP = {code: f"u{code:X}" for code in range(0xF2B1C, 0xF2B40)}
ARCHED_OPPOSED_BOWL_CMAP = {code: f"u{code:X}" for code in range(0xF2B58, 0xF2BA0)}
ABBREVIATION_CMAP = dict(sorted({**DOUBLE_BOWL_FAMILY_CMAP, **BOWLED_SPINE_FAMILY_CMAP,
                               **OPPOSED_BOWL_CMAP, **ARCHED_OPPOSED_BOWL_CMAP}.items()))
EXTENSION_CMAP = {code: f"u{code:X}" for code in range(0xF2C00, 0xF2CC0)}
# These ranges describe historical recipe identities, not active encodings.
# The independent allocation document supplies current character assignments;
# font construction metadata is deliberately not imported into this suite.
LEGACY_RECIPE_CMAP = {**MAIN_SCRIPT_CMAP, **SPECIAL_CMAP, **ABBREVIATION_CMAP, **EXTENSION_CMAP}
LEGACY_POSTURE_CMAPS = {
    False: LEGACY_RECIPE_CMAP,
    True: {**MAIN_SCRIPT_CMAP, **SPECIAL_CMAP, **BOWLED_SPINE_FAMILY_CMAP},
}
ALLOCATION = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
ALLOCATION_ENTRIES = ALLOCATION["entries"]
ALLOCATION_BY_ID = {entry["glyphId"]: entry for entry in ALLOCATION_ENTRIES}
ALLOCATION_BY_NAME = {entry["glyphName"]: entry for entry in ALLOCATION_ENTRIES}
LEGACY_RECIPE_BY_ID = {entry["glyphId"]: entry["recipeCodePoint"] for entry in ALLOCATION_ENTRIES
                       if entry["oldCodePoint"] is not None}
LEGACY_ENTRIES = sorted((entry for entry in ALLOCATION_ENTRIES if entry["oldCodePoint"] is not None),
                        key=lambda entry: entry["oldCodePoint"])
ADDED_ENTRIES = sorted((entry for entry in ALLOCATION_ENTRIES if entry["oldCodePoint"] is None),
                       key=lambda entry: entry["codePoint"])
INTERNAL_ORDER_ENTRIES = (*LEGACY_ENTRIES, *ADDED_ENTRIES)
SCRIPT_CMAP = {entry["codePoint"]: entry["glyphName"] for entry in INTERNAL_ORDER_ENTRIES}
SCRIPT_GLYPHS = tuple(SCRIPT_CMAP.values())
POSTURE_CMAPS = {
    italic: {entry["codePoint"]: entry["glyphName"] for entry in INTERNAL_ORDER_ENTRIES
             if posture in entry["postures"]}
    for italic, posture in ((False, "Roman"), (True, "Italic"))
}
POSTURE_GLYPHS = {italic: tuple(cmap.values()) for italic, cmap in POSTURE_CMAPS.items()}
LEGACY_SCRIPT_GLYPHS = tuple(f"u{code:X}" for code in range(0xF2A00, 0xF2A45))
MAIN_COMPLETION_FAMILIES = {
    "arched-arms": tuple(range(0xF2A45, 0xF2A51)),
    "double-arches": tuple(range(0xF2A51, 0xF2A5D)),
    "arched-bowls": tuple(range(0xF2A5D, 0xF2A69)),
    "descending-double-arches": tuple(range(0xF2A69, 0xF2A75)),
    "hooked-double-arches": tuple(range(0xF2A75, 0xF2A81)),
}
MAIN_COMPLETION_GLYPHS = tuple(f"u{code:X}" for code in range(0xF2A45, 0xF2A81))
ARCHED_BOWL_GLYPHS = frozenset(f"u{code:X}" for code in MAIN_COMPLETION_FAMILIES["arched-bowls"])
REPEATED_ARCH_BODY_DONORS = {
    f"u{code:X}": (0x26F if (code - first) % 4 >= 2 else 0x271 if first == 0xF2A75 else 0x6D)
    for first in (0xF2A51, 0xF2A69, 0xF2A75) for code in range(first, first + 12)
}
EXTENDED_ARCH_GLYPHS = tuple(f"u{code:X}" for code in range(0xF2A2D, 0xF2A45))
ARCH_GLYPHS = (*tuple(f"u{code:X}" for code in range(0xF2A15, 0xF2A21)), *EXTENDED_ARCH_GLYPHS)
BOWL_GLYPHS = tuple(f"u{code:X}" for code in range(0xF2A21, 0xF2A2D))
GLYPH_ORDER = (".notdef", "space", *SCRIPT_GLYPHS)
POSTURE_GLYPH_ORDERS = {
    italic: (".notdef", "space", *names) for italic, names in POSTURE_GLYPHS.items()
}
SAMPLE_WEIGHTS = (400, 500, 550, 600, 700)
MASTER_PAIRS = (
    ("Regular", "Bold", False),
    ("Italic", "BoldItalic", True),
)
STATIC_FACES = {
    "Regular": (400, False),
    "Italic": (400, True),
    "Bold": (700, False),
    "BoldItalic": (700, True),
}
VARIABLE_FILES = {
    False: "QuintessentialSerif-Variable.ttf",
    True: "QuintessentialSerif-Italic-Variable.ttf",
}
DONOR_FILES = {
    False: "STIXTwoText-VariableFont_wght.ttf",
    True: "STIXTwoText-Italic-VariableFont_wght.ttf",
}
DIRECT_DONORS = {
    "uF2B00": 0x006F,
    "uF2B01": 0x0063,
    "uF2B02": 0x025B,
    "uF2A00": 0x0131,
    "uF2A01": 0x006C,
    "uF2A06": 0x0237,
    "uF2A08": 0x0283,
    "uF2A09": 0x0072,
    "uF2A15": 0x006E,
    "uF2A17": 0x0075,
    "uF2A19": 0x0068,
    "uF2A1D": 0x0266,
    "uF2A22": 0x0070,
    "uF2A23": 0x0251,
    "uF2A24": 0x0064,
    "uF2A25": 0x0062,
    "uF2A26": 0x00FE,
    "uF2A27": 0x0071,
    "uF2A39": 0x014B,
    "uF2A3D": 0xA727,
    "uF2A41": 0x0267,
    "uF2A51": 0x006D,
    "uF2A53": 0x026F,
    "uF2A75": 0x0271,
}
ARCH_BODY_DONORS = {
    "uF2A15": 0x006E,
    "uF2A16": 0x006E,
    "uF2A17": 0x0075,
    "uF2A18": 0x0075,
    "uF2A19": 0x0068,
    "uF2A1A": 0x0068,
    "uF2A1B": 0x0265,
    "uF2A1C": 0x0265,
    "uF2A1D": 0x0266,
    "uF2A1E": 0x0266,
    "uF2A1F": 0x0075,
    "uF2A20": 0x0075,
}
EXTENDED_ARCH_BODY_DONORS = {
    "uF2A2D": 0x019E, "uF2A2E": 0x019E,
    "uF2A2F": 0x0075, "uF2A30": 0x0075,
    "uF2A31": 0xA727, "uF2A32": 0xA727,
    "uF2A33": 0x0265, "uF2A34": 0x0265,
    "uF2A35": 0x0267, "uF2A36": 0x0267,
    "uF2A37": 0x0075, "uF2A38": 0x0075,
    "uF2A39": 0x014B, "uF2A3A": 0x014B,
    "uF2A3B": 0x0075, "uF2A3C": 0x0075,
    "uF2A3D": 0xA727, "uF2A3E": 0xA727,
    "uF2A3F": 0x0265, "uF2A40": 0x0265,
    "uF2A41": 0x0267, "uF2A42": 0x0267,
    "uF2A43": 0x0075, "uF2A44": 0x0075,
}
TURNED_EXTENDED_ARCH_BASES = {
    "uF2A2F": "uF2A17", "uF2A30": "uF2A18",
    "uF2A33": "uF2A1B", "uF2A34": "uF2A1C",
    "uF2A37": "uF2A1F", "uF2A38": "uF2A20",
    "uF2A3B": "uF2A17", "uF2A3C": "uF2A18",
    "uF2A3F": "uF2A1B", "uF2A40": "uF2A1C",
    "uF2A43": "uF2A1F", "uF2A44": "uF2A20",
}
WIDENED_ARCH_GLYPHS = frozenset(("uF2A2E", "uF2A32", "uF2A36"))
LOWER_JOINED_ARCH_GLYPHS = frozenset(("uF2A3A", "uF2A3E", "uF2A42"))
UPPER_JOINED_ARCH_GLYPHS = frozenset(("uF2A3C", "uF2A40", "uF2A44"))
JOINED_ARCH_GLYPHS = LOWER_JOINED_ARCH_GLYPHS | UPPER_JOINED_ARCH_GLYPHS
BOWL_BODY_DONORS = {
    "uF2A21": 0x0062,
    "uF2A22": 0x0070,
    "uF2A23": 0x0251,
    "uF2A24": 0x0064,
    "uF2A25": 0x0062,
    "uF2A26": 0x00FE,
    "uF2A27": 0x0071,
    "uF2A28": 0x0064,
    "uF2A29": 0x0062,
    "uF2A2A": 0x00FE,
    "uF2A2B": 0x0251,
    "uF2A2C": 0x0064,
}
# The accepted 69 forms keep these independent width contracts. New composed
# main-set forms have recipe-specific width checks rather than one donor width.
WIDTH_DONORS = {
    "uF2A00": 0x0131,
    "uF2A01": 0x006C,
    "uF2A02": 0x017F,
    "uF2A03": 0x0131,
    "uF2A04": 0x006C,
    "uF2A05": 0x017F,
    "uF2A06": 0x0237,
    "uF2A07": 0x006C,
    "uF2A08": 0x0283,
    "uF2A09": 0x0072,
    "uF2A0A": 0x0072,
    "uF2A0B": 0x0279,
    "uF2A0C": 0x0279,
    "uF2A0D": 0x0072,
    "uF2A0E": 0x0072,
    "uF2A0F": 0x0279,
    "uF2A10": 0x0279,
    "uF2A11": 0x0072,
    "uF2A12": 0x0072,
    "uF2A13": 0x0279,
    "uF2A14": 0x0279,
    **ARCH_BODY_DONORS,
    **EXTENDED_ARCH_BODY_DONORS,
    **BOWL_BODY_DONORS,
}
EXPECTED_AVAR = {
    -1.0: -1.0,
    0.0: 0.0,
    0.33331298828125: 0.3157958984375,
    0.66668701171875: 0.631591796875,
    1.0: 1.0,
}
EXPECTED_SOURCE_AXIS_MAP = ((400, 92), (500, 110), (600, 128), (700, 149))
EXPECTED_INSTANCE_NAMES = {
    False: (("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700)),
    True: (("Italic", 400), ("Medium Italic", 500), ("SemiBold Italic", 600), ("Bold Italic", 700)),
}
EXPECTED_PAIR_KEYS = {
    italic: {(left, right) for left in names for right in names}
    for italic, names in POSTURE_GLYPHS.items()
}


def recorded_outline(glyph_set, name: str) -> list:
    pen = RecordingPen()
    glyph_set[name].draw(pen)
    return pen.value


def normalized_outline(glyph_set, name: str, digits: int = 5) -> list:
    return [
        (operation, tuple((round(float(x), digits), round(float(y), digits)) for x, y in points))
        for operation, points in recorded_outline(glyph_set, name)
    ]


def topology(font: Font, name: str) -> tuple:
    """Return the segment structure needed for designspace compatibility."""
    operations = recorded_outline(font, name)
    return tuple((operation, len(points)) for operation, points in operations)


def widening_connections(code: int, italic: bool) -> tuple[int, int, int]:
    """The two allowed connecting curves in the pinned native body contour."""
    if code == 0x75:
        return (0, 12, 24) if italic else (0, 8, 22)
    if code == 0x265:
        return (0, 17, 4) if italic else (0, 13, 3)
    if code == 0x19E:
        return (0, 6, 4) if italic else (0, 18, 3)
    return ((1 if code == 0x267 else 0), 9, 7) if italic else (0, 21, 6)


def expanded_native_reference(glyph_set, name: str, code: int, italic: bool, expansion: float):
    """Draw the specified two-curve expansion independently of the builder.

    Native edge order defines which controls belong to each rigid side. Only
    the two connecting runs interpolate horizontal offsets between the sides.
    """
    chosen, forward, backward = widening_connections(code, italic)
    contours, current = [], []
    for operation, points in recorded_outline(glyph_set, name):
        current.append((operation, points))
        if operation == "closePath":
            contours.append(current)
            current = []
    contour = contours[chosen]
    start = contour[0][1][0]
    edges = contour[1:-1]
    if edges[-1][1][-1] != start:
        edges = [*edges, ("lineTo", (start,))]
    count = len(edges)

    def right_side(index):
        return 0 < (index - forward) % count <= (backward - forward) % count

    start_shift = expansion if right_side(0) else 0
    moved = [("moveTo", ((start[0] + start_shift, start[1]),))]
    connections = []
    previous = moved[0][1][0]
    for index, (operation, points) in enumerate(edges):
        if index in (forward, backward):
            if operation != "qCurveTo" or len(points) < 3:
                raise AssertionError((name, index, "native connection is not a quadratic run"))
            first_offset, last_offset = (0, expansion) if index == forward else (expansion, 0)
            control_count = len(points) - 1
            controls = tuple((x + ((control_count - 1 - i) * first_offset + i * last_offset)
                              / (control_count - 1), y)
                             for i, (x, y) in enumerate(points[:-1]))
            points = (*controls, (points[-1][0] + last_offset, points[-1][1]))
            connections.append([("moveTo", (previous,)), (operation, points), ("endPath", ())])
        elif right_side(index):
            points = tuple((x + expansion, y) for x, y in points)
        moved.append((operation, points))
        previous = points[-1]
    moved.append(("closePath", ()))
    contours[chosen] = moved
    reference = Font()
    glyph = reference.newGlyph("reference")
    replayRecording([operation for contour in contours for operation in contour], glyph.getPen())
    return reference, connections


class QuadraticSegmentPen(BasePen):
    def __init__(self, glyph_set=None):
        super().__init__(glyph_set)
        self.segments = []

    def _moveTo(self, point):
        pass

    def _lineTo(self, point):
        pass

    def _qCurveToOne(self, control, end):
        self.segments.append((self._getCurrentPoint(), control, end))

    def _curveToOne(self, first, second, end):
        pass

    def _closePath(self):
        pass

    def _endPath(self):
        pass


def native_contour_edges(glyph_set, name: str, contour_index: int = 0):
    contours, current, previous, start = [], [], None, None
    # Native Italic alpha is an alias component of a; inspect its actual
    # curves with the same contour contract as non-composite donor glyphs.
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(pen)
    for operation, points in pen.value:
        if operation == "moveTo":
            previous = start = points[0]
        elif operation == "closePath":
            if previous != start:
                current.append((previous, "lineTo", (start,)))
            contours.append(current)
            current = []
        else:
            current.append((previous, operation, points))
            previous = points[-1]
    return contours[contour_index]


def quadratic_segments(glyph_set, name: str) -> list:
    pen = QuadraticSegmentPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.segments


def repeated_native_curve_segments(glyph_set, name: str, code: int, italic: bool) -> list:
    """Native arch runs and the middle stave, excluding modified outer ends."""
    if code == 0x6D:
        regions = ((2, None), (0, (3, 4, 5, 7, 8, 9))) if italic else ((0, None), (2, (4, 5, 8, 9)))
    elif code == 0x271:
        regions = ((2, None), (0, None)) if italic else ((0, (11, 12, 14, 18, 20, 21)), (1, None))
    else:
        regions = (((1, None), (0, (0, 1, 10, 11, 12, 14))) if italic else
                   ((0, (0, 2, 3, 8, 9, 24)), (1, (0, 8, 9, 12))))
    pen = QuadraticSegmentPen()
    for contour, selected in regions:
        edges = native_contour_edges(glyph_set, name, contour)
        for index, (start, operation, points) in enumerate(edges):
            if operation == "qCurveTo" and (selected is None or index in selected):
                replayRecording([("moveTo", (start,)), (operation, points), ("endPath", ())], pen)
    return pen.segments


def assert_contains_quadratics(test, actual, expected, tolerance, context):
    test.assertTrue(expected, (context, "no reference curves"))
    for segment in expected:
        error = min(max(abs(a - b) for p, q in zip(candidate, segment) for a, b in zip(p, q))
                    for candidate in actual)
        test.assertLessEqual(error, tolerance, (context, "native curve changed or removed", segment, error))


def joined_arch_reference_segments(donor: TTFont, name: str, construction: dict) -> list:
    """Independently constrain each fitted bowl quarter and retained sweep.

    A closing quarter may change horizontal distance from its receiving
    shaft. Its donor y profile, shaft-relative slant and horizontal extremum
    remain fixed. The adjoining hook curves are only translated.
    """
    italic = bool(donor["post"].italicAngle)
    glyphs, cmap = donor.getGlyphSet(), donor.getBestCmap()

    def edges(code, contour=0):
        return native_contour_edges(glyphs, cmap[code], contour)

    def shifted(edge, offset):
        start, operation, points = edge
        return ((start[0] + offset, start[1]), operation,
                tuple((x + offset, y) for x, y in points))

    def slope(edge):
        first, operation, points = edge
        assert operation == "lineTo"
        return (points[-1][0] - first[0]) / (points[-1][1] - first[1])

    def fit(edge, source_shaft, receiver, anchor, anchor_first):
        start, operation, points = edge
        source_anchor, corner = (start, points[-1]) if anchor_first else (points[-1], start)
        dy = anchor[1] - source_anchor[1]
        source_slope, target_slope = slope(source_shaft), slope(receiver)
        receiver_corner_x = receiver[0][0] + target_slope * (corner[1] + dy - receiver[0][1])
        a = ((anchor[0] - receiver_corner_x - target_slope * (source_anchor[1] - corner[1]))
             / (source_anchor[0] - corner[0] - source_slope * (source_anchor[1] - corner[1])))
        assert a > 0, (name, "closure reverses donor quarter")
        b = target_slope - a * source_slope
        c = receiver_corner_x - a * corner[0] - b * corner[1]

        def transform(point):
            x, y = point
            return a * x + b * y + c, y + dy

        return transform(start), operation, tuple(transform(point) for point in points)

    if name in LOWER_JOINED_ARCH_GLYPHS:
        code = EXTENDED_ARCH_BODY_DONORS[name]
        hook = edges(code, int(italic and code == 0x267))
        stem = edges(code, int(italic and code != 0x267))
        outer_stem, inner_stem = (1, 11 if code == 0xA727 else 10) if italic else (13, 7)
        outer_b, inner_b = edges(0x62), edges(0x62, 1)
        references = [
            fit(outer_b[0 if italic else 6], outer_b[1 if italic else 7],
                stem[outer_stem], hook[0][0], True),
            fit(inner_b[4 if italic else 1], inner_b[3 if italic else 0],
                stem[inner_stem], hook[3][0], False),
            hook[3], hook[-1],
        ]
    else:
        crown = edges(0x266)
        outer_sweep = shifted(crown[2 if italic else 4], construction["leftUpperOffsetX"])
        inner_sweep = shifted(crown[6 if italic else 8], construction["leftUpperOffsetX"])
        head = edges(0x6C)
        inner_stem = shifted(head[2 if italic else 3], construction["upperOffsetX"])
        outer_stem = shifted(head[9], construction["upperOffsetX"])
        outer_d, inner_d = edges(0x64), edges(0x64, 1)
        references = [
            fit(outer_d[2], outer_d[4], outer_stem, outer_sweep[2][-1], True),
            fit(inner_d[2], outer_d[4], inner_stem, inner_sweep[0], False),
            outer_sweep, inner_sweep,
        ]
    pen = QuadraticSegmentPen()
    for start, operation, points in references:
        replayRecording([("moveTo", (start,)), (operation, points), ("endPath", ())], pen)
    return pen.segments


def named_instances(font: TTFont) -> tuple[tuple[str, int], ...]:
    return tuple(
        (font["name"].getDebugName(instance.subfamilyNameID), round(instance.coordinates["wght"]))
        for instance in font["fvar"].instances
    )


def assert_unhinted(test: unittest.TestCase, font: TTFont) -> None:
    # STIX retains a small prep program that sets rasterizer state, but it has
    # no control values, font program, or per-glyph instruction programs.
    for tag in ("cvt ", "fpgm"):
        test.assertNotIn(tag, font)
    test.assertEqual(font["maxp"].maxSizeOfInstructions, 0)
    test.assertFalse(any(getattr(getattr(glyph, "program", None), "bytecode", b"") for glyph in font["glyf"].glyphs.values()))


def assert_outline_is_finite(test: unittest.TestCase, glyph_set, name: str) -> None:
    outline = recorded_outline(glyph_set, name)
    test.assertTrue(outline, name)
    for _operation, operands in outline:
        for operand in operands:
            if isinstance(operand, tuple):
                test.assertTrue(all(math.isfinite(float(value)) for value in operand), name)


def instantiated(path: Path, weight: int) -> TTFont:
    font = TTFont(path, recalcTimestamp=False)
    instantiateVariableFont(font, {"wght": weight}, inplace=True)
    return font


def dflt_kern_lookups(font: TTFont) -> list:
    if "GPOS" not in font:
        return []
    gpos = font["GPOS"].table
    scripts = {record.ScriptTag: record.Script for record in gpos.ScriptList.ScriptRecord}
    script = scripts.get("DFLT")
    if script is None or script.DefaultLangSys is None:
        return []
    lookup_indices = []
    for feature_index in script.DefaultLangSys.FeatureIndex:
        feature = gpos.FeatureList.FeatureRecord[feature_index]
        if feature.FeatureTag == "kern":
            lookup_indices.extend(feature.Feature.LookupListIndex)
    return [gpos.LookupList.Lookup[index] for index in lookup_indices]


def pair_values(font: TTFont) -> dict[tuple[str, str], int]:
    """Read explicit PairPos format-1 values produced by KernFeatureWriter."""
    values: dict[tuple[str, str], int] = {}
    for lookup in dflt_kern_lookups(font):
        if lookup.LookupType != 2:
            continue
        for subtable in lookup.SubTable:
            if subtable.Format != 1:
                continue
            for left, pair_set in zip(subtable.Coverage.glyphs, subtable.PairSet):
                for record in pair_set.PairValueRecord:
                    value = getattr(record.Value1, "XAdvance", 0) if record.Value1 else 0
                    if value:
                        values[left, record.SecondGlyph] = value
    return values


class PolygonPen(BasePen):
    """Flatten TrueType or PostScript curves for conservative collision tests."""

    def __init__(self, glyph_set, steps: int = 96):
        super().__init__(glyph_set)
        self.steps = steps
        self.paths: list[list[tuple[float, float]]] = []
        self.path: list[tuple[float, float]] = []

    def _moveTo(self, point):
        self.path = [point]

    def _lineTo(self, point):
        self.path.append(point)

    def _qCurveToOne(self, control, end):
        start = self._getCurrentPoint()
        for step in range(1, self.steps + 1):
            t = step / self.steps
            u = 1 - t
            self.path.append((
                u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                u * u * start[1] + 2 * u * t * control[1] + t * t * end[1],
            ))

    def _curveToOne(self, first, second, end):
        start = self._getCurrentPoint()
        for step in range(1, self.steps + 1):
            t = step / self.steps
            u = 1 - t
            self.path.append((
                u**3 * start[0] + 3 * u * u * t * first[0] + 3 * u * t * t * second[0] + t**3 * end[0],
                u**3 * start[1] + 3 * u * u * t * first[1] + 3 * u * t * t * second[1] + t**3 * end[1],
            ))

    def _closePath(self):
        if len(self.path) >= 3:
            self.paths.append(self.path)
        self.path = []

    def _endPath(self):
        self.path = []


def polygons(glyph_set, name: str, dx: float = 0, steps: int = 96,
             scale: int = 64) -> list[list[tuple[int, int]]]:
    pen = PolygonPen(glyph_set, steps=steps)
    glyph_set[name].draw(pen)
    return [[(round((x + dx) * scale), round(y * scale)) for x, y in path] for path in pen.paths]


def scanline_crossings(glyph_set, name: str, y: float) -> list[float]:
    """Return ordered outline crossings on one horizontal scanline."""
    pen = PolygonPen(glyph_set, steps=192)
    glyph_set[name].draw(pen)
    crossings = []
    for path in pen.paths:
        closed = [*path, path[0]]
        for first, second in zip(closed, closed[1:]):
            if (first[1] <= y < second[1]) or (second[1] <= y < first[1]):
                t = (y - first[1]) / (second[1] - first[1])
                crossings.append(first[0] + (second[0] - first[0]) * t)
    return sorted(crossings)


def assert_italic_stem_alignment(test: unittest.TestCase, glyph_set, name: str, italic_angle: float) -> None:
    """Require a constructed splice to follow the font's native italic axis."""
    top_y = 299.37
    top_crossings = scanline_crossings(glyph_set, name, top_y)
    test.assertEqual(len(top_crossings), 2, (name, top_y, top_crossings))
    top_center = sum(top_crossings) / 2
    slant = -math.tan(math.radians(italic_angle))
    sampled = []
    for y in (150.37, 160.37, 170.37, 180.37, 190.37, 200.37, 210.37, 220.37,
              230.37, 240.37, 250.37, 260.37, 270.37, 280.37, 290.37, top_y):
        crossings = scanline_crossings(glyph_set, name, y)
        test.assertEqual(len(crossings), 2, (name, y, crossings))
        center = sum(crossings) / 2
        expected = top_center - slant * (top_y - y)
        test.assertLessEqual(abs(center - expected), 3.0, (name, y, center, expected))
        sampled.append((y, crossings))

    # A centerline alone can hide equal-and-opposite ripples in the two edges.
    # Both boundaries must advance monotonically with the native italic lean,
    # and the tangent splice must remain close to the line between its ends.
    lower_y, lower_crossings = sampled[0]
    for edge in (0, 1):
        previous = lower_crossings[edge]
        for y, crossings in sampled[1:]:
            test.assertGreater(crossings[edge], previous, (name, edge, y, crossings[edge], previous))
            progress = (y - lower_y) / (top_y - lower_y)
            expected = lower_crossings[edge] + progress * (top_crossings[edge] - lower_crossings[edge])
            test.assertLessEqual(abs(crossings[edge] - expected), 3.0, (name, edge, y, crossings[edge], expected))
            previous = crossings[edge]


def assert_translated_donor_region(test: unittest.TestCase, built_set, target: str,
                                   donor_set, donor_name: str, samples: tuple[float, ...],
                                   side: str | None = None) -> None:
    """Compare an entire terminal region after fitting one rigid x translation.

    The offset comes from visible geometry rather than construction metadata,
    so this catches damaged donor terminals even if their recipe record agrees.
    """
    offset = None
    compared = 0
    for y in samples:
        actual = scanline_crossings(built_set, target, y)
        expected = scanline_crossings(donor_set, donor_name, y)
        if side is not None:
            # A second ending can occupy the same height. Compare every
            # crossing of the selected native terminal, including its ball.
            if not expected:
                continue
            actual = actual[:len(expected)] if side == "left" else actual[-len(expected):]
        test.assertEqual(len(actual), len(expected), (target, donor_name, y, actual, expected))
        if not expected:
            continue
        if offset is None:
            offset = sum(actual) / len(actual) - sum(expected) / len(expected)
        for actual_x, expected_x in zip(actual, expected):
            test.assertLessEqual(abs(actual_x - expected_x - offset), 0.85,
                                 (target, donor_name, y, actual_x, expected_x, offset))
        compared += 1
    test.assertGreaterEqual(compared, 3, (target, donor_name, "insufficient terminal samples"))


def canonical_flattened_outline(glyph_set, name: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Flatten and canonicalize contours independent of start point and direction."""
    pen = PolygonPen(glyph_set, steps=32)
    glyph_set[name].draw(pen)

    def canonical_path(path):
        points = tuple((float(x), float(y)) for x, y in path)
        candidates = []
        for sequence in (points, tuple(reversed(points))):
            anchor = min((round(x, 5), round(y, 5)) for x, y in sequence)
            for index, point in enumerate(sequence):
                if (round(point[0], 5), round(point[1], 5)) == anchor:
                    candidates.append(sequence[index:] + sequence[:index])
        return min(candidates, key=lambda item: tuple((round(x, 5), round(y, 5)) for x, y in item))

    return tuple(sorted((canonical_path(path) for path in pen.paths), key=lambda path: tuple((round(x, 5), round(y, 5)) for x, y in path)))


def maximum_coordinate_delta(left, right) -> float:
    if len(left) != len(right) or any(len(a) != len(b) for a, b in zip(left, right)):
        return math.inf
    return max(
        (max(abs(ax - bx), abs(ay - by)) for a, b in zip(left, right) for (ax, ay), (bx, by) in zip(a, b)),
        default=0.0,
    )


def outlines_overlap(left_paths, right_paths, advance: float) -> bool:
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(left_paths, pyclipper.PT_SUBJECT, True)
    offset = round(advance * 64)
    clipper.AddPaths([[(x + offset, y) for x, y in path] for path in right_paths], pyclipper.PT_CLIP, True)
    result = clipper.Execute(
        pyclipper.CT_INTERSECTION,
        pyclipper.PFT_NONZERO,
        pyclipper.PFT_NONZERO,
    )
    return any(abs(pyclipper.Area(path)) > 1 for path in result)


def symmetric_difference_area(left_paths, right_paths, scale: int = 64) -> float:
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(left_paths, pyclipper.PT_SUBJECT, True)
    clipper.AddPaths(right_paths, pyclipper.PT_CLIP, True)
    result = clipper.Execute(
        pyclipper.CT_XOR,
        pyclipper.PFT_NONZERO,
        pyclipper.PFT_NONZERO,
    )
    # Clipper gives holes the opposite winding from outer paths. An almost
    # coincident pair of counters can leave a thin annulus; summing absolute
    # contour areas would count its empty interior twice.
    return abs(sum(pyclipper.Area(path) for path in result)) / (scale * scale)


def filled_counter_paths(paths) -> list:
    """Find actual holes after filling all contours with the nonzero rule.

    Italic STIX p closes its counter using two clockwise components. Testing
    positive contours alone would miss a broken connection in that design.
    """
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
    pending = list(tree.Childs)
    counters = []
    while pending:
        node = pending.pop()
        pending.extend(node.Childs)
        if node.IsHole:
            counters.append(node.Contour)
    return counters


def filled_shape_paths(paths) -> list:
    """Resolve component overlap before measuring an open arch cavity."""
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    return clipper.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)


def filled_scanline_intervals(paths, y: float) -> list[tuple[float, float]]:
    crossings = []
    scan_y = y * 64
    for path in paths:
        for first, second in zip(path, [*path[1:], path[0]]):
            if (first[1] <= scan_y < second[1]) or (second[1] <= scan_y < first[1]):
                t = (scan_y - first[1]) / (second[1] - first[1])
                crossings.append((first[0] + (second[0] - first[0]) * t) / 64)
    crossings.sort()
    return list(zip(crossings[::2], crossings[1::2]))


class QuintessentialFontTests(unittest.TestCase):
    maxDiff = None

    def test_symmetric_difference_area_accounts_for_nested_holes(self):
        def square(size, scale, reverse=False):
            half = round(size * scale / 2)
            path = [(-half, -half), (half, -half), (half, half), (-half, half)]
            return list(reversed(path)) if reverse else path

        for scale in (64, 4096, 65536):
            with self.subTest(scale=scale):
                # The XOR is a one-unit-wide annulus: 10² - 9², not 10² + 9².
                self.assertEqual(symmetric_difference_area([square(10, scale)], [square(9, scale)], scale), 19)
                # Filling a real counter must still produce its whole area.
                bowl = [square(10, scale), square(5, scale, reverse=True)]
                self.assertEqual(symmetric_difference_area(bowl, [square(10, scale)], scale), 25)
                # Higher clipping precision must not conceal real drift just
                # above the static/variable acceptance limit.
                left = [[(0, 0), (scale, 0), (scale, scale), (0, scale)]]
                right = [[(0, 0), (scale, 0), (scale, round(2.1 * scale)), (0, round(2.1 * scale))]]
                self.assertGreater(symmetric_difference_area(left, right, scale), 1.0)

    def test_pinned_stix_donors_and_license(self):
        manifest = json.loads((DONORS / "source-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["upstream"]["releaseVersion"], "2.13 b171")
        self.assertEqual(manifest["upstream"]["releaseTag"], "v2.13b171")
        for field in ("repositoryUrl", "releaseUrl", "romanDesignspaceUrl", "italicDesignspaceUrl"):
            self.assertTrue(manifest["upstream"][field].startswith("https://"), field)
        axis_manifest = manifest["axisModel"]["axes"]
        self.assertEqual(len(axis_manifest), 1)
        self.assertEqual(
            (axis_manifest[0]["tag"], axis_manifest[0]["minimum"], axis_manifest[0]["default"], axis_manifest[0]["maximum"]),
            ("wght", 400, 400, 700),
        )
        self.assertEqual(
            tuple((entry["user"], entry["source"]) for entry in axis_manifest[0]["sourceDesignspaceMap"]),
            EXPECTED_SOURCE_AXIS_MAP,
        )
        self.assertEqual(set(manifest["axisModel"]["absentAxes"]), {"wdth", "opsz"})
        expected = {item["filename"]: item["sha256"].lower() for item in manifest["donors"]}
        self.assertEqual(set(expected), set(DONOR_FILES.values()))
        for filename, digest in expected.items():
            self.assertEqual(hashlib.sha256((DONORS / filename).read_bytes()).hexdigest(), digest)
            with TTFont(DONORS / filename) as font:
                italic = filename == DONOR_FILES[True]
                axes = font["fvar"].axes
                self.assertEqual([(axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue) for axis in axes], [("wght", 400, 400, 700)])
                self.assertEqual(font["head"].unitsPerEm, 1000)
                self.assertEqual(font["name"].getDebugName(5), "Version 2.13 b171")
                self.assertEqual(named_instances(font), EXPECTED_INSTANCE_NAMES[italic])
                self.assertEqual(font["avar"].segments, {"wght": EXPECTED_AVAR})
                self.assertNotIn("wdth", {axis.axisTag for axis in axes})
                self.assertNotIn("opsz", {axis.axisTag for axis in axes})
                assert_unhinted(self, font)
        expected_documents = {item["filename"]: item["sha256"].lower() for item in manifest["documents"]}
        self.assertEqual(set(expected_documents), {"OFL.txt", "FONTLOG.txt", "TRADEMARKS.txt"})
        for filename, digest in expected_documents.items():
            self.assertEqual(hashlib.sha256((DONORS / filename).read_bytes()).hexdigest(), digest)

    def test_master_pairs_are_interpolation_compatible(self):
        self.assertEqual((ALLOCATION["version"], ALLOCATION["previousVersion"]), ("0.220", "0.210"))
        self.assertEqual(len(ALLOCATION_ENTRIES), 832)
        self.assertEqual(len(ALLOCATION_BY_ID), 832)
        self.assertEqual(len(ALLOCATION_BY_NAME), 832)
        self.assertEqual(len(LEGACY_ENTRIES), 481)
        self.assertEqual(len(ADDED_ENTRIES), 351)
        self.assertEqual({entry["oldCodePoint"]: entry["glyphName"] for entry in LEGACY_ENTRIES},
                         LEGACY_RECIPE_CMAP)
        self.assertEqual([entry["glyphName"] for entry in ADDED_ENTRIES[:3]],
                         ["special-closed-double-bowl", "special-turned-open-bowl", "special-turned-double-open-bowl"])
        for entry in ADDED_ENTRIES[3:]:
            self.assertTrue(entry["middleLegs"])
            self.assertEqual(entry["glyphName"], ALLOCATION_BY_ID[entry["baseGlyphId"]]["glyphName"] + ".middle")
            self.assertEqual(entry["recipeCodePoint"], ALLOCATION_BY_ID[entry["baseGlyphId"]]["oldCodePoint"])
        for italic in (False, True):
            self.assertEqual(POSTURE_GLYPHS[italic][:len(LEGACY_POSTURE_CMAPS[italic])],
                             tuple(LEGACY_POSTURE_CMAPS[italic].values()))
        self.assertEqual({italic: len(cmap) for italic, cmap in POSTURE_CMAPS.items()},
                         {False: 832, True: 232})
        self.assertEqual({italic: len(keys) for italic, keys in EXPECTED_PAIR_KEYS.items()},
                         {False: 692224, True: 53824})
        for light_style, bold_style, italic in MASTER_PAIRS:
            light = Font.open(SOURCES / f"QuintessentialSerif-{light_style}.ufo")
            bold = Font.open(SOURCES / f"QuintessentialSerif-{bold_style}.ufo")
            glyph_order = POSTURE_GLYPH_ORDERS[italic]
            self.assertEqual(tuple(light.glyphOrder), glyph_order)
            self.assertEqual(tuple(bold.glyphOrder), glyph_order)
            self.assertEqual(set(light.kerning), EXPECTED_PAIR_KEYS[italic])
            self.assertEqual(set(bold.kerning), EXPECTED_PAIR_KEYS[italic])
            expected_unicodes = {
                ".notdef": (), "space": (0x20,),
                **{name: (code,) for code, name in POSTURE_CMAPS[italic].items()},
            }
            for master in (light, bold):
                self.assertEqual(set(master.keys()), set(glyph_order))
                self.assertEqual({name: tuple(master[name].unicodes) for name in glyph_order},
                                 expected_unicodes)
            for name in glyph_order:
                with self.subTest(pair=f"{light_style}-{bold_style}", glyph=name):
                    self.assertEqual(topology(light, name), topology(bold, name))
                    for master in (light, bold):
                        operations = {operation for operation, _points in recorded_outline(master, name)}
                        self.assertNotIn("addComponent", operations)
                        self.assertNotIn("curveTo", operations)

    def test_main_completion_has_connected_staves_counters_and_recorded_advances(self):
        widths = {}
        for style, (weight, italic) in STATIC_FACES.items():
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            for name in MAIN_COMPLETION_GLYPHS:
                with self.subTest(source=style, glyph=name):
                    construction = source[name].lib["org.quintessential.construction"]
                    self.assertGreater(source[name].width, 0)
                    widths[italic, weight, name] = source[name].width
                    direct = name in {"uF2A51", "uF2A53", "uF2A75"}
                    if direct:
                        self.assertEqual(construction["donorCodePoint"], REPEATED_ARCH_BODY_DONORS[name])
                    else:
                        self.assertEqual(source[name].width, round(construction["advanceWidth"], 6))
                    if name in REPEATED_ARCH_BODY_DONORS and not direct:
                        self.assertEqual(construction["archDonorCodePoint"], REPEATED_ARCH_BODY_DONORS[name])
                        self.assertEqual(construction["archCount"], 2)
                        self.assertNotIn("joinedTerminal", construction)

        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    glyphs = font.getGlyphSet()
                    factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                    for name in MAIN_COMPLETION_GLYPHS:
                        with self.subTest(italic=italic, weight=weight, glyph=name):
                            expected_width = widths[italic, 400, name] + factor * (
                                widths[italic, 700, name] - widths[italic, 400, name])
                            self.assertLessEqual(abs(font["hmtx"][name][0] - expected_width), 1.0)
                            if name in REPEATED_ARCH_BODY_DONORS:
                                native = donor.getBestCmap()[REPEATED_ARCH_BODY_DONORS[name]]
                                self.assertEqual(font["hmtx"][name][0], donor["hmtx"][native][0])
                            paths = polygons(glyphs, name)
                            clipper = pyclipper.Pyclipper()
                            clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
                            tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                            self.assertEqual(len(tree.Childs), 1, (name, "disconnected arch or terminal"))
                            counters = filled_counter_paths(paths)
                            bowl = name in ARCHED_BOWL_GLYPHS
                            self.assertEqual(len(counters), int(bowl), (name, "wrong counter count"))
                            if bowl:
                                self.assertGreater(abs(pyclipper.Area(counters[0])) / 4096, 20_000)
                            # Native m/ɯ/ɱ components overlap in Italic. At this
                            # common band their filled shape has three staves;
                            # a detached terminal cannot masquerade as an arch.
                            three_staves = bowl or name in REPEATED_ARCH_BODY_DONORS
                            # The turned-r shoulder itself crosses y200 in
                            # light Italic. At y250 both actual arm shafts are
                            # separate from that native terminal curve.
                            band = 200.37 if three_staves else 250.37
                            intervals = filled_scanline_intervals(filled_shape_paths(paths), band)
                            self.assertEqual(len(intervals), 3 if three_staves else 2,
                                             (name, "missing stave or arch cavity", intervals))
                            for first, second in zip(intervals, intervals[1:]):
                                self.assertGreater(second[0] - first[1], 10, (name, "cavity collapsed"))

    def test_double_bowl_families_are_distinct_connected_and_keep_two_counters(self):
        endpoint_widths = {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            signatures = {}
            for name in POSTURE_GLYPHS[False]:
                signature = repr(normalized_outline(source, name))
                self.assertNotIn(signature, signatures, (style, name, signatures.get(signature), "duplicate outline"))
                signatures[signature] = name
            for name in DOUBLE_BOWL_FAMILY_GLYPHS:
                endpoint_widths[weight, name] = source[name].width
                self.assertGreater(source[name].width, 0, (style, name))

        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font:
                glyphs = font.getGlyphSet()
                signatures = {}
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                for name in DOUBLE_BOWL_FAMILY_GLYPHS:
                    with self.subTest(glyph=name):
                        signature = repr(normalized_outline(glyphs, name))
                        self.assertNotIn(signature, signatures, (name, signatures.get(signature), "duplicate interpolated outline"))
                        signatures[signature] = name
                        expected_width = endpoint_widths[400, name] + factor * (
                            endpoint_widths[700, name] - endpoint_widths[400, name])
                        self.assertLessEqual(abs(font["hmtx"][name][0] - expected_width), 1.0)
                        paths = polygons(glyphs, name)
                        clipper = pyclipper.Pyclipper()
                        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
                        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                        self.assertEqual(len(tree.Childs), 1, (name, "disconnected body or terminal"))
                        counters = filled_counter_paths(paths)
                        self.assertEqual(len(counters), 2, (name, "Double bowl must have two enclosed counters"))
                        bounds = []
                        for counter in counters:
                            self.assertGreater(abs(pyclipper.Area(counter)) / 4096, 1000, (name, "collapsed counter"))
                            xs, ys = zip(*counter)
                            self.assertGreater((max(xs) - min(xs)) / 64, 10, (name, "counter too narrow"))
                            self.assertGreater((max(ys) - min(ys)) / 64, 10, (name, "counter too short"))
                            bounds.append((min(ys) / 64, max(ys) / 64))
                        bounds.sort()
                        self.assertGreater(bounds[1][0] - bounds[0][1], 5, (name, "missing waist between stacked counters"))

    def test_narrow_opposed_bowls_have_two_counters_and_independent_endings(self):
        endpoint_widths = {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            plain = source["uF2B1C"]
            plain_construction = plain.lib["org.quintessential.construction"]
            for code, name in OPPOSED_BOWL_CMAP.items():
                with self.subTest(source=style, glyph=name):
                    construction = source[name].lib["org.quintessential.construction"]
                    left, right = divmod(code - 0xF2B1C, 6)
                    self.assertEqual(construction["family"], "opposed-bowls")
                    self.assertEqual(construction["archCount"], 0)
                    self.assertEqual((construction["leftVariant"], construction["rightVariant"]),
                                     (left, right))
                    self.assertEqual(construction["waistAddedWidth"], 0, "endings must not stretch the spine")
                    self.assertEqual(source[name].width, plain.width, "all ending combinations stay compact")
                    for anchor in ("stemLeftX", "stemLeftInnerX", "stemRightInnerX", "stemRightX"):
                        self.assertEqual(construction[anchor], plain_construction[anchor])
                    self.assertEqual(construction["terminalCounterCount"],
                                     int(left >= 4 and right % 2 == 1) + int(left % 2 == 1 and right >= 2))
                    self.assertEqual(source[name].width, round(construction["advanceWidth"], 6))
                    endpoint_widths[weight, name] = source[name].width
        for weight in SAMPLE_WEIGHTS:
            with instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font:
                glyphs = font.getGlyphSet()
                signatures = set()
                plain_body_counters = polygons(glyphs, "uF2B1C")[1:3]
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                for code, name in OPPOSED_BOWL_CMAP.items():
                    with self.subTest(weight=weight, glyph=name):
                        signature = repr(normalized_outline(glyphs, name))
                        self.assertNotIn(signature, signatures, "ending choices must remain distinct")
                        signatures.add(signature)
                        paths = polygons(glyphs, name)
                        left, right = divmod(code - 0xF2B1C, 6)
                        terminal_counters = int(left >= 4 and right % 2 == 1) + int(left % 2 == 1 and right >= 2)
                        self.assertEqual(len(paths), 3 + terminal_counters,
                                         "one outer contour, two body counters, and joined terminal enclosures")
                        self.assertEqual(paths[1:3], plain_body_counters,
                                         "hooks and extensions must preserve both refined sigmoid counters")
                        clipper = pyclipper.Pyclipper()
                        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
                        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                        self.assertEqual(len(tree.Childs), 1, "disconnected shaft or sigmoid")
                        counters = filled_counter_paths(paths)
                        self.assertEqual(len(counters), 2 + terminal_counters,
                                         "two opposed counters plus the expected joined terminal enclosures")
                        for counter in counters:
                            self.assertGreater(abs(pyclipper.Area(counter)) / 4096, 1000, "collapsed counter")
                            xs, ys = zip(*counter)
                            self.assertGreater((max(xs) - min(xs)) / 64, 10)
                            self.assertGreater((max(ys) - min(ys)) / 64, 10)
                        expected_width = endpoint_widths[400, name] + factor * (
                            endpoint_widths[700, name] - endpoint_widths[400, name])
                        self.assertLessEqual(abs(font["hmtx"][name][0] - expected_width), 1.0)

    def test_arched_opposed_bowls_complete_the_block_with_three_connected_shafts(self):
        self.assertEqual(set(SPECIAL_CMAP) | set(ABBREVIATION_CMAP), set(range(0xF2B00, 0xF2BA0)))
        endpoint_widths = {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            for code, name in ARCHED_OPPOSED_BOWL_CMAP.items():
                with self.subTest(source=style, glyph=name):
                    right_arch = code >= 0xF2B7C
                    left, right = divmod(code - (0xF2B7C if right_arch else 0xF2B58), 6)
                    construction = source[name].lib["org.quintessential.construction"]
                    base_code = 0xF2B1C + left * 6 if right_arch else 0xF2B28 + right
                    base = source[f"u{base_code:X}"]
                    base_construction = base.lib["org.quintessential.construction"]
                    self.assertEqual(construction["family"],
                                     "right-arched-opposed-bowls" if right_arch else "left-arched-opposed-bowls")
                    self.assertEqual(construction["archCount"], 1)
                    self.assertEqual(construction["archSide"], "right" if right_arch else "left")
                    self.assertEqual((construction["leftVariant"], construction["rightVariant"]), (left, right))
                    self.assertEqual(construction["sigmoidBaseCodePoint"], base_code)
                    self.assertEqual(construction["sigmoidAdvanceWidth"], base.width)
                    self.assertEqual(construction["waistAddedWidth"], 0)
                    self.assertEqual(construction["stemRightX"] - construction["stemLeftX"],
                                     base_construction["stemRightX"] - base_construction["stemLeftX"])
                    self.assertEqual(source[name].width, round(construction["advanceWidth"], 6))
                    self.assertGreater(source[name].width, base.width)
                    endpoint_widths[weight, name] = source[name].width
        for weight in SAMPLE_WEIGHTS:
            with instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font:
                glyphs = font.getGlyphSet()
                signatures = set()
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                for code, name in ARCHED_OPPOSED_BOWL_CMAP.items():
                    with self.subTest(weight=weight, glyph=name):
                        signature = repr(normalized_outline(glyphs, name))
                        self.assertNotIn(signature, signatures, "all 72 ending and arch-side choices remain distinct")
                        signatures.add(signature)
                        paths = polygons(glyphs, name)
                        clipper = pyclipper.Pyclipper()
                        clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
                        tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                        self.assertEqual(len(tree.Childs), 1, "disconnected arch or sigmoid")
                        counters = filled_counter_paths(paths)
                        self.assertEqual(len(counters), 2, "two opposed body counters and an open arch")
                        for counter in counters:
                            self.assertGreater(abs(pyclipper.Area(counter)) / 4096, 1000)
                        filled = filled_shape_paths(paths)
                        for y in (150.37, 200.37, 350.37):
                            self.assertEqual(len(filled_scanline_intervals(filled, y)), 3,
                                             "one added shaft beside the compact two-shaft body")
                        expected_width = endpoint_widths[400, name] + factor * (
                            endpoint_widths[700, name] - endpoint_widths[400, name])
                        self.assertLessEqual(abs(font["hmtx"][name][0] - expected_width), 1.0)

    def test_bowled_spines_are_distinct_connected_and_keep_one_counter(self):
        endpoint_widths = {}
        for style, (weight, italic) in STATIC_FACES.items():
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            for code, name in BOWLED_SPINE_FAMILY_CMAP.items():
                with self.subTest(source=style, glyph=name):
                    endpoint_widths[italic, weight, name] = source[name].width
                    self.assertGreater(source[name].width, 0)
                    construction = source[name].lib["org.quintessential.construction"]
                    self.assertEqual(construction["family"], "arched-bowled-spines"
                                     if code in ARCHED_BOWLED_SPINE_CMAP else "bowled-spines")

        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    glyphs = font.getGlyphSet()
                    factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                    signatures = {}
                    for name in POSTURE_GLYPHS[italic]:
                        signature = repr(normalized_outline(glyphs, name))
                        self.assertNotIn(signature, signatures,
                                         (name, signatures.get(signature), "duplicate interpolated outline"))
                        signatures[signature] = name
                    for code, name in BOWLED_SPINE_FAMILY_CMAP.items():
                        with self.subTest(glyph=name):
                            expected_width = endpoint_widths[italic, 400, name] + factor * (
                                endpoint_widths[italic, 700, name] - endpoint_widths[italic, 400, name])
                            self.assertLessEqual(abs(font["hmtx"][name][0] - expected_width), 1.0)
                            paths = polygons(glyphs, name)
                            clipper = pyclipper.Pyclipper()
                            clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
                            tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                            self.assertEqual(len(tree.Childs), 1, (name, "disconnected spine, stem or arch"))
                            counters = filled_counter_paths(paths)
                            self.assertEqual(len(counters), 1, (name, "Bowled spine must have one enclosed counter"))
                            counter = counters[0]
                            self.assertGreater(abs(pyclipper.Area(counter)) / 4096, 1000,
                                               (name, "collapsed counter"))
                            xs, ys = zip(*counter)
                            self.assertGreater((max(xs) - min(xs)) / 64, 10, (name, "counter too narrow"))
                            self.assertGreater((max(ys) - min(ys)) / 64, 10, (name, "counter too short"))
                            first = 0xF2B4C if code in ARCHED_BOWLED_SPINE_CMAP else 0xF2B10
                            lower_bowl = (code - first) % 4 >= 2
                            # The counterpart must move the bowl, not merely its
                            # stem ending: upper/lower is part of the fixed name.
                            counter_center = (min(ys) + max(ys)) / 128
                            if lower_bowl:
                                self.assertLess(counter_center, 240, (name, "lower bowl is not below the waist"))
                            else:
                                self.assertGreater(counter_center, 240, (name, "upper bowl is not above the waist"))

    def test_bowled_spine_outer_stem_terminals_preserve_native_donors(self):
        upper = {
            **{f"u{0xF2B10 + variant:X}": 0x64 for variant in (3, 7, 11)},
            "uF2B14": 0x62, "uF2B15": 0x62,
            **{f"u{0xF2B10 + variant:X}": 0x253 for variant in (8, 9)},
            **{f"u{0xF2B4C + variant:X}": 0x6C for variant in (3, 7, 11)},
            **{f"u{0xF2B4C + variant:X}": 0x68 for variant in (4, 5)},
            **{f"u{0xF2B4C + variant:X}": 0x266 for variant in (8, 9)},
        }
        lower = {
            "uF2B11": 0x70, "uF2B15": 0x70, "uF2B19": 0x70,
            **{f"u{0xF2B4C + variant:X}": 0x70 for variant in (1, 5, 9)},
            **{f"u{0xF2B10 + variant:X}": 0x71 for variant in (6, 7)},
            **{f"u{0xF2B4C + variant:X}": 0x70 for variant in (6, 7)},
            **{f"u{first + variant:X}": 0x261 for first in (0xF2B10, 0xF2B4C) for variant in (10, 11)},
        }
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as font, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    glyphs, native, cmap = font.getGlyphSet(), donor.getGlyphSet(), donor.getBestCmap()
                    for targets, samples in (
                        (upper, (510.37, 540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)),
                        (lower, (-30.37, -60.37, -100.37, -130.37, -160.37, -180.37, -200.37, -220.37, -240.37)),
                    ):
                        for name, code in targets.items():
                            with self.subTest(glyph=name, donor=f"U+{code:04X}"):
                                assert_translated_donor_region(self, glyphs, name, native, cmap[code], samples)

    def test_roman_bowled_spines_keep_native_bellies_and_orientation_specific_free_terminals(self):
        def line_segments(glyphs, name):
            result, previous = [], None
            for operation, points in recorded_outline(glyphs, name):
                if operation == "lineTo":
                    result.append((previous, points[0]))
                previous = points[-1] if points else None
            return result

        def assert_flat_cut(glyphs, name, expected, tolerance, context):
            candidates = line_segments(glyphs, name)
            self.assertTrue(candidates, (context, "no flat terminal cut"))
            error = min(max(abs(a - b) for p, q in zip(candidate, expected) for a, b in zip(p, q))
                        for candidate in candidates)
            self.assertLessEqual(error, tolerance, (context, "native epsilon cut changed", error))

        references, cuts = {}, {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with instantiated(DONORS / DONOR_FILES[False], weight) as donor:
                for code, name in BOWLED_SPINE_FAMILY_CMAP.items():
                    with self.subTest(source=style, glyph=name):
                        arched = code in ARCHED_BOWLED_SPINE_CMAP
                        variant = code - (0xF2B4C if arched else 0xF2B10)
                        turned = variant % 4 >= 2
                        construction = source[name].lib["org.quintessential.construction"]
                        spine_code = 0x61 if turned else 0x250
                        self.assertEqual(construction["spineDonorCodePoint"], spine_code)
                        self.assertEqual(construction["freeTerminalDonorCodePoint"], 0x61 if turned else 0x25B)
                        self.assertFalse(construction.get("freeTerminalTurned", False))
                        arch_dx = construction["terminalOffsetX"] if arched and not turned else 0
                        spine_dx = construction["spineOffsetX"] + arch_dx
                        belly = native_contour_edges(donor.getGlyphSet(), donor.getBestCmap()[spine_code])
                        epsilon = native_contour_edges(donor.getGlyphSet(), donor.getBestCmap()[0x25B])

                        def shifted_belly(point):
                            return point[0] + spine_dx, point[1]

                        # The upper-bowled bottom keeps epsilon's flat cut.
                        # The lower-bowled top keeps the normal a's native bulb
                        # and inner shoulder, as explicitly corrected by the user.
                        regions = [(belly, (0, 1, 3, 4, 5, 6, 7) if turned else (15, 16), shifted_belly)]
                        if not turned:
                            terminal_dx = construction["freeTerminalOffsetX"] + arch_dx
                            terminal_dy = construction["freeTerminalOffsetY"]

                            def shifted_terminal(point):
                                return point[0] + terminal_dx, point[1] + terminal_dy

                            regions.append((epsilon, (15, 17), shifted_terminal))
                        pen = QuadraticSegmentPen()
                        for edges, indices, transform in regions:
                            for index in indices:
                                start, operation, points = edges[index]
                                self.assertEqual(operation, "qCurveTo")
                                replayRecording([("moveTo", (transform(start),)),
                                                 (operation, tuple(transform(point) for point in points)),
                                                 ("endPath", ())], pen)
                        references[weight, name] = pen.segments
                        assert_contains_quadratics(self, quadratic_segments(source, name), pen.segments,
                                                   1e-5, (style, name))
                        if not turned:
                            cut_start, operation, cut_points = epsilon[16]
                            self.assertEqual(operation, "lineTo")
                            cuts[weight, name] = shifted_terminal(cut_start), shifted_terminal(cut_points[0])
                            assert_flat_cut(source, name, cuts[weight, name], 1e-5, (style, name))

        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font:
                glyphs = font.getGlyphSet()
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                for name in BOWLED_SPINE_FAMILY_GLYPHS:
                    light, bold = references[400, name], references[700, name]
                    self.assertEqual(len(light), len(bold))
                    expected = [tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                      for p, q in zip(first, second))
                                for first, second in zip(light, bold)]
                    assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected,
                                               0.75, (weight, name))
                    if (400, name) in cuts:
                        expected_cut = tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                             for p, q in zip(cuts[400, name], cuts[700, name]))
                        assert_flat_cut(glyphs, name, expected_cut, 0.75, (weight, name))

    def test_italic_spines_keep_native_diagonal_bowls_bulbs_and_flat_bottoms(self):
        references, cuts = {}, {}

        def assert_flat_cut(glyphs, name, expected, tolerance, context):
            lines, previous = [], None
            for operation, points in recorded_outline(glyphs, name):
                if operation == "lineTo":
                    lines.append((previous, points[0]))
                previous = points[-1] if points else None
            self.assertTrue(lines, (context, "missing epsilon flat cut"))
            error = min(max(abs(a - b) for p, q in zip(line, expected) for a, b in zip(p, q))
                        for line in lines)
            self.assertLessEqual(error, tolerance, (context, "native flat bottom changed", error))

        for style, weight in (("Italic", 400), ("BoldItalic", 700)):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with instantiated(DONORS / DONOR_FILES[True], weight) as donor:
                donor_set, cmap = donor.getGlyphSet(), donor.getBestCmap()
                bowl = native_contour_edges(donor_set, cmap[0x250], 1)
                shaft = native_contour_edges(donor_set, cmap[0x250], 0)
                epsilon = native_contour_edges(donor_set, cmap[0x25B])
                for code, name in BOWLED_SPINE_FAMILY_CMAP.items():
                    with self.subTest(source=style, glyph=name):
                        arched = code in ARCHED_BOWLED_SPINE_CMAP
                        variant = code - (0xF2B4C if arched else 0xF2B10)
                        turned = variant % 4 >= 2
                        construction = source[name].lib["org.quintessential.construction"]
                        self.assertEqual(construction["spineDonorCodePoint"], 0x250)
                        self.assertEqual(construction["bodyDonorCodePoint"], 0x250)
                        self.assertEqual(construction["spineTurned"], turned)
                        self.assertEqual(construction["freeTerminalDonorCodePoint"], 0x250 if turned else 0x25B)
                        self.assertEqual(construction["freeTerminalTurned"], turned)
                        # Native Italic curves retain their actual slope. Only
                        # a rigid translation and the specified 180-degree turn
                        # are allowed; a sheared Roman approximation fails.
                        arch_dx = construction["terminalOffsetX"] if arched and not turned else 0
                        sign = -1 if turned else 1
                        dx, dy = construction["spineOffsetX"] + arch_dx, construction["spineOffsetY"]

                        def body_point(point):
                            return sign * point[0] + dx, sign * point[1] + dy

                        regions = [(bowl, tuple(range(len(bowl))), body_point)]
                        if turned:
                            # These four curves contain the native lower ball
                            # of turned a, now the upper ball of the turned spine.
                            regions.append((shaft, (15, 16, 17, 18), body_point))
                        else:
                            terminal_dx = construction["freeTerminalOffsetX"] + arch_dx
                            terminal_dy = construction["freeTerminalOffsetY"]

                            def terminal_point(point):
                                return point[0] + terminal_dx, point[1] + terminal_dy

                            regions.append((epsilon, (17, 19), terminal_point))
                            start, operation, points = epsilon[18]
                            self.assertEqual(operation, "lineTo")
                            cuts[weight, name] = terminal_point(start), terminal_point(points[0])

                        pen = QuadraticSegmentPen()
                        for edges, indices, transform in regions:
                            for index in indices:
                                start, operation, points = edges[index]
                                if operation == "qCurveTo":
                                    replayRecording([("moveTo", (transform(start),)),
                                                     (operation, tuple(transform(point) for point in points)),
                                                     ("endPath", ())], pen)
                        references[weight, name] = pen.segments
                        assert_contains_quadratics(self, quadratic_segments(source, name), pen.segments,
                                                   1e-5, (style, name))
                        if not turned:
                            assert_flat_cut(source, name, cuts[weight, name], 1e-5, (style, name))

        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), instantiated(OUTPUT / VARIABLE_FILES[True], weight) as font:
                glyphs = font.getGlyphSet()
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                for name in BOWLED_SPINE_FAMILY_GLYPHS:
                    light, bold = references[400, name], references[700, name]
                    self.assertEqual(len(light), len(bold))
                    expected = [tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                      for p, q in zip(first, second)) for first, second in zip(light, bold)]
                    assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected,
                                               0.75, (weight, name))
                    if (400, name) in cuts:
                        expected_cut = tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                             for p, q in zip(cuts[400, name], cuts[700, name]))
                        assert_flat_cut(glyphs, name, expected_cut, 0.75, (weight, name))

    def test_double_bowl_outer_terminals_preserve_native_donors(self):
        upper = {
            **{f"u{0xF2B04 + variant:X}": 0x64 for variant in (3, 7, 11)},
            "uF2B08": 0x62, "uF2B09": 0xFE,
            **{f"u{0xF2B04 + variant:X}": 0x253 for variant in (8, 9)},
            **{f"u{0xF2B40 + variant:X}": 0x6C for variant in (3, 7, 11)},
            **{f"u{0xF2B40 + variant:X}": 0x68 for variant in (4, 5)},
            **{f"u{0xF2B40 + variant:X}": 0x266 for variant in (8, 9)},
        }
        lower = {
            "uF2B05": 0x70, "uF2B09": 0xFE, "uF2B0D": 0xFE,
            **{f"u{0xF2B40 + variant:X}": 0x70 for variant in (1, 5, 9)},
            **{f"u{0xF2B04 + variant:X}": 0x71 for variant in (6, 7)},
            **{f"u{0xF2B40 + variant:X}": 0x70 for variant in (6, 7)},
            **{f"u{first + variant:X}": 0x261 for first in (0xF2B04, 0xF2B40) for variant in (10, 11)},
        }
        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), \
                    instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font, \
                    instantiated(DONORS / DONOR_FILES[False], weight) as donor:
                glyphs, native, cmap = font.getGlyphSet(), donor.getGlyphSet(), donor.getBestCmap()
                for targets, samples in (
                    (upper, (510.37, 540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)),
                    (lower, (-30.37, -60.37, -100.37, -130.37, -160.37, -180.37, -200.37, -220.37, -240.37)),
                ):
                    for name, code in targets.items():
                        with self.subTest(glyph=name, donor=f"U+{code:04X}"):
                            assert_translated_donor_region(self, glyphs, name, native, cmap[code], samples)

    def test_double_bowl_outer_lobes_waist_and_lower_counter_interiors_remain_native(self):
        references = {}
        for style, weight in (("Regular", 400), ("Bold", 700)):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with instantiated(DONORS / DONOR_FILES[False], weight) as donor:
                for name in DOUBLE_BOWL_FAMILY_GLYPHS:
                    with self.subTest(source=style, glyph=name):
                        code = int(name[1:], 16)
                        arched = code in ARCHED_DOUBLE_BOWL_CMAP
                        variant = code - (0xF2B40 if arched else 0xF2B04)
                        turned = variant % 4 >= 2
                        donor_code = 0x25B if turned else 0x25C
                        edges = native_contour_edges(donor.getGlyphSet(), donor.getBestCmap()[donor_code])
                        # Both orientations retain their own upright outer
                        # lobes/waist and lower inner curves. Upper interiors
                        # are optically deepened to balance the two hairlines.
                        indices = (0, 1, 2, 3, 4, 13, 14) if turned else (3, 4, 13, 14, 15, 16, 17)
                        selected = [edges[index] for index in indices]
                        construction = source[name].lib["org.quintessential.construction"]
                        self.assertEqual(construction["lobeDonorCodePoint"], donor_code)
                        self.assertFalse(construction.get("coreHalfTurn", False))
                        self.assertNotIn("coreTurnSumX", construction)
                        self.assertNotIn("coreTurnSumY", construction)
                        self.assertEqual(construction["counterJoinDonorCodePoint"], 0x251 if turned else 0x62)
                        self.assertEqual(construction["family"], "arched-double-bowls" if arched else "double-bowls")
                        dx = construction["lobeOffsetX"]
                        arch_dx = construction["terminalOffsetX"] if arched and not turned else 0

                        def transform(point):
                            return point[0] + dx + arch_dx, point[1]

                        pen = QuadraticSegmentPen()
                        for start, operation, points in selected:
                            if operation == "qCurveTo":
                                replayRecording([("moveTo", (transform(start),)),
                                                 (operation, tuple(transform(point) for point in points)),
                                                 ("endPath", ())], pen)
                        references[weight, name] = pen.segments
                        assert_contains_quadratics(self, quadratic_segments(source, name), pen.segments,
                                                   1e-5, (style, name))
        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font:
                glyphs = font.getGlyphSet()
                factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                for name in DOUBLE_BOWL_FAMILY_GLYPHS:
                    light, bold = references[400, name], references[700, name]
                    self.assertEqual(len(light), len(bold))
                    expected = [tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                      for p, q in zip(first, second))
                                for first, second in zip(light, bold)]
                    assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected,
                                               0.75, (weight, name))

    def test_double_bowl_counter_roofs_depth_and_curved_shaft_approaches(self):
        # These filled-shape measurements reject 0.160's brittle upper roof,
        # rotated counter hierarchy and long square counter closures without
        # repeating the construction recipe or fixing control-point counts.
        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), \
                    instantiated(OUTPUT / VARIABLE_FILES[False], weight) as font, \
                    instantiated(DONORS / DONOR_FILES[False], weight) as donor:
                glyphs, native, cmap = font.getGlyphSet(), donor.getGlyphSet(), donor.getBestCmap()
                lobe_limits = {}
                for code in (0x25B, 0x25C):
                    ys = [y / 64 for path in polygons(native, cmap[code]) for _, y in path]
                    lobe_limits[code] = min(ys), max(ys)
                for name in DOUBLE_BOWL_FAMILY_GLYPHS:
                    with self.subTest(glyph=name):
                        code = int(name[1:], 16)
                        first = 0xF2B40 if code in ARCHED_DOUBLE_BOWL_CMAP else 0xF2B04
                        turned = (code - first) % 4 >= 2
                        counters = sorted(filled_counter_paths(polygons(glyphs, name)),
                                          key=lambda path: min(y for _, y in path))
                        self.assertEqual(len(counters), 2, (name, "missing stacked counter"))
                        bounds = [(min(y for _, y in path) / 64, max(y for _, y in path) / 64)
                                  for path in counters]
                        lobe_bottom, lobe_top = lobe_limits[0x25B if turned else 0x25C]
                        bottom_hairline = bounds[0][0] - lobe_bottom
                        top_hairline = lobe_top - bounds[1][1]
                        self.assertGreater(bottom_hairline, 20, (name, "lower hairline collapsed"))
                        self.assertLessEqual(abs(top_hairline - bottom_hairline), 1.5,
                                             (name, "upper roof must balance the lower hairline",
                                              top_hairline, bottom_hairline))
                        lower_depth = bounds[0][1] - bounds[0][0]
                        upper_depth = bounds[1][1] - bounds[1][0]
                        self.assertGreater(lower_depth, 1.1 * upper_depth,
                                           (name, "lower counter must remain visibly deeper than upper",
                                            lower_depth, upper_depth))
                        for index, (counter, (bottom, top)) in enumerate(zip(counters, bounds)):
                            # Follow the shaft-facing boundary from the waist
                            # toward the lobe extremum. A true closing quarter
                            # curves away from the shaft throughout its depth;
                            # the old long vertical closure cannot pass this.
                            fractions = (0.85, 0.5, 0.15) if index == 0 else (0.15, 0.5, 0.85)
                            approach = []
                            for fraction in fractions:
                                intervals = filled_scanline_intervals([counter], bottom + (top - bottom) * fraction)
                                self.assertEqual(len(intervals), 1, (name, index, "broken counter section"))
                                edge = intervals[0][1 if turned else 0]
                                approach.append(-edge if turned else edge)
                            self.assertGreater(approach[1] - approach[0], 3,
                                               (name, index, "square shaft-side closure", approach))
                            self.assertGreater(approach[2] - approach[1], 6,
                                               (name, index, "flat counter approach to lobe", approach))

    def test_repeated_arches_preserve_native_arch_curves_and_middle_staves(self):
        anchors = {0x6D: "uF2A51", 0x26F: "uF2A53", 0x271: "uF2A75"}
        for style, (_, italic) in STATIC_FACES.items():
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            for name, code in REPEATED_ARCH_BODY_DONORS.items():
                with self.subTest(source=style, glyph=name):
                    expected = repeated_native_curve_segments(source, anchors[code], code, italic)
                    assert_contains_quadratics(self, quadratic_segments(source, name), expected, 1e-5, (style, name))
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    glyphs, native = font.getGlyphSet(), donor.getGlyphSet()
                    for name, code in REPEATED_ARCH_BODY_DONORS.items():
                        with self.subTest(italic=italic, weight=weight, glyph=name):
                            expected = repeated_native_curve_segments(native, donor.getBestCmap()[code], code, italic)
                            assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected, 0.75,
                                                       (italic, weight, name))
                    for names, code, side, samples in (
                        (("uF2A76", "uF2A7A", "uF2A7E"), 0x271, "right",
                         (-60.37, -90.37, -120.37, -150.37, -175.37, -195.37, -210.37)),
                        (("uF2A78", "uF2A7C", "uF2A80"), 0x266, "left",
                         (540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)),
                    ):
                        for name in names:
                            with self.subTest(italic=italic, weight=weight, free_hook=name):
                                assert_translated_donor_region(self, glyphs, name, native,
                                                               donor.getBestCmap()[code], samples, side)

    def test_arched_arm_ribbons_and_bowl_counters_remain_native(self):
        references = {}
        names = [name for name in MAIN_COMPLETION_GLYPHS if name not in REPEATED_ARCH_BODY_DONORS]
        for style, (weight, italic) in STATIC_FACES.items():
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                native, cmap = donor.getGlyphSet(), donor.getBestCmap()
                for name in names:
                    with self.subTest(source=style, glyph=name):
                        bowl = name in ARCHED_BOWL_GLYPHS
                        variant = int(name[1:], 16) - (0xF2A5D if bowl else 0xF2A45)
                        turned = variant % 4 >= 2
                        code = (0x251 if turned else 0x62) if bowl else (0x279 if turned else 0x72)
                        construction = source[name].lib["org.quintessential.construction"]
                        self.assertEqual(construction["archBaseCodePoint"], 0xF2A15 + variant)
                        self.assertEqual(construction["terminalDonorCodePoint"], code)
                        dx = 0 if turned else construction["terminalOffsetX"]
                        if bowl or italic:
                            contour = 1 if bowl or turned else 0
                            selected = native_contour_edges(native, cmap[code], contour)
                        else:
                            edges = native_contour_edges(native, cmap[code])
                            selected = [*edges[18:], *edges[:4]] if turned else edges[11:16]
                        pen = QuadraticSegmentPen()
                        for start, operation, points in selected:
                            if operation == "qCurveTo":
                                replayRecording([("moveTo", ((start[0] + dx, start[1]),)),
                                                 (operation, tuple((x + dx, y) for x, y in points)), ("endPath", ())], pen)
                        references[italic, weight, name] = pen.segments
                        assert_contains_quadratics(self, quadratic_segments(source, name), pen.segments, 1e-5, (style, name))
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font:
                    glyphs = font.getGlyphSet()
                    factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                    for name in names:
                        with self.subTest(italic=italic, weight=weight, glyph=name):
                            light, bold = references[italic, 400, name], references[italic, 700, name]
                            self.assertEqual(len(light), len(bold))
                            expected = [tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                              for p, q in zip(first, second))
                                        for first, second in zip(light, bold)]
                            assert_contains_quadratics(self, quadratic_segments(glyphs, name), expected, 0.75,
                                                       (italic, weight, name))

    def test_outputs_preserve_donor_vertical_metric_selection(self):
        for italic, filename in VARIABLE_FILES.items():
            paths = [OUTPUT / filename]
            paths.extend(OUTPUT / f"QuintessentialSerif-{style}.otf" for style, (_, is_italic) in STATIC_FACES.items() if is_italic == italic)
            with TTFont(DONORS / DONOR_FILES[italic]) as donor:
                for path in paths:
                    with self.subTest(font=path.name), TTFont(path) as font:
                        self.assertEqual(font["OS/2"].fsSelection & (1 << 7), donor["OS/2"].fsSelection & (1 << 7))
                        for field in ("sTypoAscender", "sTypoDescender", "sTypoLineGap", "usWinAscent", "usWinDescent"):
                            self.assertEqual(getattr(font["OS/2"], field), getattr(donor["OS/2"], field))
                        for field in ("ascent", "descent", "lineGap"):
                            self.assertEqual(getattr(font["hhea"], field), getattr(donor["hhea"], field))

    def test_constructed_master_advances_follow_their_upper_donors(self):
        self.assertEqual(set(WIDTH_DONORS), set(LEGACY_SCRIPT_GLYPHS))
        for style, (weight, italic) in STATIC_FACES.items():
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with self.subTest(style=style), instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                donor_cmap = donor.getBestCmap()
                for target, code_point in WIDTH_DONORS.items():
                    original = donor_cmap[code_point]
                    construction = source[target].lib["org.quintessential.construction"]
                    expansion = construction.get("archExpansionX", 0)
                    if target in WIDENED_ARCH_GLYPHS:
                        self.assertGreaterEqual(expansion, 0, (style, target))
                        self.assertEqual(construction["archExpansionGap"], 50)
                        self.assertEqual(tuple(construction[key] for key in
                                               ("archExpansionContour", "archExpansionForwardEdge", "archExpansionBackwardEdge")),
                                         widening_connections(code_point, italic))
                        _, connections = expanded_native_reference(donor.getGlyphSet(), original,
                                                                    code_point, italic, expansion)
                        actual_pen = QuadraticSegmentPen(source)
                        source[target].draw(actual_pen)
                        for connection in connections:
                            expected_pen = QuadraticSegmentPen()
                            replayRecording(connection, expected_pen)
                            for expected in expected_pen.segments:
                                self.assertTrue(any(max(abs(a - b) for pa, pb in zip(actual, expected)
                                                        for a, b in zip(pa, pb)) <= 1e-5
                                                    for actual in actual_pen.segments),
                                                (style, target, "changed quadratic expansion or tangent", expected))
                    else:
                        self.assertEqual(expansion, 0, (style, target, "unexpected width change"))
                    self.assertEqual(source[target].width, round(donor["hmtx"][original][0] + expansion, 6),
                                     (style, target, original))

    def test_italic_constructed_stems_follow_the_native_axis_and_finish(self):
        constructed = ("uF2A02", "uF2A03", "uF2A04", "uF2A05", "uF2A07")
        finish_samples = (0.37, 25.37, 50.37, 75.37, 100.37, 125.37, 140.37)
        for style in ("Italic", "BoldItalic"):
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with self.subTest(source=style):
                for name in constructed:
                    construction = source[name].lib["org.quintessential.construction"]
                    self.assertEqual(construction["lowerCutY"], 150)
                    assert_italic_stem_alignment(self, source, name, source.info.italicAngle)

                offset = source["uF2A02"].lib["org.quintessential.construction"]["lowerOffsetX"]
                for y in finish_samples:
                    expected = [x + offset for x in scanline_crossings(source, "uF2A00", y)]
                    actual = scanline_crossings(source, "uF2A02", y)
                    self.assertEqual(len(actual), len(expected), (style, y, actual, expected))
                    for built_x, donor_x in zip(actual, expected):
                        self.assertLessEqual(abs(built_x - donor_x), 0.5, (style, y, built_x, donor_x))

        for weight in SAMPLE_WEIGHTS:
            with self.subTest(variable_weight=weight), instantiated(OUTPUT / VARIABLE_FILES[True], weight) as font:
                glyph_set = font.getGlyphSet()
                for name in constructed:
                    assert_italic_stem_alignment(self, glyph_set, name, font["post"].italicAngle)

                reference = scanline_crossings(glyph_set, "uF2A00", finish_samples[0])
                built = scanline_crossings(glyph_set, "uF2A02", finish_samples[0])
                self.assertEqual(len(reference), len(built))
                offset = sum(built_x - donor_x for built_x, donor_x in zip(built, reference)) / len(built)
                for y in finish_samples:
                    expected = [x + offset for x in scanline_crossings(glyph_set, "uF2A00", y)]
                    actual = scanline_crossings(glyph_set, "uF2A02", y)
                    self.assertEqual(len(actual), len(expected), (weight, y, actual, expected))
                    for built_x, donor_x in zip(actual, expected):
                        # Compiling compatible quadratic masters to gvar rounds
                        # integer points and introduces at most sub-unit drift.
                        self.assertLessEqual(abs(built_x - donor_x), 0.75, (weight, y, built_x, donor_x))

    def test_variable_structure_axis_names_and_sparse_coverage(self):
        for italic, filename in VARIABLE_FILES.items():
            with self.subTest(font=filename), TTFont(OUTPUT / filename) as font:
                self.assertEqual(font.getBestCmap(), {0x20: "space", **POSTURE_CMAPS[italic]})
                self.assertEqual(tuple(font.getGlyphOrder()), POSTURE_GLYPH_ORDERS[italic])
                self.assertEqual(font["head"].unitsPerEm, 1000)
                self.assertEqual(font["name"].getDebugName(1), "Quintessential Serif")
                self.assertEqual(font["name"].getDebugName(5), f"Version {VERSION}")
                self.assertEqual([(a.axisTag, a.minValue, a.defaultValue, a.maxValue) for a in font["fvar"].axes], [("wght", 400, 400, 700)])
                self.assertEqual(named_instances(font), EXPECTED_INSTANCE_NAMES[italic])
                self.assertEqual(font["avar"].segments, {"wght": EXPECTED_AVAR})
                for table in ("avar", "STAT", "gvar", "HVAR", "GPOS"):
                    self.assertIn(table, font)
                self.assertNotIn("CFF ", font)
                self.assertEqual(bool(font["OS/2"].fsSelection & 1), italic)
                self.assertTrue(dflt_kern_lookups(font))
                assert_unhinted(self, font)

    def test_every_script_glyph_interpolates_at_sampled_weights(self):
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    glyph_set = font.getGlyphSet()
                    for name in POSTURE_GLYPHS[italic]:
                        assert_outline_is_finite(self, glyph_set, name)

    def test_component_contours_stay_simple_and_keep_their_winding(self):
        for italic, filename in VARIABLE_FILES.items():
            reference_winding = {}
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    glyph_set = font.getGlyphSet()
                    for name in POSTURE_GLYPHS[italic]:
                        paths = polygons(glyph_set, name)
                        winding = tuple(pyclipper.Area(path) > 0 for path in paths)
                        if weight == 400:
                            reference_winding[name] = winding
                        self.assertEqual(winding, reference_winding[name], (name, "contour reversal"))
                        for index, path in enumerate(paths):
                            area = abs(pyclipper.Area(path)) / (64 * 64)
                            self.assertGreater(area, 1, (name, index, "collapsed contour"))
                            # Inspect each contour separately: native Italic has
                            # independent components whose intended overlaps
                            # must not count as self-intersections.
                            simple = pyclipper.SimplifyPolygon(path, pyclipper.PFT_NONZERO)
                            resolved_area = sum(abs(pyclipper.Area(part)) for part in simple) / (64 * 64)
                            if abs(area - resolved_area) > 0.1:
                                # Acute native shoulder corners can acquire a
                                # spurious intersection after 1/64-unit integer
                                # rounding. Keep the same subdivision and area
                                # limit, but resolve that grid error precisely.
                                pen = PolygonPen(glyph_set)
                                glyph_set[name].draw(pen)
                                for scale in (256, 1024, 4096):
                                    refined = [(round(x * scale), round(y * scale)) for x, y in pen.paths[index]]
                                    area = abs(pyclipper.Area(refined)) / (scale * scale)
                                    resolved_area = sum(abs(pyclipper.Area(part)) for part in
                                                        pyclipper.SimplifyPolygon(refined, pyclipper.PFT_NONZERO)) / (scale * scale)
                            self.assertLessEqual(abs(area - resolved_area), 0.1,
                                                 (name, index, "self-intersection", area, resolved_area))

    def test_every_arch_keeps_its_intended_cavity_at_sampled_weights(self):
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    glyph_set = font.getGlyphSet()
                    for name in ARCH_GLYPHS:
                        paths = polygons(glyph_set, name)
                        self.assertEqual(len(filled_counter_paths(paths)), int(name in JOINED_ARCH_GLYPHS),
                                         (name, "wrong open or joined arch cavity"))
                        filled = filled_shape_paths(paths)
                        # Native Italic n/h add a separate diagonal shoulder
                        # interval above this band; measure the clear cavity.
                        for y in (200.37, 225.37, 250.37):
                            intervals = filled_scanline_intervals(filled, y)
                            self.assertEqual(len(intervals), 2, (name, y, "missing two-stem cavity", intervals))
                            gap = intervals[1][0] - intervals[0][1]
                            self.assertGreater(gap, 10, (name, y, "arch cavity collapsed", gap))

    def test_arch_bodies_preserve_their_native_free_side_curves(self):
        turned = {"uF2A17", "uF2A18", "uF2A1B", "uF2A1C", "uF2A1F", "uF2A20"}
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    for target, code in ARCH_BODY_DONORS.items():
                        original = donor.getBestCmap()[code]
                        samples = ((0.37, 30.37, 60.37, 90.37, 120.37, 175.37, 220.37, 300.37)
                                   if target in turned else
                                   (0.37, 40.37, 100.37, 200.37, 300.37, 375.37, 450.37, 475.37))
                        side = slice(None, 2) if target in turned else slice(-2, None)
                        for y in samples:
                            actual = scanline_crossings(built_set, target, y)[side]
                            expected = scanline_crossings(donor_set, original, y)[side]
                            self.assertEqual(len(actual), len(expected), (target, y, actual, expected))
                            for actual_x, expected_x in zip(actual, expected):
                                self.assertLessEqual(abs(actual_x - expected_x), 0.75,
                                                     (target, original, y, actual_x, expected_x))

    def test_constructed_arch_terminals_preserve_their_native_donors(self):
        upper = {"uF2A18": 0x6C, "uF2A1C": 0x6C, "uF2A20": 0x6C}
        lower = {"uF2A16": 0x70, "uF2A1A": 0x70, "uF2A1E": 0x70,
                 "uF2A1F": 0x261, "uF2A20": 0x261}
        replaced_feet = {"uF2A1B": 0x70, "uF2A1C": 0x70}
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    for targets, samples in (
                        (upper, (510.37, 540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)),
                        (lower, (-30.37, -60.37, -100.37, -130.37, -160.37, -180.37, -200.37, -220.37, -240.37)),
                        (replaced_feet, (-60.37, -80.37, -100.37, -130.37, -160.37, -180.37, -200.37, -210.37, -220.37)),
                    ):
                        for target, code in targets.items():
                            assert_translated_donor_region(self, built_set, target, donor_set,
                                                           donor.getBestCmap()[code], samples)

                    original = donor.getBestCmap()[0x265]
                    for target in replaced_feet:
                        samples = (0.37, 25.37, 50.37, 100.37, 175.37, 250.37, 275.37)
                        if target == "uF2A1B":
                            samples += (325.37, 375.37, 425.37, 450.37, 470.37)
                        # Replacing the half-serif must preserve both native
                        # shaft edges and the arch. The plain form also keeps
                        # its native short heads above the bowl-height region.
                        for y in samples:
                            actual = scanline_crossings(built_set, target, y)
                            expected = scanline_crossings(donor_set, original, y)
                            self.assertEqual(len(actual), len(expected), (target, "turned-h body", y))
                            for actual_x, expected_x in zip(actual, expected):
                                self.assertLessEqual(abs(actual_x - expected_x), 0.75,
                                                     (target, original, y, actual_x, expected_x))

    def test_plain_bowl_keeps_b_baseline_and_upright_p_head(self):
        target = "uF2A21"
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    body, head = (donor.getBestCmap()[code] for code in (0x62, 0x70))
                    # The whole lower region, including the left baseline
                    # finish, is native b; a rotated alpha or shortened p
                    # would have different contours here.
                    for y in (-10.37, 0.37, 25.37, 50.37, 75.37, 125.37, 200.37, 275.37, 299.37):
                        actual = scanline_crossings(built_set, target, y)
                        expected = scanline_crossings(donor_set, body, y)
                        self.assertEqual(len(actual), len(expected), (target, "b baseline", y))
                        for actual_x, expected_x in zip(actual, expected):
                            self.assertLessEqual(abs(actual_x - expected_x), 0.75,
                                                 (target, body, y, actual_x, expected_x))

                    # Fit one horizontal translation from the visible head,
                    # then check its complete left entrance and upper right
                    # edge. The bowl is excluded from these comparisons.
                    actual_head = scanline_crossings(built_set, target, 470.37)[:2]
                    expected_head = scanline_crossings(donor_set, head, 470.37)[:2]
                    self.assertEqual(len(actual_head), 2)
                    self.assertEqual(len(expected_head), 2)
                    offset = sum(actual_head) / 2 - sum(expected_head) / 2
                    for edge, samples in (
                        (0, (355.37, 370.37, 385.37, 400.37, 415.37, 430.37, 445.37, 460.37, 472.37)),
                        (1, (460.37, 463.37, 466.37, 469.37, 472.37)),
                    ):
                        for y in samples:
                            actual = scanline_crossings(built_set, target, y)
                            expected = scanline_crossings(donor_set, head, y)
                            self.assertGreater(len(actual), edge, (target, "missing head", y))
                            self.assertGreater(len(expected), edge, (head, y))
                            self.assertLessEqual(abs(actual[edge] - expected[edge] - offset), 0.85,
                                                 (target, head, edge, y, actual[edge], expected[edge], offset))

                    actual_y = [y for path in polygons(built_set, target) for _, y in path]
                    body_y = [y for path in polygons(donor_set, body) for _, y in path]
                    head_y = [y for path in polygons(donor_set, head) for _, y in path]
                    self.assertLessEqual(abs(min(actual_y) - min(body_y)), 1,
                                         "plain bowl acquired a descender")
                    self.assertLessEqual(max(actual_y), max(head_y) + 1,
                                         "plain bowl acquired an ascender")

    def test_extended_arches_preserve_native_curves_and_existing_endings(self):
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    for target, body_code in EXTENDED_ARCH_BODY_DONORS.items():
                        with self.subTest(glyph=target):
                            native = donor.getBestCmap()[body_code]
                            base = TURNED_EXTENDED_ARCH_BASES.get(target)
                            reference_set, original = (built_set, base) if base else (donor_set, native)
                            # The native Italic u inner arch reaches y332, so
                            # use the unchanged right head above it to fit the
                            # rigid translation of turned forms.
                            anchor_y = 450.37 if base else 250.37
                            anchor_actual = scanline_crossings(built_set, target, anchor_y)[-2:]
                            anchor_expected = scanline_crossings(reference_set, original, anchor_y)[-2:]
                            self.assertEqual(len(anchor_actual), 2)
                            self.assertEqual(len(anchor_expected), 2)
                            shift = sum(anchor_actual) / 2 - sum(anchor_expected) / 2
                            if base:
                                # Whole-unit compilation can round the crown
                                # upward and footer downward. Fit one translation
                                # across both rigid regions, without bias toward
                                # two points sharing the same rounding direction.
                                offsets = []
                                for y in (350.37, 400.37, 450.37, 470.37,
                                          -210.37, -180.37, -140.37, -100.37, -60.37, -30.37):
                                    actual = scanline_crossings(built_set, target, y)
                                    expected = scanline_crossings(built_set, base, y)
                                    if y > 0:
                                        actual, expected = actual[-2:], expected[-2:]
                                    self.assertEqual(len(actual), len(expected), (target, "rigid shift anchors", y))
                                    offsets.extend(a - b for a, b in zip(actual, expected))
                                shift = (min(offsets) + max(offsets)) / 2
                            if target not in WIDENED_ARCH_GLYPHS:
                                self.assertLessEqual(abs(shift), 0.75, (target, "unexpected body translation", shift))
                            else:
                                self.assertGreaterEqual(shift, -0.75, (target, "arch narrowed", shift))
                            advance_difference = built["hmtx"][target][0] - donor["hmtx"][native][0]
                            self.assertLessEqual(abs(advance_difference - shift), 1.0,
                                                 (target, "advance does not follow rigid right-stave shift"))

                            expanded = target in WIDENED_ARCH_GLYPHS
                            if expanded:
                                reference_set, _ = expanded_native_reference(donor_set, native, body_code, italic, shift)
                                original = "reference"

                            def compare(y, selection=slice(None)):
                                actual = scanline_crossings(built_set, target, y)
                                expected = scanline_crossings(reference_set, original, y)
                                actual, expected = actual[selection], expected[selection]
                                self.assertEqual(len(actual), len(expected), (target, y, actual, expected))
                                for index, (actual_x, expected_x) in enumerate(zip(actual, expected)):
                                    self.assertLessEqual(abs(actual_x - expected_x), 0.75,
                                                         (target, original, y, index, actual_x, expected_x))

                            if base:
                                # The right ending is the already accepted base,
                                # with one rigid translation for a wider arch.
                                for y in (-240.37, -220.37, -210.37, -180.37, -140.37, -100.37, -60.37, -30.37):
                                    actual = scanline_crossings(built_set, target, y)
                                    expected = scanline_crossings(built_set, base, y)
                                    self.assertEqual(len(actual), len(expected), (target, "right ending", y))
                                    for actual_x, expected_x in zip(actual, expected):
                                        self.assertLessEqual(abs(actual_x - expected_x - shift), 0.75,
                                                             (target, base, "right ending", y))
                                # Widened native curves follow the independently
                                # defined two-run control movement above. A
                                # separate right-tail graft can share this band,
                                # so isolate the retained side of the arch.
                                for y in (0.37, 30.37, 60.37, 90.37):
                                    compare(y, slice(None, 1) if expanded else slice(None))
                                for y in (150.37, 175.37, 220.37, 250.37, 275.37, 299.37):
                                    compare(y, slice(None, 2) if expanded else slice(None))
                                for y in (350.37, 400.37, 450.37, 470.37):
                                    actual = scanline_crossings(built_set, target, y)[-2:]
                                    expected = scanline_crossings(built_set, base, y)[-2:]
                                    self.assertEqual(len(actual), len(expected), (target, "right head", y))
                                    for actual_x, expected_x in zip(actual, expected):
                                        self.assertLessEqual(abs(actual_x - expected_x - shift), 0.75,
                                                             (target, base, "right head", y))
                            else:
                                # Compare the complete native body and head,
                                # including both intentionally longer arch runs.
                                for y in (175.37, 200.37, 250.37, 300.37, 350.37, 375.37,
                                          430.37, 450.37, 475.37, 510.37, 570.37, 630.37, 680.37, 700.37):
                                    compare(y)

    def test_extended_arch_terminals_preserve_complete_native_regions(self):
        left_ascenders = ("uF2A2F", "uF2A30", "uF2A33", "uF2A34", "uF2A37", "uF2A38")
        left_hooks = ("uF2A3B", "uF2A3F", "uF2A43")
        right_ascenders = ("uF2A30", "uF2A34", "uF2A38")
        left_descenders = ("uF2A2E", "uF2A32", "uF2A36")
        right_descenders = ("uF2A2D", "uF2A2E", "uF2A31", "uF2A32", "uF2A33",
                            "uF2A34", "uF2A35", "uF2A36", "uF2A3F", "uF2A40")
        right_hooks = {"uF2A37": 0x261, "uF2A38": 0x261, "uF2A43": 0x261, "uF2A44": 0x261}
        upper_samples = (510.37, 540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)
        lower_samples = (-60.37, -90.37, -120.37, -150.37, -175.37, -195.37, -210.37)
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    regions = (
                        ({name: 0x6C for name in left_ascenders}, "left", upper_samples),
                        ({name: 0x266 for name in left_hooks}, "left", upper_samples),
                        ({name: 0x6C for name in right_ascenders}, "right", upper_samples),
                        ({name: 0x70 for name in left_descenders}, "left", lower_samples),
                        ({name: 0x70 for name in right_descenders}, "right", lower_samples),
                        (right_hooks, "right", lower_samples),
                    )
                    for targets, side, samples in regions:
                        for target, code in targets.items():
                            with self.subTest(glyph=target, side=side):
                                assert_translated_donor_region(self, built_set, target, donor_set,
                                                               donor.getBestCmap()[code], samples, side)

    def test_extended_arch_crowded_endings_remain_separate(self):
        regions = (
            (("uF2A2E", "uF2A32", "uF2A36"), -500, -1),
        )
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    glyph_set = font.getGlyphSet()
                    for names, bottom, top in regions:
                        for target in names:
                            with self.subTest(glyph=target):
                                clipper = pyclipper.Pyclipper()
                                clipper.AddPaths(polygons(glyph_set, target), pyclipper.PT_SUBJECT, True)
                                # The three double-straight-descender forms
                                # still retain separate full native p feet.
                                clipper.AddPath([(-128000, bottom * 64), (128000, bottom * 64),
                                                 (128000, top * 64), (-128000, top * 64)], pyclipper.PT_CLIP, True)
                                endings = clipper.Execute2(pyclipper.CT_INTERSECTION,
                                                           pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
                                self.assertEqual(len(endings.Childs), 2, (target, "endings touch"))
                                bounds = sorted((min(x for x, _ in node.Contour), max(x for x, _ in node.Contour))
                                                for node in endings.Childs)
                                gap = (bounds[1][0] - bounds[0][1]) / 64
                                self.assertGreaterEqual(gap, 49, (target, "50-unit terminal clearance lost", gap))

    def test_joined_arches_keep_native_width_sweeps_and_bowl_quarters(self):
        references = {}

        def compare_segments(actual, expected, tolerance, context):
            for segment in expected:
                distance = min(max(abs(a - b) for p, q in zip(candidate, segment)
                                   for a, b in zip(p, q)) for candidate in actual)
                self.assertLessEqual(distance, tolerance, (*context, "changed closure or native sweep", segment, distance))

        for style, (weight, italic) in STATIC_FACES.items():
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            with instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                for name in sorted(JOINED_ARCH_GLYPHS):
                    with self.subTest(source=style, glyph=name):
                        construction = source[name].lib["org.quintessential.construction"]
                        lower = name in LOWER_JOINED_ARCH_GLYPHS
                        self.assertEqual(construction["joinedTerminal"], "lower" if lower else "upper")
                        self.assertEqual(construction["closureDonorCodePoint"], 0x62 if lower else 0x64)
                        self.assertNotIn("archExpansionX", construction)
                        expected = joined_arch_reference_segments(donor, name, construction)
                        references[italic, weight, name] = expected
                        actual = QuadraticSegmentPen(source)
                        source[name].draw(actual)
                        compare_segments(actual.segments, expected, 1e-5, (style, name))

        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with instantiated(OUTPUT / filename, weight) as font, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    glyphs = font.getGlyphSet()
                    factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)
                    for name in sorted(JOINED_ARCH_GLYPHS):
                        with self.subTest(italic=italic, weight=weight, glyph=name):
                            native = donor.getBestCmap()[EXTENDED_ARCH_BODY_DONORS[name]]
                            self.assertEqual(font["hmtx"][name][0], donor["hmtx"][native][0],
                                             (name, "joined arch no longer has native advance"))
                            counters = filled_counter_paths(polygons(glyphs, name))
                            self.assertEqual(len(counters), 1, (name, "missing single closed counter"))
                            area = abs(pyclipper.Area(counters[0])) / (64 * 64)
                            self.assertGreater(area, 20_000, (name, "joined counter collapsed", area))
                            counter_y = [y / 64 for _, y in counters[0]]
                            if name in LOWER_JOINED_ARCH_GLYPHS:
                                self.assertLess(min(counter_y), -100, (name, "lower join did not close the arch cavity"))
                            else:
                                self.assertGreater(max(counter_y), 600, (name, "upper join did not close the arch cavity"))
                            light = references[italic, 400, name]
                            bold = references[italic, 700, name]
                            self.assertEqual(len(light), len(bold))
                            expected = [tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                                              for p, q in zip(first, second))
                                        for first, second in zip(light, bold)]
                            actual = QuadraticSegmentPen(glyphs)
                            glyphs[name].draw(actual)
                            compare_segments(actual.segments, expected, 0.75, (italic, weight, name))

    def test_every_bowl_keeps_one_open_counter_at_sampled_weights(self):
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    glyph_set = font.getGlyphSet()
                    for name in BOWL_GLYPHS:
                        counters = filled_counter_paths(polygons(glyph_set, name))
                        self.assertEqual(len(counters), 1, (name, "counter closed or extra hole introduced"))
                        area = abs(pyclipper.Area(counters[0])) / (64 * 64)
                        self.assertGreater(area, 20_000, (name, "counter collapsed", area))

    def test_bowl_bodies_and_counters_preserve_their_native_donors(self):
        turned = {"uF2A23", "uF2A24", "uF2A27", "uF2A28", "uF2A2B", "uF2A2C"}
        direct_bodies = {code: target for target, code in DIRECT_DONORS.items()}
        # Native gvar counter packing must preserve the authoritative sources,
        # not conceal a changed endpoint by replacing it during compilation.
        for style in STATIC_FACES:
            source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
            for target, code in BOWL_BODY_DONORS.items():
                if target in DIRECT_DONORS:
                    continue
                with self.subTest(source=style, glyph=target):
                    actual = [tuple((point.x, point.y, point.type) for point in contour.points)
                              for contour in source[target].contours[1:]]
                    expected = [tuple((point.x, point.y, point.type) for point in contour.points)
                                for contour in source[direct_bodies[code]].contours[1:]]
                    self.assertEqual(actual, expected, "authoritative native secondary contours changed")
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    for target, code in BOWL_BODY_DONORS.items():
                        original = donor.getBestCmap()[code]
                        actual_counters = filled_counter_paths(polygons(built_set, target, steps=192))
                        expected_counters = filled_counter_paths(polygons(donor_set, original, steps=192))
                        self.assertEqual(len(actual_counters), 1, (target, "built counter"))
                        self.assertEqual(len(expected_counters), 1, (original, "donor counter"))
                        area = symmetric_difference_area(actual_counters, expected_counters)
                        self.assertLessEqual(area, 1.0, (target, original, "counter geometry", area))
                        for y in (75.37, 125.37, 200.37, 300.37, 375.37, 430.37):
                            # The two free-side crossings cover both the inner
                            # and outer bowl curves, away from shaft joins.
                            side = slice(None, 2) if target in turned else slice(-2, None)
                            actual = scanline_crossings(built_set, target, y)[side]
                            expected = scanline_crossings(donor_set, original, y)[side]
                            self.assertEqual(len(actual), len(expected), (target, y, actual, expected))
                            for actual_x, expected_x in zip(actual, expected):
                                self.assertLessEqual(abs(actual_x - expected_x), 0.75,
                                                     (target, original, y, actual_x, expected_x))

    def test_constructed_bowl_terminals_preserve_their_native_donors(self):
        upper = {"uF2A29": 0x253, "uF2A2A": 0x253}
        # Matching a rigidly translated native g region also checks the full
        # hook width: the former narrow j hook and any x scaling must fail.
        lower = {"uF2A28": 0x71, "uF2A2B": 0x261, "uF2A2C": 0x261}
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    for targets, samples in (
                        (upper, (510.37, 540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)),
                        (lower, (-30.37, -60.37, -100.37, -130.37, -160.37, -180.37, -200.37, -220.37, -240.37)),
                    ):
                        for target, code in targets.items():
                            assert_translated_donor_region(self, built_set, target, donor_set,
                                                           donor.getBestCmap()[code], samples)

    def test_direct_mappings_match_stix_at_sampled_weights(self):
        for italic in (False, True):
            built_path = OUTPUT / VARIABLE_FILES[italic]
            donor_path = DONORS / DONOR_FILES[italic]
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight):
                    with instantiated(built_path, weight) as built, instantiated(donor_path, weight) as donor:
                        donor_cmap = donor.getBestCmap()
                        built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                        direct_donors = {**DIRECT_DONORS, **({"uF2A0B": 0x0279} if italic else {})}
                        for target, code_point in direct_donors.items():
                            original = donor_cmap[code_point]
                            coordinate_delta = maximum_coordinate_delta(
                                canonical_flattened_outline(built_set, target),
                                canonical_flattened_outline(donor_set, original),
                            )
                            self.assertLessEqual(coordinate_delta, 1 / 64, (target, original, coordinate_delta))
                            self.assertEqual(built["hmtx"][target], donor["hmtx"][original])

    def test_roman_turned_arm_uses_u_stem_and_retains_native_arm(self):
        for weight in SAMPLE_WEIGHTS:
            with self.subTest(weight=weight), \
                    instantiated(OUTPUT / VARIABLE_FILES[False], weight) as built, \
                    instantiated(DONORS / DONOR_FILES[False], weight) as donor:
                built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                cmap = donor.getBestCmap()
                turnr, u = cmap[0x279], cmap[0x75]
                arm_stem = scanline_crossings(donor_set, turnr, 250)
                u_stem = scanline_crossings(donor_set, u, 250)[-2:]
                offset = arm_stem[0] - u_stem[0]
                for y in (200.37, 300.37, 400.37, 430.37, 450.37, 470.37, 475.37):
                    expected = [x + offset for x in scanline_crossings(donor_set, u, y)[-2:]]
                    actual = scanline_crossings(built_set, "uF2A0B", y)
                    self.assertEqual(len(actual), len(expected), (weight, y, actual, expected))
                    for actual_x, expected_x in zip(actual, expected):
                        self.assertLessEqual(abs(actual_x - expected_x), 0.75, (weight, y, actual_x, expected_x))
                for y in (-3.37, 15.37, 30.37, 50.37, 70.37):
                    expected = [x + offset for x in scanline_crossings(donor_set, u, y)[-2:]]
                    actual = scanline_crossings(built_set, "uF2A0B", y)[-2:]
                    self.assertEqual(len(actual), len(expected), (weight, y, actual, expected))
                    for actual_x, expected_x in zip(actual, expected):
                        self.assertLessEqual(abs(actual_x - expected_x), 0.75, (weight, y, actual_x, expected_x))
                for y in (-9.37, 0.37, 30.37, 60.37, 90.37, 120.37, 140.37):
                    expected = [x for x in scanline_crossings(donor_set, turnr, y) if x < arm_stem[0] - 0.75]
                    actual = [x for x in scanline_crossings(built_set, "uF2A0B", y) if x < arm_stem[0] - 0.75]
                    self.assertEqual(len(actual), len(expected), (weight, y, actual, expected))
                    for actual_x, expected_x in zip(actual, expected):
                        self.assertLessEqual(abs(actual_x - expected_x), 0.75, (weight, y, actual_x, expected_x))
                self.assertEqual(built["hmtx"]["uF2A0B"][0], donor["hmtx"][turnr][0])

    def test_complete_arm_family_preserves_native_arm_regions(self):
        normal = ("uF2A09", "uF2A0A", "uF2A0D", "uF2A0E", "uF2A11", "uF2A12")
        turned = ("uF2A0B", "uF2A0C", "uF2A0F", "uF2A10", "uF2A13", "uF2A14")
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    slant = -math.tan(math.radians(donor["post"].italicAngle))
                    for targets, code, samples, direction in (
                        (normal, 0x72, (330.37, 360.37, 390.37, 420.37, 450.37, 470.37), 1),
                        (turned, 0x279, (-9.37, 0.37, 30.37, 60.37, 90.37, 120.37, 140.37), -1),
                    ):
                        original = donor.getBestCmap()[code]
                        stem = scanline_crossings(donor_set, original, 250.37)
                        edge = stem[-1] if direction == 1 else stem[0]
                        for target in targets:
                            compared = 0
                            for y in samples:
                                # Exclude the shaft and its newly joined edges;
                                # the free arm beyond it must stay STIX's own.
                                threshold = edge + slant * (y - 250.37) + direction * 20
                                expected = [x for x in scanline_crossings(donor_set, original, y)
                                            if direction * (x - threshold) > 0]
                                actual = [x for x in scanline_crossings(built_set, target, y)
                                          if direction * (x - threshold) > 0]
                                self.assertEqual(len(actual), len(expected), (target, y, actual, expected))
                                for actual_x, expected_x in zip(actual, expected):
                                    self.assertLessEqual(abs(actual_x - expected_x), 0.75,
                                                         (target, y, actual_x, expected_x))
                                compared += bool(expected)
                            self.assertGreaterEqual(compared, 3, (target, "insufficient arm samples"))

    def test_constructed_arm_terminals_preserve_their_native_donors(self):
        upper = {
            "uF2A0C": 0x6C, "uF2A0D": 0x6C, "uF2A0E": 0x6C,
            "uF2A10": 0x6C, "uF2A11": 0x17F, "uF2A12": 0x17F, "uF2A14": 0x6C,
        }
        lower = {
            "uF2A0A": 0x70, "uF2A0E": 0x70, "uF2A0F": 0x70,
            "uF2A10": 0x70, "uF2A12": 0x70, "uF2A13": 0x237, "uF2A14": 0x237,
        }
        for italic in (False, True):
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), \
                        instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as built, \
                        instantiated(DONORS / DONOR_FILES[italic], weight) as donor:
                    built_set, donor_set = built.getGlyphSet(), donor.getGlyphSet()
                    for targets, samples in (
                        (upper, (510.37, 540.37, 570.37, 600.37, 630.37, 650.37, 680.37, 700.37)),
                        (lower, (-30.37, -60.37, -100.37, -130.37, -160.37, -180.37, -200.37, -220.37, -240.37)),
                    ):
                        for target, code in targets.items():
                            assert_translated_donor_region(self, built_set, target, donor_set,
                                                           donor.getBestCmap()[code], samples)

    def test_static_faces_are_hinted_sparse_cff_fonts(self):
        for style, (weight, italic) in STATIC_FACES.items():
            filename = f"QuintessentialSerif-{style}.otf"
            with self.subTest(style=style), TTFont(OUTPUT / filename) as font:
                self.assertEqual(font.getBestCmap(), {0x20: "space", **POSTURE_CMAPS[italic]})
                self.assertEqual(tuple(font.getGlyphOrder()), POSTURE_GLYPH_ORDERS[italic])
                self.assertIn("CFF ", font)
                self.assertEqual(font["OS/2"].usWeightClass, weight)
                self.assertEqual(bool(font["OS/2"].fsSelection & 1), italic)
                self.assertEqual(font["name"].getDebugName(5), f"Version {VERSION}")
                self.assertEqual(font["name"].getDebugName(1), "Quintessential Serif")
                self.assertEqual(font["name"].getDebugName(2), "Bold Italic" if style == "BoldItalic" else style)
                self.assertEqual(bool(font["OS/2"].fsSelection & (1 << 5)), weight == 700)
                self.assertEqual(bool(font["OS/2"].fsSelection & (1 << 6)), style == "Regular")
                self.assertEqual(font["head"].macStyle & 0b11, (1 if weight == 700 else 0) | (2 if italic else 0))
                cff = font["CFF "].cff.topDictIndex[0]
                self.assertTrue(cff.Private.BlueValues)
                hinted = 0
                for name in POSTURE_GLYPHS[italic]:
                    charstring = cff.CharStrings[name]
                    charstring.decompile()
                    if any(operator in charstring.program for operator in ("hstem", "hstemhm", "vstem", "vstemhm", "hintmask")):
                        hinted += 1
                self.assertEqual(hinted, len(POSTURE_GLYPHS[italic]))

    def test_static_faces_match_variable_endpoints_geometrically(self):
        for style, (weight, italic) in STATIC_FACES.items():
            with self.subTest(style=style), \
                    instantiated(OUTPUT / VARIABLE_FILES[italic], weight) as variable, \
                    TTFont(OUTPUT / f"QuintessentialSerif-{style}.otf") as static:
                variable_set, static_set = variable.getGlyphSet(), static.getGlyphSet()
                for name in POSTURE_GLYPHS[italic]:
                    self.assertEqual(variable["hmtx"][name][0], static["hmtx"][name][0])
                    # Equivalent cubic and quadratic paths can subdivide the
                    # same curve differently. Refine subdivision and integer
                    # clipping precision independently before treating a
                    # near-threshold numeric result as outline drift.
                    for steps in (192, 384, 768):
                        for scale in (64, 4096, 65536):
                            area = symmetric_difference_area(
                                polygons(variable_set, name, steps=steps, scale=scale),
                                polygons(static_set, name, steps=steps, scale=scale), scale=scale,
                            )
                            if area <= 1.0:
                                break
                        if area <= 1.0:
                            break
                    self.assertLessEqual(area, 1.0, (style, name, area))

    def test_variable_kerning_clears_every_ordered_pair(self):
        for italic, filename in VARIABLE_FILES.items():
            for weight in SAMPLE_WEIGHTS:
                with self.subTest(italic=italic, weight=weight), instantiated(OUTPUT / filename, weight) as font:
                    kern = pair_values(font)
                    glyph_set = font.getGlyphSet()
                    # Flatten once per glyph; growing catalogue coverage still
                    # checks every pair without repeatedly sampling its curves.
                    shapes = {name: polygons(glyph_set, name) for name in POSTURE_GLYPHS[italic]}
                    bounds = {}
                    for name, paths in shapes.items():
                        points = [point for path in paths for point in path]
                        bounds[name] = (min(x for x, _ in points), min(y for _, y in points),
                                        max(x for x, _ in points), max(y for _, y in points))
                    for left in POSTURE_GLYPHS[italic]:
                        for right in POSTURE_GLYPHS[italic]:
                            advance = font["hmtx"][left][0] + kern.get((left, right), 0)
                            left_min_x, left_min_y, left_max_x, left_max_y = bounds[left]
                            right_min_x, right_min_y, right_max_x, right_max_y = bounds[right]
                            offset = round(advance * 64)
                            # These are the exact integer vertices and shift
                            # passed to Clipper. Disjoint or touching boxes
                            # cannot have a positive-area filled intersection.
                            if (left_max_x <= right_min_x + offset or right_max_x + offset <= left_min_x
                                    or left_max_y <= right_min_y or right_max_y <= left_min_y):
                                continue
                            self.assertFalse(outlines_overlap(shapes[left], shapes[right], advance), (italic, weight, left, right, kern.get((left, right), 0)))

    def test_woff2_files_preserve_sfnt_tables(self):
        basenames = [
            "QuintessentialSerif-Variable",
            "QuintessentialSerif-Italic-Variable",
            *[f"QuintessentialSerif-{style}" for style in STATIC_FACES],
        ]
        for basename in basenames:
            sfnt_extension = "ttf" if basename.endswith("Variable") else "otf"
            with self.subTest(font=basename), TTFont(OUTPUT / f"{basename}.{sfnt_extension}") as original:
                restored = BytesIO()
                decompress(OUTPUT / f"{basename}.woff2", restored)
                restored.seek(0)
                with TTFont(restored) as web:
                    self.assertEqual(set(original.keys()), set(web.keys()))
                    for tag in original.keys():
                        if tag in ("GlyphOrder", "head"):
                            continue
                        self.assertEqual(original.getTableData(tag), web.getTableData(tag), tag)

    def test_proof_data_manifest_and_license_metadata(self):
        proof = json.loads((OUTPUT / "proof-data.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["version"], VERSION)
        self.assertEqual(proof["unitsPerEm"], 1000)
        self.assertEqual((proof["axis"]["tag"], proof["axis"]["min"], proof["axis"]["default"], proof["axis"]["max"]), ("wght", 400, 400, 700))
        self.assertEqual(
            tuple((instance["name"], instance["value"]) for instance in proof["axis"]["instances"]),
            EXPECTED_INSTANCE_NAMES[False],
        )
        self.assertEqual(
            tuple((entry["user"], entry["source"]) for entry in proof["axis"]["designspaceMap"]),
            EXPECTED_SOURCE_AXIS_MAP,
        )
        self.assertEqual(
            {entry["from"]: entry["to"] for entry in proof["axis"]["avarMappings"]},
            EXPECTED_AVAR,
        )
        self.assertEqual(tuple(glyph["codePoint"] for glyph in proof["glyphs"]), tuple(SCRIPT_CMAP))
        self.assertEqual(len(proof["glyphs"]), 832)
        proof_ids = {glyph["codePoint"]: glyph["id"] for glyph in proof["glyphs"]}
        self.assertEqual(proof_ids, {entry["codePoint"]: entry["glyphId"] for entry in ALLOCATION_ENTRIES})
        self.assertEqual(len(set(proof_ids.values())), 832)
        legacy_codes = tuple(LEGACY_RECIPE_BY_ID[glyph["id"]] for glyph in proof["glyphs"]
                             if glyph["id"] in LEGACY_RECIPE_BY_ID)
        self.assertEqual(legacy_codes, tuple(LEGACY_RECIPE_CMAP))
        main_codes = tuple(code for code in legacy_codes if 0xF2A45 <= code <= 0xF2A80)
        self.assertEqual(main_codes, tuple(range(0xF2A45, 0xF2A81)))
        self.assertEqual(len(main_codes), 60)
        expected_new_codes = [code for family in MAIN_COMPLETION_FAMILIES.values() for code in family]
        self.assertEqual(expected_new_codes, list(main_codes))
        for family, expected_codes in MAIN_COMPLETION_FAMILIES.items():
            with self.subTest(family=family):
                self.assertEqual(len(expected_codes), 12)
                self.assertEqual(tuple(code for code in legacy_codes if code in expected_codes), expected_codes)
        self.assertEqual(tuple(code for code in legacy_codes if code >= 0xF2B00),
                         (*SPECIAL_CMAP, *ABBREVIATION_CMAP, *EXTENSION_CMAP))
        expected_faces = {(italic, weight) for italic in (False, True) for weight in (400, 500, 600, 700)}
        self.assertEqual({(face["italic"], face["weight"]) for face in proof["faces"]}, expected_faces)
        self.assertEqual(len(proof["faces"]), len(expected_faces))
        double_bowl_references = (
            {0x62, 0x70}, {0x70}, {0x251}, {0x64}, {0x62}, {0xFE},
            {0x71}, {0x64, 0x71}, {0x62, 0x253}, {0xFE, 0x253}, {0x251, 0x261}, {0x64, 0x261},
        )
        arched_double_bowl_references = (
            {0x6E, 0x62}, {0x6E, 0x70, 0x62}, {0x75, 0x251}, {0x75, 0x6C, 0x251},
            {0x68, 0x62}, {0x68, 0x70, 0x62}, {0x265, 0x70, 0x251}, {0x265, 0x6C, 0x70, 0x251},
            {0x266, 0x62}, {0x266, 0x70, 0x62}, {0x75, 0x261, 0x251}, {0x75, 0x6C, 0x261, 0x251},
        )
        bowled_spine_references = (
            {0x62, 0x70}, {0x62, 0x70}, {0x251}, {0x64}, {0x62}, {0x62, 0x70},
            {0x71}, {0x64, 0x71}, {0x62, 0x253}, {0x62, 0x70, 0x253}, {0x251, 0x261}, {0x64, 0x261},
        )
        italic_bowled_spine_references = (
            {0x70}, {0x70}, {0x251}, {0x251, 0x64}, {0x62}, {0x62, 0x70},
            {0x251, 0x71}, {0x251, 0x64, 0x71}, {0x253}, {0x70, 0x253}, {0x251, 0x261}, {0x251, 0x64, 0x261},
        )
        italic_arched_spine_references = (
            {0x6E}, {0x6E, 0x70}, {0x75, 0x251}, {0x75, 0x6C, 0x251},
            {0x68}, {0x68, 0x70}, {0x265, 0x70, 0x251}, {0x265, 0x6C, 0x70, 0x251},
            {0x266}, {0x266, 0x70}, {0x75, 0x261, 0x251}, {0x75, 0x6C, 0x261, 0x251},
        )
        for face in proof["faces"]:
            face_codes = POSTURE_CMAPS[face["italic"]]
            self.assertEqual(tuple(glyph["codePoint"] for glyph in face["glyphs"]), tuple(face_codes))
            self.assertEqual({glyph["codePoint"]: glyph["id"] for glyph in face["glyphs"]},
                             {code: proof_ids[code] for code in face_codes})
            for glyph in face["glyphs"]:
                self.assertTrue(glyph["builtPath"])
                self.assertTrue(glyph["adaptation"])
                self.assertEqual(len(glyph["bounds"]), 4)
                self.assertTrue(glyph["references"])
                recipe_code = LEGACY_RECIPE_BY_ID.get(glyph["id"])
                if recipe_code in SPECIAL_CMAP and recipe_code != 0xF2B03:
                    self.assertEqual({reference["codePoint"] for reference in glyph["references"]},
                                     {(0x6F, 0x63, 0x25B, 0x73)[recipe_code - 0xF2B00]})
                if recipe_code in OPPOSED_BOWL_CMAP:
                    self.assertFalse(face["italic"])
                    left, right = divmod(recipe_code - 0xF2B1C, 6)
                    expected = {0x250, 0x61, 0x62, (0x70, 0x62, 0x253)[left // 2],
                                (0x251, 0x71, 0x261)[right // 2]}
                    self.assertEqual({reference["codePoint"] for reference in glyph["references"]},
                                     expected | ({0x70} if left % 2 else set()) | ({0x64} if right % 2 else set()))
                if recipe_code in ARCHED_OPPOSED_BOWL_CMAP:
                    self.assertFalse(face["italic"])
                    right_arch = recipe_code >= 0xF2B7C
                    left, right = divmod(recipe_code - (0xF2B7C if right_arch else 0xF2B58), 6)
                    if right_arch:
                        expected = {0x250, 0x61, 0x62, 0x251, (0x70, 0x62, 0x253)[left // 2]}
                        expected |= ({0x70} if left % 2 else set())
                        expected |= ({0x75}, {0x75, 0x6C}, {0x265, 0x70},
                                     {0x265, 0x70, 0x6C}, {0x75, 0x261}, {0x75, 0x261, 0x6C})[right]
                    else:
                        expected = {0x250, 0x61, 0x62, (0x251, 0x71, 0x261)[right // 2],
                                    (0x6E, 0x68, 0x266)[left // 2]}
                        expected |= ({0x70} if left % 2 else set()) | ({0x64} if right % 2 else set())
                    self.assertEqual({reference["codePoint"] for reference in glyph["references"]}, expected)
                if recipe_code in DOUBLE_BOWL_FAMILY_CMAP:
                    self.assertFalse(face["italic"])
                    if recipe_code in DOUBLE_BOWL_CMAP:
                        variant = recipe_code - 0xF2B04
                        expected = double_bowl_references[variant]
                    else:
                        variant = recipe_code - 0xF2B40
                        expected = arched_double_bowl_references[variant]
                    lobe_donor = 0x25B if variant % 4 >= 2 else 0x25C
                    counter_donor = 0x251 if variant % 4 >= 2 else 0x62
                    self.assertEqual({reference["codePoint"] for reference in glyph["references"]},
                                     expected | {lobe_donor, counter_donor})
                if recipe_code in BOWLED_SPINE_FAMILY_CMAP and not face["italic"]:
                    if recipe_code in BOWLED_SPINE_CMAP:
                        variant = recipe_code - 0xF2B10
                        expected = bowled_spine_references[variant]
                    else:
                        variant = recipe_code - 0xF2B4C
                        expected = arched_double_bowl_references[variant]
                    spine_donor = 0x61 if variant % 4 >= 2 else 0x250
                    self.assertEqual({reference["codePoint"] for reference in glyph["references"]},
                                     expected | {spine_donor} | ({0x25B} if variant % 4 < 2 else set()))
                if recipe_code in BOWLED_SPINE_FAMILY_CMAP and face["italic"]:
                    references = {reference["codePoint"] for reference in glyph["references"]}
                    self.assertIn(0x250, references, "Italic spine belly comes from native turned a")
                    self.assertNotIn(0x61, references, "Single-storey Italic a is not the spine-belly donor")
                    if recipe_code in ARCHED_BOWLED_SPINE_CMAP:
                        variant = recipe_code - 0xF2B4C
                        expected = italic_arched_spine_references[variant]
                    else:
                        variant = recipe_code - 0xF2B10
                        expected = italic_bowled_spine_references[variant]
                    self.assertEqual(references, expected | {0x250} | ({0x25B} if variant % 4 < 2 else set()))
                if recipe_code == 0xF2A0B:
                    self.assertEqual(
                        {reference["codePoint"] for reference in glyph["references"]},
                        {0x279} if face["italic"] else {0x279, 0x75},
                    )
                if recipe_code == 0xF2A21:
                    self.assertEqual(
                        {reference["codePoint"] for reference in glyph["references"]}, {0x62, 0x70},
                    )
                if recipe_code in (0xF2A1B, 0xF2A1C):
                    self.assertEqual(
                        {reference["codePoint"] for reference in glyph["references"]},
                        {0x265, 0x70} | ({0x6C} if recipe_code == 0xF2A1C else set()),
                    )
                name = ALLOCATION_BY_ID[glyph["id"]]["glyphName"]
                if name in EXTENDED_ARCH_BODY_DONORS:
                    expected = {EXTENDED_ARCH_BODY_DONORS[name]}
                    if name in TURNED_EXTENDED_ARCH_BASES:
                        expected.add(0x266 if recipe_code >= 0xF2A3B else 0x6C)
                        base = TURNED_EXTENDED_ARCH_BASES[name]
                        if base in ("uF2A18", "uF2A1C", "uF2A20"):
                            expected.add(0x6C)
                        if base in ("uF2A1B", "uF2A1C"):
                            expected.add(0x70)
                        if base in ("uF2A1F", "uF2A20"):
                            expected.add(0x261)
                    elif name in LOWER_JOINED_ARCH_GLYPHS:
                        expected.add(0x62)
                    elif name not in DIRECT_DONORS:
                        expected.add(0x70)
                    if name in UPPER_JOINED_ARCH_GLYPHS:
                        expected.add(0x64)
                    self.assertEqual({reference["codePoint"] for reference in glyph["references"]}, expected)
                if recipe_code in (0xF2A2B, 0xF2A2C):
                    self.assertEqual(
                        {reference["codePoint"] for reference in glyph["references"]},
                        {BOWL_BODY_DONORS[name], 0x261},
                    )
                if recipe_code in (0xF2A29, 0xF2A2A):
                    self.assertEqual(
                        {reference["codePoint"] for reference in glyph["references"]},
                        {BOWL_BODY_DONORS[name], 0x253},
                    )
                for reference in glyph["references"]:
                    self.assertIn(reference["codePoint"], (0x006F, 0x0063, 0x0073, 0x0131, 0x006C, 0x017F, 0x0070, 0x0237, 0x0283, 0x0072, 0x0279, 0x0075, 0x0061, 0x0250, 0x0062, 0x0064, 0x0071, 0x0251, 0x0252, 0x0253, 0x0254, 0x025B, 0x025C, 0x0261, 0x00FE, 0x006E, 0x0068, 0x0265, 0x0266, 0x019E, 0x014B, 0xA727, 0x0267, 0x006D, 0x026F, 0x0271))
                    self.assertTrue(reference["path"])
                    self.assertEqual(len(reference["bounds"]), 4)

        manifest = json.loads((OUTPUT / "build-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["family"], "Quintessential Serif")
        self.assertEqual(manifest["version"], VERSION)
        self.assertEqual(manifest["base"]["version"], "2.13 b171")
        self.assertEqual(
            hashlib.sha256((ROOT / manifest["base"]["manifest"]).read_bytes()).hexdigest(),
            manifest["base"]["manifestSha256"],
        )
        self.assertEqual(
            (manifest["axis"]["tag"], manifest["axis"]["minimum"], manifest["axis"]["default"], manifest["axis"]["maximum"]),
            ("wght", 400, 400, 700),
        )
        self.assertEqual(tuple(map(tuple, manifest["axis"]["designspaceMap"])), EXPECTED_SOURCE_AXIS_MAP)
        self.assertEqual(manifest["characters"], ["U+0020", *[f"U+{code:X}" for code in SCRIPT_CMAP]])
        self.assertEqual(manifest["charactersByPosture"], {
            "Roman": ["U+0020", *[f"U+{code:X}" for code in SCRIPT_CMAP]],
            "Italic": ["U+0020", *[f"U+{code:X}" for code in POSTURE_CMAPS[True]]],
        })
        expected_output_names = {
            *VARIABLE_FILES.values(),
            *(filename.replace(".ttf", ".woff2") for filename in VARIABLE_FILES.values()),
            *(f"QuintessentialSerif-{style}.{extension}" for style in STATIC_FACES for extension in ("otf", "woff2")),
            "OFL.txt", "FONTLOG.txt", "TRADEMARKS.txt", "proof-data.json",
        }
        self.assertEqual(set(manifest["outputs"]), expected_output_names)
        for name, record in manifest["outputs"].items():
            data = (OUTPUT / name).read_bytes()
            self.assertEqual(len(data), record["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
        self.assertTrue({"tools/stix_repeated_arch.py", "tools/stix_arched_terminals.py", "tools/stix_double_bowl.py",
                         "tools/stix_bowled_spine.py", "tools/stix_bowled_spine_normal.py",
                         "tools/stix_bowled_spine_italic.py", "tools/stix_bowled_spine_italic_normal.py",
                         "tools/stix_opposed_bowls.py", "tools/stix_arched_opposed_bowls.py", "tools/stix_extensions.py",
                         "tools/stix_middle_legs.py", "tools/stix_middle_terminals.py", "tools/stix_middle_hook_joins.py",
                         "tools/stix_stemless.py",
                         "resources/quintessential-latin-allocation.json"}
                        <= set(manifest["sources"]))
        for name, digest in manifest["sources"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

        for filename in (*VARIABLE_FILES.values(), *[f"QuintessentialSerif-{style}.otf" for style in STATIC_FACES]):
            with TTFont(OUTPUT / filename) as font:
                self.assertEqual(font["OS/2"].fsType, 0)
                self.assertIn("Open Font License", font["name"].getDebugName(13))
                self.assertIn("STIX", font["name"].getDebugName(10))


if __name__ == "__main__":
    unittest.main()

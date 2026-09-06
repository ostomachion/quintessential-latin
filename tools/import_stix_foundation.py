#!/usr/bin/env python3
"""Create the STIX Two based Quintessential Serif endpoint masters.

This is a deliberate source-bootstrap command, not part of the routine build.
It derives four small UFOs and two designspaces from the pinned STIX Two Text
variable fonts. Direct mappings retain native outlines and advances. The
constructed glyphs use the same splice recipe at both weight endpoints so the
result remains interpolation-compatible.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil

from fontPens.flattenPen import FlattenPen
from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.designspaceLib import (
    AxisDescriptor,
    AxisLabelDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)
from fontTools.misc.bezierTools import solveCubic, splitCubicAtT
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import (
    DecomposingRecordingPen,
    RecordingPen,
    replayRecording,
)
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from quintessential_font import (
    AXIS_DEFAULT,
    AXIS_MAP,
    AXIS_MAXIMUM,
    AXIS_MINIMUM,
    AXIS_NAME,
    AXIS_TAG,
    DONOR_MANIFEST,
    DONORS,
    FAMILY_NAME,
    GLYPHS,
    GLYPH_ORDER,
    glyphs_for_posture,
    glyph_order_for_posture,
    MASTERS,
    NAMED_WEIGHTS,
    POSTURES,
    ROOT,
    SOURCES,
    SOURCE_DATE_EPOCH,
    VENDOR_ID,
    VERSION,
    VERSION_MAJOR,
    VERSION_MINOR,
    posture_by_name,
)

Point = tuple[float, float]
UPPER_CUT = 300.0
LOWER_CUT = 100.0
ITALIC_LOWER_CUT = 150.0
MIN_INK_GAP = 10.0
QUADRATIC_ERROR = 0.001
ROUND_DIGITS = 6


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point
    controls: tuple[Point, ...] = ()

    @property
    def kind(self) -> str:
        return "curveTo" if self.controls else "lineTo"

    def operation(self) -> tuple[str, tuple[Point, ...]]:
        return self.kind, (*self.controls, self.end)

    def reversed(self) -> "Segment":
        return Segment(self.end, self.start, tuple(reversed(self.controls)))

    def translated(self, dx: float) -> "Segment":
        move = lambda point: (point[0] + dx, point[1])
        return Segment(move(self.start), move(self.end), tuple(move(point) for point in self.controls))

    def point(self, t: float) -> Point:
        if not self.controls:
            return (
                self.start[0] + (self.end[0] - self.start[0]) * t,
                self.start[1] + (self.end[1] - self.start[1]) * t,
            )
        p0, p1, p2, p3 = self.start, *self.controls, self.end
        mt = 1.0 - t
        return (
            mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0],
            mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1],
        )


@dataclass(frozen=True)
class OpenPath:
    start: Point
    segments: tuple[Segment, ...]

    @property
    def end(self) -> Point:
        return self.segments[-1].end

    def reversed(self) -> "OpenPath":
        segments = tuple(segment.reversed() for segment in reversed(self.segments))
        return OpenPath(segments[0].start, segments)

    def translated(self, dx: float) -> "OpenPath":
        segments = tuple(segment.translated(dx) for segment in self.segments)
        return OpenPath((self.start[0] + dx, self.start[1]), segments)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def donor_paths_from_manifest() -> dict[str, Path]:
    if not DONOR_MANIFEST.exists():
        raise SystemExit(f"Missing pinned donor manifest: {DONOR_MANIFEST}")
    manifest = json.loads(DONOR_MANIFEST.read_text(encoding="utf-8"))
    records = {record["style"]: record for record in manifest["donors"]}
    paths: dict[str, Path] = {}
    for posture in POSTURES:
        record = records[posture.name]
        if record["filename"] != posture.donor_filename:
            raise SystemExit(f"Unexpected {posture.name} donor filename in source manifest")
        path = DONORS / record["filename"]
        if not path.exists() or sha256(path) != record["sha256"]:
            raise SystemExit(f"Pinned donor checksum mismatch: {path}")
        paths[posture.name] = path
    return paths


def rounded(value: float) -> float | int:
    value = round(float(value), ROUND_DIGITS)
    nearest = round(value)
    return nearest if abs(value - nearest) < 10 ** -ROUND_DIGITS else value


def rounded_recording(recording: list[tuple[str, tuple]]) -> list[tuple[str, tuple]]:
    result = []
    for operation, operands in recording:
        if operation == "addComponent":
            raise RuntimeError("Donor decomposition left a component behind")
        result.append((
            operation,
            tuple((rounded(point[0]), rounded(point[1])) for point in operands),
        ))
    return result


def decomposed_recording(font: TTFont, glyph_name: str) -> list[tuple[str, tuple]]:
    glyph_set = font.getGlyphSet()
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return rounded_recording(pen.value)


def cubic_recording(font: TTFont, glyph_name: str) -> list[tuple[str, tuple]]:
    source = decomposed_recording(font, glyph_name)
    cubic = RecordingPen()
    replayRecording(source, Qu2CuPen(cubic, 1e-6, all_cubic=True))
    return rounded_recording(cubic.value)


def recording_contours(recording: list[tuple[str, tuple]]) -> list[list[Segment]]:
    contours: list[list[Segment]] = []
    segments: list[Segment] | None = None
    start: Point | None = None
    current: Point | None = None
    for operation, operands in recording:
        if operation == "moveTo":
            if segments is not None:
                raise ValueError("Nested moveTo in closed donor outline")
            start = current = operands[0]
            segments = []
        elif operation == "lineTo":
            assert segments is not None and current is not None
            segment = Segment(current, operands[0])
            segments.append(segment)
            current = segment.end
        elif operation == "curveTo":
            assert segments is not None and current is not None
            if len(operands) != 3:
                raise ValueError("Cubic conversion produced a non-cubic curveTo")
            segment = Segment(current, operands[-1], tuple(operands[:-1]))
            segments.append(segment)
            current = segment.end
        elif operation == "closePath":
            assert segments is not None and start is not None and current is not None
            if current != start:
                segments.append(Segment(current, start))
            contours.append(segments)
            segments = None
            start = current = None
        else:
            raise ValueError(f"Unsupported outline operation: {operation}")
    if segments is not None:
        raise ValueError("Open contour in donor outline")
    return contours


def roots_at_y(segment: Segment, y: float) -> list[float]:
    if not segment.controls:
        dy = segment.end[1] - segment.start[1]
        if abs(dy) < 1e-9:
            return []
        t = (y - segment.start[1]) / dy
        return [t] if 1e-8 < t < 1 - 1e-8 else []
    p0, p1, p2, p3 = segment.start, *segment.controls, segment.end
    coefficients = (
        -p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1],
        3 * p0[1] - 6 * p1[1] + 3 * p2[1],
        -3 * p0[1] + 3 * p1[1],
        p0[1] - y,
    )
    result = []
    for root in solveCubic(*coefficients):
        if isinstance(root, complex):
            if abs(root.imag) > 1e-8:
                continue
            root = root.real
        root = float(root)
        if 1e-8 < root < 1 - 1e-8 and all(abs(root - old) > 1e-7 for old in result):
            result.append(root)
    return sorted(result)


def split_at_y(segment: Segment, y: float) -> list[Segment]:
    roots = roots_at_y(segment, y)
    if not roots:
        return [segment]
    if not segment.controls:
        points = [segment.start, *(segment.point(root) for root in roots), segment.end]
        return [Segment(first, second) for first, second in zip(points, points[1:])]
    pieces = splitCubicAtT(segment.start, *segment.controls, segment.end, *roots)
    return [Segment(piece[0], piece[3], (piece[1], piece[2])) for piece in pieces]


def region_runs(contour: list[Segment], y: float, keep_above: bool) -> list[OpenPath]:
    pieces = [piece for segment in contour for piece in split_at_y(segment, y)]
    selected = [piece.point(0.5)[1] >= y if keep_above else piece.point(0.5)[1] <= y for piece in pieces]
    if all(selected):
        return [OpenPath(pieces[0].start, tuple(pieces))]
    starts = [index for index, flag in enumerate(selected) if flag and not selected[index - 1]]
    runs = []
    for start_index in starts:
        run = []
        index = start_index
        while selected[index]:
            run.append(pieces[index])
            index = (index + 1) % len(pieces)
            if index == start_index:
                break
        runs.append(OpenPath(run[0].start, tuple(run)))
    return runs


def extract_region(font: TTFont, code_point: int, y: float, keep_above: bool) -> OpenPath:
    glyph_name = font.getBestCmap()[code_point]
    contours = recording_contours(cubic_recording(font, glyph_name))
    runs = [run for contour in contours for run in region_runs(contour, y, keep_above)]
    if not runs:
        raise RuntimeError(f"U+{code_point:04X} has no {'upper' if keep_above else 'lower'} region at y={y}")

    def extrema(run: OpenPath) -> tuple[float, float]:
        points = [run.start]
        for segment in run.segments:
            points.extend((*segment.controls, segment.end))
        ys = [point[1] for point in points]
        return min(ys), max(ys)

    # The highest run excludes a long-s crossbar; the lowest run selects the
    # p descender rather than the separately connected bowl.
    return max(runs, key=lambda run: extrema(run)[1]) if keep_above else min(runs, key=lambda run: extrema(run)[0])


def p_descender_region(font: TTFont, cut_y: float) -> OpenPath:
    """Return only p's lower shaft and foot, never its bowl or shoulder."""
    glyph_name = font.getBestCmap()[0x70]
    contours = recording_contours(cubic_recording(font, glyph_name))
    italic = font["post"].italicAngle != 0
    if italic:
        # STIX italic p draws its bowl and diagonal descender stem as separate
        # contours. The lower run of the second contour is already exactly the
        # straight shaft and native foot that this component needs.
        runs = region_runs(contours[1], cut_y, keep_above=False)
        if len(runs) != 1:
            raise RuntimeError("Unexpected italic-p descender topology")
        return runs[0]

    # In the Roman p the bowl and descender share one contour. Isolate the
    # native lower-foot arc explicitly: extend the inner shaft edge straight
    # to the join, retain the complete foot/serif around the bottom, and stop
    # on the outer shaft edge. These segment positions are compatible in both
    # pinned STIX endpoint masters and are asserted before use.
    outer = contours[0]
    if len(outer) != 30:
        raise RuntimeError("Unexpected Roman-p contour topology")
    outer_edge = outer[4]
    inner_edge = outer[25]
    if (
        outer_edge.kind != "lineTo"
        or inner_edge.kind != "lineTo"
        or abs(outer_edge.start[0] - outer_edge.end[0]) > 1e-6
        or abs(inner_edge.start[0] - inner_edge.end[0]) > 1e-6
        or not (outer_edge.start[1] < cut_y < outer_edge.end[1])
        or inner_edge.start[1] >= cut_y
    ):
        raise RuntimeError("Pinned Roman-p shaft edges no longer match the splice recipe")
    outer_pieces = split_at_y(outer_edge, cut_y)
    outer_lower = next(
        piece for piece in outer_pieces
        if piece.start[1] < cut_y and abs(piece.end[1] - cut_y) < 1e-5
    )
    start = (inner_edge.start[0], cut_y)
    segments = (
        Segment(start, inner_edge.start),
        *outer[25:],
        *outer[:4],
        outer_lower,
    )
    return OpenPath(start, tuple(segments))


def roman_turned_arm_outline(font: TTFont) -> tuple[list[tuple[str, tuple]], float]:
    """Retain turnr's arm but replace its rotated serifs with u's right stem."""
    cmap = font.getBestCmap()
    arm = decomposed_recording(font, cmap[0x279])
    u = decomposed_recording(font, cmap[0x75])
    if len(arm) != 21 or len(u) != 25:
        raise RuntimeError("Unexpected Roman turned-r/u donor topology")
    # Both pinned endpoint donors have equal stem widths. Translate the entire
    # native quadratic region directly, avoiding even a curve round-trip that
    # could change off-curve points when the variable font rounds its masters.
    arm_inner, arm_outer = arm[5][1][-1][0], arm[11][1][-1][0]
    u_inner, u_outer = u[10][1][-1][0], u[15][1][-1][0]
    offset = arm_inner - u_inner
    if (arm_outer - arm_inner != u_outer - u_inner
            or any(item[0] != "lineTo" for item in (arm[5], arm[11], arm[18], u[10], u[15], u[20]))):
        raise RuntimeError("Roman turned-r/u shaft edges no longer match")
    stem = [(operation, tuple((x + offset, y) for x, y in points)) for operation, points in u[10:21]]
    # The two existing arm curves end at different heights from u's bowl.
    # Extend only the straight shaft edges to those attachment heights; retain
    # every control point of the ball, arm, head serif, and baseline exit.
    return_point = (stem[-1][1][-1][0], arm[18][1][-1][1])
    recording = [
        *arm[:5],
        *stem,
        ("lineTo", (return_point,)),
        *arm[18:],
    ]
    return rounded_recording(recording), rounded(offset)


def endpoint_slope(segment: Segment, at_start: bool) -> float:
    if not segment.controls:
        first, second = (segment.start, segment.end) if at_start else (segment.end, segment.start)
    elif at_start:
        first, second = segment.start, segment.controls[0]
    else:
        first, second = segment.end, segment.controls[-1]
    dy = second[1] - first[1]
    if abs(dy) < 1e-7:
        chord_dy = segment.end[1] - segment.start[1]
        return 0.0 if abs(chord_dy) < 1e-7 else (segment.end[0] - segment.start[0]) / chord_dy
    return (second[0] - first[0]) / dy


def tangent_connector(start: Point, end: Point, start_slope: float, end_slope: float) -> Segment:
    third_y = (end[1] - start[1]) / 3.0
    controls = (
        (start[0] + third_y * start_slope, start[1] + third_y),
        (end[0] - third_y * end_slope, end[1] - third_y),
    )
    return Segment(start, end, controls)


def compose_outline(
    font: TTFont,
    upper_code_point: int,
    lower_code_point: int,
) -> tuple[list[tuple[str, tuple]], float, float]:
    italic_angle = float(font["post"].italicAngle)
    lower_cut = ITALIC_LOWER_CUT if italic_angle else LOWER_CUT
    upper = extract_region(font, upper_code_point, UPPER_CUT, keep_above=True)
    lower = (
        p_descender_region(font, lower_cut)
        if lower_code_point == 0x70
        else extract_region(font, lower_code_point, lower_cut, keep_above=False)
    )
    if upper.start[0] > upper.end[0]:
        upper = upper.reversed()
    if lower.start[0] < lower.end[0]:
        lower = lower.reversed()

    upper_center = (upper.start[0] + upper.end[0]) / 2.0
    lower_center = (lower.start[0] + lower.end[0]) / 2.0
    # Preserve the Roman construction while placing italic lower donors on the
    # font's native slant axis. Centering the two cuts at the same x forces the
    # endpoint-tangent connectors into an S curve in an italic face.
    axis_slope = -math.tan(math.radians(italic_angle))
    target_lower_center = upper_center - axis_slope * (UPPER_CUT - lower_cut)
    lower_dx = target_lower_center - lower_center
    lower = lower.translated(lower_dx)

    right_join = tangent_connector(
        upper.end,
        lower.start,
        endpoint_slope(upper.segments[-1], at_start=False),
        endpoint_slope(lower.segments[0], at_start=True),
    )
    left_join = tangent_connector(
        lower.end,
        upper.start,
        endpoint_slope(lower.segments[-1], at_start=False),
        endpoint_slope(upper.segments[0], at_start=True),
    )
    operations: list[tuple[str, tuple]] = [("moveTo", (upper.start,))]
    operations.extend(segment.operation() for segment in upper.segments)
    operations.append(right_join.operation())
    operations.extend(segment.operation() for segment in lower.segments)
    operations.append(left_join.operation())
    operations.append(("closePath", ()))
    # Preserve the metadata's numeric shape across regenerations.  The original
    # Roman sources record their y=100 cut as a real, and keeping the selected
    # cut as a float prevents an italic-only recipe change from rewriting those
    # otherwise unchanged GLIF files.
    return rounded_recording(operations), rounded(lower_dx), float(lower_cut)


def glyph_recording(glyph) -> list[tuple[str, tuple]]:
    pen = RecordingPen()
    glyph.draw(pen)
    return rounded_recording(pen.value)


@dataclass(frozen=True)
class NativePath:
    """An open donor recording whose quadratic control points stay intact."""
    start: Point
    operations: tuple[tuple[str, tuple], ...]

    @property
    def end(self) -> Point:
        return self.operations[-1][1][-1]

    @property
    def center(self) -> float:
        return (self.start[0] + self.end[0]) / 2

    def translated(self, dx: float) -> "NativePath":
        return NativePath((self.start[0] + dx, self.start[1]), tuple(
            (op, tuple((x + dx, y) for x, y in points)) for op, points in self.operations
        ))

    def slope(self, at_start: bool) -> float:
        if at_start:
            first, second = self.start, self.operations[0][1][0]
        else:
            points = self.operations[-1][1]
            first = points[-2] if len(points) > 1 else self.operations[-2][1][-1]
            second = self.end
        return (second[0] - first[0]) / (second[1] - first[1])


def native_region(recording, y: float, above: bool, contour_index: int = 0) -> NativePath:
    """Cut only straight shaft edges, never re-fit a native quadratic curve."""
    contours, current = [], []
    start = previous = None
    for op, points in recording:
        if op == "moveTo":
            start = previous = points[0]
            current = []
        elif op == "closePath":
            if previous != start:
                current.append((previous, "lineTo", (start,)))
            contours.append(current)
        else:
            current.append((previous, op, points))
            previous = points[-1]
    pieces = []
    for start, op, points in contours[contour_index]:
        end = points[-1]
        low = min(point[1] for point in (start, *points))
        high = max(point[1] for point in (start, *points))
        if low < y < high:
            if op != "lineTo":
                raise RuntimeError(f"Native curve crosses shaft cut y={y}: {op} {points}")
            t = (y - start[1]) / (end[1] - start[1])
            split = (start[0] + t * (end[0] - start[0]), y)
            pieces.extend(((start, op, (split,)), (split, op, (end,))))
        else:
            pieces.append((start, op, points))
    selected = [((start[1] + points[-1][1]) / 2 >= y if above
                 else (start[1] + points[-1][1]) / 2 <= y)
                for start, _, points in pieces]
    starts = [i for i, flag in enumerate(selected) if flag and not selected[i - 1]]
    if len(starts) != 1:
        raise RuntimeError(f"Expected one native shaft region at y={y}, found {len(starts)}")
    index, operations = starts[0], []
    start = pieces[index][0]
    while selected[index]:
        _, op, points = pieces[index]
        operations.append((op, points))
        index = (index + 1) % len(pieces)
    path = NativePath(start, tuple(operations))
    if (path.start[0] < path.end[0]) != above:
        raise RuntimeError("Unexpected native donor contour direction")
    return path


def native_terminal(font: TTFont, code: int, y: float, above: bool) -> NativePath:
    recording = decomposed_recording(font, font.getBestCmap()[code])
    if code == 0x70 and not font["post"].italicAngle:
        # p's Roman bowl shares its outer contour. Keep only the complete foot
        # between its two straight shaft edges, retaining the native q-curves.
        if len(recording) != 27:
            raise RuntimeError("Unexpected Roman p topology")
        right, left = recording[17][1][-1][0], recording[3][1][-1][0]
        return NativePath((right, y), (
            recording[17], recording[18], ("lineTo", recording[0][1]),
            *recording[1:4], ("lineTo", ((left, y),)),
        ))
    return native_region(recording, y, above, 1 if code == 0x70 else 0)


def join_native_regions(upper: NativePath, lower: NativePath) -> list[tuple[str, tuple]]:
    right = tangent_connector(upper.end, lower.start, upper.slope(False), lower.slope(True))
    left = tangent_connector(lower.end, upper.start, lower.slope(False), upper.slope(True))
    return rounded_recording([
        ("moveTo", (upper.start,)), *upper.operations, right.operation(),
        *lower.operations, left.operation(), ("closePath", ()),
    ])


# The basic Arms family is a twelve-form product of orientation and stem endings.
ARM_RECIPES = {
    0xF2A0A: (False, None, 0x70),
    0xF2A0C: (True, 0x6C, None),
    0xF2A0D: (False, 0x6C, None),
    0xF2A0E: (False, 0x6C, 0x70),
    0xF2A0F: (True, None, 0x70),
    0xF2A10: (True, 0x6C, 0x70),
    0xF2A11: (False, 0x17F, None),
    0xF2A12: (False, 0x17F, 0x70),
    0xF2A13: (True, None, 0x237),
    0xF2A14: (True, 0x6C, 0x237),
}


def arm_outline(font: TTFont, code_point: int) -> tuple[list[tuple[str, tuple]], dict]:
    """Splice native stem terminals while retaining the arm's donor curves.

    Roman arms share a contour with their shaft, so the two orientations use
    complementary, explicitly bounded splices. Italic arms are separate donor
    contours; keep them unchanged and construct only their companion shaft.
    All indices are contracts with the two hash-pinned endpoint donors.
    """
    turned, upper_code, lower_code = ARM_RECIPES[code_point]
    arm_code = 0x279 if turned else 0x72
    italic = bool(font["post"].italicAngle)
    base = decomposed_recording(font, font.getBestCmap()[arm_code])
    metadata = {"armDonorCodePoint": arm_code, "upperDonorCodePoint": upper_code,
                "lowerDonorCodePoint": lower_code}

    if italic:
        # Keep the donor's independent arm contour byte-for-byte through source
        # construction. The stem runs on STIX's native italic axis.
        split = next(i for i, (op, _) in enumerate(base[1:], 1) if op == "moveTo")
        arm = base[split:] if turned else base[:split]
        stem = base[:split] if turned else base[split:]
        upper = (native_terminal(font, upper_code, UPPER_CUT, True) if upper_code
                 else native_region(stem, UPPER_CUT, True))
        native_upper = native_region(stem, UPPER_CUT, True)
        upper_dx = native_upper.center - upper.center
        upper = upper.translated(upper_dx)
        # The turned-r baseline curve rises to y=214. Preserve it whole by
        # cutting the native shaft above it, at y=220, for the ascender-only form.
        lower_cut = 220.0 if turned and not lower_code else ITALIC_LOWER_CUT
        lower = (native_terminal(font, lower_code, lower_cut, False) if lower_code
                 else native_region(stem, lower_cut, False))
        slope = -math.tan(math.radians(font["post"].italicAngle))
        lower_dx = upper.center - slope * (UPPER_CUT - lower_cut) - lower.center
        recording = [*join_native_regions(upper, lower.translated(lower_dx)), *arm]
        metadata.update(upperCutY=UPPER_CUT, lowerCutY=lower_cut,
                        upperOffsetX=rounded(upper_dx), lowerOffsetX=rounded(lower_dx))
        return rounded_recording(recording), metadata

    if turned:
        base, _ = roman_turned_arm_outline(font)
        if len(base) != 20:
            raise RuntimeError("Unexpected corrected Roman turned-arm topology")
        shaft_center = (base[4][1][-1][0] + base[9][1][-1][0]) / 2
        recording = base[:5]  # Native ball and upper arm curve.
        if upper_code:
            upper = native_terminal(font, upper_code, UPPER_CUT, True)
            dx = shaft_center - upper.center
            upper = upper.translated(dx)
            recording += [("lineTo", (upper.start,)), *upper.operations]
            metadata.update(upperCutY=UPPER_CUT, upperOffsetX=rounded(dx))
        else:
            recording += base[5:10]  # Upright native u head.
        if lower_code:
            cut = float(base[16][1][-1][1])
            lower = native_terminal(font, lower_code, cut, False)
            dx = shaft_center - lower.center
            lower = lower.translated(dx)
            recording += [("lineTo", (lower.start,)), *lower.operations, *base[17:]]
            metadata.update(lowerCutY=cut, lowerOffsetX=rounded(dx))
        else:
            recording += base[10:]
        return rounded_recording(recording), metadata

    if len(base) != 20:
        raise RuntimeError("Unexpected Roman r topology")
    if upper_code:
        cut = float(base[10][1][-1][1])
        upper = native_terminal(font, upper_code, cut, True)
        shaft_center = (base[3][1][-1][0] + base[16][1][-1][0]) / 2
        dx = shaft_center - upper.center
        upper = upper.translated(dx)
        # The tiny native shoulder-entry line terminates inside the shaft;
        # join its outer endpoint directly, retaining every arm curve.
        base = [*base[:4], ("lineTo", (upper.start,)), *upper.operations, *base[11:]]
        metadata.update(upperCutY=cut, upperOffsetX=rounded(dx))
    if lower_code:
        upper = native_region(base, UPPER_CUT, True)
        lower = native_terminal(font, 0x70, LOWER_CUT, False)
        dx = upper.center - lower.center
        base = join_native_regions(upper, lower.translated(dx))
        metadata.update(lowerCutY=LOWER_CUT, lowerOffsetX=rounded(dx))
    return rounded_recording(base), metadata


# These five extended Bowls replace only a stem terminal; the closed bowl
# and its counter stay native. The short b/p hybrid has its own recipe below.
BOWL_RECIPES = {
    0xF2A28: (0x64, 0x71, False),
    0xF2A29: (0x62, 0x253, True),
    0xF2A2A: (0xFE, 0x253, True),
    0xF2A2B: (0x251, 0x261, False),
    0xF2A2C: (0x64, 0x261, False),
}


def contour_edges(recording, *, allow_connections: bool = False):
    """Return cyclic native edges, including the implicit closing line."""
    if recording[0][0] != "moveTo" or recording[-1][0] != "closePath":
        raise RuntimeError("Expected one closed native contour")
    start = previous = recording[0][1][0]
    edges = []
    for op, points in recording[1:-1]:
        if op not in (("lineTo", "qCurveTo", "curveTo") if allow_connections else ("lineTo", "qCurveTo")):
            raise RuntimeError(f"Unexpected native contour operation: {op}")
        edges.append((previous, op, points))
        previous = points[-1]
    if previous != start:
        edges.append((previous, "lineTo", (start,)))
    return edges


def shaft_point(edge, y: float, *, extend: bool = False) -> Point:
    start, op, points = edge
    end = points[-1]
    if op != "lineTo" or start[1] == end[1]:
        raise RuntimeError("Bowl splice must cut a straight shaft edge")
    t = (y - start[1]) / (end[1] - start[1])
    if not extend and not 0 <= t <= 1:
        raise RuntimeError(f"Bowl shaft cut {y} is outside {start}, {end}")
    return (start[0] + t * (end[0] - start[0]), y)


def native_arc(edges, first: int, start: Point, last: int, end: Point) -> NativePath:
    """Keep the directed arc between two shaft cuts without fitting curves."""
    operations = []
    index = first
    while index != last:
        _, op, points = edges[index]
        if start != points[-1] or operations:
            operations.append((op, points))
        index = (index + 1) % len(edges)
    if not operations or operations[-1][1][-1] != end:
        operations.append(("lineTo", (end,)))
    return NativePath(start, tuple(operations))


def bowl_lower_terminal(font: TTFont, code: int, end_y: float) -> NativePath:
    """Retain complete native q feet or the broad single-story-g lower hook."""
    recording = decomposed_recording(font, font.getBestCmap()[code])
    italic = bool(font["post"].italicAngle)
    outer_end = next(i for i, (op, _) in enumerate(recording) if op == "closePath")
    edges = contour_edges(recording[:outer_end + 1])
    if code == 0x71:
        # q's left shaft reaches the bowl sooner at heavier weights. Extend
        # that straight edge to the body's attachment, preserving its slant.
        right, left = (10, 1) if italic else (11, 3)
        return native_arc(edges, right, shaft_point(edges[right], 0.0), left,
                          shaft_point(edges[left], end_y, extend=True))
    if code != 0x261:
        raise RuntimeError(f"Unexpected lower bowl donor U+{code:04X}")
    right = 13 if italic else 12
    if len(edges) != (15 if italic else 14):
        raise RuntimeError("Unexpected single-story-g topology")
    # y=50 is above the hook's highest native curve entry at both weights.
    # Preserve its full sweep and ball, extending only the straight left
    # shaft to the retained bowl's attachment. No scaling of the hook.
    return native_arc(edges, right, shaft_point(edges[right], 50.0), 4,
                      shaft_point(edges[4], end_y, extend=True))


def bowl_outline(font: TTFont, code_point: int) -> tuple[list[tuple[str, tuple]], dict]:
    body_code, terminal_code, upper_hook = BOWL_RECIPES[code_point]
    italic = bool(font["post"].italicAngle)
    base = decomposed_recording(font, font.getBestCmap()[body_code])
    outer_end = next(i for i, (op, _) in enumerate(base) if op == "closePath")
    edges = contour_edges(base[:outer_end + 1])
    remaining = base[outer_end + 1:]
    metadata = {"bowlDonorCodePoint": body_code,
                "terminalDonorCodePoint": terminal_code}
    if upper_hook:
        # Indices identify the shaft, not a horizontal region: cutting the
        # whole body at this height would also sever its curved shoulder.
        left_op, right_op = ((2, 9) if body_code == 0x62 else (2, 10)) if italic else (
            (8, 2) if body_code == 0x62 else (4, 10))
        right, left = right_op - 1, left_op - 1
        body = native_arc(edges, right, shaft_point(edges[right], 430.0),
                          left, shaft_point(edges[left], 380.0))
        hook_base = decomposed_recording(font, font.getBestCmap()[terminal_code])
        hook_end = next(i for i, (op, _) in enumerate(hook_base) if op == "closePath")
        hook_edges = contour_edges(hook_base[:hook_end + 1])
        hook_left, hook_right = (1, 7) if italic else (1, 9)
        # Asymmetric cuts leave room above b's high shoulder and below the
        # native U+0253 crown, without cutting either donor's curved outline.
        hook = native_arc(hook_edges, hook_left, shaft_point(hook_edges[hook_left], 420.0),
                          hook_right, shaft_point(hook_edges[hook_right], 470.0))
        slope = -math.tan(math.radians(font["post"].italicAngle))
        dx = body.center + slope * 40.0 - hook.center
        result = [*join_native_regions(hook.translated(dx), body), *remaining]
        metadata.update(bodyLeftCutY=380.0, bodyRightCutY=430.0,
                        terminalLeftCutY=420.0, terminalRightCutY=470.0,
                        terminalOffsetX=rounded(dx))
    else:
        right_op, corner_op = ((12, 20) if body_code == 0x64 else (7, 15)) if italic else (
            (11, 18) if body_code == 0x64 else (7, 14))
        corner = base[corner_op][1][-1]
        anchor = base[corner_op - 1][1][-1]
        right = right_op - 1
        cut = shaft_point(edges[right], 180.0)
        body = native_arc(edges, corner_op, corner, right, cut)
        lower = bowl_lower_terminal(font, terminal_code, corner[1])
        dx = anchor[0] - lower.end[0] if italic else cut[0] - lower.start[0]
        lower = lower.translated(dx)
        bridge = tangent_connector(cut, lower.start, body.slope(False), lower.slope(True))
        result = [("moveTo", (body.start,)), *body.operations, bridge.operation(),
                  *lower.operations, ("lineTo", (corner,)), ("closePath", ()), *remaining]
        metadata.update(bodyCutY=180.0, terminalEntryY=lower.start[1],
                        bowlAttachmentY=corner[1], terminalOffsetX=rounded(dx))
    return rounded_recording(result), metadata


def short_bowl_outline(font: TTFont) -> tuple[list[tuple[str, tuple]], dict]:
    """Combine b's complete bowl and baseline with p's upright short head."""
    italic = bool(font["post"].italicAngle)
    base = decomposed_recording(font, font.getBestCmap()[0x62])
    end = next(i for i, (op, _) in enumerate(base) if op == "closePath")
    edges = contour_edges(base[:end + 1])
    left, right = (1, 8) if italic else (7, 1)
    body = native_arc(edges, right, shaft_point(edges[right], 430.0),
                      left, shaft_point(edges[left], 300.0))
    head_base = decomposed_recording(font, font.getBestCmap()[0x70])
    head_end = next(i for i, (op, _) in enumerate(head_base) if op == "closePath")
    head_contour = head_base[head_end + 1:] if italic else head_base[:head_end + 1]
    head_edges = contour_edges(head_contour)
    head_left, head_right = (1, 8) if italic else (3, 9)
    # Asymmetric shaft cuts preserve both p's low entrance curves and b's
    # high shoulder. No donor curve is clipped, rotated, or re-fitted.
    head = native_arc(head_edges, head_left, shaft_point(head_edges[head_left], 350.0),
                      head_right, shaft_point(head_edges[head_right], 460.0))
    slope = -math.tan(math.radians(font["post"].italicAngle))
    dx = body.center + slope * 40.0 - head.center
    result = [*join_native_regions(head.translated(dx), body), *base[end + 1:]]
    return rounded_recording(result), {
        "bowlDonorCodePoint": 0x62, "headDonorCodePoint": 0x70,
        "bodyLeftCutY": 300.0, "bodyRightCutY": 430.0,
        "headLeftCutY": 350.0, "headRightCutY": 460.0,
        "headOffsetX": rounded(dx),
    }


# Four Arches are complete native n/u/h/h-with-hook donors. The remaining
# eight replace only requested terminals, retaining the donor arch curves.
ARCH_RECIPES = {
    0xF2A16: (0x6E, False, True, False),
    0xF2A18: (0x75, True, False, False),
    0xF2A1A: (0x68, False, True, False),
    0xF2A1B: (0x265, False, False, False),
    0xF2A1C: (0x265, True, False, False),
    0xF2A1E: (0x266, False, True, False),
    0xF2A1F: (0x75, False, False, True),
    0xF2A20: (0x75, True, False, True),
}


def arch_outline(font: TTFont, code_point: int) -> tuple[list[tuple[str, tuple]], dict]:
    """Preserve open arch contours and splice along straight shaft edges.

    Edge indices are contracts with the hash-pinned donor endpoints. Separate
    n/h shoulder contours remain untouched; the integrated Roman hook-h and
    turned forms retain every curved arch edge in their original position.
    """
    body_code, ascender, descender, tail = ARCH_RECIPES[code_point]
    italic = bool(font["post"].italicAngle)
    base = decomposed_recording(font, font.getBestCmap()[body_code])
    metadata = {"archDonorCodePoint": body_code}

    if descender:
        # Below y=150 the n/h shoulder has already joined the left shaft.
        # The p footer begins at y=50, leaving only straight shaft to bridge.
        if body_code == 0x266 and not italic:
            edges = contour_edges(base)
            upper = native_arc(edges, 3, shaft_point(edges[3], 150.0),
                               22, shaft_point(edges[22], 150.0))
            before, after = [], []
        else:
            split = next(i for i, (op, _) in enumerate(base[1:], 1) if op == "moveTo")
            if body_code == 0x266:
                stem, before, after = base[:split], [], base[split:]
            else:
                stem, before, after = base[split:], base[:split], []
            upper = native_region(stem, 150.0, True)
        lower = native_terminal(font, 0x70, 50.0, False)
        slope = (upper.slope(True) + upper.slope(False)) / 2
        dx = upper.center - slope * 100.0 - lower.center
        result = [*before, *join_native_regions(upper, lower.translated(dx)), *after]
        metadata.update(lowerDonorCodePoint=0x70, bodyCutY=150.0,
                        lowerCutY=50.0, lowerOffsetX=rounded(dx))
        return rounded_recording(result), metadata

    edges = contour_edges(base)
    # The italic arch joins its inner right shaft higher than the Roman one.
    # These cuts are above the curve and below the native u/turned-h head.
    inner, outer = ((13, 15) if body_code == 0x75 else (18, 20)) if italic else (
        (9, 14) if body_code == 0x75 else (14, 20))
    body_y = 400.0 if italic else 300.0
    inner_cut = shaft_point(edges[inner], body_y)
    outer_cut = shaft_point(edges[outer], body_y)
    if ascender:
        upper_y = body_y + 100.0
        upper = native_terminal(font, 0x6C, upper_y, True)
        slope = -math.tan(math.radians(font["post"].italicAngle))
        dx = (inner_cut[0] + outer_cut[0]) / 2 + slope * 100.0 - upper.center
        upper = upper.translated(dx)
        metadata.update(upperDonorCodePoint=0x6C, upperBodyCutY=body_y,
                        upperCutY=upper_y, upperOffsetX=rounded(dx))

    if not tail:
        if body_code == 0x265:
            # Native turned h has only half a Roman foot serif. Keep its
            # complete arch but use the same full p finish as other descenders.
            foot_inner = 1
            left_cut = shaft_point(edges[foot_inner], 0.0)
            right_cut = shaft_point(edges[outer], 0.0)
            if ascender:
                first = native_arc(edges, foot_inner, left_cut, inner, inner_cut)
                last = native_arc(edges, outer, outer_cut, outer, right_cut)
                left_join = tangent_connector(first.end, upper.start,
                                              first.slope(False), upper.slope(True))
                right_join = tangent_connector(upper.end, last.start,
                                               upper.slope(False), last.slope(True))
                body = NativePath(left_cut, (*first.operations, left_join.operation(),
                                            *upper.operations, right_join.operation(), *last.operations))
            else:
                body = native_arc(edges, foot_inner, left_cut, outer, right_cut)
            lower = native_terminal(font, 0x70, -50.0, False)
            slope = (body.slope(True) + body.slope(False)) / 2
            dx = body.center - slope * 50.0 - lower.center
            metadata.update(lowerDonorCodePoint=0x70, lowerBodyCutY=0.0,
                            lowerCutY=-50.0, lowerOffsetX=rounded(dx))
            return join_native_regions(body, lower.translated(dx)), metadata
        lower_body = native_arc(edges, outer, outer_cut, inner, inner_cut)
        return join_native_regions(upper, lower_body), metadata

    # Keep u's complete inner and outer arch, ending at its small inner
    # attachment corner. Replace its right baseline exit with the full g tail.
    corner_op = 24 if italic else 22
    corner = base[corner_op][1][-1]
    anchor = base[corner_op - 1][1][-1]
    lower_body_y = 250.0
    cut = shaft_point(edges[outer], lower_body_y)
    if ascender:
        first = native_arc(edges, corner_op, corner, inner, inner_cut)
        last = native_arc(edges, outer, outer_cut, outer, cut)
        left_join = tangent_connector(first.end, upper.start,
                                      first.slope(False), upper.slope(True))
        right_join = tangent_connector(upper.end, last.start,
                                       upper.slope(False), last.slope(True))
        body = NativePath(corner, (*first.operations, left_join.operation(),
                                  *upper.operations, right_join.operation(), *last.operations))
    else:
        body = native_arc(edges, corner_op, corner, outer, cut)
    lower = bowl_lower_terminal(font, 0x261, corner[1])
    # Match u's inner shaft at its attachment. Aligning the outer shaft in
    # Roman Bold would put g's inner edge one unit left of the arch corner,
    # making it cross the retained native curve. The outer tangent bridge
    # absorbs the small native difference in shaft width.
    dx = anchor[0] - lower.end[0]
    lower = lower.translated(dx)
    bridge = tangent_connector(cut, lower.start, body.slope(False), lower.slope(True))
    result = [("moveTo", (body.start,)), *body.operations, bridge.operation(),
              *lower.operations, ("lineTo", (corner,)), ("closePath", ())]
    metadata.update(lowerDonorCodePoint=0x261, lowerBodyCutY=lower_body_y,
                    lowerCutY=50.0, archAttachmentY=corner[1], lowerOffsetX=rounded(dx))
    return rounded_recording(result), metadata


def splice_arch_terminal(recording, source_edges, cut_y, terminal, *, above):
    """Replace one ending, locating its unchanged native shaft edges exactly.

    A second splice may encounter tangent bridges from the first. Those are
    carried intact; only the two explicitly identified straight donor edges
    are cut. All other contours keep their original order and coordinates.
    """
    start = 0
    for stop, (operation, _) in enumerate(recording):
        if operation != "closePath":
            continue
        edges = contour_edges(recording[start:stop + 1], allow_connections=True)
        matches = [[i for i, edge in enumerate(edges) if edge == source] for source in source_edges]
        if all(len(indices) == 1 for indices in matches):
            first, last = (indices[0] for indices in matches)
            body = native_arc(edges, last, shaft_point(edges[last], cut_y),
                              first, shaft_point(edges[first], cut_y))
            slope = (body.slope(True) + body.slope(False)) / 2
            terminal_y = (terminal.start[1] + terminal.end[1]) / 2
            dx = body.center + slope * (terminal_y - cut_y) - terminal.center
            terminal = terminal.translated(dx)
            joined = join_native_regions(terminal, body) if above else join_native_regions(body, terminal)
            return [*recording[:start], *joined, *recording[stop + 1:]], rounded(dx)
        start = stop + 1
    raise RuntimeError("Could not locate both unchanged native arch shaft edges")


def donor_contour_edges(font, code, contour_index=0):
    recording = decomposed_recording(font, font.getBestCmap()[code])
    start = 0
    for stop, (operation, _) in enumerate(recording):
        if operation == "closePath":
            if contour_index == 0:
                return contour_edges(recording[start:stop + 1])
            contour_index -= 1
            start = stop + 1
    raise RuntimeError(f"Missing native contour in U+{code:04X}")


def native_path_bounds(path):
    pen = BoundsPen(None)
    replayRecording([("moveTo", (path.start,)), *path.operations, ("closePath", ())], pen)
    return pen.bounds


def open_arch_spacing(recording, forward_edge, backward_edge, amount):
    """Open the two connecting arch curves while keeping terminals rigid.

    Only two native quadratic runs change shape. Their y coordinates stay
    fixed, and translating each endpoint with its adjacent control preserves
    the attachment tangent. Intermediate control offsets progress uniformly;
    the arch stays curved instead of gaining a flat platform at its crown.
    """
    def connecting_curve(edge, start_shift, end_shift):
        point, operation, points = edge
        if operation != "qCurveTo" or len(points) < 3:
            raise RuntimeError("Expected a multi-control native arch connection")
        controls = points[:-1]
        moved = tuple((x + start_shift + (end_shift - start_shift) * i / (len(controls) - 1), y)
                      for i, (x, y) in enumerate(controls))
        end = (points[-1][0] + end_shift, points[-1][1])
        return NativePath((point[0] + start_shift, point[1]), ((operation, (*moved, end)),))

    start = 0
    for stop, (operation, _) in enumerate(recording):
        if operation != "closePath":
            continue
        edges = contour_edges(recording[start:stop + 1], allow_connections=True)
        starts = [i for i, edge in enumerate(edges) if edge == forward_edge]
        ends = [i for i, edge in enumerate(edges) if edge == backward_edge]
        if len(starts) == len(ends) == 1:
            first, last = starts[0], ends[0]
            forward = connecting_curve(forward_edge, 0.0, amount)
            backward = connecting_curve(backward_edge, amount, 0.0)
            right = native_arc(edges, (first + 1) % len(edges), forward_edge[2][-1],
                               last, backward_edge[0]).translated(amount)
            left = native_arc(edges, (last + 1) % len(edges), backward_edge[2][-1],
                              first, forward_edge[0])
            result = [("moveTo", (forward.start,)), *forward.operations,
                      *right.operations, *backward.operations, *left.operations,
                      ("closePath", ())]
            return [*recording[:start], *result, *recording[stop + 1:]]
        start = stop + 1
    raise RuntimeError("Could not locate the two native connecting arch curves")


# Each tuple selects an existing arch body and replacements on its two staves.
# Native eng, heng and hooked heng are the three complete hooked anchors.
EXTENDED_ARCH_RECIPES = {
    0xF2A2D: (0x19E, True, False),
    0xF2A2E: (0x19E, True, True),
    0xF2A31: (0xA727, True, False),
    0xF2A32: (0xA727, True, True),
    0xF2A35: (0x267, True, False),
    0xF2A36: (0x267, True, True),
    0xF2A3A: (0x14B, False, True),
    0xF2A3E: (0xA727, False, True),
    0xF2A42: (0x267, False, True),
}
TURNED_EXTENDED_ARCH_RECIPES = {
    0xF2A2F: (0xF2A17, 0x6C), 0xF2A30: (0xF2A18, 0x6C),
    0xF2A33: (0xF2A1B, 0x6C), 0xF2A34: (0xF2A1C, 0x6C),
    0xF2A37: (0xF2A1F, 0x6C), 0xF2A38: (0xF2A20, 0x6C),
    0xF2A3B: (0xF2A17, 0x266), 0xF2A3C: (0xF2A18, 0x266),
    0xF2A3F: (0xF2A1B, 0x266), 0xF2A40: (0xF2A1C, 0x266),
    0xF2A43: (0xF2A1F, 0x266), 0xF2A44: (0xF2A20, 0x266),
}


def native_recording_contours(recording):
    start = 0
    for stop, (operation, _) in enumerate(recording):
        if operation == "closePath":
            yield recording[start:stop + 1]
            start = stop + 1


def fitted_bowl_join(edge, reference_shaft, receiver_shaft, anchor, *, anchor_first):
    """Fit only a native bowl's closing quarter-curve between two fixed ports.

    Keep its vertical profile and horizontal tangent at the bowl extremum.
    Fit horizontal distances from the receiving shaft, accounting for each
    donor's native slant. The native bowl corner at the shaft is intentional.
    """
    start, operation, points = edge
    source_anchor = start if anchor_first else points[-1]
    corner = points[-1] if anchor_first else start
    dy = anchor[1] - source_anchor[1]
    slope = endpoint_slope(Segment(reference_shaft[0], reference_shaft[2][-1]), at_start=True)

    def reference_x(y):
        return corner[0] + slope * (y - corner[1])

    receiver_at_anchor = shaft_point(receiver_shaft, anchor[1], extend=True)[0]
    factor = (anchor[0] - receiver_at_anchor) / (source_anchor[0] - reference_x(source_anchor[1]))
    if factor <= 0:
        raise RuntimeError("Bowl closure would reverse its native curve")

    def fit(point):
        if point == source_anchor:
            return anchor
        x, y = point
        return (shaft_point(receiver_shaft, y + dy, extend=True)[0]
                + factor * (x - reference_x(y)), y + dy)

    return NativePath(fit(start), ((operation, tuple(fit(point) for point in points)),))


def closed_lower_arch_outline(font, body_code):
    """Close the eng hook into its left shaft with b's two lower joins."""
    italic = bool(font["post"].italicAngle)
    contours = list(native_recording_contours(decomposed_recording(font, font.getBestCmap()[body_code])))
    hook_index = 1 if italic and body_code == 0x267 else 0
    stem_index = (0 if body_code == 0x267 else 1) if italic else 0
    hook = contour_edges(contours[hook_index])
    stem = contour_edges(contours[stem_index])
    inner, outer = ((11 if body_code == 0xA727 else 10), 1) if italic else (7, 13)
    bowl_outer = donor_contour_edges(font, 0x62)
    bowl_counter = donor_contour_edges(font, 0x62, 1)
    lower_outer = fitted_bowl_join(bowl_outer[0 if italic else 6], bowl_outer[1 if italic else 7],
                                  stem[outer], hook[0][0], anchor_first=True)
    lower_inner = fitted_bowl_join(bowl_counter[4 if italic else 1], bowl_counter[3 if italic else 0],
                                  stem[inner], hook[3][0], anchor_first=False)
    if not italic:
        outside = native_arc(hook, outer, lower_outer.end, 0, lower_outer.start)
        counter = native_arc(hook, 3, lower_inner.end, inner, lower_inner.start)
        result = [("moveTo", (outside.start,)), *outside.operations, *lower_outer.operations,
                  ("closePath", ()), ("moveTo", (counter.start,)), *counter.operations,
                  *lower_inner.operations, ("closePath", ())]
    else:
        # Italic eng already uses separate shoulder and shaft contours. Keep
        # that native construction, as in italic p's attached bowl: the new
        # closing ribbon overlaps the extended shaft, with no ball or foot.
        body = native_arc(hook, 3, lower_inner.end, 0, lower_outer.start)
        closed_hook = [("moveTo", (body.start,)), *body.operations, *lower_outer.operations,
                       ("lineTo", (lower_inner.start,)), *lower_inner.operations, ("closePath", ())]
        bottom_y = lower_outer.end[1]
        extended_stem = native_arc(stem, outer, lower_outer.end, inner,
                                   shaft_point(stem[inner], bottom_y, extend=True))
        closed_stem = [("moveTo", (extended_stem.start,)), *extended_stem.operations, ("closePath", ())]
        contours[hook_index], contours[stem_index] = closed_hook, closed_stem
        result = [operation for contour in contours for operation in contour]
    return rounded_recording(result), {
        "archDonorCodePoint": body_code, "joinedTerminal": "lower",
        "closureDonorCodePoint": 0x62,
        "closureOuterJoin": lower_outer.end, "closureInnerJoin": lower_inner.start,
    }


def close_upper_arch(font, recording, metadata, crown):
    """Replace the facing hook ball and l head with native d bowl joins."""
    edges = contour_edges(recording, allow_connections=True)
    crown_edges = contour_edges(rounded_recording([("moveTo", (crown.start,)), *crown.operations, ("closePath", ())]))
    outer_hook = crown_edges[1]
    inner_hook = crown_edges[-3]
    head = native_terminal(font, 0x6C, metadata["upperCutY"], True).translated(metadata["upperOffsetX"])
    head_edges = contour_edges(rounded_recording([("moveTo", (head.start,)), *head.operations, ("closePath", ())]))
    inner_head, outer_head = head_edges[0], head_edges[-2]

    def locate(reference):
        # Metadata offsets are rounded independently of the complete outline.
        matches = [i for i, candidate in enumerate(edges)
                   if candidate[1] == reference[1] and len(candidate[2]) == len(reference[2])
                   and all(abs(a - b) <= 0.000002
                           for p, q in zip((candidate[0], *candidate[2]), (reference[0], *reference[2]))
                           for a, b in zip(p, q))]
        if len(matches) != 1:
            raise RuntimeError("Could not identify the native closure port")
        return matches[0]

    outer_hook_index, inner_hook_index = locate(outer_hook), locate(inner_hook)
    inner_head_index, outer_head_index = locate(inner_head), locate(outer_head)
    outer_hook, inner_hook = edges[outer_hook_index], edges[inner_hook_index]
    inner_head, outer_head = edges[inner_head_index], edges[outer_head_index]
    d_outer = donor_contour_edges(font, 0x64)
    d_counter = donor_contour_edges(font, 0x64, 1)
    upper_outer = fitted_bowl_join(d_outer[2], d_outer[4], outer_head,
                                  outer_hook[2][-1], anchor_first=True)
    upper_inner = fitted_bowl_join(d_counter[2], d_outer[4], inner_head,
                                  inner_hook[0], anchor_first=False)
    outside = native_arc(edges, outer_head_index, outer_head[2][-1],
                         (outer_hook_index + 1) % len(edges), upper_outer.start)
    counter = native_arc(edges, inner_hook_index, upper_inner.end,
                         inner_head_index, inner_head[0])
    result = [("moveTo", (outside.start,)), *outside.operations, *upper_outer.operations,
              ("closePath", ()), ("moveTo", (counter.start,)), *counter.operations,
              ("lineTo", (upper_inner.start,)), *upper_inner.operations, ("closePath", ())]
    metadata.update(joinedTerminal="upper", closureDonorCodePoint=0x64,
                    closureOuterJoin=upper_outer.end, closureInnerJoin=upper_inner.start)
    return rounded_recording(result), metadata


def extended_arch_outline(font, code_point):
    """Complete the two-stave descender/hook families without rotating donors."""
    italic = bool(font["post"].italicAngle)
    if code_point in TURNED_EXTENDED_ARCH_RECIPES:
        base_code, upper_code = TURNED_EXTENDED_ARCH_RECIPES[code_point]
        body_code = 0x265 if base_code in (0xF2A1B, 0xF2A1C) else 0x75
        if base_code == 0xF2A17:
            recording = decomposed_recording(font, font.getBestCmap()[body_code])
            metadata = {"archDonorCodePoint": body_code}
        else:
            recording, metadata = arch_outline(font, base_code)
        edges = donor_contour_edges(font, body_code)
        left, right = ((7, 14) if italic else (5, 11)) if body_code == 0x265 else (
            (2, 9) if italic else (1, 6))
        upper_y = 430.0 if upper_code == 0x266 else 400.0
        if upper_code == 0x266:
            hook_edges = donor_contour_edges(font, upper_code)
            hook_left, hook_right = (1, 7) if italic else (3, 9)
            upper = native_arc(hook_edges, hook_left, shaft_point(hook_edges[hook_left], upper_y),
                               hook_right, shaft_point(hook_edges[hook_right], upper_y))
        else:
            upper = native_terminal(font, upper_code, upper_y, True)
        result, dx = splice_arch_terminal(recording, (edges[left], edges[right]),
                                          300.0, upper, above=True)
        metadata.update(baseGlyphCodePoint=base_code, leftUpperDonorCodePoint=upper_code,
                        leftUpperBodyCutY=300.0, leftUpperCutY=upper_y, leftUpperOffsetX=dx)
        if upper_code == 0x266 and base_code in (0xF2A18, 0xF2A1C, 0xF2A20):
            return close_upper_arch(font, result, metadata, upper.translated(dx))
        return rounded_recording(result), metadata

    body_code, right_descender, left_descender = EXTENDED_ARCH_RECIPES[code_point]
    if left_descender and not right_descender:
        return closed_lower_arch_outline(font, body_code)
    recording = decomposed_recording(font, font.getBestCmap()[body_code])
    metadata = {"archDonorCodePoint": body_code}
    if right_descender:
        right_contour = 1 if italic and body_code == 0x267 else 0
        edges = donor_contour_edges(font, body_code, right_contour)
        outer, inner = ((9, 1) if italic else (20, 1)) if body_code == 0x19E else (
            (12, 4) if italic else (23, 4))
        body_y, lower_y = (0.0, -50.0) if body_code == 0x19E else (150.0, 50.0)
        lower = native_terminal(font, 0x70, lower_y, False)
        recording, dx = splice_arch_terminal(recording, (edges[outer], edges[inner]),
                                             body_y, lower, above=False)
        metadata.update(rightLowerDonorCodePoint=0x70, rightLowerBodyCutY=body_y,
                        rightLowerCutY=lower_y, rightLowerOffsetX=dx)
    if left_descender:
        left_contour = 1 if italic and body_code != 0x267 else 0
        edges = donor_contour_edges(font, body_code, left_contour)
        if italic:
            inner, outer = (11, 1) if body_code == 0xA727 else (10, 1)
        else:
            inner, outer = (4, 10) if body_code == 0x19E else (7, 13)
        lower = native_terminal(font, 0x70, 50.0, False)
        recording, dx = splice_arch_terminal(recording, (edges[inner], edges[outer]),
                                             150.0, lower, above=False)
        metadata.update(leftLowerDonorCodePoint=0x70, leftLowerBodyCutY=150.0,
                        leftLowerCutY=50.0, leftLowerOffsetX=dx)
        left_foot = lower.translated(dx)
        if right_descender:
            right_foot = native_terminal(font, 0x70, metadata["rightLowerCutY"], False).translated(
                metadata["rightLowerOffsetX"])
        else:
            right_contour = 1 if italic and body_code == 0x267 else 0
            right_edges = donor_contour_edges(font, body_code, right_contour)
            outer, inner = (12, 4) if italic else (23, 4)
            right_foot = native_arc(right_edges, outer, shaft_point(right_edges[outer], 150.0),
                                    inner, shaft_point(right_edges[inner], 150.0))
        expansion = max(0.0, native_path_bounds(left_foot)[2] + 50.0 - native_path_bounds(right_foot)[0])
        arch_contour = 1 if italic and body_code == 0x267 else 0
        arch_edges = donor_contour_edges(font, body_code, arch_contour)
        outer, inner = ((6, 4) if italic else (18, 3)) if body_code == 0x19E else (
            (9, 7) if italic else (21, 6))
        recording = open_arch_spacing(recording, arch_edges[outer], arch_edges[inner], expansion)
        metadata.update(archExpansionX=rounded(expansion), archExpansionGap=50.0,
                        archExpansionForwardEdge=outer, archExpansionBackwardEdge=inner,
                        archExpansionContour=arch_contour)
    return rounded_recording(recording), metadata


def glyph_bounds(glyph) -> tuple[float, float, float, float] | None:
    bounds = glyph.getBounds()
    return tuple(bounds) if bounds is not None else None


def flattened_contours(glyph) -> list[list[Point]]:
    flattened = RecordingPen()
    glyph.draw(FlattenPen(flattened, approximateSegmentLength=2, segmentLines=False))
    contours: list[list[Point]] = []
    current: list[Point] | None = None
    for operation, operands in flattened.value:
        if operation == "moveTo":
            current = [operands[0]]
        elif operation == "lineTo":
            assert current is not None
            current.append(operands[0])
        elif operation == "closePath":
            assert current is not None
            if current[-1] != current[0]:
                current.append(current[0])
            contours.append(current)
            current = None
        else:
            raise RuntimeError(f"FlattenPen left unexpected operation {operation}")
    return contours


def scanline_interval(contours: list[list[Point]], y: float) -> tuple[float, float] | None:
    crossings = []
    for contour in contours:
        for first, second in zip(contour, contour[1:]):
            if (first[1] <= y < second[1]) or (second[1] <= y < first[1]):
                t = (y - first[1]) / (second[1] - first[1])
                crossings.append(first[0] + (second[0] - first[0]) * t)
    return (min(crossings), max(crossings)) if crossings else None


def kerning_profile(glyph) -> dict[int, tuple[float, float] | None]:
    """Cache all integer-offset scanlines once for the complete pair matrix."""
    bounds = glyph_bounds(glyph)
    if bounds is None:
        return {}
    contours = flattened_contours(glyph)
    return {y: scanline_interval(contours, y + 0.37)
            for y in range(math.floor(bounds[1]), math.ceil(bounds[3]))}


def pair_kerning(left, right, profiles=None) -> int:
    left_bounds, right_bounds = glyph_bounds(left), glyph_bounds(right)
    if left_bounds is None or right_bounds is None:
        return 0
    bottom = max(left_bounds[1], right_bounds[1])
    top = min(left_bounds[3], right_bounds[3])
    if bottom >= top:
        return 0
    if profiles is None:
        left_contours, right_contours = flattened_contours(left), flattened_contours(right)
    required = 0.0
    y = math.floor(bottom) + 0.37
    while y < top:
        if profiles is None:
            left_interval = scanline_interval(left_contours, y)
            right_interval = scanline_interval(right_contours, y)
        else:
            left_interval = profiles[left.name][math.floor(y)]
            right_interval = profiles[right.name][math.floor(y)]
        if left_interval and right_interval:
            gap = left.width + right_interval[0] - left_interval[1]
            required = max(required, MIN_INK_GAP - gap)
        y += 3.0
    return max(0, math.ceil(required))


def set_font_info(font: Font, donor: TTFont, style: str, weight: int, italic: bool) -> None:
    os2, hhea, post = donor["OS/2"], donor["hhea"], donor["post"]
    info = font.info
    info.familyName = FAMILY_NAME
    info.styleName = style
    info.styleMapFamilyName = FAMILY_NAME
    info.styleMapStyleName = (
        "bold italic" if weight == 700 and italic else
        "bold" if weight == 700 else
        "italic" if italic else "regular"
    )
    info.unitsPerEm = donor["head"].unitsPerEm
    info.ascender = os2.sTypoAscender
    info.descender = os2.sTypoDescender
    info.xHeight = os2.sxHeight
    info.capHeight = os2.sCapHeight
    info.italicAngle = post.italicAngle
    info.versionMajor = VERSION_MAJOR
    info.versionMinor = VERSION_MINOR
    info.copyright = (
        "Copyright 2001-2021 The STIX Fonts Project Authors "
        "(https://github.com/stipub/stixfonts). Modified 2026 for Quintessential Serif."
    )
    info.trademark = "STIX Fonts is a trademark of The Institute of Electrical and Electronics Engineers, Inc."
    info.openTypeNameDesigner = (
        "Original STIX Two design: Ross Mills, John Hudson and Paul Hanslow, "
        "Tiro Typeworks Ltd; with prior portions by MicroPress Inc. and Coen Hoffman."
    )
    info.openTypeNameDesignerURL = "https://www.stixfonts.org"
    info.openTypeNameDescription = (
        "A sparse experimental script font derived from STIX Two Text 2.13 b171; "
        "U+F2A00-U+F2A2C implement the complete Stems, Arms, Arches and Bowls families."
    )
    info.openTypeNameLicense = (
        "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
        "See the accompanying OFL.txt."
    )
    info.openTypeNameLicenseURL = "https://openfontlicense.org"
    info.openTypeNameManufacturer = "The STIX Fonts Project Authors; modified for Quintessential Serif"
    info.openTypeNameVersion = f"Version {VERSION}"
    info.openTypeNameUniqueID = f"{VERSION};{VENDOR_ID};QuintessentialSerif-{style}"
    info.postscriptFontName = f"QuintessentialSerif-{style}"
    info.postscriptFullName = f"{FAMILY_NAME} {style}"
    info.postscriptUnderlinePosition = post.underlinePosition
    info.postscriptUnderlineThickness = post.underlineThickness
    info.openTypeHeadCreated = "2026/09/04 00:00:00"
    info.openTypeHheaAscender = hhea.ascent
    info.openTypeHheaDescender = hhea.descent
    info.openTypeHheaLineGap = hhea.lineGap
    info.openTypeHheaCaretSlopeRise = 1000
    info.openTypeHheaCaretSlopeRun = 213 if italic else 0
    info.openTypeHheaCaretOffset = 0
    info.openTypeOS2TypoAscender = os2.sTypoAscender
    info.openTypeOS2TypoDescender = os2.sTypoDescender
    info.openTypeOS2TypoLineGap = os2.sTypoLineGap
    info.openTypeOS2Selection = [bit for bit in (1, 2, 3, 4, 7, 8, 9) if os2.fsSelection & (1 << bit)]
    info.openTypeOS2WinAscent = os2.usWinAscent
    info.openTypeOS2WinDescent = os2.usWinDescent
    info.openTypeOS2WeightClass = weight
    info.openTypeOS2WidthClass = 5
    info.openTypeOS2VendorID = VENDOR_ID
    info.openTypeOS2Type = []
    info.postscriptBlueFuzz = 1
    info.postscriptBlueScale = 0.039625
    info.postscriptBlueShift = 7
    info.postscriptBlueValues = [-16, 0, os2.sxHeight - 8, os2.sxHeight + 12, os2.sCapHeight - 8, os2.sCapHeight + 12, 704, 722]
    info.postscriptOtherBlues = [-242, -220]
    if italic:
        info.postscriptStemSnapV = [126 if weight == 700 else 72]
        info.postscriptStemSnapH = [40 if weight == 700 else 28]
    else:
        info.postscriptStemSnapV = [140 if weight == 700 else 83]
        info.postscriptStemSnapH = [40 if weight == 700 else 28]
    info.postscriptForceBold = weight == 700


def add_glyph(font: Font, name: str, recording: list[tuple[str, tuple]], width: float, code_point: int | None, construction: dict) -> None:
    glyph = font.newGlyph(name)
    replayRecording(recording, glyph.getPen())
    glyph.width = rounded(width)
    if code_point is not None:
        glyph.unicodes = [code_point]
    glyph.lib["org.quintessential.construction"] = construction


def legacy_outline(donor, spec, italic=None):
    """Resolve a preserved construction by its original recipe key."""
    italic = bool(donor["post"].italicAngle) if italic is None else italic
    cmap = donor.getBestCmap()
    recipe_code = spec.recipe_code_point or spec.code_point
    recipes = {
        0xF2A02: (0x17F, 0x131),
        0xF2A03: (0x131, 0x70),
        0xF2A04: (0x6C, 0x70),
        0xF2A05: (0x17F, 0x70),
        0xF2A07: (0x6C, 0x237),
    }
    width_name = cmap[spec.width_donor]
    if 0xF2C00 <= recipe_code <= 0xF2CBF:
        from stix_extensions import extensions_outline
        recording, construction = extensions_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif 0xF2B58 <= recipe_code <= 0xF2B9F:
        from stix_arched_opposed_bowls import arched_opposed_bowls_outline
        recording, construction = arched_opposed_bowls_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif 0xF2B1C <= recipe_code <= 0xF2B3F:
        from stix_opposed_bowls import opposed_bowls_outline
        recording, construction = opposed_bowls_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif 0xF2B10 <= recipe_code <= 0xF2B1B or 0xF2B4C <= recipe_code <= 0xF2B57:
        from stix_bowled_spine import bowled_spine_outline
        recording, construction = bowled_spine_outline(donor, recipe_code)
        construction["method"] = spec.adaptation_for(italic)
    elif 0xF2B04 <= recipe_code <= 0xF2B0F or 0xF2B40 <= recipe_code <= 0xF2B4B:
        from stix_double_bowl import double_bowl_outline
        recording, construction = double_bowl_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif 0xF2A45 <= recipe_code <= 0xF2A50 or 0xF2A5D <= recipe_code <= 0xF2A68:
        from stix_arched_terminals import arched_terminal_outline
        recording, construction = arched_terminal_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif (0xF2A51 <= recipe_code <= 0xF2A5C or 0xF2A69 <= recipe_code <= 0xF2A80) and spec.direct_donor is None:
        from stix_repeated_arch import repeated_arch_outline
        recording, construction = repeated_arch_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif recipe_code in EXTENDED_ARCH_RECIPES or recipe_code in TURNED_EXTENDED_ARCH_RECIPES:
        recording, construction = extended_arch_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif recipe_code == 0xF2A21:
        recording, construction = short_bowl_outline(donor)
        construction["method"] = spec.adaptation
    elif recipe_code in ARCH_RECIPES:
        recording, construction = arch_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif recipe_code in BOWL_RECIPES:
        recording, construction = bowl_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
    elif recipe_code in ARM_RECIPES:
        recording, construction = arm_outline(donor, recipe_code)
        construction["method"] = spec.adaptation
        # UFO plist dictionaries cannot contain None values.
        construction = {key: value for key, value in construction.items() if value is not None}
    elif spec.roman_stem_donor is not None and not italic:
        recording, stem_dx = roman_turned_arm_outline(donor)
        construction = {
            "armDonorCodePoint": spec.direct_donor,
            "armDonorGlyph": cmap[spec.direct_donor],
            "stemDonorCodePoint": spec.roman_stem_donor,
            "stemDonorGlyph": cmap[spec.roman_stem_donor],
            "stemOffsetX": stem_dx,
            "method": spec.adaptation,
        }
    elif spec.direct_donor is not None:
        donor_name = cmap[spec.direct_donor]
        recording = decomposed_recording(donor, donor_name)
        construction = {
            "donorCodePoint": spec.direct_donor,
            "donorGlyph": donor_name,
            "method": spec.adaptation,
        }
    else:
        upper, lower = recipes[recipe_code]
        recording, lower_dx, lower_cut = compose_outline(donor, upper, lower)
        construction = {
            "upperDonorCodePoint": upper,
            "upperDonorGlyph": cmap[upper],
            "lowerDonorCodePoint": lower,
            "lowerDonorGlyph": cmap[lower],
            "upperCutY": UPPER_CUT,
            "lowerCutY": lower_cut,
            "lowerOffsetX": lower_dx,
            "method": spec.adaptation,
        }
    width = construction.get("advanceWidth", donor["hmtx"][width_name][0] + construction.get("archExpansionX", 0.0))
    construction["advanceWidth"] = width
    return recording, construction


def make_master(master, donor_path: Path) -> Font:
    variable = TTFont(donor_path)
    donor = instantiateVariableFont(variable, {AXIS_TAG: master.weight}, inplace=False, optimize=True)
    font = Font()
    set_font_info(font, donor, master.style, master.weight, master.italic)
    cmap = donor.getBestCmap()

    add_glyph(
        font, ".notdef", decomposed_recording(donor, ".notdef"), donor["hmtx"][".notdef"][0], None,
        {"method": "Native STIX Two .notdef outline and advance, unchanged."},
    )
    add_glyph(
        font, "space", decomposed_recording(donor, cmap[0x20]), donor["hmtx"][cmap[0x20]][0], 0x20,
        {"donorCodePoint": 0x20, "donorGlyph": cmap[0x20], "method": "Native STIX Two space advance, unchanged."},
    )

    for spec in glyphs_for_posture(master.italic):
        if spec.stemless:
            from stix_stemless import stemless_outline
            recording, construction = stemless_outline(donor, spec.glyph_id)
        elif spec.middle_legs:
            from stix_middle_legs import middle_legs_outline
            recording, construction = middle_legs_outline(donor, spec.recipe_code_point)
        else:
            recording, construction = legacy_outline(donor, spec, master.italic)
        construction["method"] = spec.adaptation_for(master.italic)
        construction["glyphId"] = spec.glyph_id
        if spec.recipe_code_point is not None:
            construction["recipeCodePoint"] = spec.recipe_code_point
        width = construction.get("advanceWidth", donor["hmtx"][cmap[spec.width_donor]][0])
        add_glyph(font, spec.glyph_name, recording, width, spec.code_point, construction)

    font.glyphOrder = list(glyph_order_for_posture(master.italic))
    font.lib["public.glyphOrder"] = font.glyphOrder
    font.lib["org.quintessential.source"] = {
        "baseFamily": "STIX Two Text",
        "baseVersion": "2.13 b171",
        "donorFilename": donor_path.name,
        "donorSha256": sha256(donor_path),
        "posture": master.posture,
        "userWeight": master.weight,
        "designWeight": master.design_weight,
        "axisMap": [list(item) for item in AXIS_MAP],
    }
    donor.close()
    variable.close()
    return font


def convert_master_pairs_to_quadratic(fonts: dict[str, Font]) -> None:
    """Convert custom cubic recipes pairwise so all source contours are quadratic."""
    for first, second in (("Regular", "Bold"), ("Italic", "BoldItalic")):
        fonts_to_quadratic(
            [fonts[first], fonts[second]],
            max_err=QUADRATIC_ERROR,
            reverse_direction=False,
            remember_curve_type=True,
            all_quadratic=True,
        )
    for font in fonts.values():
        font.kerning.clear()
        profiles = {name: kerning_profile(font[name]) for name in font.glyphOrder[2:]}
        for left in font.glyphOrder[2:]:
            for right in font.glyphOrder[2:]:
                font.kerning[left, right] = pair_kerning(font[left], font[right], profiles)


def compatible_structure(font: Font, glyph_name: str) -> tuple:
    recording = glyph_recording(font[glyph_name])
    return tuple((operation, len(operands)) for operation, operands in recording)


def validate_sources(fonts: dict[str, Font]) -> None:
    for style, font in fonts.items():
        italic = bool(font.info.italicAngle)
        order = glyph_order_for_posture(italic)
        expected_unicodes = {0x20, *(glyph.code_point for glyph in glyphs_for_posture(italic))}
        if tuple(font.glyphOrder) != order or set(font.keys()) != set(order):
            raise RuntimeError(f"{style} has an unexpected glyph repertoire")
        actual_unicodes = {code_point for glyph in font for code_point in glyph.unicodes}
        if actual_unicodes != expected_unicodes:
            raise RuntimeError(f"{style} has an unexpected cmap source repertoire")
        expected_pairs = {(left, right) for left in order[2:] for right in order[2:]}
        if set(font.kerning) != expected_pairs:
            raise RuntimeError(f"{style} does not contain all {len(expected_pairs)} explicit kerning pairs")
        for glyph_name in order:
            recording = glyph_recording(font[glyph_name])
            if any(operation == "curveTo" for operation, _ in recording):
                raise RuntimeError(f"{style} {glyph_name} contains a cubic source segment")
            if font[glyph_name].components:
                raise RuntimeError(f"{style} {glyph_name} contains an undecomposed component")

    for first, second in (("Regular", "Bold"), ("Italic", "BoldItalic")):
        for glyph_name in fonts[first].glyphOrder:
            if compatible_structure(fonts[first], glyph_name) != compatible_structure(fonts[second], glyph_name):
                raise RuntimeError(f"{glyph_name} is not interpolation-compatible in {first}/{second}")


def make_designspace(stage: Path, posture_name: str) -> Path:
    posture = posture_by_name(posture_name)
    document = DesignSpaceDocument()
    document.formatVersion = "5.0"
    axis = AxisDescriptor(
        tag=AXIS_TAG,
        name=AXIS_NAME,
        minimum=AXIS_MINIMUM,
        default=AXIS_DEFAULT,
        maximum=AXIS_MAXIMUM,
        map=list(AXIS_MAP),
        axisOrdering=0,
        axisLabels=[
            AxisLabelDescriptor(name=name, userValue=weight, elidable=weight == 400)
            for weight, name in NAMED_WEIGHTS
        ],
    )
    document.addAxis(axis)
    masters = [master for master in MASTERS if master.posture == posture_name]
    for master in masters:
        source = SourceDescriptor(
            filename=master.filename,
            name=f"Quintessential Serif {master.style}",
            familyName=FAMILY_NAME,
            styleName=master.style,
            designLocation={AXIS_NAME: master.design_weight},
        )
        if master.weight == AXIS_DEFAULT:
            source.copyInfo = True
            source.copyLib = True
            source.copyFeatures = True
            source.copyGroups = True
        document.addSource(source)

    for weight, weight_name in NAMED_WEIGHTS:
        style = f"{weight_name} Italic" if posture.italic and weight != 400 else "Italic" if posture.italic else weight_name
        postscript_style = style.replace(" ", "")
        instance = InstanceDescriptor(
            name=f"{FAMILY_NAME} {style}",
            familyName=FAMILY_NAME,
            styleName=style,
            postScriptFontName=f"QuintessentialSerif-{postscript_style}",
            styleMapFamilyName=FAMILY_NAME,
            styleMapStyleName=(
                "bold italic" if posture.italic and weight == 700 else
                "italic" if posture.italic else
                "bold" if weight == 700 else "regular"
            ),
            userLocation={AXIS_NAME: weight},
        )
        document.addInstance(instance)
    path = stage / posture.designspace_filename
    document.write(path)
    return path


def replace_sources(stage: Path) -> None:
    source_root = SOURCES.resolve()
    if source_root != (ROOT / "fonts" / "QuintessentialSerif").resolve():
        raise RuntimeError("Refusing to replace sources outside the expected workspace directory")
    SOURCES.mkdir(parents=True, exist_ok=True)
    allowed = {master.filename for master in MASTERS} | {posture.designspace_filename for posture in POSTURES}
    for name in sorted(allowed):
        destination = (SOURCES / name).resolve()
        if destination.parent != source_root:
            raise RuntimeError(f"Unsafe source destination: {destination}")
        staged = stage / name
        if not staged.exists():
            raise RuntimeError(f"Missing staged source: {staged}")
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists():
            destination.unlink()
        if staged.is_dir():
            shutil.copytree(staged, destination)
        else:
            shutil.copyfile(staged, destination)


def expected_targets() -> tuple[Path, ...]:
    return tuple(
        [SOURCES / master.filename for master in MASTERS]
        + [SOURCES / posture.designspace_filename for posture in POSTURES]
    )


def check_existing_sources() -> None:
    donor_paths_from_manifest()
    missing = [path for path in expected_targets() if not path.exists()]
    if missing:
        raise SystemExit("Missing STIX foundation source(s): " + ", ".join(str(path) for path in missing))
    fonts = {master.style: Font.open(SOURCES / master.filename) for master in MASTERS}
    validate_sources(fonts)
    expected_map = list(AXIS_MAP)
    for posture in POSTURES:
        path = SOURCES / posture.designspace_filename
        document = DesignSpaceDocument.fromfile(path)
        if len(document.axes) != 1:
            raise RuntimeError(f"{path.name} must have exactly one axis")
        axis = document.axes[0]
        if (
            axis.tag != AXIS_TAG
            or axis.name != AXIS_NAME
            or (axis.minimum, axis.default, axis.maximum) != (AXIS_MINIMUM, AXIS_DEFAULT, AXIS_MAXIMUM)
            or axis.map != expected_map
        ):
            raise RuntimeError(f"{path.name} has unexpected weight-axis metadata")
        expected_source_names = {
            master.filename for master in MASTERS if master.posture == posture.name
        }
        if {Path(source.filename).name for source in document.sources} != expected_source_names:
            raise RuntimeError(f"{path.name} has unexpected master sources")
    print("Pinned donors, four UFO masters, and two designspaces pass foundation checks.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the existing pinned donors and checked-in sources without writing files.",
    )
    mode.add_argument(
        "--force",
        action="store_true",
        help="Explicitly replace existing masters and designspaces from the pinned donors.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_existing_sources()
        return

    existing = [path for path in expected_targets() if path.exists()]
    if existing and not args.force:
        raise SystemExit(
            "STIX foundation sources already exist; refusing to replace incremental edits. "
            "Use --check to validate them or --force for an intentional full bootstrap."
        )
    donor_paths = donor_paths_from_manifest()
    stage = ROOT / ".tmp" / "stix-source-import"
    stage_root = stage.resolve()
    if stage_root.parent != (ROOT / ".tmp").resolve():
        raise RuntimeError("Unsafe staging directory")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    fonts: dict[str, Font] = {}
    for master in MASTERS:
        font = make_master(master, donor_paths[master.posture])
        fonts[master.style] = font
        print(f"Staged {master.style} master")
    convert_master_pairs_to_quadratic(fonts)
    validate_sources(fonts)
    for master in MASTERS:
        fonts[master.style].save(stage / master.filename)
    for posture in POSTURES:
        make_designspace(stage, posture.name)
        print(f"Staged {posture.name} designspace")

    # Reopen the serialized UFOs before replacing authoritative sources.
    reopened = {master.style: Font.open(stage / master.filename) for master in MASTERS}
    validate_sources(reopened)
    replace_sources(stage)
    shutil.rmtree(stage)
    print("Replaced four UFO masters and two designspaces with the STIX Two foundation.")


if __name__ == "__main__":
    main()

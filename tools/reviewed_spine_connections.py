"""Independent preservation boundaries for reviewed internal-spine joins.

This module does not import the outline builders. Two body counters and small
explicit connection windows are the only geometric allowances; the ordered
elementary curves everywhere else must retain their types and coordinates.
"""
from fontTools.misc.fixedTools import floatToFixedToFloat
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import replayRecording
from fontTools.varLib.models import piecewiseLinearMap


def interpolate_connection_metadata(first, second, weight):
    from test_quintessential_font import EXPECTED_AVAR
    factor = floatToFixedToFloat(piecewiseLinearMap((weight - 400) / 300, EXPECTED_AVAR), 14)

    def interpolate(a, b):
        if isinstance(a, dict):
            assert a.keys() == b.keys(), "Connection metadata differs between masters"
            return {key: interpolate(a[key], b[key]) for key in a}
        if isinstance(a, (tuple, list)):
            assert len(a) == len(b), "Connection metadata topology differs between masters"
            return [interpolate(x, y) for x, y in zip(a, b)]
        if a == b:
            return a
        if isinstance(a, (int, float)) and not isinstance(a, bool):
            return a + factor * (b - a)
        raise AssertionError((a, b, "Discrete connection metadata changed between masters"))

    return interpolate(first, second)


def _body_variants(entry):
    recipe, middle = entry["recipeCodePoint"], entry["middleLegs"]
    for first, side in ((0xF2B1C, None), (0xF2B58, "left"), (0xF2B7C, "right"),
                        (0xF2C54, "left"), (0xF2C78, "right"), (0xF2C9C, "both")):
        if first <= recipe < first + 36:
            left, right = divmod(recipe - first, 6)
            if side in ("left", "both"):
                left = 3 if middle else 2
            if side in ("right", "both"):
                right = 1 if middle else 0
            return left, right
    raise AssertionError("Connection allowance requires an internal-spine identity")


def connection_windows(entry, metadata):
    """Return tightly bounded, named local regions in the actual glyph frame."""
    left, right = _body_variants(entry)
    offset = metadata.get("sigmoidOffsetX", 0)
    inner_left = metadata["stemLeftInnerX"] + offset
    inner_right = metadata["stemRightInnerX"] + offset
    outer_left = metadata["stemLeftX"] + offset
    outer_right = metadata["stemRightX"] + offset
    factor = ((inner_left - outer_left) - 83) / 60
    windows = []
    if right % 2:
        windows.append(("upper receiving quarters", (inner_left - 1, 390, inner_right + 5, 500)))
    if left % 2:
        windows.append(("lower receiving quarters", (inner_left - 5, -15, inner_right + 1, 70)))
    if left % 2 and right // 2 == 2:
        for label, first, last in (
            ("lower-hook outer quarter", metadata.get("lowerClosureOuterAnchor", (196 + 22 * factor, -235)), metadata["lowerClosureOuterJoin"]),
            ("lower-hook inner quarter", metadata["lowerClosureInnerJoin"], metadata.get("lowerClosureInnerAnchor", (216 + 11 * factor, -202 + 14 * factor))),
        ):
            x0, x1 = sorted((first[0] + offset, last[0] + offset))
            y0, y1 = sorted((first[1], last[1]))
            windows.append((label, (x0 - 1, y0 - 1, x1 + 1, y1 + 1)))
    recipe = entry["recipeCodePoint"]
    # Independent endpoint envelopes recorded during visual review. Do not
    # trust production metadata to enlarge the geometric exception itself.
    arch_regions = {item["side"]: item["bounds"] for item in metadata.get("archSpineJoinRegions", [])}
    specifications = (
        ("left", (0xF2B58 <= recipe <= 0xF2B7B or 0xF2C54 <= recipe <= 0xF2C77 or 0xF2C9C <= recipe <= 0xF2CBF),
         (80, 368, 166, 410.5), (72, 386.819277, 219, 449.734939) if right % 2 else (72, 353.734939, 219, 402)),
        ("right", (0xF2B7C <= recipe <= 0xF2B9F or 0xF2C78 <= recipe <= 0xF2C9B or 0xF2C9C <= recipe <= 0xF2CBF),
         (342, 64, 426, 109.275362), (332, 28.765625, 477, 69.9375) if left % 2 else (332, 59, 477, 108.765625)),
    )
    for side, required, regular, bold in specifications:
        if required:
            bounds = [a + factor * (b - a) for a, b in zip(regular, bold)]
            if side in arch_regions:
                assert max(abs(a - b) for a, b in zip(bounds, arch_regions[side])) < .01, (side, "Reviewed port envelope changed")
            x0, y0, x1, y1 = bounds
            windows.append((f"{side} arch-body port", (x0 + offset - 1, y0 - 1, x1 + offset + 1, y1 + 1)))
    return windows


def _contours(recording):
    result, current = [], []
    for item in recording:
        current.append(item)
        if item[0] == "closePath":
            result.append(current)
            current = []
    assert not current, "Unclosed source outline"
    return result


class _Segments(BasePen):
    def __init__(self):
        super().__init__(None)
        self.segments = []
        self.first = None

    def _moveTo(self, point):
        self.first = point

    def _lineTo(self, point):
        if self._getCurrentPoint() != point:
            self.segments.append(("line", (self._getCurrentPoint(), point)))

    def _qCurveToOne(self, control, point):
        self.segments.append(("quadratic", (self._getCurrentPoint(), control, point)))

    def _curveToOne(self, first, second, point):
        self.segments.append(("cubic", (self._getCurrentPoint(), first, second, point)))

    def _closePath(self):
        self._lineTo(self.first)


def _nonbody_segments(recording):
    result, counters = [], 0
    for contour in _contours(recording):
        area = AreaPen(None)
        replayRecording(contour, area)
        points = [point for _, values in contour for point in values]
        if area.value > 1000 and min(y for _, y in points) >= 0 and max(y for _, y in points) <= 500:
            counters += 1
            continue
        pen = _Segments()
        replayRecording(contour, pen)
        result.extend(pen.segments)
    assert counters == 2, (counters, "Expected exactly two enclosed body counters")
    return result


def _in_window(segment, window, tolerance):
    x0, y0, x1, y1 = window
    return all(x0 - tolerance <= x <= x1 + tolerance and y0 - tolerance <= y <= y1 + tolerance
               for x, y in segment[1])


def is_reviewed_connection_segment(points, entry, metadata, tolerance=1e-6):
    """Identify only a curve wholly inside one explicitly reviewed join."""
    return any(_in_window(("curve", points), window, tolerance)
               for _, window in connection_windows(entry, metadata))


def retained_connection_segments(recording, entry, metadata, tolerance=1e-6):
    windows = connection_windows(entry, metadata)
    retained = []
    for segment in _nonbody_segments(recording):
        pieces = [segment]
        if segment[0] == "line":
            # A port can shorten a long straight shaft. Split that shaft at
            # review boundaries so its untouched length remains an exact test.
            start, end = segment[1]
            cuts = {0.0, 1.0}
            for _, (x0, y0, x1, y1) in windows:
                for axis, values in ((0, (x0, x1)), (1, (y0, y1))):
                    if end[axis] != start[axis]:
                        cuts.update((value - start[axis]) / (end[axis] - start[axis])
                                    for value in values if 0 < (value - start[axis]) / (end[axis] - start[axis]) < 1)
            values = sorted(cuts)
            at = lambda t: tuple(a + t * (b - a) for a, b in zip(start, end))
            pieces = [("line", (at(a), at(b))) for a, b in zip(values, values[1:])]
        retained.extend(piece for piece in pieces
                        if not any(_in_window(piece, window, tolerance) for _, window in windows))
    return retained


def assert_preserved_connections(old, current, entry, metadata, tolerance=1e-6):
    """Require every segment outside the explicitly reviewed regions intact."""
    first = retained_connection_segments(old, entry, metadata, tolerance)
    second = retained_connection_segments(current, entry, metadata, tolerance)
    assert len(first) == len(second), (entry["glyphId"], len(first), len(second), "Unreviewed segment count changed")
    maximum = 0
    for index, ((op, points), (other_op, other_points)) in enumerate(zip(first, second)):
        assert (op, len(points)) == (other_op, len(other_points)), (entry["glyphId"], index, "Unreviewed segment type changed")
        difference = max(abs(a - b) for point, other in zip(points, other_points) for a, b in zip(point, other))
        assert difference <= tolerance, (entry["glyphId"], index, difference, "Unreviewed curve changed")
        maximum = max(maximum, difference)
    return {"retainedSegments": len(first), "maximumRetainedDelta": maximum,
            "changedRegions": [name for name, _ in connection_windows(entry, metadata)]}

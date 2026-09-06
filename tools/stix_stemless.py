"""Stemless Specials from the pinned Roman and Italic STIX vocabulary.

Open forms use posture-specific native terminals, with the turned Roman
double opening corrected to a thin upper finish and lower ball. The closed
double bowl joins upright epsilon wings into two rounded counters. The
spine retains native s's diagonal body with an upper ball and thin finish.
"""


DIRECT_DONORS = {
    "special-ring": 0x6F,
    "special-open-bowl": 0x63,
    "special-turned-open-bowl": 0x254,
    "special-double-open-bowl": 0x25B,
    "special-turned-double-open-bowl": 0x25C,
}


def _move(recording, dx=0, dy=0, reflect_x=False):
    sign = -1 if reflect_x else 1
    return [(op, tuple((sign * x + dx, y + dy) for x, y in points))
            for op, points in recording]


def _fit(operation, old_start, old_end, new_start, new_end):
    """Fit only a receiving quarter while retaining its endpoint tangents."""
    def point(p):
        return tuple(new_start[i] + (p[i] - old_start[i]) *
                     (new_end[i] - new_start[i]) / (old_end[i] - old_start[i])
                     if old_end[i] != old_start[i]
                     else p[i] + new_start[i] - old_start[i]
                     for i in (0, 1))
    return operation[0], tuple(point(p) for p in operation[1])


def _mean(first, second):
    return tuple((a + b) / 2 for a, b in zip(first, second))


def _reverse_run(start, operations):
    """Reverse native quadratic runs without approximating their curves."""
    edges, previous = [], start
    for op, points in operations:
        if op not in ("lineTo", "qCurveTo"):
            raise ValueError("Expected an open native quadratic run")
        edges.append((previous, op, points))
        previous = points[-1]
    reversed_ops = []
    for first, op, points in reversed(edges):
        reversed_ops.append((op, (*reversed(points[:-1]), first)))
    return previous, reversed_ops


def _closed_double_bowl(font):
    import import_stix_foundation as s
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.recordingPen import replayRecording

    cmap = font.getBestCmap()
    left = s.decomposed_recording(font, cmap[0x25B])
    right = s.decomposed_recording(font, cmap[0x25C])
    italic = bool(font["post"].italicAngle)
    if (len(left), len(right)) != ((22, 20) if italic else (20, 20)):
        raise RuntimeError("Pinned stemless epsilon topology changed")
    dx = left[5][1][-1][0] - right[13][1][-1][0]
    right = _move(right, dx)
    top = _mean(left[5][1][-1], right[13][1][-1])
    bottom = _mean(left[0][1][0], right[18][1][-1])
    outer = [
        ("moveTo", (bottom,)),
        _fit(left[1], left[0][1][0], left[1][1][-1], bottom, left[1][1][-1]),
        *left[2:5],
        _fit(left[5], left[4][1][-1], left[5][1][-1], left[4][1][-1], top),
        _fit(right[14], right[13][1][-1], right[14][1][-1], top, right[14][1][-1]),
        *right[15:18],
        _fit(right[18], right[17][1][-1], right[18][1][-1], right[17][1][-1], bottom),
        ("closePath", ()),
    ]
    upper_left, lower_left = ((11, 12), (16, 17)) if italic else ((9, 10), (14, 15))
    upper_top = _mean(left[upper_left[0] - 1][1][-1], right[10][1][-1])
    upper_waist = _mean(left[upper_left[1]][1][-1], right[8][1][-1])
    lower_bottom = _mean(left[lower_left[1]][1][-1], right[3][1][-1])
    lower_waist = _mean(left[lower_left[0] - 1][1][-1], right[5][1][-1])

    def fitted(index, recording, new_start=None, new_end=None):
        old_start, old_end = recording[index - 1][1][-1], recording[index][1][-1]
        return _fit(recording[index], old_start, old_end,
                    old_start if new_start is None else new_start,
                    old_end if new_end is None else new_end)

    upper = [("moveTo", (upper_top,)),
             fitted(upper_left[0], left, new_start=upper_top),
             fitted(upper_left[1], left, new_end=upper_waist),
             fitted(9, right, new_start=upper_waist),
             fitted(10, right, new_end=upper_top), ("closePath", ())]
    lower = [("moveTo", (lower_waist,)),
             fitted(lower_left[0], left, new_start=lower_waist),
             fitted(lower_left[1], left, new_end=lower_bottom),
             fitted(4, right, new_start=lower_bottom),
             fitted(5, right, new_end=lower_waist), ("closePath", ())]
    recording = [*outer, *upper, *lower]
    native_right = s.decomposed_recording(font, cmap[0x25C])
    pen = BoundsPen(None)
    replayRecording(native_right, pen)
    right_bearing = font["hmtx"][cmap[0x25C]][0] - pen.bounds[2]
    pen = BoundsPen(None)
    replayRecording(recording, pen)
    return recording, {
        "bodyDesign": "upright-native-epsilon-wings-with-two-rounded-counters",
        "leftDonorCodePoint": 0x25B,
        "rightDonorCodePoint": 0x25C,
        "rightDonorOffsetX": dx,
        "counterCount": 2,
        "counterJoinDesign": "fitted-native-inner-quarters-with-horizontal-waist-tangents",
        "upperCounterTopY": upper_top[1],
        "lowerCounterBottomY": lower_bottom[1],
        "upperCounterWaistY": upper_waist[1],
        "lowerCounterWaistY": lower_waist[1],
        "advanceWidth": pen.bounds[2] + right_bearing,
    }


def _spine(font):
    import import_stix_foundation as s
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.recordingPen import replayRecording

    cmap = font.getBestCmap()
    body = s.decomposed_recording(font, cmap[0x73])
    epsilon = s.decomposed_recording(font, cmap[0x25B])
    italic = bool(font["post"].italicAngle)
    if (len(body), len(epsilon)) != ((24, 22) if italic else (23, 20)):
        raise RuntimeError("Pinned stemless s topology changed")
    outer_top_index, inner_top_index = (11, 19) if italic else (7, 15)
    lower_inner_index, outer_bottom_index = (8, 22) if italic else (4, 18)
    upper_end = 11 if italic else 9
    upper_dx = body[outer_top_index][1][-1][0] - epsilon[5][1][-1][0]
    upper_dy = body[outer_top_index][1][-1][1] - epsilon[5][1][-1][1]
    upper = _move(epsilon[6:upper_end], upper_dx, upper_dy)
    if italic:
        # Only the local native epsilon finish changes opening direction;
        # s's native Italic body, slant and both waist sweeps stay untouched.
        lower_start, lower_ops = _reverse_run(epsilon[17][1][-1], epsilon[18:21])
        lower_dx = body[outer_bottom_index][1][-1][0] + lower_start[0]
        lower_dy = body[outer_bottom_index][1][-1][1] - lower_start[1]
        lower = _move(lower_ops, lower_dx, lower_dy, reflect_x=True)
        lower_donor = 0x25B
    else:
        reversed_e = s.decomposed_recording(font, cmap[0x25C])
        lower_dx = body[outer_bottom_index][1][-1][0] - reversed_e[0][1][0][0]
        lower_dy = body[outer_bottom_index][1][-1][1] - reversed_e[0][1][0][1]
        lower = _move(reversed_e[1:4], lower_dx, lower_dy)
        lower_donor = 0x25C
    lower_join = _fit(body[lower_inner_index], body[lower_inner_index - 1][1][-1],
                      body[lower_inner_index][1][-1], lower[-1][1][-1],
                      body[lower_inner_index][1][-1])
    upper_join = _fit(body[inner_top_index], body[inner_top_index - 1][1][-1],
                      body[inner_top_index][1][-1], upper[-1][1][-1],
                      body[inner_top_index][1][-1])
    recording = [("moveTo", (body[outer_bottom_index][1][-1],)),
                 *lower, lower_join, *body[lower_inner_index + 1:outer_top_index + 1],
                 *upper, upper_join, *body[inner_top_index + 1:outer_bottom_index + 1],
                 ("closePath", ())]
    native_bounds, new_bounds = BoundsPen(None), BoundsPen(None)
    replayRecording(body, native_bounds)
    replayRecording(recording, new_bounds)
    # The Italic lower finish reaches farther left than s's wedge. Restore
    # the native left sidebearing and add that span to the advance; retaining
    # the old advance would make Bold self-pairs collide at the lower sweep.
    body_dx = max(0, native_bounds.bounds[0] - new_bounds.bounds[0])
    recording = _move(recording, body_dx)
    return recording, {
        "bodyDonorCodePoint": 0x73,
        "bodyOffsetX": body_dx,
        "bodyDesign": "native-s-diagonal-body-with-rounded-open-terminals",
        "upperTerminalDonorCodePoint": 0x25B,
        "upperTerminalOffsetX": upper_dx + body_dx,
        "upperTerminalOffsetY": upper_dy,
        "lowerTerminalDonorCodePoint": lower_donor,
        "lowerTerminalOffsetX": lower_dx + body_dx,
        "lowerTerminalOffsetY": lower_dy,
        "lowerTerminalReflectedX": italic,
        "terminalDesign": "upper-ball-and-thin-lower-finish",
        "counterCount": 0,
        "advanceWidth": font["hmtx"][cmap[0x73]][0] + body_dx,
    }


def _turned_double_open_bowl(font):
    """Retain the Roman reversed-epsilon body with orientation-correct ends."""
    import import_stix_foundation as s

    cmap = font.getBestCmap()
    body = s.decomposed_recording(font, cmap[0x25C])
    epsilon = s.decomposed_recording(font, cmap[0x25B])
    if len(body) != 20 or len(epsilon) != 20:
        raise RuntimeError("Pinned Roman stemless epsilon topology changed")
    lower_dx = body[0][1][0][0] + epsilon[5][1][-1][0]
    lower_dy = body[0][1][0][1] + epsilon[5][1][-1][1]
    lower = [(op, tuple((lower_dx - x, lower_dy - y) for x, y in points))
             for op, points in epsilon[6:9]]
    upper_start, upper_ops = _reverse_run(body[0][1][0], body[1:4])
    upper_dx = body[13][1][-1][0] - body[0][1][0][0]
    upper_dy = body[13][1][-1][1] + body[0][1][0][1]
    upper = [(op, tuple((x + upper_dx, upper_dy - y) for x, y in points))
             for op, points in upper_ops]
    upper_start = upper_start[0] + upper_dx, upper_dy - upper_start[1]
    lower_join = _fit(body[4], body[3][1][-1], body[4][1][-1],
                      lower[-1][1][-1], body[4][1][-1])
    upper_join = _fit(body[10], body[9][1][-1], body[10][1][-1],
                      body[9][1][-1], upper_start)
    return [body[0], *lower, lower_join, *body[5:10], upper_join,
            *upper, *body[14:]], {
        "bodyDonorCodePoint": 0x25C,
        "bodyDesign": "native-reversed-epsilon-lobes-with-turned-opening-terminals",
        "upperTerminalDonorCodePoint": 0x25C,
        "upperTerminalOffsetX": upper_dx,
        "upperTerminalOffsetY": upper_dy,
        "upperTerminalReflectedY": True,
        "upperTerminalReversed": True,
        "lowerTerminalDonorCodePoint": 0x25B,
        "lowerTerminalOffsetX": lower_dx,
        "lowerTerminalOffsetY": lower_dy,
        "lowerTerminalTurned": True,
        "terminalDesign": "thin-upper-finish-and-lower-ball",
        "counterCount": 0,
        "advanceWidth": font["hmtx"][cmap[0x25C]][0],
    }


def stemless_outline(font, glyph_id):
    """Return one of the seven Specials and plist-safe construction metadata."""
    import import_stix_foundation as s

    if glyph_id == "special-turned-double-open-bowl" and not font["post"].italicAngle:
        recording, metadata = _turned_double_open_bowl(font)
    elif glyph_id in DIRECT_DONORS:
        code = DIRECT_DONORS[glyph_id]
        name = font.getBestCmap()[code]
        recording = s.decomposed_recording(font, name)
        metadata = {"bodyDonorCodePoint": code, "bodyDesign": "native-direct-outline",
                    "counterCount": 1 if glyph_id == "special-ring" else 0,
                    "advanceWidth": font["hmtx"][name][0]}
    elif glyph_id == "special-closed-double-bowl":
        recording, metadata = _closed_double_bowl(font)
    elif glyph_id == "special-spine":
        recording, metadata = _spine(font)
    else:
        raise ValueError(f"Unknown stemless Special: {glyph_id}")
    metadata.update(family="stemless-specials", glyphId=glyph_id,
                    posture="Italic" if font["post"].italicAngle else "Roman")
    return s.rounded_recording(recording), metadata

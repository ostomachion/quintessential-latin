"""Upper-bowled Roman spines built from the native turned-a bowl.

Only the curved free terminal is borrowed from epsilon.  The bowl keeps
turned-a's own sloping belly and counter; the receiving shaft and its
endings come from the established b/p/hooked-b vocabulary.
"""


def _move(recording, dx=0, dy=0):
    return [(op, tuple((x + dx, y + dy) for x, y in points))
            for op, points in recording]


def _fit(operation, old_start, old_end, new_start, new_end):
    def point(p):
        return tuple(new_start[i] + (p[i] - old_start[i]) *
                     (new_end[i] - new_start[i]) / (old_end[i] - old_start[i])
                     if old_end[i] != old_start[i]
                     else p[i] + new_start[i] - old_start[i]
                     for i in (0, 1))
    return operation[0], tuple(point(p) for p in operation[1])


def _counter(turned_a, stem):
    """End the native counter on its shaft, excluding a's overlap seam.

    The donor is a single overlapping contour. Its last inner quadratic
    runs a few units inside the shaft before doubling back into the outer
    shoulder. Split that quadratic at the actual shaft intersection rather
    than retaining the overlap as a spur in a separate counter contour.
    """
    from fontTools.misc.bezierTools import solveQuadratic, splitQuadraticAtT

    first, control, end = turned_a[12][1]
    middle = tuple((first[i] + control[i]) / 2 for i in (0, 1))
    a = middle[0] - 2 * control[0] + end[0]
    b = 2 * (control[0] - middle[0])
    roots = [t for t in solveQuadratic(a, b, middle[0] - stem) if 0 < t < 1]
    if len(roots) != 1:
        raise RuntimeError("Turned-a counter does not meet its receiving shaft once")
    _, fitted_control, fitted_end = splitQuadraticAtT(middle, control, end, roots[0])[0]
    if abs(fitted_end[0] - stem) > 1e-6:
        raise RuntimeError("Turned-a counter shaft intersection drifted")
    return [
        ("moveTo", (turned_a[9][1][-1],)),
        *turned_a[10:12],
        ("qCurveTo", (first, middle)),
        ("qCurveTo", (fitted_control, (stem, fitted_end[1]))),
        ("closePath", ()),
    ], fitted_end[1]


def normal_spine(font, variant):
    """Return one of the six single-shaft upper-bowled spine variants."""
    import import_stix_foundation as s

    if font["post"].italicAngle or variant not in (0, 1, 4, 5, 8, 9):
        raise ValueError("Normal bowled spines require a Roman normal variant")
    cmap = font.getBestCmap()
    native = lambda code: s.decomposed_recording(font, cmap[code])
    bowl, turned_a, epsilon, p = native(0x62), native(0x250), native(0x25B), native(0x70)
    if (len(bowl), len(turned_a), len(epsilon), len(p)) != (20, 25, 20, 27):
        raise RuntimeError("Pinned upper-bowled spine donor topology changed")

    left, right = bowl[8][1][-1][0], bowl[2][1][-1][0]
    dx = right - turned_a[9][1][-1][0]
    turned_a = _move(turned_a, dx)
    if abs(turned_a[2][1][-1][0] - left) > 1e-6:
        raise RuntimeError("Turned-a and b no longer share their native shaft width")

    # The native b shoulder owns the outer join into the shaft.  Fit its
    # far extremum to turned-a's bowl, retaining both horizontal tangents.
    shoulder = _fit(bowl[4], bowl[3][1][-1], bowl[4][1][-1],
                    bowl[3][1][-1], turned_a[15][1][-1])
    low = turned_a[0][1][0]
    epsilon_dx = low[0] - epsilon[18][1][-1][0]
    epsilon_dy = low[1] - epsilon[18][1][-1][1]
    free_terminal = _move(epsilon[16:19], epsilon_dx, epsilon_dy)
    inner_low = _move(epsilon[15:16], epsilon_dx, epsilon_dy)[0][1][-1]
    lower_shoulder = _fit(turned_a[19], turned_a[18][1][-1], turned_a[19][1][-1],
                          turned_a[18][1][-1], inner_low)

    body = [bowl[2], bowl[3], shoulder, *turned_a[16:19], lower_shoulder, *free_terminal]
    lower_dx = None
    if variant % 2:
        # A descending shaft enters the lower sweep on its inner side.
        # p's native lower-bowl quarter provides the smooth, shallow return
        # to that inner edge; its entire foot remains rigid and unmodified.
        lower = s.native_terminal(font, 0x70, p[16][1][-1][1], False)
        lower_dx = right - lower.start[0]
        lower = lower.translated(lower_dx)
        native_join = _move(p[15:17], lower_dx)
        join = _fit(native_join[0], _move(p[14:15], lower_dx)[0][1][-1],
                    native_join[0][1][-1], low, native_join[0][1][-1])
        body.extend([join, native_join[1], *lower.operations])
    else:
        body.append(turned_a[1])
    body.append(("lineTo", ((left, 300),)))

    if variant // 4 == 0:
        head_code, first, last, left_cut, right_cut = 0x70, 3, 9, 350, 460
    elif variant // 4 == 1:
        head_code, first, last, left_cut, right_cut = 0x62, 7, 1, 550, 550
    else:
        head_code, first, last, left_cut, right_cut = 0x253, 1, 9, 420, 470
    edges = s.donor_contour_edges(font, head_code)
    head = s.native_arc(edges, first, s.shaft_point(edges[first], left_cut),
                        last, s.shaft_point(edges[last], right_cut))
    head_dx = (left + right) / 2 - head.center
    head = head.translated(head_dx)
    body_path = s.NativePath((right, 430), tuple(body))
    outer = s.join_native_regions(head, body_path)
    counter, counter_join = _counter(turned_a, right)
    # Native a's narrower bowl keeps its original proportions. Its advance
    # is aligned with b's established shaft and native far-side sidebearing.
    advance = font["hmtx"][cmap[0x250]][0] + dx
    return s.rounded_recording([*outer, *counter]), {
        "bodyDonorCodePoint": 0x250,
        "bodyOffsetX": dx,
        "spineDonorCodePoint": 0x250,
        "spineOffsetX": dx,
        "shaftDonorCodePoint": 0x62,
        "upperDonorCodePoint": head_code,
        "upperOffsetX": head_dx,
        "lowerDonorCodePoint": 0x70 if variant % 2 else None,
        "lowerOffsetX": lower_dx,
        "freeTerminalDonorCodePoint": 0x25B,
        "freeTerminalOffsetX": epsilon_dx,
        "freeTerminalOffsetY": epsilon_dy,
        "freeTerminalTurned": False,
        "counterDesign": "native-turned-a-shaft-intersection",
        "counterShaftIntersectionY": counter_join,
        "stemLeftX": left,
        "stemRightX": right,
        "advanceWidth": advance,
        "family": "bowled-spines",
    }


def normal_spine_terminal(font):
    """Pretrim the ascender at its shoulder for a terminal-owned arch port."""
    import import_stix_foundation as s

    recording, metadata = normal_spine(font, 4)
    bowl = s.decomposed_recording(font, font.getBestCmap()[0x62])
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    first = next(i for i, operation in enumerate(outer) if operation == bowl[2])
    left, right = metadata["stemLeftX"], metadata["stemRightX"]
    last = next(i for i, operation in enumerate(outer)
                if operation == ("lineTo", ((left, 300),)))
    top = bowl[2][1][-1][1]
    terminal = [("moveTo", ((right, top),)), *outer[first + 1:last],
                ("lineTo", ((left, top),)), ("closePath", ()), *contours[1]]
    return s.rounded_recording(terminal), metadata, (left + right) / 2

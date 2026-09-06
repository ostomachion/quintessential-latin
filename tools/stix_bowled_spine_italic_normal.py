"""Native Italic upper-bowled spines, independent of single-storey a.

STIX's Italic turned-a has an actual diagonal upper bowl, drawn separately
from its shaft. Keep that bowl rigid, replace the lower ball by epsilon's
flat terminal, and attach each native stem ending on its own slanted axis.
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


def italic_normal_spine(font, variant):
    """Return one of the six normal narrow Italic spine variants."""
    import import_stix_foundation as s

    if not font["post"].italicAngle or variant not in (0, 1, 4, 5, 8, 9):
        raise ValueError("Italic normal spines require an Italic normal variant")
    cmap = font.getBestCmap()
    native = lambda code: s.decomposed_recording(font, cmap[code])
    source, epsilon, p = native(0x250), native(0x25B), native(0x70)
    if (len(source), len(epsilon), len(p)) != (31, 22, 27):
        raise RuntimeError("Pinned Italic spine donor topology changed")
    contours = list(s.native_recording_contours(source))
    edges = s.contour_edges(contours[0])
    left_edge, right_edge = edges[2], edges[12]
    shaft_at = lambda edge, y: s.shaft_point(edge, y, extend=True)
    center_at = lambda y: (shaft_at(left_edge, y)[0] + shaft_at(right_edge, y)[0]) / 2
    center = center_at(250)
    low = source[0][1][0]
    terminal_dx = low[0] - epsilon[20][1][-1][0]
    terminal_dy = low[1] - epsilon[20][1][-1][1]
    terminal = _move(epsilon[18:21], terminal_dx, terminal_dy)
    inner_low = _move(epsilon[17:18], terminal_dx, terminal_dy)[0][1][-1]
    inner_curve = _fit(source[15], source[14][1][-1], source[15][1][-1],
                       source[14][1][-1], inner_low)
    body_start = s.shaft_point(edges[9], 430)
    body_end = s.shaft_point(left_edge, 300)
    lower_dx = None
    arm = []
    if variant % 2:
        # The native p has a separate shaft and bowl, with a deliberately
        # overlapping lower attachment. Retain that construction model:
        # the full foot owns the straight descending shaft; the open lower
        # sweep has an internal port, hidden inside that receiving shaft.
        p_edges = s.contour_edges(list(s.native_recording_contours(p))[1])
        p_center = sum(shaft_at(p_edges[i], 250)[0] for i in (1, 10)) / 2
        lower_dx = center - p_center
        lower = s.native_terminal(font, 0x70, 50, False).translated(lower_dx)
        body = list(source[10:14])
        entry = source[13][1][-1]
        into_foot = s.tangent_connector(entry, lower.start,
                                        (right_edge[2][-1][0] - right_edge[0][0]) /
                                        (right_edge[2][-1][1] - right_edge[0][1]),
                                        lower.slope(True))
        out_of_foot = s.tangent_connector(lower.end, body_end, lower.slope(False),
                                         (left_edge[2][-1][0] - left_edge[0][0]) /
                                         (left_edge[2][-1][1] - left_edge[0][1]))
        body.extend([into_foot.operation(), *lower.operations, out_of_foot.operation()])
        native_return = _move(p[1:2], lower_dx)[0]
        outer_return = _fit(native_return, _move(p[:1], lower_dx)[0][1][0],
                            native_return[1][-1], low, native_return[1][-1])
        port_y = native_return[1][-1][1]
        arm = [("moveTo", (entry,)), source[14], inner_curve, *terminal,
               outer_return, ("lineTo", ((center_at(port_y), port_y),)),
               ("lineTo", ((center_at(entry[1]), entry[1]),)), ("closePath", ())]
    else:
        body = [*source[10:15], inner_curve, *terminal, *source[1:3],
                ("lineTo", (body_end,))]
    body_path = s.NativePath(body_start, tuple(body))

    kind = variant // 4
    if kind == 0:
        head_code, contour, first, last, axis_right, left_y, right_y = 0x70, 1, 1, 8, 10, 350, 460
    elif kind == 1:
        head_code, contour, first, last, axis_right, left_y, right_y = 0x62, 0, 1, 8, 8, 450, 500
    else:
        head_code, contour, first, last, axis_right, left_y, right_y = 0x253, 0, 1, 7, 7, 420, 470
    head_edges = s.donor_contour_edges(font, head_code, contour)
    head_center = sum(shaft_at(head_edges[i], 250)[0] for i in (first, axis_right)) / 2
    head_dx = center - head_center
    head = s.native_arc(head_edges, first, s.shaft_point(head_edges[first], left_y),
                        last, s.shaft_point(head_edges[last], right_y)).translated(head_dx)
    recording = [*s.join_native_regions(head, body_path), *arm, *contours[1]]
    metadata = {
        "spineDonorCodePoint": 0x250,
        "spineOffsetX": 0,
        "spineOffsetY": 0,
        "spineTurned": False,
        "bodyDonorCodePoint": 0x250,
        "upperDonorCodePoint": head_code,
        "upperOffsetX": head_dx,
        "freeTerminalDonorCodePoint": 0x25B,
        "freeTerminalOffsetX": terminal_dx,
        "freeTerminalOffsetY": terminal_dy,
        "freeTerminalTurned": False,
        "sharedStemCenterX": center,
        "sharedStemCenterY": 250,
        "advanceWidth": font["hmtx"][cmap[0x250]][0],
        "counterDesign": "native-italic-turned-a-bowl",
        "family": "bowled-spines",
    }
    if variant % 2:
        metadata.update(lowerDonorCodePoint=0x70, lowerOffsetX=lower_dx,
                        lowerAttachmentDesign="native-p-quarter-and-overlap-port")
    return s.rounded_recording(recording), metadata


def italic_normal_spine_terminal(font):
    """Expose the native shoulder port without an ascender head."""
    import import_stix_foundation as s

    recording, metadata = italic_normal_spine(font, 4)
    contours = list(s.native_recording_contours(recording))
    source = s.decomposed_recording(font, font.getBestCmap()[0x250])
    outer = contours[0]
    first = next(i for i, operation in enumerate(outer) if operation == source[10])
    body_left = source[3][1][-1]
    last = next(i for i, operation in enumerate(outer) if operation[0] == "lineTo"
                and operation[1][-1][1] == 300)
    # Extend the retained slanted left shaft to the native top of its
    # straight segment. The short closing port lies beneath the incoming
    # arch's shared stem and is never visible in the composed outline.
    terminal = [("moveTo", (source[10][1][-1],)), *outer[first + 1:last],
                ("lineTo", (body_left,)), ("closePath", ()), *contours[1]]
    return s.rounded_recording(terminal), metadata, metadata["sharedStemCenterX"]

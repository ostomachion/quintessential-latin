"""The native Italic shared sigmoid and its two slanted receiving shafts.

Both lobes use the independently drawn turned-a, with a rigid half-turn for
the lower one. Paired counters describe one shared diagonal; every terminal
and side-arch product reuses this body at its unchanged native span.
"""

from stix_geometry import fit_operation, move
from stix_double_bowl_italic import _head, _native


def _receiving_shoulder(recording, start, operation, receiver, *, port):
    """Trim the donor's buried entrance at the actual receiving head axis.

    Turned-a draws its bowl as an independent overlapping component. Its
    internal entrance must not be visited after a shared outer shaft: Bold
    would double back across that shaft before the roof emerges. Keep the
    native roof above the intersection and join at that intersection once.
    """
    if port:
        # This cap is hidden inside the incoming arch. Taking the direct
        # chord avoids the same backwards detour through a projected port.
        return [*recording, ("lineTo", (start,)), operation]
    from fontTools.misc.bezierTools import solveQuadratic, splitQuadraticAtT
    first, target = receiver
    direction = (target[0] - first[0], target[1] - first[1])
    cross = lambda a: a[0] * direction[1] - a[1] * direction[0]
    control = operation[1][0]
    end = tuple((control[i] + operation[1][1][i]) / 2 for i in (0, 1))
    roots = [t for t in solveQuadratic(
        cross(tuple(start[i] - 2 * control[i] + end[i] for i in (0, 1))),
        cross(tuple(2 * (control[i] - start[i]) for i in (0, 1))),
        cross(tuple(start[i] - first[i] for i in (0, 1)))) if 0 < t < 1]
    if len(roots) != 1:
        raise RuntimeError("Native Italic roof must meet its receiving head axis once")
    entry, handle, endpoint = splitQuadraticAtT(start, control, end, roots[0])[1]
    return [*recording, ("lineTo", (entry,)),
            ("qCurveTo", (handle, endpoint)),
            ("qCurveTo", operation[1][1:])]


def _geometry(font):
    import import_stix_foundation as s
    source = _native(font, 0x250)
    if len(source) != 31:
        raise RuntimeError("Pinned Italic turned-a topology changed")
    edges = s.donor_contour_edges(font, 0x250)
    left = lambda y: s.shaft_point(edges[2], y, extend=True)
    inner = lambda y: s.shaft_point(edges[12], y, extend=True)
    sum_y = source[27][1][-1][1] + source[0][1][0][1]
    tip = source[28][1][-1]
    sum_x = left(sum_y - tip[1])[0] + tip[0]
    right = lambda y: (sum_x - left(sum_y - y)[0], y)
    right_inner = lambda y: (sum_x - inner(sum_y - y)[0], y)
    return source, move(source, sum_x, sum_y, True), left, inner, right_inner, right, sum_x, sum_y


def _counters(font, geometry):
    """Fit two native counter runs together, preserving their donor tangents."""
    source, turned, left, inner, ri, right, sum_x, sum_y = geometry
    width = inner(250)[0] - left(250)[0]
    factor = (width - 80) / 54
    low_y, join_y = 232 + 23 * factor, 350 - 5 * factor
    low, high = inner(low_y), ri(join_y)
    top = source[24][1][-1]
    left_top = inner(372 - 20 * factor)
    diagonal = fit_operation(source[23], source[22][1][-1], source[23][1][-1], low, high)
    roof = fit_operation(source[24], source[23][1][-1], source[24][1][-1], high, top)
    returning = fit_operation(source[25], source[24][1][-1], source[25][1][-1], top, left_top)
    upper = [("moveTo", (low,)), diagonal, roof, returning, ("closePath", ())]
    return [*upper, *move(upper, sum_x, sum_y, True)]


def _join_upper(font, recording, metadata, right, ri):
    """Close a facing native hook into the ascending right shaft."""
    hook = move(_native(font, 0x253), metadata["upperOffsetX"])
    d = move(_native(font, 0x64), metadata["rightUpperOffsetX"])
    alpha = _native(font, 0x251)
    outer_anchor, inner_anchor = hook[3][1][-1], hook[6][1][-1]
    outer_end, inner_start = right(620), ri(620)
    outer = fit_operation(d[3], d[2][1][-1], d[3][1][-1], outer_anchor, outer_end)
    outer_points = list(outer[1])
    outer_points[-2] = right(outer_end[1] + 55)
    outer = (outer[0], tuple(outer_points))
    inner = fit_operation(alpha[21], alpha[20][1][-1], alpha[21][1][-1], inner_start, inner_anchor)
    oh, ih = recording.index(hook[3]), recording.index(hook[7])
    dh, do = recording.index(d[4]), recording.index(d[11])
    counter = [("moveTo", (inner_anchor,)), *recording[ih:dh + 1],
               ("lineTo", (inner_start,)), inner, ("closePath", ())]
    outside = [*recording[:oh + 1], outer, *recording[do + 1:]]
    metadata.update(joinedUpper=True, upperClosureDonorCodePoint=0x64,
                    upperClosureDesign="native-italic-hook-and-alpha-quarter")
    return outside, counter


def _join_lower_hook(font, recording, metadata, left, inner):
    """Close g's native sweep into the opposite descending p shaft."""
    g = move(_native(font, 0x261), metadata["rightLowerOffsetX"])
    p = move(_native(font, 0x70), metadata["leftLowerOffsetX"])
    b = _native(font, 0x62)
    outside_end, inside_start = left(-150), p[24][1][-1]
    outer = ("qCurveTo", (left(g[0][1][0][1]), outside_end))
    inside = fit_operation(b[20], b[19][1][-1], b[20][1][-1], inside_start, g[3][1][-1])
    inside_points = list(inside[1])
    inside_points[0] = (inside_start[0], inside_start[1] - .65 *
                        (inside_start[1] - g[3][1][-1][1]))
    inside = (inside[0], tuple(inside_points))
    oh, ih = recording.index(g[15]), recording.index(g[4])
    pi = recording.index(p[24])
    # The complete native p foot is the last region before the left return.
    counter = [("moveTo", (g[3][1][-1],)), *recording[ih:pi + 1], inside, ("closePath", ())]
    outside = [*recording[:oh + 1], outer, ("lineTo", (left(300),)), ("closePath", ())]
    metadata.update(joinedLower="hook", lowerClosureDonorCodePoint=0x62,
                    lowerClosureDesign="native-italic-shaft-quarter-return")
    return outside, counter


def _join_descenders(font, recording, metadata, left, inner, ri):
    q = move(_native(font, 0x71), metadata["rightLowerOffsetX"])
    p = move(_native(font, 0x70), metadata["leftLowerOffsetX"])
    qb = recording.index(q[1])
    qi = qb + 1  # Bold q's native inner shaft is extended to the body port.
    pi = recording.index(p[24])
    end, start = ri(-150), p[24][1][-1]
    depth = -205
    bridge = ("curveTo", ((start[0] - 10, depth), (end[0] - 10, depth), end))
    counter = [("moveTo", (end,)), *recording[qi:pi + 1], bridge, ("closePath", ())]
    outside = [*recording[:qb], ("lineTo", p[13][1]),
               ("lineTo", (left(300),)), ("closePath", ())]
    metadata.update(joinedLower="descenders", lowerClosureDonorCodePoints=[0x70, 0x71],
                    lowerClosureDesign="native-italic-p-q-shared-foot")
    return outside, counter


def _outline(font, left_variant, right_variant, ports=(), extended_ports=False):
    import import_stix_foundation as s
    if not font["post"].italicAngle or not 0 <= left_variant < 6 or not 0 <= right_variant < 6:
        raise ValueError("Expected native Italic opposed-bowl endings")
    geometry = _geometry(font)
    a, ta, left, inner, ri, right, sum_x, sum_y = geometry
    left_kind, left_extended = divmod(left_variant, 2)
    right_kind, right_extended = divmod(right_variant, 2)
    extended_ports = (extended_ports, extended_ports) if isinstance(extended_ports, bool) else extended_ports
    if "left" in ports:
        left_extended = bool(extended_ports[0])
    if "right" in ports:
        right_extended = bool(extended_ports[1])
    left_center = (left(250)[0] + inner(250)[0]) / 2
    right_center = (right(250)[0] + ri(250)[0]) / 2
    head, head_code, head_dx = _head(font, left_kind, left_center)
    head_start = left(350 if "left" in ports else 300)
    if "left" in ports:
        # The arch cap terminates below this slanted receiving shaft.
        recording = [("moveTo", (head_start,))]
    else:
        recording = [("moveTo", (head_start,)), ("lineTo", (head.start,)),
                     *head.operations]
    d = _native(font, 0x64)
    d_edges = s.donor_contour_edges(font, 0x64)
    d_dx = right(250)[0] - s.shaft_point(d_edges[11], 250)[0]
    d = move(d, d_dx)
    if right_extended:
        # A rising shaft needs room for its receiving quarter. Reserve a
        # quarter-stem span at Bold too; a reversed shoulder folds over itself.
        width = inner(250)[0] - left(250)[0]
        top = (min(a[27][1][-1][0], d[3][1][-1][0] - width / 4), a[27][1][-1][1])
        shoulder = fit_operation(a[27], a[26][1][-1], a[27][1][-1], a[26][1][-1], top)
        recording = _receiving_shoulder(recording, a[26][1][-1], shoulder,
                                        (head.end, inner(430)), port="left" in ports)
        recording.extend([fit_operation(d[3], d[2][1][-1], d[3][1][-1],
                                        top, d[3][1][-1]), *d[4:12],
                          ("lineTo", (right(250),))])
    else:
        recording = _receiving_shoulder(recording, a[26][1][-1], a[27],
                                        (head.end, inner(430)), port="left" in ports)
        recording.append(a[28])
    foot_code = (0x251, 0x71, 0x261)[right_kind]
    if "right" in ports:
        recording.extend([("lineTo", (right(85),)), ("lineTo", (ri(85),))])
        corner = ri(85)
        foot_dx = 0
    elif right_kind == 0:
        alpha_edges = s.donor_contour_edges(font, 0x251)
        foot = s.native_arc(alpha_edges, 6, s.shaft_point(alpha_edges[6], 180),
                            15, alpha_edges[15][0])
        foot_dx = right(180)[0] - foot.start[0]
        foot = foot.translated(foot_dx)
        recording.extend([("lineTo", (foot.start,)), *foot.operations])
        corner = foot.end
    else:
        foot = s.bowl_lower_terminal(font, foot_code, 85)
        foot_dx = right(foot.start[1])[0] - foot.start[0]
        foot = foot.translated(foot_dx)
        recording.extend([("lineTo", (foot.start,)), *foot.operations])
        corner = foot.end
    lower_dx = None
    if left_extended:
        p_edges = s.donor_contour_edges(font, 0x70, 1)
        p_center = sum(s.shaft_point(p_edges[i], 250, extend=True)[0] for i in (1, 10)) / 2
        lower_dx = left_center - p_center
        lower = s.native_terminal(font, 0x70, 50, False).translated(lower_dx)
        width = inner(250)[0] - left(250)[0]
        low = (max(ta[27][1][-1][0], lower.start[0] + width / 4), ta[27][1][-1][1])
        recording.append(fit_operation(ta[27], ta[26][1][-1], ta[27][1][-1], corner, low))
        recording.extend([fit_operation(ta[28], ta[27][1][-1], ta[28][1][-1],
                                        low, lower.start), *lower.operations])
    else:
        recording.append(fit_operation(ta[27], ta[26][1][-1], ta[27][1][-1], corner, ta[27][1][-1]))
        recording.append(ta[28])
    recording.extend([("lineTo", (head_start,)), ("closePath", ())])
    alpha = _native(font, 0x251)
    alpha_edges = s.donor_contour_edges(font, 0x251)
    alpha_dx = right(180)[0] - s.shaft_point(alpha_edges[6], 180)[0]
    metadata = dict(family="opposed-bowls", leftVariant=left_variant, rightVariant=right_variant,
                    archCount=0, bodyDonorCodePoints=[0x250], lowerBowlTurned=True,
                    upperBowlOffsetX=0, lowerBowlOffsetX=sum_x, lowerBowlOffsetY=sum_y,
                    waistAddedWidth=0, stemLeftX=left(250)[0], stemLeftInnerX=inner(250)[0],
                    stemRightInnerX=ri(250)[0], stemRightX=right(250)[0], stemCoordinateY=250,
                    stemLeftSlope=left(251)[0]-left(250)[0],
                    stemRightSlope=right(251)[0]-right(250)[0],
                    upperDonorCodePoint=head_code, upperOffsetX=head_dx,
                    rightUpperDonorCodePoint=0x64 if right_extended else None,
                    rightUpperOffsetX=d_dx if right_extended else None,
                    rightLowerDonorCodePoint=foot_code, rightLowerOffsetX=foot_dx,
                    leftLowerDonorCodePoint=0x70 if left_extended else None,
                    leftLowerOffsetX=lower_dx, terminalCounterCount=0,
                    counterDesign="paired-native-italic-turned-a-shared-diagonal",
                    opticalRevision="native-italic-shared-spine-1",
                    advanceWidth=font["hmtx"][font.getBestCmap()[0x251]][0] + alpha_dx)
    terminal_counters = []
    if left_kind == 2 and right_extended and "left" not in ports:
        recording, counter = _join_upper(font, recording, metadata, right, ri)
        terminal_counters.extend(counter)
        metadata["terminalCounterCount"] += 1
    if left_extended and right_kind and "right" not in ports:
        recording, counter = (_join_lower_hook(font, recording, metadata, left, inner) if right_kind == 2
                               else _join_descenders(font, recording, metadata, left, inner, ri))
        terminal_counters.extend(counter)
        metadata["terminalCounterCount"] += 1
    recording.extend([*_counters(font, geometry), *terminal_counters])
    return s.rounded_recording(recording), {k: v for k, v in metadata.items() if v is not None}, left_center, right_center


def italic_opposed_terminal(font, variant, side, extended=False):
    """Prepare one or both shared ports, retaining their optional free ends."""
    if side not in ("left", "right", "both"):
        raise ValueError("Expected left, right, or both native Italic arch ports")
    ports = ("left", "right") if side == "both" else (side,)
    left_variant, right_variant = (2, variant) if side == "left" else (variant, 0)
    recording, metadata, left, right = _outline(font, left_variant, right_variant, ports, extended)
    metadata.update(sharedArchPortInset=3 if side in ("left", "both") else 0,
                    preparedPortSide=side)
    return ((recording, metadata, left, right) if side == "both"
            else (recording, metadata, left if side == "left" else right))


def italic_opposed_bowls_outline(font, code_point):
    if not 0xF2B1C <= code_point <= 0xF2B3F:
        raise ValueError("Outside the narrow opposed-bowl assignments")
    left, right = divmod(code_point - 0xF2B1C, 6)
    recording, metadata, _, _ = _outline(font, left, right)
    return recording, metadata

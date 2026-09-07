"""Native Italic double bowls and their shared arch ports.

The two directions retain independently drawn epsilon/reversed-e lobes.
STIX b and alpha provide the receiving slanted shafts and bowl quarters;
all heads, feet and hooks are native Italic regions, never sheared Romans.
"""

from stix_geometry import fit_operation, move


def _native(font, code):
    import import_stix_foundation as s
    return s.decomposed_recording(font, font.getBestCmap()[code])


def _axis(font, code, left, right):
    import import_stix_foundation as s
    edges = s.donor_contour_edges(font, code)
    at = lambda index, y: s.shaft_point(edges[index], y, extend=True)
    return edges, at, (at(left, 250)[0] + at(right, 250)[0]) / 2


def _head(font, kind, center):
    import import_stix_foundation as s
    code, contour, first, last, axis_right, y0, y1 = (
        (0x70, 1, 1, 8, 10, 350, 460),
        (0x62, 0, 1, 8, 8, 450, 500),
        (0x253, 0, 1, 7, 7, 420, 470))[kind]
    edges = s.donor_contour_edges(font, code, contour)
    donor_center = sum(s.shaft_point(edges[i], 250, extend=True)[0]
                       for i in (first, axis_right)) / 2
    dx = center - donor_center
    path = s.native_arc(edges, first, s.shaft_point(edges[first], y0),
                        last, s.shaft_point(edges[last], y1)).translated(dx)
    return path, code, dx


def _normal(font, kind=0, extended=False, port=False):
    import import_stix_foundation as s
    b, epsilon = _native(font, 0x62), _native(font, 0x25C)
    if (len(b), len(epsilon)) != (22, 20):
        raise RuntimeError("Pinned Italic b/reversed-e topology changed")
    edges, at, center = _axis(font, 0x62, 1, 8)
    dx = max(x for _, ps in b[12:14] for x, _ in ps) - max(
        x for _, ps in epsilon[14:19] for x, _ in ps)
    e = move(epsilon, dx)
    top, low = e[13][1][-1], e[18][1][-1]
    body_start, body_end = at(8, 430), at(1, 300)
    body = [b[9], b[10], fit_operation(b[11], b[10][1][-1],
                                      b[11][1][-1], b[10][1][-1], top), *e[14:19]]
    lower_dx = None
    if extended:
        p_edges = s.donor_contour_edges(font, 0x70, 1)
        p_center = sum(s.shaft_point(p_edges[i], 250, extend=True)[0] for i in (1, 10)) / 2
        lower_dx = center - p_center
        lower = s.native_terminal(font, 0x70, 50, False).translated(lower_dx)
        body.extend([fit_operation(b[1], b[0][1][0], b[1][1][-1], low, lower.start),
                     *lower.operations, ("lineTo", (body_end,))])
    else:
        body.extend([fit_operation(b[1], b[0][1][0], b[1][1][-1], low, b[1][1][-1]),
                     ("lineTo", (body_end,))])

    # The lobe interiors remain native. Only the stem-side quarter joins
    # are fitted, with endpoints following b's true slanted inner shaft.
    upper_waist, upper_top = e[8][1][-1], e[10][1][-1]
    lower_waist, lower_bottom = e[5][1][-1], e[3][1][-1]
    inner = lambda y: at(8, y)
    upper_close = fit_operation(b[18], b[17][1][-1], b[18][1][-1],
                                upper_top, inner(upper_waist[1]))
    lower_close = fit_operation(b[20], b[19][1][-1], b[20][1][-1],
                                inner(lower_waist[1]), lower_bottom)
    counters = [("moveTo", (inner(upper_waist[1]),)), ("lineTo", (upper_waist,)),
                *e[9:11], upper_close, ("closePath", ()),
                ("moveTo", (inner(lower_waist[1]),)), lower_close,
                *e[4:6], ("closePath", ())]
    if port:
        recording = [("moveTo", (body_start,)), *body, ("closePath", ()), *counters]
        upper_code = upper_dx = None
    else:
        head, upper_code, upper_dx = _head(font, kind, center)
        recording = [*s.join_native_regions(head, s.NativePath(body_start, tuple(body))), *counters]
    metadata = dict(bodyDonorCodePoint=0x62, lobeDonorCodePoint=0x25C,
                    lobeOffsetX=dx, counterJoinDonorCodePoint=0x62,
                    counterDesign="native-italic-bowl-epsilon-two-counters",
                    lobeAnchor="native-bowl-free-extremum", lobeTopY=top[1],
                    lobeBottomY=low[1], sharedStemCenterX=center, sharedStemCenterY=250,
                    upperDonorCodePoint=upper_code, upperOffsetX=upper_dx,
                    lowerDonorCodePoint=0x70 if extended else None, lowerOffsetX=lower_dx,
                    advanceWidth=font["hmtx"][font.getBestCmap()[0x62]][0])
    return s.rounded_recording(recording), {k: v for k, v in metadata.items() if v is not None}


def _turned(font, kind=0, extended=False, port=False):
    import import_stix_foundation as s
    alpha, epsilon = _native(font, 0x251), _native(font, 0x25B)
    if (len(alpha), len(epsilon)) != (25, 22):
        raise RuntimeError("Pinned Italic alpha/epsilon topology changed")
    edges = s.donor_contour_edges(font, 0x251)
    outer_at = lambda y: s.shaft_point(edges[6], y, extend=True)
    b_edges, b_at, _ = _axis(font, 0x62, 1, 8)
    width = b_at(8, 250)[0] - b_at(1, 250)[0]
    inner_at = lambda y: (outer_at(y)[0] - width, y)
    center = outer_at(250)[0] - width / 2
    dx = min(x for _, ps in alpha[1:3] for x, _ in ps) - min(
        x for _, ps in epsilon[1:6] for x, _ in ps)
    e = move(epsilon, dx)
    low, top = e[0][1][0], e[5][1][-1]
    recording = [("moveTo", (low,)), *e[1:6]]
    head_dx = None
    if extended:
        d = _native(font, 0x64)
        d_edges = s.donor_contour_edges(font, 0x64)
        head_dx = outer_at(250)[0] - s.shaft_point(d_edges[11], 250)[0]
        d = move(d, head_dx)
        recording.extend([fit_operation(d[3], d[2][1][-1], d[3][1][-1], top, d[3][1][-1]),
                          *d[4:12], ("lineTo", (outer_at(250),))])
    else:
        recording.extend([fit_operation(alpha[3], alpha[2][1][-1], alpha[3][1][-1],
                                        top, alpha[3][1][-1]), *alpha[4:7]])
    lower_dx = None
    if port:
        recording.extend([("lineTo", (outer_at(85),)), ("lineTo", (inner_at(85),))])
        corner = inner_at(85)
        lower_code = None
    elif kind:
        lower_code = 0x71 if kind == 1 else 0x261
        lower = s.bowl_lower_terminal(font, lower_code, 85)
        lower_dx = outer_at(lower.start[1])[0] - lower.start[0]
        lower = lower.translated(lower_dx)
        recording.extend([("lineTo", (lower.start,)), *lower.operations])
        corner = lower.end
    else:
        lower_code = 0x251
        recording.extend(alpha[7:16])
        corner = alpha[15][1][-1]
    recording.extend([fit_operation(alpha[16], alpha[15][1][-1], alpha[16][1][-1],
                                    corner, low), ("closePath", ())])
    upper_top, upper_waist = e[10][1][-1], e[12][1][-1]
    lower_waist, lower_bottom = e[15][1][-1], e[17][1][-1]
    upper_close = fit_operation(alpha[21], alpha[20][1][-1], alpha[21][1][-1],
                                inner_at(upper_waist[1]), upper_top)
    lower_close = fit_operation(alpha[19], alpha[18][1][-1], alpha[19][1][-1],
                                lower_bottom, inner_at(lower_waist[1]))
    recording.extend([("moveTo", (upper_waist,)), ("lineTo", (inner_at(upper_waist[1]),)),
                      upper_close, *e[11:13], ("closePath", ()),
                      ("moveTo", (inner_at(lower_waist[1]),)), ("lineTo", (lower_waist,)),
                      *e[16:18], lower_close, ("closePath", ())])
    metadata = dict(bodyDonorCodePoint=0x251, lobeDonorCodePoint=0x25B,
                    lobeOffsetX=dx, counterJoinDonorCodePoint=0x251,
                    counterDesign="native-italic-bowl-epsilon-two-counters",
                    lobeAnchor="native-bowl-free-extremum", lobeTopY=top[1], lobeBottomY=low[1],
                    sharedStemCenterX=center, sharedStemCenterY=250,
                    upperDonorCodePoint=0x64 if extended else None, upperOffsetX=head_dx,
                    lowerDonorCodePoint=lower_code, lowerOffsetX=lower_dx,
                    advanceWidth=font["hmtx"][font.getBestCmap()[0x251]][0])
    return s.rounded_recording(recording), {k: v for k, v in metadata.items() if v is not None}


def italic_normal_double_terminal(font, extended=False):
    recording, metadata = _normal(font, extended=extended, port=True)
    return recording, metadata, metadata["sharedStemCenterX"]


def italic_turned_double_terminal(font, extended=False):
    recording, metadata = _turned(font, extended=extended, port=True)
    return recording, metadata, metadata["sharedStemCenterX"]


def italic_double_bowl_outline(font, code_point):
    import import_stix_foundation as s
    arched = 0xF2B40 <= code_point <= 0xF2B4B
    variant = code_point - (0xF2B40 if arched else 0xF2B04)
    if not font["post"].italicAngle or not 0 <= variant < 12:
        raise ValueError("Expected an Italic double-bowl assignment")
    turned, extended, kind = variant % 4 >= 2, bool(variant % 2), variant // 4
    if arched:
        from stix_arched_terminals import arched_terminal_outline
        terminal, metadata, center = (italic_turned_double_terminal(font) if turned
                                       else italic_normal_double_terminal(font))
        recording, arch_metadata = arched_terminal_outline(
            font, 0xF2A5D + variant, terminal_override=terminal,
            prepared_terminal_center=center, prepared_terminal_advance=metadata["advanceWidth"])
        metadata.update(arch_metadata)
    else:
        recording, metadata = (_turned(font, kind, extended) if turned else _normal(font, kind, extended))
    metadata["family"] = "arched-double-bowls" if arched else "double-bowls"
    return s.rounded_recording(recording), metadata

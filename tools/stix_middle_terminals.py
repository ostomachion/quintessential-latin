"""Prepared bowl and sigmoid ports with extended free shared-shaft ends.

The original bodies, counters, width and incoming-arch ports stay fixed.
Only the free end of a shared shaft acquires its native p foot or d head.
"""


def _move(recording, dx=0):
    return [(op, tuple((x + dx, y) for x, y in points)) for op, points in recording]


def _clean(value):
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items() if item is not None}
    if isinstance(value, (tuple, list)):
        return [_clean(item) for item in value if item is not None]
    return value


def _spine(font, turned):
    import import_stix_foundation as s
    italic = bool(font["post"].italicAngle)
    if turned:
        if italic:
            from stix_bowled_spine_italic import italic_turned_spine as build
        else:
            from stix_bowled_spine import turned_spine as build
        recording, metadata = build(font, 3, arch_port=True)
        return recording, metadata, metadata["sharedStemCenterX"]
    if italic:
        from stix_bowled_spine_italic_normal import italic_normal_spine
        recording, metadata = italic_normal_spine(font, 5)
        contours = list(s.native_recording_contours(recording))
        source = s.decomposed_recording(font, font.getBestCmap()[0x250])
        outer = contours[0]
        first = next(i for i, op in enumerate(outer) if op == source[10])
        last = next(i for i, op in enumerate(outer) if op[1] and op[1][-1][1] == 300)
        terminal = [("moveTo", (source[10][1][-1],)), *outer[first + 1:last + 1],
                    ("lineTo", (source[3][1][-1],)), ("closePath", ()), *sum(contours[1:], [])]
        metadata.update(sharedArchCutY=250, sharedArchPortInset=3)
        return terminal, metadata, metadata["sharedStemCenterX"]
    from stix_bowled_spine_normal import normal_spine
    recording, metadata = normal_spine(font, 5)
    bowl = s.decomposed_recording(font, font.getBestCmap()[0x62])
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    first = next(i for i, op in enumerate(outer) if op == bowl[2])
    left, right = metadata["stemLeftX"], metadata["stemRightX"]
    last = next(i for i, op in enumerate(outer) if op == ("lineTo", ((left, 300),)))
    top = bowl[2][1][-1][1]
    terminal = [("moveTo", ((right, top),)), *outer[first + 1:last],
                ("lineTo", ((left, top),)), ("closePath", ()), *sum(contours[1:], [])]
    return terminal, metadata, (left + right) / 2


def _bowl(font, kind, turned):
    import import_stix_foundation as s
    from stix_double_bowl import fit_operation
    italic = bool(font["post"].italicAngle)
    if italic and kind == "double-bowl":
        raise ValueError("Stemmed double bowls remain Roman only")
    code = 0x251 if turned else 0x62
    cmap = font.getBestCmap()
    native = s.decomposed_recording(font, cmap[code])
    native_contours = list(s.native_recording_contours(native))
    native_edges = s.contour_edges(native_contours[0])
    metadata = {"terminalDonorCodePoint": code,
                "advanceWidth": font["hmtx"][cmap[code]][0]}
    if kind == "double-bowl":
        from stix_double_bowl import normal_body, turned_body
        recording, body_metadata = turned_body(font, code) if turned else normal_body(font, code)
        metadata.update(body_metadata)
    else:
        recording = native
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    if turned:
        d = s.decomposed_recording(font, cmap[0x64])
        d_edges = s.contour_edges(list(s.native_recording_contours(d))[0])
        head_outer = d_edges[11 if italic else 10]
        original_outer = native_edges[6]
        outer_at = lambda y: s.shaft_point(original_outer, y, extend=True)
        head_dx = outer_at(250)[0] - s.shaft_point(head_outer, 250)[0]
        d = _move(d, head_dx)
        shoulder_index = next(i for i, op in enumerate(outer) if op[1] and op[1][-1] == native[3][1][-1])
        # The old alpha shoulder was fitted for double bowls. Its endpoint
        # still identifies the first head operation without assuming indices.
        high = outer[shoulder_index - 1][1][-1]
        shoulder = fit_operation(d[3], d[2][1][-1], d[3][1][-1], high, d[3][1][-1])
        corner_index = 15 if italic else 14
        corner = native[corner_index][1][-1]
        return_index = next(i for i, op in enumerate(outer) if op[1] and op[1][-1] == corner)
        head_end = 12 if italic else 11
        head = [shoulder, *d[4:head_end], ("lineTo", (outer_at(250),)),
                ("lineTo", (outer_at(corner[1]),))]
        body = [("moveTo", (corner,)), *outer[return_index + 1:-1],
                *outer[1:shoulder_index], *head, ("closePath", ())]
        outer_x = outer_at(250)[0]
        if italic:
            counter = s.recording_contours(s.cubic_recording(font, cmap[code]))[1]
            inner_x = max(edge.point(t)[0] for edge in counter for t in s.roots_at_y(edge, 250))
        else:
            counter = s.contour_edges(native_contours[1])
            inner_x = s.shaft_point(counter[1], 250)[0]
        center = (outer_x + inner_x) / 2
        metadata.update(freeLegDonorCodePoint=0x64, freeLegOffsetX=head_dx)
    else:
        p = s.decomposed_recording(font, cmap[0x70])
        left_index, right_index = (1, 8) if italic else (7, 1)
        left_edge, right_edge = native_edges[left_index], native_edges[right_index]
        center = sum(s.shaft_point(edge, 250, extend=True)[0] for edge in (left_edge, right_edge)) / 2
        crown_y = right_edge[2][-1][1]
        crown = right_edge[2][-1]
        first = next(i for i, op in enumerate(outer) if op[1] and op[1][-1] == crown)
        if italic:
            foot_edges = s.donor_contour_edges(font, 0x70, 1)
            foot_center = sum(s.shaft_point(foot_edges[i], 250, extend=True)[0] for i in (1, 10)) / 2
            foot_dx = center - foot_center
            foot = s.native_terminal(font, 0x70, p[1][1][-1][1], False).translated(foot_dx)
            low = outer[-2][1][-1]
            original_return = _move(p[1:2], foot_dx)[0]
            lower_return = fit_operation(original_return, _move(p[:1], foot_dx)[0][1][0],
                                         original_return[1][-1], low, foot.start)
            cap = s.shaft_point(left_edge, crown_y, extend=True)
            left_slope = (left_edge[2][-1][0] - left_edge[0][0]) / (left_edge[2][-1][1] - left_edge[0][1])
            return_to_cap = s.tangent_connector(foot.end, cap, foot.slope(False), left_slope).operation()
            body = [("moveTo", (crown,)), *outer[first + 1:-1], lower_return,
                    *foot.operations, return_to_cap, ("closePath", ())]
        else:
            foot_dx = s.shaft_point(right_edge, 250, extend=True)[0] - p[16][1][-1][0]
            foot = s.native_terminal(font, 0x70, p[16][1][-1][1], False).translated(foot_dx)
            return_index = next(i for i, op in enumerate(outer) if op == native[8]) - 1
            low = outer[return_index - 1][1][-1]
            shifted = _move(p, foot_dx)
            lower_return = fit_operation(shifted[15], shifted[14][1][-1], shifted[15][1][-1],
                                         low, shifted[15][1][-1])
            cap = s.shaft_point(left_edge, crown_y, extend=True)
            body = [("moveTo", (crown,)), *outer[first + 1:return_index],
                    lower_return, shifted[16], *foot.operations,
                    ("lineTo", (cap,)), ("closePath", ())]
        metadata.update(freeLegDonorCodePoint=0x70, freeLegOffsetX=foot_dx)
    return [*body, *sum(contours[1:], [])], metadata, center


def prepared_terminal(font, kind, turned):
    """Return the prepared terminal with a descender or turned ascender."""
    import import_stix_foundation as s
    if kind not in ("bowl", "double-bowl", "spine"):
        raise ValueError("Unsupported extended middle terminal family")
    recording, metadata, center = _spine(font, turned) if kind == "spine" else _bowl(font, kind, turned)
    metadata.update(middleLegs="extended", extendedSharedStemDirection="ascender" if turned else "descender",
                    extendedSharedStemCenterX=center,
                    freeLegDonorCodePoint=0x64 if turned else 0x70)
    return s.rounded_recording(recording), _clean(metadata), center


def opposed_terminal(font, left_variant, right_variant, side="left"):
    """Keep the compact sigmoid while extending each incoming arch's free leg.

    Return one or two centers as a tuple in left-to-right source-frame order.
    Outside ending choices belong to the incoming arches on prepared sides.
    """
    import import_stix_foundation as s
    from stix_opposed_bowls import opposed_bowls_outline
    if font["post"].italicAngle or side not in ("left", "right", "both"):
        raise ValueError("Opposed middle terminals require a Roman side selection")
    if left_variant not in range(6) or right_variant not in range(6):
        raise ValueError("Opposed endings must be in range(6)")
    source_left = 3 if side in ("left", "both") else left_variant
    source_right = 1 if side in ("right", "both") else right_variant
    code = 0xF2B1C + source_left * 6 + source_right
    recording, metadata = opposed_bowls_outline(font, code)
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    centers = []
    if side in ("left", "both"):
        bowl = s.decomposed_recording(font, font.getBestCmap()[0x62])
        shoulder = bowl[2]
        first = next(i for i, op in enumerate(outer) if op == shoulder)
        cut_y = shoulder[1][-1][1]
        left, inner = metadata["stemLeftX"], metadata["stemLeftInnerX"]
        outer = [("moveTo", ((inner, cut_y),)), *outer[first + 1:-2],
                 ("lineTo", ((left, cut_y),)), ("closePath", ())]
        centers.append((left + inner) / 2)
    if side in ("right", "both"):
        alpha = _move(s.decomposed_recording(font, font.getBestCmap()[0x251]), metadata["rightLowerOffsetX"])
        first, last = (next(i for i, op in enumerate(outer) if op == alpha[index]) for index in (7, 14))
        corner = alpha[14][1][-1]
        outer = [*outer[:first], ("lineTo", ((metadata["stemRightX"], corner[1]),)),
                 ("lineTo", (corner,)), *outer[last + 1:]]
        centers.append((metadata["stemRightInnerX"] + metadata["stemRightX"]) / 2)
    metadata.update(middleLegs="extended", middleTerminalSide=side,
                    middleTerminalSourceCodePoint=code,
                    sourceLeftVariant=source_left, sourceRightVariant=source_right,
                    sigmoidAdvanceWidth=metadata["advanceWidth"])
    return s.rounded_recording([*outer, *sum(contours[1:], [])]), _clean(metadata), tuple(centers)

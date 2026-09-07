"""Native STIX m/turned-m bodies with independently selected outer endings."""

from __future__ import annotations


# Body, left upper, left lower, right upper, right lower. The middle stave
# always remains native. A third stave keeps facing outer hooks separate;
# the two-stave contextual bowl closures do not apply to these forms.
REPEATED_ARCH_RECIPES = {
    0xF2A51: (0x6D, None, None, None, None),
    0xF2A52: (0x6D, None, 0x70, None, None),
    0xF2A53: (0x26F, None, None, None, None),
    0xF2A54: (0x26F, None, None, 0x6C, None),
    0xF2A55: (0x6D, 0x6C, None, None, None),
    0xF2A56: (0x6D, 0x6C, 0x70, None, None),
    0xF2A57: (0x26F, None, None, None, 0x70),
    0xF2A58: (0x26F, None, None, 0x6C, 0x70),
    0xF2A59: (0x6D, 0x266, None, None, None),
    0xF2A5A: (0x6D, 0x266, 0x70, None, None),
    0xF2A5B: (0x26F, None, None, None, 0x261),
    0xF2A5C: (0x26F, None, None, 0x6C, 0x261),
    0xF2A69: (0x6D, None, None, None, 0x70),
    0xF2A6A: (0x6D, None, 0x70, None, 0x70),
    0xF2A6B: (0x26F, 0x6C, None, None, None),
    0xF2A6C: (0x26F, 0x6C, None, 0x6C, None),
    0xF2A6D: (0x6D, 0x6C, None, None, 0x70),
    0xF2A6E: (0x6D, 0x6C, 0x70, None, 0x70),
    0xF2A6F: (0x26F, 0x6C, None, None, 0x70),
    0xF2A70: (0x26F, 0x6C, None, 0x6C, 0x70),
    0xF2A71: (0x6D, 0x266, None, None, 0x70),
    0xF2A72: (0x6D, 0x266, 0x70, None, 0x70),
    0xF2A73: (0x26F, 0x6C, None, None, 0x261),
    0xF2A74: (0x26F, 0x6C, None, 0x6C, 0x261),
    0xF2A75: (0x271, None, None, None, None),
    0xF2A76: (0x271, None, 0x70, None, None),
    0xF2A77: (0x26F, 0x266, None, None, None),
    0xF2A78: (0x26F, 0x266, None, 0x6C, None),
    0xF2A79: (0x271, 0x6C, None, None, None),
    0xF2A7A: (0x271, 0x6C, 0x70, None, None),
    0xF2A7B: (0x26F, 0x266, None, None, 0x70),
    0xF2A7C: (0x26F, 0x266, None, 0x6C, 0x70),
    0xF2A7D: (0x271, 0x266, None, None, None),
    0xF2A7E: (0x271, 0x266, 0x70, None, None),
    0xF2A7F: (0x26F, 0x266, None, None, 0x261),
    0xF2A80: (0x26F, 0x266, None, 0x6C, 0x261),
}


def _shaft_edges(recording, references, cut_y):
    """Find retained pieces of native shaft edges after an earlier splice."""
    import import_stix_foundation as stix

    found = []
    for reference in references:
        expected = stix.shaft_point(reference, cut_y)
        matches = []
        for contour in stix.native_recording_contours(recording):
            for edge in stix.contour_edges(contour, allow_connections=True):
                start, operation, points = edge
                end = points[-1]
                if operation != "lineTo" or not min(start[1], end[1]) < cut_y < max(start[1], end[1]):
                    continue
                point = stix.shaft_point(edge, cut_y)
                if abs(point[0] - expected[0]) < 0.000002:
                    matches.append(edge)
        if len(matches) != 1:
            raise RuntimeError(f"Expected one retained native shaft at {expected}, found {len(matches)}")
        found.append(matches[0])
    return tuple(found)


def _upper_terminal(font, code, cut_y):
    import import_stix_foundation as stix

    if code == 0x6C:
        return stix.native_terminal(font, code, cut_y, True)
    if code != 0x266:
        raise ValueError(f"Unsupported repeated-arch upper donor U+{code:04X}")
    edges = stix.donor_contour_edges(font, code)
    left, right = (1, 7) if font["post"].italicAngle else (3, 9)
    return stix.native_arc(edges, left, stix.shaft_point(edges[left], cut_y),
                           right, stix.shaft_point(edges[right], cut_y))


def _replace_terminal(font, recording, references, body_y, donor_code, terminal_y, above):
    import import_stix_foundation as stix

    terminal = (_upper_terminal(font, donor_code, terminal_y) if above else
                stix.bowl_lower_terminal(font, donor_code, terminal_y) if donor_code == 0x261 else
                stix.native_terminal(font, donor_code, terminal_y, False))
    current_edges = _shaft_edges(recording, references, body_y)
    return stix.splice_arch_terminal(recording, current_edges, body_y, terminal, above=above)


def _roman_turned_lower(font, recording, edges, code):
    """Keep both turned-m arch curves and their small right attachment spur."""
    import import_stix_foundation as stix

    corner, anchor = edges[23][2][-1], edges[23][0]
    outer = _shaft_edges(recording, (edges[16],), 250.0)[0]
    contours = list(stix.native_recording_contours(recording))
    current = stix.contour_edges(contours[0], allow_connections=True)
    # The outer curve and the native spur survive any preceding head splice.
    start = next(i for i, edge in enumerate(current) if edge == edges[24])
    stop = current.index(outer)
    body = stix.native_arc(current, start, corner, stop, stix.shaft_point(outer, 250.0))
    if code == 0x261:
        lower = stix.bowl_lower_terminal(font, code, corner[1])
    else:
        lower = stix.native_terminal(font, code, 50.0, False)
        # Extend only the last straight edge to the native attachment height.
        endpoint = (lower.end[0] + lower.slope(False) * (corner[1] - lower.end[1]), corner[1])
        lower = stix.NativePath(lower.start, (*lower.operations[:-1], ("lineTo", (endpoint,))))
    dx = anchor[0] - lower.end[0]
    lower = lower.translated(dx)
    bridge = stix.tangent_connector(body.end, lower.start, body.slope(False), lower.slope(True))
    contours[0] = [("moveTo", (body.start,)), *body.operations, bridge.operation(),
                   *lower.operations, ("lineTo", (corner,)), ("closePath", ())]
    return [operation for contour in contours for operation in contour], stix.rounded(dx), corner[1]


def _roman_hooked_upper(font, recording, code):
    """Keep hooked-m's integrated first arch when replacing its short head."""
    import import_stix_foundation as stix

    contours = list(stix.native_recording_contours(recording))
    edges = stix.contour_edges(contours[0])
    # The right port must remain above the native shoulder entry. Cutting the
    # low inner shaft instead would detach and discard the entire first arch.
    body = stix.native_arc(edges, 9, stix.shaft_point(edges[9], 430.0),
                           3, stix.shaft_point(edges[3], 300.0))
    donor = stix.donor_contour_edges(font, code)
    upper_left_y = 430.0 if code == 0x266 else 400.0
    upper = stix.native_arc(donor, 3, stix.shaft_point(donor[3], upper_left_y),
                            9, stix.shaft_point(donor[9], 550.0))
    dx = body.center - upper.center
    contours[0] = stix.join_native_regions(upper.translated(dx), body)
    return [operation for contour in contours for operation in contour], stix.rounded(dx), upper_left_y


def repeated_arch_outline(font, code_point):
    """Return an endpoint outline and its native-body advance/recipe metadata."""
    import import_stix_foundation as stix

    body_code, left_upper, left_lower, right_upper, right_lower = REPEATED_ARCH_RECIPES[code_point]
    italic = bool(font["post"].italicAngle)
    name = font.getBestCmap()[body_code]
    result = stix.open_arch_recording(font, body_code)
    metadata = {"archDonorCodePoint": body_code, "archCount": 2,
                "advanceWidth": font["hmtx"][name][0]}
    if not any((left_upper, left_lower, right_upper, right_lower)):
        metadata["directDonorCodePoint"] = body_code
        return result, metadata

    if body_code == 0x26F:
        left = stix.donor_contour_edges(font, body_code, 0 if italic else 1)
        right = stix.donor_contour_edges(font, body_code, 2 if italic else 0)
        left_head = (left[2], left[9]) if italic else (left[1], left[7])
        right_head = (right[3], right[5]) if italic else (right[10], right[16])
    else:
        left = stix.donor_contour_edges(font, body_code, 1 if italic or body_code == 0x6D else 0)
        right = stix.donor_contour_edges(font, body_code, 0 if italic else 2) if body_code == 0x6D else None
        left_head = (left[1], left[8]) if italic else (left[3], left[11 if body_code == 0x6D else 22])
        left_foot = (left[10], left[1]) if italic else (left[11 if body_code == 0x6D else 22], left[3])

    if left_upper:
        if body_code == 0x271 and not italic:
            result, dx, upper_y = _roman_hooked_upper(font, result, left_upper)
            body_y = 300.0
            metadata.update(leftUpperInnerBodyCutY=430.0, leftUpperInnerCutY=550.0)
        else:
            body_y = 350.0 if italic and body_code != 0x26F else 300.0
            upper_y = 430.0 if left_upper == 0x266 else body_y + 100.0
            result, dx = _replace_terminal(font, result, left_head, body_y, left_upper, upper_y, True)
        metadata.update(leftUpperDonorCodePoint=left_upper, leftUpperBodyCutY=body_y,
                        leftUpperCutY=upper_y, leftUpperOffsetX=dx)
    if left_lower:
        result, dx = _replace_terminal(font, result, left_foot, 150.0, left_lower, 50.0, False)
        metadata.update(leftLowerDonorCodePoint=left_lower, leftLowerBodyCutY=150.0,
                        leftLowerCutY=50.0, leftLowerOffsetX=dx)
    if right_upper:
        body_y = 400.0 if italic else 300.0
        result, dx = _replace_terminal(font, result, right_head, body_y, right_upper, body_y + 100.0, True)
        metadata.update(rightUpperDonorCodePoint=right_upper, rightUpperBodyCutY=body_y,
                        rightUpperCutY=body_y + 100.0, rightUpperOffsetX=dx)
    if right_lower:
        if body_code == 0x26F and not italic:
            result, dx, attachment_y = _roman_turned_lower(font, result, right, right_lower)
            metadata["rightArchAttachmentY"] = attachment_y
            body_y = 250.0
        else:
            outer, inner = (5, 2) if body_code == 0x26F else ((10, 2) if italic else (10, 3))
            body_y = 250.0 if body_code == 0x26F else 150.0
            result, dx = _replace_terminal(font, result, (right[outer], right[inner]), body_y,
                                           right_lower, 50.0, False)
        metadata.update(rightLowerDonorCodePoint=right_lower, rightLowerBodyCutY=body_y,
                        rightLowerCutY=50.0, rightLowerOffsetX=dx)
    return stix.rounded_recording(result), metadata

"""Fixed Extensions composed from native Italic STIX shafts and ribbons.

The native m and turned-m keep their independent middle contours. A repeated
interior ribbon adds the third arch by translation; receiving terminals keep
their own slanted shafts and body counters. No Roman contour is transformed.
"""

from stix_extensions import EXTENSION_FAMILIES, FAMILY_NAMES, _move
from stix_geometry import clean_metadata


def italic_terminal(font, kind, turned):
    """Return a prepared terminal, metadata, and its shaft center at y=250."""
    import import_stix_foundation as s

    if kind == "spine":
        if turned:
            from stix_bowled_spine_italic import italic_turned_spine
            recording, metadata = italic_turned_spine(font, 2, arch_port=True)
            return recording, metadata, metadata["sharedStemCenterX"]
        from stix_bowled_spine_italic_normal import italic_normal_spine_terminal
        recording, metadata, center = italic_normal_spine_terminal(font)
        metadata.update(sharedArchPortInset=3)
        return recording, metadata, center
    if kind == "double-bowl":
        from stix_double_bowl_italic import italic_normal_double_terminal, italic_turned_double_terminal
        return (italic_turned_double_terminal(font) if turned
                else italic_normal_double_terminal(font))

    code = (0x279 if turned else 0x72) if kind == "arm" else (0x251 if turned else 0x62)
    native = s.decomposed_recording(font, font.getBestCmap()[code])
    contours = list(s.native_recording_contours(native))
    metadata = {"terminalDonorCodePoint": code,
                "advanceWidth": font["hmtx"][font.getBestCmap()[code]][0]}
    if kind == "arm":
        stem = s.contour_edges(contours[0 if turned else 1])
        shaft_indices = (3, 5) if turned else (1, 10)
        center = sum(s.shaft_point(stem[i], 250)[0] for i in shaft_indices) / 2
        terminal = contours[1 if turned else 0]
        if not turned:
            start, end = terminal[0][1][0], terminal[1][1][0]
            terminal = [terminal[0], ("lineTo", ((start[0] - 30, start[1]),)),
                        ("lineTo", ((end[0] - 30, end[1]),)), *terminal[1:]]
        return terminal, metadata, center

    edges = s.contour_edges(contours[0])
    if turned:
        corner = edges[15][0]
        body = s.native_arc(edges, 15, corner, 6, s.shaft_point(edges[6], corner[1], extend=True))
        outer = s.shaft_point(edges[6], 250)[0]
        counter = s.recording_contours(s.cubic_recording(font, font.getBestCmap()[code]))[1]
        inner = max(edge.point(t)[0] for edge in counter for t in s.roots_at_y(edge, 250))
        center = (outer + inner) / 2
    else:
        crown = edges[8][2][-1]
        body = s.native_arc(edges, 8, crown, 1, s.shaft_point(edges[1], crown[1]))
        center = sum(s.shaft_point(edges[i], 250, extend=True)[0] for i in (1, 8)) / 2
    terminal = [("moveTo", (body.start,)), *body.operations,
                ("closePath", ()), *sum(contours[1:], [])]
    return terminal, metadata, center


def italic_double_arch_terminal(font, variant, terminal, center, advance, *, arm=False,
                                port_inset=0, arch_override=None):
    """Attach a native double arch to an already prepared slanted port."""
    import import_stix_foundation as s
    from stix_repeated_arch import repeated_arch_outline

    turned = variant % 4 >= 2
    arch, metadata = repeated_arch_outline(font, 0xF2A51 + variant)
    if arch_override is not None:
        arch = arch_override
    donor = metadata["archDonorCodePoint"]
    references = s.donor_contour_edges(font, donor, 0)
    inner, outer = (9, 2) if turned else (2, 10)
    arch_center = sum(s.shaft_point(references[i], 250, extend=True)[0]
                      for i in (inner, outer)) / 2
    if not arm:
        clipped, found = [], False
        for contour in s.native_recording_contours(arch):
            edges = s.contour_edges(contour, allow_connections=True)
            matches = [[i for i, edge in enumerate(edges) if edge == references[reference]]
                       for reference in (inner, outer)]
            if not all(len(indices) == 1 for indices in matches):
                clipped.extend(contour)
                continue
            first, last = (indices[0] for indices in matches)
            cut_y = 250 if turned or port_inset else 200
            body = s.native_arc(edges, first, s.shaft_point(edges[first], cut_y),
                                last, s.shaft_point(edges[last], cut_y))
            if port_inset:
                if turned:
                    raise ValueError("A narrowed upper port cannot receive a turned arch")
                start = (body.start[0] + port_inset, body.start[1])
                end = (body.end[0] - port_inset, body.end[1])
                body = s.NativePath(start, (*body.operations[:-1], ("lineTo", (end,))))
            clipped.extend([("moveTo", (body.start,)), *body.operations, ("closePath", ())])
            found = True
        if not found:
            raise RuntimeError("The native Italic double-arch receiving shaft was not retained")
        arch = clipped
    dx = arch_center - center
    result = [*terminal, *_move(arch, -dx)] if turned else [*arch, *_move(terminal, dx)]
    metadata.pop("directDonorCodePoint", None)
    metadata.update(archBaseCodePoint=0xF2A51 + variant,
                    terminalOffsetX=s.rounded(dx),
                    terminalTranslationX=0 if turned else s.rounded(dx),
                    archOffsetX=s.rounded(-dx) if turned else 0,
                    sharedStemCenterX=s.rounded(center if turned else arch_center),
                    sharedStemCenterY=250,
                    sharedStemOwner="arch" if arm else "terminal",
                    advanceWidth=s.rounded(metadata["advanceWidth"] - dx if turned else advance + dx))
    if port_inset:
        metadata.update(sharedArchCutY=250, sharedArchPortInset=port_inset)
    return s.rounded_recording(result), metadata


def italic_triple_arch(font, code_point):
    """Repeat one native middle ribbon while moving the outer ribbon rigidly."""
    import import_stix_foundation as s
    from stix_repeated_arch import repeated_arch_outline

    result, metadata = repeated_arch_outline(font, code_point)
    contours = list(s.native_recording_contours(result))
    turned = metadata["archDonorCodePoint"] == 0x26F
    donor = metadata["archDonorCodePoint"]
    native = list(s.native_recording_contours(
        s.decomposed_recording(font, font.getBestCmap()[donor])))
    # The middle contour is the complete native interior shaft and its
    # incoming ribbon. The adjacent outer shaft establishes its native pitch
    # on the y=250 reference line, including each donor's actual slant.
    middle_index, outer_index = (1, 2) if turned else (2, 0)
    middle = s.contour_edges(native[middle_index])
    outer = s.contour_edges(native[outer_index])
    middle_edge, outer_edge = ((6, 5) if turned else
                              (10, 13) if donor == 0x271 else (9, 10))
    dx = (s.shaft_point(outer[outer_edge], 250, extend=True)[0]
          - s.shaft_point(middle[middle_edge], 250, extend=True)[0])
    result = []
    for index, contour in enumerate(contours):
        result.extend(_move(contour, dx) if index == outer_index else contour)
    result.extend(_move(native[middle_index], dx))
    metadata.pop("directDonorCodePoint", None)
    for key in ("rightUpperOffsetX", "rightLowerOffsetX"):
        if key in metadata:
            metadata[key] += dx
    metadata.update(archCount=3, addedArchDonorCodePoint=donor,
                    addedArchOffsetX=dx, outerRibbonOffsetX=dx,
                    advanceWidth=metadata["advanceWidth"] + dx,
                    addedArchDesign="native-italic-interior-ribbon-translation")
    return s.rounded_recording(result), metadata


def italic_opposed_extension(font, family_index, variant):
    import import_stix_foundation as s
    from stix_opposed_bowls_italic import italic_opposed_terminal
    from stix_arched_terminals import arched_terminal_outline

    left, right = divmod(variant, 6)
    if family_index == 9:
        terminal, metadata, left_center, right_center = italic_opposed_terminal(font, 0, "both")
        narrow_advance = metadata["advanceWidth"]
        left_variant = (left // 2) * 4 + left % 2
        right_variant = (right // 2) * 4 + right % 2 + 2
        result, left_arch = arched_terminal_outline(
            font, 0xF2A5D + left_variant, terminal_override=terminal,
            prepared_terminal_center=left_center, prepared_terminal_advance=narrow_advance,
            prepared_port_inset=metadata.get("sharedArchPortInset", 0))
        offset = left_arch["terminalOffsetX"]
        result, right_arch = arched_terminal_outline(
            font, 0xF2A5D + right_variant, terminal_override=result,
            prepared_terminal_center=right_center + offset,
            prepared_terminal_advance=left_arch["advanceWidth"])
        metadata.update(leftArch=left_arch, rightArch=right_arch,
                        advanceWidth=right_arch["advanceWidth"], archSide="both",
                        sigmoidOffsetX=offset, sigmoidBaseCodePoint=0xF2B28,
                        sharedLeftStemCenterX=left_center + offset,
                        sharedRightStemCenterX=right_center + offset)
    else:
        right_arch = family_index == 8
        side = "right" if right_arch else "left"
        terminal, metadata, center = italic_opposed_terminal(font, left if right_arch else right, side)
        narrow_advance = metadata["advanceWidth"]
        ending = right if right_arch else left
        arch_variant = (ending // 2) * 4 + ending % 2 + (2 if right_arch else 0)
        result, arch_metadata = italic_double_arch_terminal(
            font, arch_variant, terminal, center, narrow_advance,
            port_inset=metadata.get("sharedArchPortInset", 0))
        metadata.update(arch_metadata)
        metadata.update(archSide=side, sigmoidOffsetX=arch_metadata["terminalTranslationX"],
                        sigmoidBaseCodePoint=0xF2B1C + left * 6 if right_arch else 0xF2B28 + right)
    metadata.update(leftVariant=left, rightVariant=right, archCount=2,
                    sigmoidAdvanceWidth=narrow_advance, terminalCounterCount=0)
    return s.rounded_recording(result), metadata


def italic_extensions_outline(font, code_point):
    """Return all fixed Italic Extensions with native component provenance."""
    import import_stix_foundation as s

    if not font["post"].italicAngle or not 0xF2C00 <= code_point <= 0xF2CBF:
        raise ValueError("Expected an Italic U+F2C00-U+F2CBF assignment")
    index, (start, count, base) = next((i, spec) for i, spec in enumerate(EXTENSION_FAMILIES)
                                      if spec[0] <= code_point < spec[0] + spec[1])
    variant = code_point - start
    if index in (1, 3, 4):
        result, metadata = italic_triple_arch(font, base + variant)
    elif index >= 7:
        result, metadata = italic_opposed_extension(font, index, variant)
    else:
        kind = {0: "arm", 2: "bowl", 5: "double-bowl", 6: "spine"}[index]
        terminal, metadata, center = italic_terminal(font, kind, variant % 4 >= 2)
        result, arch_metadata = italic_double_arch_terminal(
            font, variant, terminal, center, metadata["advanceWidth"], arm=kind == "arm",
            port_inset=metadata.get("sharedArchPortInset", 0))
        metadata.update(arch_metadata)
    metadata.update(family=FAMILY_NAMES[index], extensionBaseCodePoint=base + variant,
                    shaftCount=4 if index in (1, 3, 4, 7, 8, 9) else 3)
    return s.rounded_recording(result), clean_metadata(metadata)

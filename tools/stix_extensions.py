"""All fixed Extensions, composed from the completed STIX vocabulary.

Double arches use the native m/turned-m middle shaft and arch ribbons. Triple
arches repeat one native interior ribbon; bodies and outside endings translate
rigidly. Bilateral opposed bowls join both existing native side-arch ports.
No prior family helper, donor, body counter, or sigmoid width is modified.
Italic uses its independently drawn shafts and ribbons in a separate helper.
"""


EXTENSION_FAMILIES = (
    (0xF2C00, 12, 0xF2A45), (0xF2C0C, 12, 0xF2A51),
    (0xF2C18, 12, 0xF2A5D), (0xF2C24, 12, 0xF2A69),
    (0xF2C30, 12, 0xF2A75), (0xF2C3C, 12, 0xF2B40),
    (0xF2C48, 12, 0xF2B4C), (0xF2C54, 36, 0xF2B58),
    (0xF2C78, 36, 0xF2B7C), (0xF2C9C, 36, 0xF2B58),
)
FAMILY_NAMES = (
    "double-arched-arms", "triple-arches", "double-arched-bowls",
    "descending-triple-arches", "hooked-triple-arches",
    "double-arched-double-bowls", "double-arched-bowled-spines",
    "left-double-arched-opposed-bowls", "right-double-arched-opposed-bowls",
    "double-arched-opposed-bowls",
)


def _move(recording, dx):
    return [(op, tuple((x + dx, y) for x, y in points)) for op, points in recording]


def _plist_metadata(value):
    """Omit absent optional recipe fields throughout the UFO lib tree."""
    if isinstance(value, dict):
        return {key: _plist_metadata(item) for key, item in value.items() if item is not None}
    if isinstance(value, (tuple, list)):
        return [_plist_metadata(item) for item in value if item is not None]
    return value


def _terminal(font, kind, turned):
    """Return a completed terminal, its native receiving axis, and metadata."""
    import import_stix_foundation as s

    if font["post"].italicAngle:
        from stix_extensions_italic import italic_terminal
        recording, metadata, center = italic_terminal(font, kind, turned)
        return recording, center, metadata

    if kind == "spine":
        if turned:
            from stix_bowled_spine import turned_spine
            result, metadata = turned_spine(font, 2, arch_port=True)
            return result, metadata["sharedStemCenterX"], metadata
        from stix_bowled_spine_normal import normal_spine_terminal
        result, metadata, center = normal_spine_terminal(font)
        return result, center, metadata

    code = (0x279 if turned else 0x72) if kind == "arm" else (0x251 if turned else 0x62)
    native = s.decomposed_recording(font, font.getBestCmap()[code])
    native_contours = list(s.native_recording_contours(native))
    native_edges = s.contour_edges(native_contours[0])
    metadata = {"terminalDonorCodePoint": code,
                "advanceWidth": font["hmtx"][font.getBestCmap()[code]][0]}
    if kind == "arm":
        left, right = (4, 10) if turned else (3, 16)
        center = sum(s.shaft_point(native_edges[i], 250)[0] for i in (left, right)) / 2
        first, last = (18, 4) if turned else (11, 16)
        arm = s.native_arc(native_edges, first, native_edges[first][0], last, native_edges[last][0])
        port = 40 if turned else -40
        result = [("moveTo", (arm.start,)), *arm.operations,
                  ("lineTo", ((arm.end[0] + port, arm.end[1]),)),
                  ("lineTo", ((arm.start[0] + port, arm.start[1]),)), ("closePath", ())]
        return result, center, metadata

    if kind == "double-bowl":
        from stix_double_bowl import normal_body, turned_body
        native, body_metadata = turned_body(font, code) if turned else normal_body(font, code)
        metadata.update(body_metadata)
    contours = list(s.native_recording_contours(native))
    edges = s.contour_edges(contours[0])
    if turned:
        corner = native_edges[14][0]
        first = next(i for i, edge in enumerate(edges) if edge[0] == corner)
        last = edges.index(native_edges[6])
        body = s.native_arc(edges, first, corner, last, s.shaft_point(edges[last], corner[1], extend=True))
        counter = s.contour_edges(native_contours[1])
        center = (s.shaft_point(native_edges[6], 250)[0] + s.shaft_point(counter[1], 250)[0]) / 2
    else:
        left, right = (edges.index(native_edges[i]) for i in (7, 1))
        crown_y = edges[right][2][-1][1]
        body = s.native_arc(edges, right, edges[right][2][-1], left, s.shaft_point(edges[left], crown_y))
        center = sum(s.shaft_point(native_edges[i], 250, extend=True)[0] for i in (7, 1)) / 2
    return [("moveTo", (body.start,)), *body.operations, ("closePath", ()),
            *sum(contours[1:], [])], center, metadata


def _double_arch_terminal(font, variant, terminal, center, advance, *, arm=False, arch_override=None,
                          port_inset=0):
    """Join the outer m/turned-m shaft through the established terminal port."""
    import import_stix_foundation as s
    from stix_repeated_arch import repeated_arch_outline

    if font["post"].italicAngle:
        from stix_extensions_italic import italic_double_arch_terminal
        return italic_double_arch_terminal(font, variant, terminal, center, advance,
                                            arm=arm, arch_override=arch_override, port_inset=port_inset)

    turned = variant % 4 >= 2
    arch, metadata = repeated_arch_outline(font, 0xF2A51 + variant)
    if arch_override is not None:
        arch = arch_override
    donor = 0x26F if turned else 0x6D
    references = s.donor_contour_edges(font, donor, 1 if turned else 2)
    inner, outer = (7, 1) if turned else (3, 10)
    arch_center = sum(s.shaft_point(references[i], 250, extend=True)[0] for i in (inner, outer)) / 2
    if not arm:
        clipped = []
        found = False
        for contour in s.native_recording_contours(arch):
            edges = s.contour_edges(contour, allow_connections=True)
            matches = [[i for i, edge in enumerate(edges) if edge == references[reference]]
                       for reference in (inner, outer)]
            if all(len(indices) == 1 for indices in matches):
                first, last = (indices[0] for indices in matches)
                cut_y = 250 if turned else 200
                body = s.native_arc(edges, first, s.shaft_point(edges[first], cut_y),
                                    last, s.shaft_point(edges[last], cut_y))
                clipped.extend([("moveTo", (body.start,)), *body.operations, ("closePath", ())])
                found = True
            else:
                clipped.extend(contour)
        if not found:
            raise RuntimeError("The native double-arch receiving shaft was not retained")
        arch = clipped
    dx = arch_center - center
    result = [*terminal, *_move(arch, -dx)] if turned else [*arch, *_move(terminal, dx)]
    metadata.pop("directDonorCodePoint", None)
    metadata.update(archBaseCodePoint=0xF2A51 + variant,
                    terminalOffsetX=s.rounded(dx),
                    terminalTranslationX=0 if turned else s.rounded(dx),
                    archOffsetX=s.rounded(-dx) if turned else 0,
                    sharedStemCenterX=s.rounded(center if turned else arch_center),
                    sharedStemOwner="arch" if arm else "terminal",
                    advanceWidth=s.rounded(metadata["advanceWidth"] - dx if turned else advance + dx))
    return s.rounded_recording(result), metadata


def _triple_arch(font, code_point):
    """Insert an unchanged native interior ribbon into a completed double arch."""
    import import_stix_foundation as s
    from stix_repeated_arch import repeated_arch_outline

    result, metadata = repeated_arch_outline(font, code_point)
    contours = list(s.native_recording_contours(result))
    donor = metadata["archDonorCodePoint"]
    if donor == 0x26F:
        source = s.decomposed_recording(font, font.getBestCmap()[0x26F])
        native = list(s.native_recording_contours(source))
        left = s.contour_edges(native[1])[1]
        middle = s.contour_edges(native[0])[1]
        dx = s.shaft_point(middle, 250)[0] - s.shaft_point(left, 250)[0]
        result = [*_move(contours[0], dx), *contours[1], *_move(native[1], dx)]
    else:
        source = s.decomposed_recording(font, font.getBestCmap()[0x6D])
        native = list(s.native_recording_contours(source))
        left = s.contour_edges(native[1])[3]
        middle = s.contour_edges(native[0])[3]
        dx = s.shaft_point(middle, 250)[0] - s.shaft_point(left, 250)[0]
        # The hooked donor's first two shafts share one integrated contour;
        # its final hook/arch ribbon is still independently translatable.
        result = [*sum(contours[:-1], []), *_move(native[0], dx), *_move(contours[-1], dx)]
    metadata.pop("directDonorCodePoint", None)
    for key in ("rightUpperOffsetX", "rightLowerOffsetX"):
        if key in metadata:
            metadata[key] += dx
    metadata.update(archCount=3, addedArchDonorCodePoint=0x26F if donor == 0x26F else 0x6D,
                    addedArchOffsetX=dx, outerRibbonOffsetX=dx,
                    advanceWidth=metadata["advanceWidth"] + dx)
    return s.rounded_recording(result), metadata


def _both_opposed_ports(font):
    """Keep the compact sigmoid and both counters while removing both exits."""
    import import_stix_foundation as s
    from stix_arched_opposed_bowls import _left_terminal

    recording, metadata, left_center = _left_terminal(font, 0)
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    alpha = _move(s.decomposed_recording(font, font.getBestCmap()[0x251]), metadata["rightLowerOffsetX"])
    first, last = (next(i for i, operation in enumerate(outer) if operation == alpha[index]) for index in (7, 14))
    corner = alpha[14][1][-1]
    contours[0] = [*outer[:first], ("lineTo", ((metadata["stemRightX"], corner[1]),)),
                   ("lineTo", (corner,)), *outer[last + 1:]]
    right_center = (metadata["stemRightInnerX"] + metadata["stemRightX"]) / 2
    from stix_arch_spine_joins import fair_spine_arch_port
    terminal = fair_spine_arch_port(font, sum(contours, []), metadata, "right")
    return terminal, metadata, left_center, right_center


def _opposed(font, family_index, variant):
    import import_stix_foundation as s
    from stix_arched_opposed_bowls import _left_terminal, _right_terminal
    from stix_arched_terminals import arched_terminal_outline

    left, right = divmod(variant, 6)
    if family_index == 9:
        terminal, metadata, left_center, right_center = _both_opposed_ports(font)
        narrow_advance = metadata["advanceWidth"]
        left_arch_variant = (left // 2) * 4 + left % 2
        right_arch_variant = (right // 2) * 4 + right % 2 + 2
        result, left_arch = arched_terminal_outline(
            font, 0xF2A5D + left_arch_variant, terminal_override=terminal,
            prepared_terminal_center=left_center, prepared_terminal_advance=narrow_advance)
        offset = left_arch["terminalOffsetX"]
        result, right_arch = arched_terminal_outline(
            font, 0xF2A5D + right_arch_variant, terminal_override=result,
            prepared_terminal_center=right_center + offset,
            prepared_terminal_advance=left_arch["advanceWidth"])
        metadata.update(leftArch=left_arch, rightArch=right_arch,
                        advanceWidth=right_arch["advanceWidth"],
                        archSide="both", sigmoidOffsetX=offset,
                        sigmoidBaseCodePoint=0xF2B28,
                        sharedLeftStemCenterX=left_center + offset,
                        sharedRightStemCenterX=right_center + offset)
    else:
        right_arch = family_index == 8
        terminal, metadata, center = _right_terminal(font, left) if right_arch else _left_terminal(font, right)
        narrow_advance = metadata["advanceWidth"]
        ending = right if right_arch else left
        arch_variant = (ending // 2) * 4 + ending % 2 + (2 if right_arch else 0)
        result, arch_metadata = _double_arch_terminal(font, arch_variant, terminal, center, narrow_advance)
        metadata.update(arch_metadata)
        metadata.update(archSide="right" if right_arch else "left",
                        sigmoidOffsetX=arch_metadata["terminalTranslationX"],
                        sigmoidBaseCodePoint=0xF2B1C + left * 6 if right_arch else 0xF2B28 + right)
    metadata.update(leftVariant=left, rightVariant=right, archCount=2,
                    sigmoidAdvanceWidth=narrow_advance, terminalCounterCount=0)
    return s.rounded_recording(result), metadata


def extensions_outline(font, code_point):
    """Return an endpoint outline and auditable recipe for one fixed Extension."""
    import import_stix_foundation as s

    if font["post"].italicAngle:
        from stix_extensions_italic import italic_extensions_outline
        return italic_extensions_outline(font, code_point)
    if not 0xF2C00 <= code_point <= 0xF2CBF:
        raise ValueError("Extensions require a fixed U+F2C00-U+F2CBF assignment")
    index, (start, count, base) = next((i, spec) for i, spec in enumerate(EXTENSION_FAMILIES)
                                      if spec[0] <= code_point < spec[0] + spec[1])
    variant = code_point - start
    if index in (1, 3, 4):
        result, metadata = _triple_arch(font, base + variant)
    elif index >= 7:
        result, metadata = _opposed(font, index, variant)
    else:
        kind = {0: "arm", 2: "bowl", 5: "double-bowl", 6: "spine"}[index]
        terminal, center, metadata = _terminal(font, kind, variant % 4 >= 2)
        result, arch_metadata = _double_arch_terminal(
            font, variant, terminal, center, metadata["advanceWidth"], arm=kind == "arm")
        metadata.update(arch_metadata)
    metadata.update(family=FAMILY_NAMES[index], extensionBaseCodePoint=base + variant,
                    shaftCount=4 if index in (1, 3, 4, 7, 8, 9) else 3)
    return s.rounded_recording(result), _plist_metadata(metadata)

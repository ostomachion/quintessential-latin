"""The two single-side-arch opposed-bowl families, in native Roman STIX.

The middle shaft belongs to the compact sigmoid. Its incoming arch owns the
outer third shaft and that side's ending choices. Only rigid translation is
applied to the S body; the donor arch is neither reflected nor flattened.
"""


def _left_terminal(font, right_variant):
    """Remove the shared left head at its native b shoulder port."""
    import import_stix_foundation as s
    from stix_opposed_bowls import opposed_bowls_outline

    recording, metadata = opposed_bowls_outline(font, 0xF2B28 + right_variant)
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    bowl = s.decomposed_recording(font, font.getBestCmap()[0x62])
    shoulder = bowl[2]
    first = next(index for index, operation in enumerate(outer) if operation == shoulder)
    cut_y = shoulder[1][-1][1]
    left, right = metadata["stemLeftX"], metadata["stemLeftInnerX"]
    terminal = [("moveTo", ((right, cut_y),)), *outer[first + 1:-2],
                ("lineTo", ((left, cut_y),)), ("closePath", ()),
                *sum(contours[1:], [])]
    return s.rounded_recording(terminal), metadata, (left + right) / 2


def _right_terminal(font, left_variant):
    """Remove the shared alpha foot at its native lower-bowl attachment."""
    import import_stix_foundation as s
    from stix_opposed_bowls import opposed_bowls_outline

    recording, metadata = opposed_bowls_outline(font, 0xF2B1C + left_variant * 6)
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    alpha = s.decomposed_recording(font, font.getBestCmap()[0x251])
    offset = metadata["rightLowerOffsetX"]
    shifted = lambda operation: (operation[0], tuple((x + offset, y) for x, y in operation[1]))
    first = next(index for index, operation in enumerate(outer) if operation == shifted(alpha[7]))
    last = next(index for index, operation in enumerate(outer) if operation == shifted(alpha[14]))
    corner = shifted(alpha[14])[1][-1]
    inner, outer_x = metadata["stemRightInnerX"], metadata["stemRightX"]
    terminal = [*outer[:first], ("lineTo", ((outer_x, corner[1]),)),
                ("lineTo", (corner,)), *outer[last + 1:], *sum(contours[1:], [])]
    return s.rounded_recording(terminal), metadata, (inner + outer_x) / 2


def arched_opposed_bowls_outline(font, code_point):
    import import_stix_foundation as s
    from stix_arched_terminals import arched_terminal_outline

    if font["post"].italicAngle or not 0xF2B58 <= code_point <= 0xF2B9F:
        raise ValueError("Arched opposed bowls require a Roman Abbreviations assignment")
    right_arch = code_point >= 0xF2B7C
    first = 0xF2B7C if right_arch else 0xF2B58
    left, right = divmod(code_point - first, 6)
    terminal, metadata, shared_center = (_right_terminal(font, left) if right_arch
                                         else _left_terminal(font, right))
    ending = right if right_arch else left
    arch_variant = (ending // 2) * 4 + ending % 2 + (2 if right_arch else 0)
    narrow_advance = metadata["advanceWidth"]
    recording, arch_metadata = arched_terminal_outline(
        font, 0xF2A5D + arch_variant, terminal_override=terminal,
        prepared_terminal_center=shared_center, prepared_terminal_advance=narrow_advance)
    offset = 0 if right_arch else arch_metadata["terminalOffsetX"]
    # Preserve the source-frame stem coordinates as an independently auditable
    # reference. Actual chart coordinates include the single rigid S offset.
    metadata.update(arch_metadata)
    metadata.update(
        family="right-arched-opposed-bowls" if right_arch else "left-arched-opposed-bowls",
        leftVariant=left, rightVariant=right, archCount=1,
        archSide="right" if right_arch else "left", sigmoidOffsetX=offset,
        sigmoidAdvanceWidth=narrow_advance,
        sigmoidBaseCodePoint=0xF2B1C + left * 6 if right_arch else 0xF2B28 + right,
        sharedStemCenterX=shared_center + offset,
        terminalCounterCount=0,
    )
    return s.rounded_recording(recording), metadata

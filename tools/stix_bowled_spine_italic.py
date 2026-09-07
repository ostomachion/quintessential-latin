"""Native Italic diagonal spines, independent of the single-storey a.

The independently drawn turned-a supplies the diagonal bowl and its ball.
A rigid half-turn preserves its native slope for the lower-bowled forms;
alpha/d/q/g supply the correctly oriented shaft endings.
"""

from stix_geometry import fit_operation, move


def italic_turned_spine(font, variant, *, arch_port=False):
    import import_stix_foundation as s

    if not font["post"].italicAngle or variant not in (2, 3, 6, 7, 10, 11):
        raise ValueError("Expected a native Italic lower-bowled spine")
    cmap = font.getBestCmap()
    native = lambda code: s.decomposed_recording(font, cmap[code])
    source, alpha = native(0x250), native(0x251)
    if len(source) != 31 or len(alpha) != 25:
        raise RuntimeError("Pinned Italic turned-a/alpha topology changed")
    alpha_edges = s.contour_edges(list(s.native_recording_contours(alpha))[0])
    source_edges = s.contour_edges(list(s.native_recording_contours(source))[0])
    turn_y = source[27][1][-1][1] + source[0][1][0][1]
    turn_x = (s.shaft_point(alpha_edges[6], 250)[0]
              + s.shaft_point(source_edges[2], turn_y - 250)[0])
    a = move(source, turn_x, turn_y, True)
    outer_edge = (a[2][1][-1], "lineTo", a[3][1])
    inner_edge = (a[12][1][-1], "lineTo", a[13][1])
    outer_at = lambda y: s.shaft_point(outer_edge, y, extend=True)
    inner_at = lambda y: s.shaft_point(inner_edge, y, extend=True)
    center = (outer_at(250)[0] + inner_at(250)[0]) / 2
    extended, kind = bool(variant % 2), variant // 4

    # Keep the independently drawn native ball and all its curves. Only
    # the shoulder receiving an ascender changes; the short form keeps the
    # complete donor upper sweep as well.
    recording = [a[0]]
    head_dx = None
    head_slope = None
    if extended:
        d = native(0x64)
        edges = s.contour_edges(list(s.native_recording_contours(d))[0])
        head_dx = outer_at(250)[0] - s.shaft_point(edges[11], 250)[0]
        d = move(d, head_dx)
        shoulder = fit_operation(d[3], d[2][1][-1], d[3][1][-1],
                                 a[0][1][0], d[3][1][-1])
        recording.extend([shoulder, *d[4:12]])
        # Keep d's complete outer ascender on its native axis. Connecting
        # its crown directly to a q/g foot would silently change that slope.
        head_cut = outer_at(250)
        head_slope = (edges[11][2][-1][0] - edges[11][0][0]) / (
            edges[11][2][-1][1] - edges[11][0][1])
        recording.append(("lineTo", (head_cut,)))
    else:
        recording.extend(a[1:3])

    lower_dx = None
    if arch_port:
        # The native u continuation owns the baseline. End the open-head
        # shaft below its diagonal bowl attachment, with no alpha exit.
        recording.extend([("lineTo", (outer_at(85),)),
                          ("lineTo", (inner_at(85),))])
        lower_code = None
    elif kind:
        lower_code = 0x71 if kind == 1 else 0x261
        lower = s.bowl_lower_terminal(font, lower_code, 85.0)
        lower_dx = outer_at(lower.start[1])[0] - lower.start[0]
        lower = lower.translated(lower_dx)
        connector = (s.tangent_connector(head_cut, lower.start, head_slope,
                                         lower.slope(True)).operation() if extended
                     else ("lineTo", (lower.start,)))
        recording.extend([connector, *lower.operations])
    else:
        lower_code = 0x251
        lower = s.native_arc(alpha_edges, 6, s.shaft_point(alpha_edges[6], 180),
                             15, alpha_edges[15][0])
        lower_dx = outer_at(180)[0] - lower.start[0]
        lower = lower.translated(lower_dx)
        connector = (s.tangent_connector(head_cut, lower.start, head_slope,
                                         lower.slope(True)).operation() if extended
                     else ("lineTo", (lower.start,)))
        recording.extend([connector, *lower.operations])
    recording.extend([a[13], *a[14:21], *a[21:]])

    # Keep one shared span for all six shaft endings. Alpha's native exit
    # sidebearing sets the right margin of the narrower turned-a bowl.
    foot_dx = outer_at(180)[0] - s.shaft_point(alpha_edges[6], 180)[0]
    metadata = {
        "family": "bowled-spines", "bodyDonorCodePoint": 0x250,
        "spineDonorCodePoint": 0x250, "spineTurned": True,
        "spineOffsetX": turn_x, "spineOffsetY": turn_y,
        "shaftDonorCodePoint": 0x251,
        "upperDonorCodePoint": 0x64 if extended else None, "upperOffsetX": head_dx,
        "lowerDonorCodePoint": lower_code, "lowerOffsetX": lower_dx,
        "freeTerminalDonorCodePoint": 0x250, "freeTerminalTurned": True,
        "freeTerminalOffsetX": turn_x, "freeTerminalOffsetY": turn_y,
        "sharedStemCenterX": center,
        "counterDesign": "native-italic-turned-a-attached-diagonal-bowl",
        "advanceWidth": font["hmtx"][cmap[0x251]][0] + foot_dx,
    }
    return s.rounded_recording(recording), metadata


def italic_bowled_spine_outline(font, code_point):
    import import_stix_foundation as s
    from stix_bowled_spine_italic_normal import italic_normal_spine, italic_normal_spine_terminal
    from stix_arched_terminals import arched_terminal_outline

    arched = 0xF2B4C <= code_point <= 0xF2B57
    variant = code_point - (0xF2B4C if arched else 0xF2B10)
    if not 0 <= variant < 12:
        raise ValueError("Outside the narrow bowled-spine increment")
    turned = variant % 4 >= 2
    if arched:
        if turned:
            terminal, metadata = italic_turned_spine(font, 2, arch_port=True)
            center = metadata["sharedStemCenterX"]
        else:
            terminal, metadata, center = italic_normal_spine_terminal(font)
        recording, arch_metadata = arched_terminal_outline(
            font, 0xF2A5D + variant, terminal_override=terminal,
            prepared_terminal_center=center,
            prepared_terminal_advance=metadata["advanceWidth"],
            prepared_port_inset=0 if turned else 3)
        metadata.update(arch_metadata)
        metadata["terminalDonorCodePoint"] = 0x250
        metadata.pop("upperDonorCodePoint", None)
        metadata.pop("upperOffsetX", None)
        if not turned:
            metadata.update(sharedArchCutY=250, sharedArchPortInset=3)
    else:
        recording, metadata = (italic_turned_spine(font, variant) if turned
                               else italic_normal_spine(font, variant))
    metadata["family"] = "arched-bowled-spines" if arched else "bowled-spines"
    return s.rounded_recording(recording), {k: v for k, v in metadata.items() if v is not None}

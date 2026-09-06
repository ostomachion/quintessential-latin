"""Native STIX arch ribbons joined to arm and bowl terminals.

The outside stave carries the grammatical extensions; the shared inside
stave belongs to the terminal. Donor quadratics are never rotated or sheared.
"""


def arched_terminal_outline(font, code_point, terminal_override=None, prepared_terminal_center=None,
                            prepared_terminal_advance=None, prepared_port_inset=0, arch_override=None):
    import import_stix_foundation as s

    bowl = code_point >= 0xF2A5D
    variant = code_point - (0xF2A5D if bowl else 0xF2A45)
    base_code = 0xF2A15 + variant
    turned = variant % 4 >= 2
    italic = bool(font["post"].italicAngle)
    cmap = font.getBestCmap()
    direct = {0xF2A15: 0x6E, 0xF2A17: 0x75, 0xF2A19: 0x68, 0xF2A1D: 0x266}
    if base_code in direct:
        arch = s.decomposed_recording(font, cmap[direct[base_code]])
        arch_metadata = {"archDonorCodePoint": direct[base_code]}
    else:
        arch, arch_metadata = s.arch_outline(font, base_code)

    if arch_override is not None:
        arch = arch_override

    donor_code = arch_metadata["archDonorCodePoint"]
    arch_edges = s.donor_contour_edges(font, donor_code)
    if turned:
        outer, inner = (((7, 14) if italic else (5, 11)) if donor_code == 0x265
                        else ((2, 9) if italic else (1, 6)))
    elif donor_code == 0x266 and not italic:
        # Hook-h is an integrated contour; locate the same right shaft by
        # its low straight pair instead of assuming n's contour layout.
        candidates = [(i, e) for i, e in enumerate(arch_edges)
                      if e[1] == "lineTo" and min(e[0][1], e[2][-1][1]) < 200
                      and max(e[0][1], e[2][-1][1]) > 200]
        right = sorted(candidates, key=lambda item: s.shaft_point(item[1], 200)[0])[-2:]
        inner, outer = right[0][0], right[1][0]
    else:
        if donor_code == 0x266 and italic:
            arch_edges = s.donor_contour_edges(font, donor_code, 1)
        inner, outer = (2, 10) if italic else (3, 10)

    # Use the native arch's actual shaft axis, including its italic slant.
    join_y = 250.0
    arch_center = sum(s.shaft_point(arch_edges[i], join_y, extend=True)[0] for i in (inner, outer)) / 2
    terminal_code = (0x251 if turned else 0x62) if bowl else (0x279 if turned else 0x72)
    terminal = s.decomposed_recording(font, cmap[terminal_code])
    contours = list(s.native_recording_contours(terminal))
    native_contours = contours
    if terminal_override is not None:
        terminal = terminal_override
        contours = list(s.native_recording_contours(terminal))

    if bowl:
        if prepared_terminal_center is not None:
            # A different terminal family can supply its already-trimmed
            # shared port without pretending to have alpha/b contour indices.
            if terminal_override is None:
                raise ValueError("A prepared shared port requires a terminal outline")
            terminal_center = prepared_terminal_center
        elif turned:
            edges = s.contour_edges(contours[0])
            # Keep alpha's complete left bowl and short upper finish, but
            # omit the baseline exit which would protrude into the new arch.
            corner = edges[15 if italic else 14][0]
            end_edge = 6
            first = 15 if italic else 14
            if terminal_override is not None:
                original_edges = s.contour_edges(native_contours[0])
                corner = original_edges[14][0]
                first = next(i for i, edge in enumerate(edges) if edge[0] == corner)
                end_edge = edges.index(original_edges[6])
            body = s.native_arc(edges, first, corner,
                                end_edge, s.shaft_point(edges[end_edge], corner[1], extend=True))
            terminal = [("moveTo", (body.start,)), *body.operations,
                        ("closePath", ()), *sum(contours[1:], [])]
            counter = s.contour_edges(native_contours[1])
            # The italic counter shaft is curved: its natural center at the
            # shared port is taken from the corresponding outer shaft width.
            outer_x = s.shaft_point(edges[end_edge], join_y)[0]
            if not italic:
                stem_width = outer_x - s.shaft_point(counter[1], join_y)[0]
            else:
                cubic_counter = s.recording_contours(s.cubic_recording(font, cmap[terminal_code]))[1]
                intersections = [edge.point(t)[0] for edge in cubic_counter
                                 for t in s.roots_at_y(edge, join_y)]
                stem_width = outer_x - max(intersections)
            terminal_center = outer_x - stem_width / 2
        else:
            edges = s.contour_edges(contours[0])
            left, right = (1, 8) if italic else (7, 1)
            if terminal_override is not None:
                original_edges = s.contour_edges(native_contours[0])
                left, right = (edges.index(original_edges[i]) for i in (left, right))
            crown_y = edges[right][2][-1][1]
            body = s.native_arc(edges, right, edges[right][2][-1],
                                left, s.shaft_point(edges[left], crown_y))
            terminal = [("moveTo", (body.start,)), *body.operations,
                        ("closePath", ()), *sum(contours[1:], [])]
            terminal_center = sum(s.shaft_point(edges[i], join_y, extend=True)[0]
                                  for i in (left, right)) / 2

        # Retain only the incoming arch above/below its shared-stem port.
        # Its companion outer stem and all its requested endings stay intact.
        source_edges = (arch_edges[inner], arch_edges[outer])
        clipped = []
        found = False
        for contour in s.native_recording_contours(arch):
            edges = s.contour_edges(contour, allow_connections=True)
            matches = [[i for i, edge in enumerate(edges) if edge == source] for source in source_edges]
            if all(len(indices) == 1 for indices in matches):
                first, last = (indices[0] for indices in matches)
                cut_y = 250.0 if turned else 200.0
                if prepared_port_inset:
                    if not italic or turned or prepared_terminal_center is None:
                        raise ValueError("Inset ports require a prepared upper-bowled Italic terminal")
                    cut_y = 250.0
                start = s.shaft_point(edges[first], cut_y)
                end = s.shaft_point(edges[last], cut_y)
                path = s.native_arc(edges, first, s.shaft_point(edges[first], cut_y),
                                    last, s.shaft_point(edges[last], cut_y))
                if prepared_port_inset:
                    # Only the straight, hidden cap is narrowed. Different
                    # native Italic shafts diverge slightly below this join;
                    # bury the incoming cap inside the receiving shaft so it
                    # cannot leave a tiny horizontal spur. All arch curves
                    # and the companion stem remain exactly native.
                    start = (start[0] + prepared_port_inset, start[1])
                    end = (end[0] - prepared_port_inset, end[1])
                    path = s.NativePath(start, (*path.operations[:-1], ("lineTo", (end,))))
                clipped.extend([("moveTo", (path.start,)), *path.operations, ("closePath", ())])
                found = True
            else:
                clipped.extend(contour)
        if not found:
            raise RuntimeError("Could not find the native shared arch stave")
        arch = clipped
    else:
        if italic:
            stem_index, arm_index = (0, 1) if turned else (1, 0)
            stem = s.contour_edges(contours[stem_index])
            left, right = (3, 5) if turned else (1, 10)
            terminal_center = sum(s.shaft_point(stem[i], join_y)[0] for i in (left, right)) / 2
            terminal = contours[arm_index]
            if not turned:
                # Bold r's curved lower attachment otherwise leaves a small
                # enclosed sliver beside n's exit. Extend only the straight
                # hidden port into the receiving shaft, keeping every arm
                # curve and its original endpoints.
                start, end = terminal[0][1][0], terminal[1][1][0]
                terminal = [terminal[0],
                            ("lineTo", ((start[0] - 30, start[1]),)),
                            ("lineTo", ((end[0] - 30, end[1]),)),
                            *terminal[1:]]
        else:
            edges = s.contour_edges(contours[0])
            left, right = (4, 10) if turned else (3, 16)
            terminal_center = sum(s.shaft_point(edges[i], join_y)[0] for i in (left, right)) / 2
            first, last = (18, 4) if turned else (11, 16)
            arm = s.native_arc(edges, first, edges[first][0], last, edges[last][0])
            # A short attachment port lies inside the receiving native arch
            # shaft. The arm's original curves and ball remain unchanged.
            port = 40.0 if turned else -40.0
            terminal = [("moveTo", (arm.start,)), *arm.operations,
                        ("lineTo", ((arm.end[0] + port, arm.end[1]),)),
                        ("lineTo", ((arm.start[0] + port, arm.start[1]),)),
                        ("closePath", ())]

    dx = arch_center - terminal_center
    move = lambda recording, x: [(op, tuple((px + x, py) for px, py in points)) for op, points in recording]
    if turned:
        recording = [*terminal, *move(arch, -dx)]
        advance = font["hmtx"][cmap[0x75]][0] - dx
    else:
        recording = [*arch, *move(terminal, dx)]
        advance = (font["hmtx"][cmap[terminal_code]][0] if prepared_terminal_advance is None
                   else prepared_terminal_advance) + dx
    return s.rounded_recording(recording), {
        "archBaseCodePoint": base_code, "archDonorCodePoint": arch_metadata["archDonorCodePoint"],
        "terminalDonorCodePoint": terminal_code, "terminalOffsetX": s.rounded(dx),
        "sharedStemOwner": "terminal" if bowl else "arch",
        "advanceWidth": s.rounded(advance),
    }

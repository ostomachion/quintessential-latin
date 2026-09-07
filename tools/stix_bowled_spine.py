"""Single-stem bowled spines in the pinned Roman STIX vocabulary.

The diagonal belly comes from a/turned a. Upper-bowled forms have epsilon's
flat lower finish; lower-bowled forms keep a's upper ball. Upright shaft
endings are independent native regions. No double-bowl contour is used.
"""


from stix_geometry import fit_operation, move


def turned_spine(font, variant, *, arch_port=False):
    import import_stix_foundation as s
    cmap = font.getBestCmap()
    extended, kind = variant % 2 == 1, variant // 4
    body_code = 0x64 if extended else 0x71 if kind == 1 else 0x251
    base = s.decomposed_recording(font, cmap[body_code])
    source = s.decomposed_recording(font, cmap[0x61])
    if len(source) != 25:
        raise RuntimeError("Pinned a topology changed")
    inner_index = {0x251: 19, 0x64: 23, 0x71: 17}[body_code]
    inner = base[inner_index][1][-1][0]
    dx = inner-source[17][1][-1][0]
    a = move(source, dx)
    outer = a[9][1][-1][0]
    # The lower-bowled direction keeps a's native upper ball. Only the
    # upper-bowled direction has the thin lower epsilon finish.
    top = a[8][1][-1]
    recording = a[:9]
    # An ascender owns the full upright shaft. Its native bowl quarter-join
    # receives the open shoulder horizontally, avoiding a clipped a curve
    # with an arbitrary corner where it meets the rising stem.
    if extended:
        recording.append(fit_operation(base[3], base[2][1][-1], base[3][1][-1],
                                       top, base[3][1][-1]))
        recording.extend(base[4:11])
    else:
        recording.append(a[9])

    corner_index = {0x251: 14, 0x64: 18, 0x71: 5}[body_code]
    corner = base[corner_index][1][-1]
    if arch_port:
        # The receiving u arch supplies the bottom shared-stem continuation.
        # Remove the entire native baseline exit before composing the arch.
        recording.extend([("lineTo", ((outer, corner[1]),)),
                          ("lineTo", (corner,))])
    elif kind == 2 or (kind == 1 and extended):
        lower_code = 0x261 if kind == 2 else 0x71
        lower = s.bowl_lower_terminal(font, lower_code, corner[1])
        lower_dx = outer-lower.start[0]
        lower = lower.translated(lower_dx)
        recording.extend([("lineTo", (lower.start,)), *lower.operations,
                          ("lineTo", (corner,))])
    elif body_code == 0x71:
        recording.extend([base[12], *base[13:14], ("lineTo", base[0][1]),
                          *base[1:6]])
    else:
        start = 11 if extended else 7
        recording.extend(base[start:corner_index+1])
    # Keep the native belly and a healthy closed counter, removing only the
    # donor's tiny overlapping seam and curling baseline foot.
    recording.append(fit_operation(a[23], a[22][1][-1], a[23][1][-1],
                                   corner, a[23][1][-1]))
    recording.append(("closePath", ()))
    from fontTools.misc.bezierTools import solveQuadratic, splitQuadraticAtT
    first, control, end = a[20][1]
    middle = tuple((first[i]+control[i])/2 for i in (0, 1))
    roots = [t for t in solveQuadratic(middle[0]-2*control[0]+end[0],
                                      2*(control[0]-middle[0]), middle[0]-inner)
             if 0 < t < 1]
    if len(roots) != 1:
        raise RuntimeError("The a counter must cross its receiving shaft once")
    _, counter_control, counter_end = splitQuadraticAtT(middle, control, end, roots[0])[0]
    recording.extend([("moveTo", a[17][1]), *a[18:20],
                      ("qCurveTo", (first, middle)),
                      ("qCurveTo", (counter_control, (inner, counter_end[1]))),
                      ("closePath", ())])
    # Use a's native sidebearing and advance for its narrower belly. The
    # replacement alpha foot fits that width, and no empty alpha-bowl space
    # is retained to the left of the smaller spine.
    recording = move(recording, -dx)
    metadata = {
        "spineDonorCodePoint": 0x61, "bodyDonorCodePoint": body_code,
        "spineOffsetX": 0, "shaftOffsetX": -dx, "freeTerminalDonorCodePoint": 0x61,
        "freeTerminalOffsetX": 0, "freeTerminalOffsetY": 0,
        "freeTerminalTurned": False, "counterStemX": inner-dx,
        "sharedStemCenterX": (inner+outer)/2-dx,
        "advanceWidth": font["hmtx"][cmap[0x61]][0],
        "counterDesign": "native-a-belly-with-upright-shaft",
    }
    if not arch_port and (kind == 2 or (kind == 1 and extended)):
        metadata.update(terminalDonorCodePoint=lower_code, terminalOffsetX=lower_dx-dx)
    return s.rounded_recording(recording), metadata


def bowled_spine_outline(font, code_point):
    import import_stix_foundation as s
    from stix_bowled_spine_normal import normal_spine, normal_spine_terminal
    if font["post"].italicAngle:
        from stix_bowled_spine_italic import italic_bowled_spine_outline
        return italic_bowled_spine_outline(font, code_point)
    arched = 0xF2B4C <= code_point <= 0xF2B57
    variant = code_point-(0xF2B4C if arched else 0xF2B10)
    if not 0 <= variant < 12:
        raise ValueError("Outside the single-stem bowled-spine increment")
    turned = variant % 4 >= 2
    if arched:
        from stix_arched_terminals import arched_terminal_outline
        if turned:
            terminal, metadata = turned_spine(font, 2, arch_port=True)
            recording, arch_metadata = arched_terminal_outline(
                font, 0xF2A5D+variant, terminal_override=terminal,
                prepared_terminal_center=metadata["sharedStemCenterX"])
        else:
            terminal, metadata, center = normal_spine_terminal(font)
            recording, arch_metadata = arched_terminal_outline(
                font, 0xF2A5D+variant, terminal_override=terminal,
                prepared_terminal_center=center,
                prepared_terminal_advance=metadata["advanceWidth"])
        metadata.update(arch_metadata)
    else:
        recording, metadata = turned_spine(font, variant) if turned else normal_spine(font, variant)
    metadata["family"] = "arched-bowled-spines" if arched else "bowled-spines"
    return s.rounded_recording(recording), {key: value for key, value in metadata.items() if value is not None}

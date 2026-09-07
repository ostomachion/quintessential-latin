"""Narrow Roman opposed bowls: two upright shafts and one shared S body.

Only the 6 by 6 unarched catalogue product is built.  Native a and turned-a
provide the opposing diagonal bowls; the two counters share one enclosing
contour. Facing hook and extended-shaft endings close together with native
bowl quarters. The S body and its shaft spacing never stretch.
"""


def _move(recording, dx=0):
    return [(op, tuple((x + dx, y) for x, y in points))
            for op, points in recording]


def _shaft(x):
    return ((x, -300), "lineTo", ((x, 800),))


def _operation_index(recording, operation):
    matches = [index for index, candidate in enumerate(recording) if candidate == operation]
    if len(matches) != 1:
        raise RuntimeError("Expected one native terminal port in the opposed-bowl outline")
    return matches[0]


def _close_upper(font, recording, metadata):
    """Close the facing hook and ascender exactly as the compact main forms."""
    import import_stix_foundation as s
    cmap = font.getBestCmap()
    hook = _move(s.decomposed_recording(font, cmap[0x253]), metadata["upperOffsetX"])
    head = _move(s.decomposed_recording(font, cmap[0x64]), metadata["rightUpperOffsetX"])
    d_outer = s.donor_contour_edges(font, 0x64)
    d_counter = s.donor_contour_edges(font, 0x64, 1)
    outer = s.fitted_bowl_join(d_outer[2], d_outer[4], _shaft(metadata["stemRightX"]),
                               hook[4][1][-1], anchor_first=True)
    inner = s.fitted_bowl_join(d_counter[2], d_outer[4], _shaft(metadata["stemRightInnerX"]),
                               hook[8][1][-1], anchor_first=False)
    outer_hook = _operation_index(recording, hook[4])
    inner_hook = _operation_index(recording, hook[9])
    inner_head = _operation_index(recording, head[5])
    outer_head = _operation_index(recording, head[10])
    outside = [*recording[:outer_hook + 1], *outer.operations, *recording[outer_head + 1:]]
    counter = [("moveTo", (inner.end,)), *recording[inner_hook:inner_head],
               ("lineTo", (inner.start,)), *inner.operations, ("closePath", ())]
    metadata.update(joinedUpper=True, upperClosureDonorCodePoint=0x64,
                    upperClosureOuterJoin=outer.end, upperClosureInnerJoin=inner.start)
    return outside, counter


def _close_lower_hook(font, recording, metadata):
    """Close the g sweep into the left shaft using native b lower quarters."""
    import import_stix_foundation as s
    cmap = font.getBestCmap()
    hook = _move(s.decomposed_recording(font, cmap[0x261]), metadata["rightLowerOffsetX"])
    foot = _move(s.decomposed_recording(font, cmap[0x70]), metadata["leftLowerOffsetX"])
    b_outer = s.donor_contour_edges(font, 0x62)
    b_counter = s.donor_contour_edges(font, 0x62, 1)
    outer = s.fitted_bowl_join(b_outer[6], b_outer[7], _shaft(metadata["stemLeftX"]),
                               hook[0][1][0], anchor_first=True)
    inner = s.fitted_bowl_join(b_counter[1], b_counter[0], _shaft(metadata["stemLeftInnerX"]),
                               hook[3][1][-1], anchor_first=False)
    # A closed tail is a continuous return into its descending shaft. The
    # donor b's deliberate corner becomes a conspicuous elbow here, especially
    # beside the narrow Bold enclosure. Ease only the two shaft-facing handles;
    # keep the hook's horizontal tangents, both endpoints, and native depths.
    outer_points = list(outer.operations[0][1])
    outer_points[-2] = (outer.end[0], outer.end[1] - .45 * (outer.end[1] - outer.start[1]))
    outer = s.NativePath(outer.start, ((outer.operations[0][0], tuple(outer_points)),))
    inner_points = list(inner.operations[0][1])
    inner_points[0] = (inner.start[0], inner.start[1] - .45 * (inner.start[1] - inner.end[1]))
    inner = s.NativePath(inner.start, ((inner.operations[0][0], tuple(inner_points)),))
    outer_hook = _operation_index(recording, hook[14])
    inner_hook = _operation_index(recording, hook[4])
    inner_foot = _operation_index(recording, foot[17])
    outside = [*recording[:outer_hook + 1], *outer.operations,
               ("lineTo", recording[0][1]), ("closePath", ())]
    counter = [("moveTo", (inner.end,)), *recording[inner_hook:inner_foot],
               ("lineTo", (inner.start,)), *inner.operations, ("closePath", ())]
    metadata.update(joinedLower="hook", lowerClosureDonorCodePoint=0x62,
                    lowerClosureOuterJoin=outer.end, lowerClosureInnerJoin=inner.start,
                    lowerClosureOuterAnchor=outer.start, lowerClosureInnerAnchor=inner.end,
                    lowerClosureDesign="shaft-tangent-native-quarter-return")
    return outside, counter


def _close_descending_feet(font, recording, metadata):
    """The two native serif feet share a bar, with a smooth inner p/q return."""
    import import_stix_foundation as s
    from stix_geometry import fit_operation
    cmap = font.getBestCmap()
    left = _move(s.decomposed_recording(font, cmap[0x70]), metadata["leftLowerOffsetX"])
    right = _move(s.decomposed_recording(font, cmap[0x71]), metadata["rightLowerOffsetX"])
    right_base = _operation_index(recording, ("lineTo", right[0][1]))
    left_base = _operation_index(recording, left[1])
    right_inner = _operation_index(recording, right[3])
    left_inner = _operation_index(recording, left[18])
    bridge = ((metadata["stemLeftInnerX"] + metadata["stemRightInnerX"]) / 2,
              min(left[18][1][-1][1], right[2][1][-1][1]))
    first = fit_operation(left[18], left[17][1][-1], left[18][1][-1],
                          left[17][1][-1], bridge)
    second = fit_operation(right[3], right[2][1][-1], right[3][1][-1],
                           bridge, right[3][1][-1])
    outside = [*recording[:right_base + 1], *recording[left_base:]]
    counter = [("moveTo", left[17][1]), first, second,
               *recording[right_inner + 1:left_inner], ("closePath", ())]
    metadata.update(joinedLower="descenders", lowerClosureDonorCodePoints=[0x70, 0x71],
                    lowerClosureBridge=bridge)
    return outside, counter


def opposed_bowls_outline(font, code_point):
    import import_stix_foundation as s
    from stix_geometry import fit_operation
    from stix_bowled_spine_normal import _counter

    if font["post"].italicAngle:
        from stix_opposed_bowls_italic import italic_opposed_bowls_outline
        return italic_opposed_bowls_outline(font, code_point)
    if not 0xF2B1C <= code_point <= 0xF2B3F:
        raise ValueError("Opposed bowls require a narrow Roman assignment")
    left_variant, right_variant = divmod(code_point - 0xF2B1C, 6)
    left_kind, left_extended = divmod(left_variant, 2)
    right_kind, right_extended = divmod(right_variant, 2)
    cmap = font.getBestCmap()
    native = lambda code: s.decomposed_recording(font, cmap[code])
    a, ta, b, p, d, alpha, q, g = map(native, (0x61, 0x250, 0x62, 0x70,
                                             0x64, 0x251, 0x71, 0x261))
    if tuple(map(len, (a, ta, b, p, d, alpha, q, g))) != (25, 25, 20, 27, 28, 24, 22, 23):
        raise RuntimeError("Pinned opposed-bowl donor topology changed")
    stem_left, stem_inner = b[8][1][-1][0], b[2][1][-1][0]
    stem_width = stem_inner - stem_left
    ta_dx = stem_inner - ta[9][1][-1][0]
    ta = _move(ta, ta_dx)
    right_outer = ta[16][1][-1][0]
    right_inner = right_outer - stem_width
    a_dx = right_inner - a[17][1][-1][0]
    a = _move(a, a_dx)

    left_foot = s.native_terminal(font, 0x70, p[16][1][-1][1], False)
    left_foot_dx = stem_inner - left_foot.start[0]
    left_foot = left_foot.translated(left_foot_dx)
    upper, lower = ta, a

    # The native p/b/hooked-b head is shared with the accepted upper-bowled
    # spine.  Both ends stay on their own native upright shaft edges.
    head_code, first, last, cut_left, cut_right = (
        (0x70, 3, 9, 350, 460), (0x62, 7, 1, 550, 550),
        (0x253, 1, 9, 420, 470))[left_kind]
    edges = s.donor_contour_edges(font, head_code)
    head = s.native_arc(edges, first, s.shaft_point(edges[first], cut_left),
                        last, s.shaft_point(edges[last], cut_right))
    head_dx = (stem_left + stem_inner) / 2 - head.center
    head = head.translated(head_dx)
    right_head_dx = right_outer - d[11][1][-1][0]
    shifted_d = _move(d, right_head_dx)
    shoulder_top = upper[15][1][-1]
    if right_extended:
        # Reserve a short receiving quarter without compressing the rising
        # shoulder into a near-vertical lump in Bold. A quarter-stem span
        # keeps positive room at the ascender and a fair run into the apex.
        shoulder_top = (min(shoulder_top[0], shifted_d[3][1][-1][0] - stem_width / 4),
                        shoulder_top[1])
    recording = [("moveTo", (head.start,)), *head.operations,
                 ("lineTo", ((stem_inner, b[2][1][-1][1]),)), b[3],
                 fit_operation(b[4], b[3][1][-1], b[4][1][-1],
                               b[3][1][-1], shoulder_top)]
    if right_extended:
        recording.extend([fit_operation(shifted_d[3], shifted_d[2][1][-1],
                                        shifted_d[3][1][-1], shoulder_top,
                                        shifted_d[3][1][-1]), *shifted_d[4:11]])
    else:
        recording.append(upper[16])

    foot_code = (0x251, 0x71, 0x261)[right_kind]
    if right_kind == 0:
        foot_dx = right_outer - alpha[7][1][-1][0]
        foot = _move(alpha, foot_dx)
        recording.extend(foot[7:15])
        corner = foot[14][1][-1]
    else:
        corner_y = q[5][1][-1][1]
        foot = s.bowl_lower_terminal(font, foot_code, corner_y)
        foot_dx = right_outer - foot.start[0]
        foot = foot.translated(foot_dx)
        recording.extend([("lineTo", (foot.start,)), *foot.operations])
        corner = foot.end
    lower_bottom = lower[23][1][-1]
    if left_extended:
        lower_join = _move(p[15:17], left_foot_dx)
        # Match the upper return's receiving proportion. The former half-
        # stem reservation squeezed Bold's exit into a steep hanging lobe.
        lower_bottom = (max(lower_bottom[0], lower_join[0][1][-1][0] + stem_width / 4),
                        lower_bottom[1])
    recording.append(fit_operation(lower[23], lower[22][1][-1], lower[23][1][-1],
                                   corner, lower_bottom))
    if left_extended:
        previous = _move(p[14:15], left_foot_dx)[0][1][-1]
        recording.extend([fit_operation(lower_join[0], previous, lower_join[0][1][-1],
                                        lower_bottom, lower_join[0][1][-1]),
                          lower_join[1], *left_foot.operations])
    else:
        recording.append(lower[1])
    recording.extend([("lineTo", (head.start,)), ("closePath", ())])

    # Native counter references establish the body before the paired optical
    # counters replace them. The S remains part of one enclosing contour.
    upper_counter, _ = _counter(ta, stem_inner)
    from fontTools.misc.bezierTools import solveQuadratic, splitQuadraticAtT
    first_control, control, end = a[20][1]
    midpoint = tuple((first_control[i] + control[i]) / 2 for i in (0, 1))
    roots = [t for t in solveQuadratic(midpoint[0] - 2 * control[0] + end[0],
                                      2 * (control[0] - midpoint[0]),
                                      midpoint[0] - right_inner) if 0 < t < 1]
    if len(roots) != 1:
        raise RuntimeError("Native lower counter no longer meets its shaft once")
    _, last_control, last_point = splitQuadraticAtT(midpoint, control, end, roots[0])[0]
    lower_counter = [("moveTo", a[17][1]), *a[18:20],
                     ("qCurveTo", (first_control, midpoint)),
                     ("qCurveTo", (last_control, (right_inner, last_point[1]))),
                     ("closePath", ())]
    # Preserve the native far-side bearing of the right-hand alpha finish.
    advance = font["hmtx"][cmap[0x251]][0] + right_outer - alpha[7][1][-1][0]
    metadata = {
        "family": "opposed-bowls", "leftVariant": left_variant,
        "rightVariant": right_variant, "archCount": 0,
        "advanceWidth": advance, "bodyDonorCodePoints": [0x250, 0x61],
        "upperBowlOffsetX": ta_dx, "lowerBowlOffsetX": a_dx,
        "waistAddedWidth": 0,
        "stemLeftX": stem_left, "stemLeftInnerX": stem_inner,
        "stemRightInnerX": right_inner, "stemRightX": right_outer,
        "upperDonorCodePoint": head_code, "upperOffsetX": head_dx,
        "rightUpperDonorCodePoint": 0x64 if right_extended else None,
        "rightUpperOffsetX": right_head_dx if right_extended else None,
        "rightLowerDonorCodePoint": foot_code, "rightLowerOffsetX": foot_dx,
        "leftLowerDonorCodePoint": 0x70 if left_extended else None,
        "leftLowerOffsetX": left_foot_dx if left_extended else None,
        "counterDesign": "integrated-native-opposed-bowls-two-counters",
    }
    terminal_counters = []
    if left_kind == 2 and right_extended:
        recording, counter = _close_upper(font, recording, metadata)
        terminal_counters.extend(counter)
    if left_extended and right_kind:
        recording, counter = (_close_lower_hook(font, recording, metadata) if right_kind == 2
                              else _close_descending_feet(font, recording, metadata))
        terminal_counters.extend(counter)
    metadata["terminalCounterCount"] = int(left_kind == 2 and right_extended) + int(left_extended and right_kind > 0)
    recording.extend([*upper_counter, *lower_counter, *terminal_counters])
    from stix_compact_spine import compact_spine_outline
    return compact_spine_outline(font, s.rounded_recording(recording),
                                 {key: value for key, value in metadata.items() if value is not None})

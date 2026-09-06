"""Close an outer hook into its newly extended neighboring middle shaft.

Reuse the accepted b/d corner curves, removing the facing ball and free
foot/head. The hook's outside sweep, arches, and shaft spacing stay fixed.
"""


def _move(operation, dx):
    return operation[0], tuple((x + dx, y) for x, y in operation[1])


def _same(first, second):
    return (first[0] == second[0] and len(first[1]) == len(second[1])
            and all(abs(a - b) < .000003 for p, q in zip(first[1], second[1])
                    for a, b in zip(p, q)))


def _receiver(font, contours, leg, turned):
    import import_stix_foundation as s
    terminal = s.native_terminal(font, 0x6C if turned else 0x70, 450 if turned else 50, turned)
    cut = 550 if turned else -50
    dx = leg["terminalOffsetX"]
    wanted = [point[0] + slope * (cut - point[1]) + dx
              for point, slope in ((terminal.start, terminal.slope(True)),
                                   (terminal.end, terminal.slope(False)))]
    for index, contour in enumerate(contours):
        edges = s.contour_edges(contour, allow_connections=True)
        matches = [[i for i, edge in enumerate(edges)
                    if edge[1] == "lineTo" and min(edge[0][1], edge[2][-1][1]) < cut < max(edge[0][1], edge[2][-1][1])
                    and abs(s.shaft_point(edge, cut)[0] - x) < .000004] for x in wanted]
        if all(len(match) == 1 for match in matches):
            return index, edges, matches[0][0], matches[1][0]
    raise RuntimeError("Could not locate the new middle shaft beside its hook")


def close_middle_hooks(font, recording, metadata, recipe_code_point):
    """Return unchanged other families or one b/d closure with its provenance."""
    import import_stix_foundation as s
    start = next((start for start in (0xF2A75, 0xF2C30)
                  if start <= recipe_code_point < start + 12), None)
    if start is None:
        return recording, []
    turned = (recipe_code_point - start) % 4 >= 2
    italic = bool(font["post"].italicAngle)
    legs = metadata["extendedMiddleLegs"]
    leg = min(legs, key=lambda item: item["centerX"]) if turned else max(legs, key=lambda item: item["centerX"])
    contours = list(s.native_recording_contours(recording))
    receiver_index, receiver, inner_index, outer_index = _receiver(font, contours, leg, turned)
    inner_shaft, outer_shaft = receiver[inner_index], receiver[outer_index]
    if turned:
        hook = s.decomposed_recording(font, font.getBestCmap()[0x266])
        dx = metadata["leftUpperOffsetX"]
        outer_operation = _move(hook[3 if italic else 5], dx)
        inner_operation = _move(hook[7 if italic else 9], dx)
        hook_index = next(i for i, contour in enumerate(contours)
                          if any(_same(op, outer_operation) for op in contour))
        current = contours[hook_index]
        first = next(i for i, op in enumerate(current) if _same(op, outer_operation))
        last = next(i for i, op in enumerate(current) if _same(op, inner_operation))
        outer_anchor, inner_anchor = current[first][1][-1], current[last - 1][1][-1]
        donor_outer, donor_counter = s.donor_contour_edges(font, 0x64), s.donor_contour_edges(font, 0x64, 1)
        outside = s.fitted_bowl_join(donor_outer[2], donor_outer[4], outer_shaft,
                                     outer_anchor, anchor_first=True)
        inside = s.fitted_bowl_join(donor_counter[2], donor_outer[4], inner_shaft,
                                    inner_anchor, anchor_first=False)
        contours[hook_index] = [*current[:first + 1], *outside.operations,
                                ("lineTo", (inside.start,)), *inside.operations, *current[last:]]
    else:
        hook = list(s.native_recording_contours(s.decomposed_recording(font, font.getBestCmap()[0x271])))[0 if italic else 1]
        dx = metadata.get("outerRibbonOffsetX", 0)
        first_operation = _move(hook[1], dx)
        hook_index = next(i for i, contour in enumerate(contours)
                          if any(_same(op, first_operation) for op in contour))
        current = contours[hook_index]
        if not all(_same(current[i], _move(hook[i], dx)) for i in range(4)):
            raise RuntimeError("Pinned hooked-m free terminal topology changed")
        outer_anchor, inner_anchor = current[0][1][0], current[3][1][-1]
        donor_outer, donor_counter = s.donor_contour_edges(font, 0x62), s.donor_contour_edges(font, 0x62, 1)
        outside = s.fitted_bowl_join(donor_outer[0 if italic else 6], donor_outer[1 if italic else 7],
                                     outer_shaft, outer_anchor, anchor_first=True)
        inside = s.fitted_bowl_join(donor_counter[4 if italic else 1], donor_counter[3 if italic else 0],
                                    inner_shaft, inner_anchor, anchor_first=False)
        contours[hook_index] = [("moveTo", (inside.start,)), *inside.operations,
                                *current[4:-1], *outside.operations, ("closePath", ())]
    if hook_index == receiver_index:
        raise RuntimeError("The hook and new middle shaft must have independent source contours")
    # Retain the complete receiving arch and curved Italic middle shaft.
    # Only the p foot or l head beyond the new outside corner is discarded.
    cut_y = outside.end[1]
    body = s.native_arc(receiver, outer_index, s.shaft_point(outer_shaft, cut_y, extend=True),
                        inner_index, s.shaft_point(inner_shaft, cut_y, extend=True))
    contours[receiver_index] = [("moveTo", (body.start,)), *body.operations, ("closePath", ())]
    return s.rounded_recording(sum(contours, [])), [{
        "direction": "upper" if turned else "lower", "donorCodePoint": 0x64 if turned else 0x62,
        "hookDonorCodePoint": 0x266 if turned else 0x271, "hookOffsetX": dx,
        "middleStemCenterX": leg["centerX"], "removedTerminalDonorCodePoint": 0x6C if turned else 0x70,
        "outerAnchor": outer_anchor, "innerAnchor": inner_anchor,
        "outerJoin": outside.end, "innerJoin": inside.start,
        "terminalDesign": "native-bowl-quarter-closure-without-facing-ball-or-serif",
    }]

"""Roman double bowls: double-thorn counter structure in the STIX vocabulary.

The outer STIX reversed-e lobes remain native. Enclosed counters need their
own curved approaches to the shaft, informed by double thorn: the open-e
interiors and square closures used in 0.160 made a brittle, capital-B body.
Both endpoints execute the same operations; stems and endings stay native.
"""


from stix_geometry import fit_operation, move


def normal_body(font, body_code=0x62):
    import import_stix_foundation as s
    cmap = font.getBestCmap()
    base = s.decomposed_recording(font, cmap[body_code])
    lobes = s.decomposed_recording(font, cmap[0x25C])
    if len(lobes) != 20:
        raise RuntimeError("Pinned reversed-e lobe topology changed")
    shoulder, bottom, stem = (4, 7, base[2][1][0][0]) if body_code == 0x62 else (
        12, 15, base[17][1][0][0])
    native_top = lobes[13][1][-1]
    # Align the free-side ink edge, not the top extremum. Those extrema
    # move differently with weight in b and epsilon: matching their tops
    # had widened the old Bold bowl by 55 units beyond its native body.
    dx = max(x for _,points in base[shoulder+1:bottom] for x,_ in points) - max(
        x for _,points in lobes[14:19] for x,_ in points)
    wing = move(lobes[14:19], dx)
    top = (native_top[0]+dx, native_top[1])
    low = wing[-1][1][-1]
    old_shoulder_start = base[shoulder-1][1][-1]
    outer = [*base[:shoulder],
             fit_operation(base[shoulder], old_shoulder_start, base[shoulder][1][-1],
                           old_shoulder_start, top), *wing,
             fit_operation(base[bottom], base[bottom-1][1][-1], base[bottom][1][-1],
                           low, base[bottom][1][-1])]
    end = next(i for i, (op, _) in enumerate(base) if op == "closePath")
    outer.extend(base[bottom+1:end+1])
    upper_waist = (lobes[8][1][-1][0]+dx, lobes[8][1][-1][1])
    upper_top = (lobes[10][1][-1][0]+dx, lobes[10][1][-1][1])
    lower_waist = (lobes[5][1][-1][0]+dx, lobes[5][1][-1][1])
    lower_bottom = (lobes[3][1][-1][0]+dx, lobes[3][1][-1][1])
    # Match the upper roof to the lower bowl's native hairline. This leaves
    # the external lobe untouched but gives the enclosed top counter enough
    # ink above it. Only its inner upper run changes vertically.
    roof = lower_bottom[1] - low[1]
    counter_top = top[1] - roof
    top_scale = (counter_top-upper_waist[1])/(upper_top[1]-upper_waist[1])
    upper_run = [(op, tuple((x+dx, upper_waist[1]+(y-upper_waist[1])*top_scale)
                            for x,y in points)) for op,points in lobes[9:11]]
    upper_top = upper_run[-1][1][-1]
    # Use the bowl's own stem-side quarter curves, fitted between the
    # epsilon extrema and waist. The last/first control approaches the
    # receiving shaft vertically, avoiding a dark square corner at the bar.
    bowl = s.decomposed_recording(font, cmap[0x62])
    upper_close = fit_operation(bowl[18], bowl[17][1][-1], bowl[18][1][-1],
                                upper_top, (stem, upper_waist[1]))
    lower_close = fit_operation(bowl[15], bowl[14][1][-1], bowl[15][1][-1],
                                (stem, lower_waist[1]), lower_bottom)
    upper_points = list(upper_close[1])
    upper_points[-2] = (stem+(upper_points[-2][0]-stem)*.20, upper_points[-2][1])
    lower_points = list(lower_close[1])
    lower_points[0] = (stem+(lower_points[0][0]-stem)*.20, lower_points[0][1])
    counters = [
        ("moveTo", ((stem, upper_waist[1]),)), ("lineTo", (upper_waist,)),
        *upper_run,
        (upper_close[0], tuple(upper_points)),
        ("closePath", ()),
        ("moveTo", ((stem, lower_waist[1]),)),
        (lower_close[0], tuple(lower_points)),
        *move(lobes[4:6], dx), ("closePath", ()),
    ]
    return outer+counters, {"lobeDonorCodePoint": 0x25C, "bodyDonorCodePoint": body_code,
                           "lobeOffsetX": dx, "counterStemX": stem,
                           "lobeTopY": top[1], "lobeBottomY": low[1],
                           "counterDesign": "native-bowl-epsilon-v2",
                           "counterJoinDonorCodePoint": 0x62,
                           "lobeAnchor": "native-bowl-free-extremum",
                           "upperCounterTopY": counter_top, "bowlHairline": roof}


def turned_body(font, body_code):
    import import_stix_foundation as s
    cmap = font.getBestCmap()
    base = s.decomposed_recording(font, cmap[body_code])
    if body_code == 0x251:
        first, last, top_join, bottom_join, inner = 1, 2, 3, 15, base[19][1][-1][0]
    elif body_code == 0x64:
        first, last, top_join, bottom_join, inner = 1, 2, 3, 19, base[23][1][-1][0]
    elif body_code == 0x71:
        first, last, top_join, bottom_join, inner = 7, 8, 9, 6, base[17][1][-1][0]
    else:
        raise ValueError("Unexpected turned double-bowl body")
    lobes = s.decomposed_recording(font, cmap[0x25B])
    if len(lobes) != 20:
        raise RuntimeError("Pinned upright-epsilon lobe topology changed")
    # Align the native free-side bowl edge independently in this direction.
    # Epsilon keeps its own asymmetry; no rotation, reflection, or forced
    # matching to the other orientation's extrema is involved.
    dx = min(x for _,points in base[first:last+1] for x,_ in points) - min(
        x for _,points in lobes[1:6] for x,_ in points)
    wing = move(lobes[1:6], dx)
    start = (lobes[0][1][0][0]+dx, lobes[0][1][0][1])
    end = wing[-1][1][-1]
    old_low = base[first-1][1][-1]
    old_high = base[last][1][-1]
    modified = list(base)
    if first == 1:
        modified[0] = ("moveTo", (start,))
    modified[top_join] = fit_operation(base[top_join], old_high, base[top_join][1][-1], end, base[top_join][1][-1])
    modified[bottom_join] = fit_operation(base[bottom_join], base[bottom_join-1][1][-1], old_low,
                                          base[bottom_join-1][1][-1], start)
    outer_end = next(i for i, (op, _) in enumerate(base) if op == "closePath")
    outer = [*modified[:first], *wing, *modified[last+1:outer_end+1]]
    upper_waist = move(lobes[10:11],dx)[0][1][-1]
    upper_top = move(lobes[8:9],dx)[0][1][-1]
    lower_waist = move(lobes[13:14],dx)[0][1][-1]
    lower_bottom = move(lobes[15:16],dx)[0][1][-1]
    roof = lower_bottom[1]-start[1]
    counter_top = end[1]-roof
    scale = (counter_top-upper_waist[1])/(upper_top[1]-upper_waist[1])
    upper_top = (upper_top[0],counter_top)
    upper_run = [(op,tuple((x+dx,upper_waist[1]+(y-upper_waist[1])*scale)
                           for x,y in points)) for op,points in lobes[9:11]]
    # The right-hand bowl supplies the matching native quarter curves.
    # Alpha and d share this counter construction; q uses the same alpha
    # quarter curves aligned to its own shaft, retaining its outer endings.
    bowl = s.decomposed_recording(font,cmap[0x251])
    upper_close = fit_operation(bowl[20],bowl[19][1][-1],bowl[20][1][-1],
                                (inner,upper_waist[1]),upper_top)
    lower_close = fit_operation(bowl[18],bowl[17][1][-1],bowl[18][1][-1],
                                lower_bottom,(inner,lower_waist[1]))
    upper_points = list(upper_close[1])
    upper_points[0] = (inner+(upper_points[0][0]-inner)*.20,upper_points[0][1])
    lower_points = list(lower_close[1])
    lower_points[-2] = (inner+(lower_points[-2][0]-inner)*.20,lower_points[-2][1])
    counters = [
        ("moveTo",(upper_waist,)),("lineTo",((inner,upper_waist[1]),)),
        (upper_close[0],tuple(upper_points)),*upper_run,("closePath",()),
        ("moveTo",((inner,lower_waist[1]),)),("lineTo",(lower_waist,)),
        *move(lobes[14:16],dx),(lower_close[0],tuple(lower_points)),("closePath",()),
    ]
    recording = [*outer,*counters]
    meta = {"lobeDonorCodePoint":0x25B,"bodyDonorCodePoint":body_code,
            "lobeOffsetX":dx,"counterStemX":inner,
            "lobeTopY":end[1],"lobeBottomY":start[1],
            "counterDesign":"native-bowl-epsilon-v2","counterJoinDonorCodePoint":0x251,
            "lobeAnchor":"native-bowl-free-extremum",
            "upperCounterTopY":counter_top,"bowlHairline":roof}
    return recording, meta


def upper_terminal(font, recording, body_code, hook=False):
    import import_stix_foundation as s
    base = s.decomposed_recording(font, font.getBestCmap()[body_code])
    native_edges = s.contour_edges(list(s.native_recording_contours(base))[0])
    contours = list(s.native_recording_contours(recording))
    edges = s.contour_edges(contours[0])
    left, right = (7, 1) if body_code == 0x62 else (3, 9)
    left_index, right_index = (edges.index(native_edges[i]) for i in (left, right))
    body = s.native_arc(edges, right_index, s.shaft_point(edges[right_index], 430),
                        left_index, s.shaft_point(edges[left_index], 300 if not hook else 380))
    head_code = 0x253 if hook else 0x70
    head_edges = s.donor_contour_edges(font, head_code)
    head_left, head_right = (1, 9) if hook else (3, 9)
    head = s.native_arc(head_edges, head_left, s.shaft_point(head_edges[head_left], 420 if hook else 350),
                        head_right, s.shaft_point(head_edges[head_right], 470 if hook else 460))
    dx = body.center-head.center
    return [*s.join_native_regions(head.translated(dx), body), *sum(contours[1:], [])], dx


def lower_terminal(font, recording, body_code, hook):
    import import_stix_foundation as s
    base = s.decomposed_recording(font, font.getBestCmap()[body_code])
    contours = list(s.native_recording_contours(recording))
    edges = s.contour_edges(contours[0])
    native_edges = s.contour_edges(list(s.native_recording_contours(base))[0])
    right, corner_op = (10, 18) if body_code == 0x64 else (6, 14)
    right_index = edges.index(native_edges[right])
    corner = base[corner_op][1][-1]
    first = next(i for i, edge in enumerate(edges) if edge[0] == corner)
    cut = s.shaft_point(edges[right_index], 180)
    body = s.native_arc(edges, first, corner, right_index, cut)
    lower = s.bowl_lower_terminal(font, 0x261 if hook else 0x71, corner[1])
    dx = cut[0]-lower.start[0]
    lower = lower.translated(dx)
    bridge = s.tangent_connector(cut, lower.start, body.slope(False), lower.slope(True))
    return [("moveTo", (body.start,)), *body.operations, bridge.operation(),
            *lower.operations, ("lineTo", (corner,)), ("closePath", ()), *sum(contours[1:], [])], dx


def double_bowl_outline(font, code_point):
    import import_stix_foundation as s
    if font["post"].italicAngle:
        from stix_double_bowl_italic import italic_double_bowl_outline
        return italic_double_bowl_outline(font, code_point)
    arched = 0xF2B40 <= code_point <= 0xF2B4B
    variant = code_point-(0xF2B40 if arched else 0xF2B04)
    if not 0 <= variant < 12:
        raise ValueError("Outside the double-bowl increment")
    turned = variant % 4 >= 2
    extended = variant % 2 == 1
    kind = variant // 4
    if arched:
        from stix_arched_terminals import arched_terminal_outline
        body_code = 0x251 if turned else 0x62
        terminal, meta = turned_body(font, body_code) if turned else normal_body(font, body_code)
        recording, arch_meta = arched_terminal_outline(font, 0xF2A5D+variant, terminal_override=terminal)
        meta.update(arch_meta)
    elif turned:
        body_code = 0x64 if extended else 0x71 if kind == 1 else 0x251
        recording, meta = turned_body(font, body_code)
        if kind == 2 or (kind == 1 and extended):
            recording, dx = lower_terminal(font, recording, body_code, kind == 2)
            meta.update(terminalDonorCodePoint=0x261 if kind == 2 else 0x71, terminalOffsetX=dx)
    else:
        body_code = 0xFE if extended and kind else 0x70 if extended else 0x62
        recording, meta = normal_body(font, body_code)
        if kind == 2 or (kind == 0 and not extended):
            recording, dx = upper_terminal(font, recording, body_code, kind == 2)
            meta.update(terminalDonorCodePoint=0x253 if kind == 2 else 0x70, terminalOffsetX=dx)
    meta.setdefault("advanceWidth", font["hmtx"][font.getBestCmap()[body_code]][0])
    meta["family"] = "arched-double-bowls" if arched else "double-bowls"
    return s.rounded_recording(recording), meta

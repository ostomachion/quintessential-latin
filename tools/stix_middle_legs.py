"""Extend free internal legs while retaining native arches and outside endings."""


def _leg_selection(extensions, count):
    """Validate the optional mask in final visual left-to-right order."""
    if extensions is None:
        return (True,) * count
    if (not isinstance(extensions, (tuple, list)) or len(extensions) != count
            or any(type(value) is not bool for value in extensions)):
        raise ValueError(f"Expected {count} middle-leg extension booleans in left-to-right order")
    return tuple(extensions)


def _split_shared_middle_feet(font, recording, legs):
    """Keep neighboring p feet simple when their native bars share a contour.

    An integrated hooked-m body can contain two full p feet. Their serif
    tips overlap at Bold, so retain the new foot as an independent native
    contour, overlapping its unchanged shaft from -50 to 20. The shared
    bottom bar is then composed by the same rule as independent m ribbons.
    """
    import import_stix_foundation as s
    if font["post"].italicAngle:
        return recording, []
    p = s.decomposed_recording(font, font.getBestCmap()[0x70])
    floor = p[1][1][-1][1]
    terminal = s.native_terminal(font, 0x70, 50, False)
    splits = []
    for leg in legs:
        if leg["direction"] != "descender":
            continue
        dx = leg.get("terminalOffsetX", leg["centerX"] - terminal.center)
        wanted = [terminal.start[0] + dx, terminal.end[0] + dx]
        contours = list(s.native_recording_contours(recording))
        for index, contour in enumerate(contours):
            edges = s.contour_edges(contour, allow_connections=True)
            bars = [edge for edge in edges if edge[1] == "lineTo"
                    and edge[0][1] == edge[2][-1][1] == floor
                    and abs(edge[0][0] - edge[2][-1][0]) > 100]
            if len(bars) < 2:
                continue
            matches = [[i for i, edge in enumerate(edges) if edge[1] == "lineTo"
                        and min(edge[0][1], edge[2][-1][1]) < -50 < max(edge[0][1], edge[2][-1][1])
                        and abs(s.shaft_point(edge, -50)[0] - x) < .000004] for x in wanted]
            if not all(len(match) == 1 for match in matches):
                continue
            inner, outer = (match[0] for match in matches)
            pair = edges[inner], edges[outer]
            body = s.native_arc(edges, outer, s.shaft_point(pair[1], -50),
                                inner, s.shaft_point(pair[0], -50))
            foot = s.native_arc(edges, inner, s.shaft_point(pair[0], 20),
                                outer, s.shaft_point(pair[1], 20))
            contours[index] = [("moveTo", (body.start,)), *body.operations, ("closePath", ())]
            contours.insert(index + 1, [("moveTo", (foot.start,)), *foot.operations, ("closePath", ())])
            recording = s.rounded_recording(sum(contours, []))
            splits.append({"middleStemCenterX": leg["centerX"], "donorCodePoint": 0x70,
                           "bodyCutY": -50, "footTopY": 20,
                           "design": "independent-native-foot-overlapping-unchanged-shaft"})
            break
    return recording, splits


def _join_middle_feet(font, recording, legs):
    """Give crowded native p feet one shared bar throughout the weight axis.

    The bar lies below the native curved returns. Its ends are inside the two
    existing serif bars even when their tips already overlap at Bold.
    """
    import import_stix_foundation as s
    if font["post"].italicAngle:
        return recording, []
    centers = [leg["centerX"] for leg in legs if leg["direction"] == "descender"]
    if not centers:
        return recording, []
    p = s.decomposed_recording(font, font.getBestCmap()[0x70])
    floor, top = p[1][1][-1][1], p[2][1][-1][1]
    bars = []
    for contour in s.native_recording_contours(recording):
        for edge in s.contour_edges(contour, allow_connections=True):
            if edge[1] == "lineTo" and edge[0][1] == edge[2][-1][1] == floor:
                left, right = sorted((edge[0][0], edge[2][-1][0]))
                if right - left > 100:
                    bars.append((left, right))
    bars.sort()
    joins, contours = [], []
    for first, second in zip(bars, bars[1:]):
        if second[0] - first[1] > 80:
            continue
        if not any(first[0] < center < first[1] or second[0] < center < second[1] for center in centers):
            continue
        left, right = sum(first) / 2, sum(second) / 2
        contours.extend([("moveTo", ((right, floor),)), ("lineTo", ((left, floor),)),
                         ("lineTo", ((left, top),)), ("lineTo", ((right, top),)), ("closePath", ())])
        joins.append({"leftCenterX": left, "rightCenterX": right, "floor": floor, "top": top})
    return [*recording, *contours], joins


def _caps(recording, above):
    import import_stix_foundation as s
    cut = 300 if above else 150
    caps = []
    for contour in s.native_recording_contours(recording):
        edges = s.contour_edges(contour, allow_connections=True)
        for first, edge in enumerate(edges):
            if edge[1] != "lineTo":
                continue
            start, end = edge[0][1], edge[2][-1][1]
            if not (start < cut < end if above else end < cut < start):
                continue
            index = (first + 1) % len(edges)
            while index != first:
                candidate = edges[index]
                a, b = candidate[0][1], candidate[2][-1][1]
                if candidate[1] == "lineTo" and (b < cut < a if above else a < cut < b):
                    x1 = s.shaft_point(edge, 250, extend=True)[0]
                    x2 = s.shaft_point(candidate, 250, extend=True)[0]
                    if 20 < abs(x2 - x1) < 190:
                        caps.append(((x1 + x2) / 2, (edge, candidate)))
                    break
                if any(y < cut - 1e-6 if above else y > cut + 1e-6 for _, y in candidate[2]):
                    break
                index = (index + 1) % len(edges)
    return caps


def _italic_middle_foot(font, recording, expected=1, middle_leg_extensions=None):
    """Keep each Italic m middle curve; replace only its baseline cap."""
    import import_stix_foundation as s
    contours = list(s.native_recording_contours(recording))
    candidates = [(i, contour) for i, contour in enumerate(contours)
                  if contour[0][0] == "moveTo" and contour[1][0] == "lineTo"
                  and contour[0][1][0][1] == contour[1][1][0][1] == 0
                  and contour[2][0] == "qCurveTo"]
    if len(candidates) != expected:
        raise RuntimeError(f"Expected {expected} native curved Italic middle shafts, found {len(candidates)}")
    selection = _leg_selection(middle_leg_extensions, expected)
    selected = {index for (index, _), extend in zip(
        sorted(candidates, key=lambda item: item[1][0][1][0][0]), selection) if extend}
    from fontTools.misc.bezierTools import splitQuadraticAtT
    changes = []
    for index, contour in candidates:
        if index not in selected:
            continue
        points = contour[2][1]
        endpoint = tuple((points[0][i] + points[1][i]) / 2 for i in (0, 1))
        _, (left, control, endpoint) = splitQuadraticAtT(contour[1][1][-1], points[0], endpoint, .5)
        right_edge = (contour[-2][1][-1], "lineTo", contour[0][1])
        right = s.shaft_point(right_edge, left[1])
        body = s.NativePath(left, (("qCurveTo", (control, endpoint)), ("qCurveTo", points[1:]),
                                   *contour[3:-1], ("lineTo", (right,))))
        terminal = s.native_terminal(font, 0x70, 20, False)
        slope = (body.slope(True) + body.slope(False)) / 2
        dx = body.center + slope * (20 - left[1]) - terminal.center
        contours[index] = s.join_native_regions(body, terminal.translated(dx))
        changes.append({"centerX": s.rounded(body.center), "centerY": left[1],
                        "direction": "descender", "donorCodePoint": 0x70,
                        "terminalOffsetX": s.rounded(dx), "shaftProfile": "native-curved"})
    return sum(contours, []), changes


def extend_arch_legs(font, recording, shaft_count, turned, *, shared_arm=False,
                     middle_leg_extensions=None):
    """Replace only the selected native free cap, never an arch ribbon."""
    import import_stix_foundation as s
    selection = _leg_selection(middle_leg_extensions, shaft_count - (1 if shared_arm else 2))
    if shaft_count == 2 and not shared_arm:
        return recording, []
    if font["post"].italicAngle and shaft_count >= 3 and not turned:
        recording, changes = _italic_middle_foot(font, recording, shaft_count - 2,
                                                selection[:-1] if shared_arm else selection)
        if shared_arm and selection[-1]:
            # The arm receives the native final m shaft. Its free cap also
            # descends, while all native arch ribbons stay unchanged.
            caps = _caps(recording, False)
            if not caps:
                raise RuntimeError("The native final Italic arch shaft has no free cap")
            center, edges = max(caps, key=lambda cap: cap[0])
            terminal = s.native_terminal(font, 0x70, 50, False)
            recording, dx = s.splice_arch_terminal(recording, edges, 150, terminal, above=False)
            changes.append({"centerX": s.rounded(center), "direction": "descender",
                            "donorCodePoint": 0x70, "terminalOffsetX": dx})
        return recording, changes
    if shaft_count == 2 and shared_arm:
        current_axes = sorted(center for center, _ in _caps(recording, turned))
        if not current_axes:
            raise RuntimeError("The shared arm shaft has no free native cap")
        axes = [current_axes[0], None] if turned else [None, current_axes[-1]]
    elif shaft_count == 4:
        from quintessential_font import LEGACY_GLYPH_BY_CODE
        reference, _ = s.legacy_outline(font, LEGACY_GLYPH_BY_CODE[0xF2C0E if turned else 0xF2C0C])
        axes = sorted(center for center, _ in _caps(reference, turned))
    else:
        donor = (0x26F if turned else 0x6D) if shaft_count == 3 else (0x75 if turned else 0x6E)
        reference = s.decomposed_recording(font, font.getBestCmap()[donor])
        axes = sorted(center for center, _ in _caps(reference, turned))
    if len(axes) != shaft_count:
        raise RuntimeError(f"Expected {shaft_count} native free-leg axes, found {axes}")
    targets = (axes[:-1] if turned else axes[1:]) if shared_arm else axes[1:-1]
    changes = []
    for axis, extend in zip(targets, selection):
        if not extend:
            continue
        candidates = [(center, edges) for center, edges in _caps(recording, turned) if abs(center - axis) < 0.001]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one free internal arch cap at {axis}, found {len(candidates)}")
        center, edges = candidates[0]
        donor = 0x6C if turned else 0x70
        terminal = s.native_terminal(font, donor, 450 if turned else 50, turned)
        recording, dx = s.splice_arch_terminal(recording, edges, 300 if turned else 150, terminal, above=turned)
        changes.append({"centerX": s.rounded(center), "direction": "ascender" if turned else "descender",
                        "donorCodePoint": donor, "terminalOffsetX": dx})
    return s.rounded_recording(recording), changes


def _arch(font, variant, double=False):
    import import_stix_foundation as s
    from quintessential_font import LEGACY_GLYPH_BY_CODE
    code = (0xF2A51 if double else 0xF2A15) + variant
    return s.legacy_outline(font, LEGACY_GLYPH_BY_CODE[code])


def _move_legs(legs, dx):
    return [dict(leg, centerX=leg["centerX"] + dx) for leg in legs]


def _terminal_family(font, recipe, start, kind, double, middle_leg_extensions=None):
    import import_stix_foundation as s
    from stix_arched_terminals import arched_terminal_outline
    from stix_extensions import _double_arch_terminal
    variant = recipe - start
    turned = variant % 4 >= 2
    selection = _leg_selection(middle_leg_extensions, 2 if double else 1)
    arch_selection = selection if kind == "arm" else (selection[1:] if turned else selection[:-1])
    terminal_extended = selection[0] if turned else selection[-1]
    arch, _ = _arch(font, variant, double)
    arch, legs = extend_arch_legs(font, arch, 3 if double else 2, turned, shared_arm=kind == "arm",
                                  middle_leg_extensions=arch_selection)
    if kind == "arm":
        if double:
            from stix_extensions import _terminal
            terminal, center, metadata = _terminal(font, kind, turned)
            result, composed = _double_arch_terminal(font, variant, terminal, center, metadata["advanceWidth"],
                                                     arm=True, arch_override=arch)
        else:
            result, composed = arched_terminal_outline(font, 0xF2A45 + variant, arch_override=arch)
            metadata = {}
    else:
        from stix_middle_terminals import prepared_terminal
        terminal, metadata, center = prepared_terminal(font, kind, turned, extended=terminal_extended)
        if double:
            result, composed = _double_arch_terminal(font, variant, terminal, center, metadata["advanceWidth"],
                                                     arch_override=arch,
                                                     port_inset=metadata.get("sharedArchPortInset", 0))
        else:
            result, composed = arched_terminal_outline(font, 0xF2A5D + variant, terminal_override=terminal,
                                                       prepared_terminal_center=center,
                                                       prepared_terminal_advance=metadata["advanceWidth"],
                                                       prepared_port_inset=3 if kind == "spine" and font["post"].italicAngle and not turned else 0,
                                                       arch_override=arch)
        terminal_shift = 0 if turned else composed["terminalOffsetX"]
        if terminal_extended:
            legs.append({"centerX": center + terminal_shift, "direction": "ascender" if turned else "descender",
                         "donorCodePoint": 0x64 if turned else 0x70, "owner": "terminal"})
    arch_shift = -composed["terminalOffsetX"] if turned else 0
    legs = [dict(leg, centerX=leg["centerX"] + (arch_shift if leg.get("owner") != "terminal" else 0)) for leg in legs]
    metadata.update(composed)
    metadata["extendedMiddleLegs"] = legs
    return s.rounded_recording(result), metadata


def _opposed(font, recipe, start, side, double, middle_leg_extensions=None):
    import import_stix_foundation as s
    from stix_arched_terminals import arched_terminal_outline
    from stix_extensions import _double_arch_terminal
    from stix_middle_terminals import opposed_terminal
    left, right = divmod(recipe - start, 6)
    selection = _leg_selection(middle_leg_extensions, 2 if double or side == "both" else 1)
    terminal_selection = selection if side == "both" else (selection[0] if side == "right" else selection[-1])
    terminal, metadata, centers = opposed_terminal(font, left, right, side=side, extended=terminal_selection)
    if not font["post"].italicAngle:
        from stix_arch_spine_joins import fair_spine_arch_port
        terminal = fair_spine_arch_port(font, terminal, metadata, side)
    advance = metadata["advanceWidth"]
    if side == "both":
        left_variant = left // 2 * 4 + left % 2
        right_variant = right // 2 * 4 + right % 2 + 2
        result, left_meta = arched_terminal_outline(font, 0xF2A5D + left_variant, terminal_override=terminal,
                                                   prepared_terminal_center=centers[0], prepared_terminal_advance=advance,
                                                   prepared_port_inset=metadata.get("sharedArchPortInset", 0))
        offset = left_meta["terminalOffsetX"]
        result, right_meta = arched_terminal_outline(font, 0xF2A5D + right_variant, terminal_override=result,
                                                    prepared_terminal_center=centers[1] + offset,
                                                    prepared_terminal_advance=left_meta["advanceWidth"])
        legs = [leg for leg, extend in zip(
            ({"centerX": centers[0] + offset, "direction": "descender", "donorCodePoint": 0x70},
             {"centerX": centers[1] + offset, "direction": "ascender", "donorCodePoint": 0x64}), selection) if extend]
        metadata.update(leftArch=left_meta, rightArch=right_meta, advanceWidth=right_meta["advanceWidth"], sigmoidOffsetX=offset)
    else:
        turned = side == "right"
        ending = right if turned else left
        variant = ending // 2 * 4 + ending % 2 + (2 if turned else 0)
        arch, _ = _arch(font, variant, double)
        arch, legs = extend_arch_legs(font, arch, 3 if double else 2, turned,
                                      middle_leg_extensions=selection[1:] if turned else selection[:-1])
        center = centers[0]
        if double:
            result, composed = _double_arch_terminal(font, variant, terminal, center, advance, arch_override=arch,
                                                     port_inset=metadata.get("sharedArchPortInset", 0))
        else:
            result, composed = arched_terminal_outline(font, 0xF2A5D + variant, terminal_override=terminal,
                                                       prepared_terminal_center=center, prepared_terminal_advance=advance,
                                                       prepared_port_inset=metadata.get("sharedArchPortInset", 0),
                                                       arch_override=arch)
        offset = 0 if turned else composed["terminalOffsetX"]
        legs = _move_legs(legs, -composed["terminalOffsetX"] if turned else 0)
        if terminal_selection:
            legs.append({"centerX": center + offset, "direction": "ascender" if turned else "descender",
                         "donorCodePoint": 0x64 if turned else 0x70})
        metadata.update(composed)
        metadata["sigmoidOffsetX"] = offset
    metadata.update(extendedMiddleLegs=legs, leftVariant=left, rightVariant=right,
                    archSide=side, sigmoidAdvanceWidth=advance)
    return s.rounded_recording(result), metadata


def middle_legs_outline(font, recipe_code_point, middle_leg_extensions=None):
    """Extend selected middle legs in final visual left-to-right order.

    None preserves the established all-extended outline and provenance.
    Explicit booleans select independently from the unchanged native base.
    """
    import import_stix_foundation as s
    from quintessential_font import LEGACY_GLYPH_BY_CODE
    code = recipe_code_point
    selection = _leg_selection(middle_leg_extensions, 2 if 0xF2C00 <= code < 0xF2CC0 else 1)
    for start, kind, double in ((0xF2A45, "arm", False), (0xF2A5D, "bowl", False),
                                (0xF2B40, "double-bowl", False), (0xF2B4C, "spine", False),
                                (0xF2C00, "arm", True), (0xF2C18, "bowl", True),
                                (0xF2C3C, "double-bowl", True), (0xF2C48, "spine", True)):
        if start <= code < start + 12:
            result, metadata = _terminal_family(font, code, start, kind, double, selection)
            break
    else:
        for start, side, double in ((0xF2B58, "left", False), (0xF2B7C, "right", False),
                                    (0xF2C54, "left", True), (0xF2C78, "right", True), (0xF2C9C, "both", False)):
            if start <= code < start + 36:
                result, metadata = _opposed(font, code, start, side, double, selection)
                break
        else:
            start = next((start for start in (0xF2A51, 0xF2A69, 0xF2A75, 0xF2C0C, 0xF2C24, 0xF2C30)
                          if start <= code < start + 12), None)
            if start is None:
                raise ValueError("A middle-leg companion requires an arch-added base")
            result, metadata = s.legacy_outline(font, LEGACY_GLYPH_BY_CODE[code])
            result, legs = extend_arch_legs(font, result, 4 if code >= 0xF2C00 else 3, (code - start) % 4 >= 2,
                                            middle_leg_extensions=selection)
            metadata["extendedMiddleLegs"] = legs
    metadata.pop("directDonorCodePoint", None)
    from stix_middle_hook_joins import close_middle_hooks
    hook_start = next((start for start in (0xF2A75, 0xF2C30) if start <= code < start + 12), None)
    hook_neighbor_extended = hook_start is None or selection[0 if (code - hook_start) % 4 >= 2 else -1]
    result, closures = close_middle_hooks(font, result, metadata, code) if hook_neighbor_extended else (result, [])
    metadata["middleHookJoins"] = closures
    result, splits = _split_shared_middle_feet(font, result, metadata["extendedMiddleLegs"])
    metadata["middleFootContourSplits"] = splits
    result, joins = _join_middle_feet(font, result, metadata["extendedMiddleLegs"])
    metadata["middleFootJoins"] = joins
    metadata.update(recipeCodePoint=code, middleLegs="extended", middleLegCount=len(metadata["extendedMiddleLegs"]))
    if middle_leg_extensions is not None:
        metadata.update(middleLegExtensions=list(selection), middleLegCount=len(selection),
                        extendedMiddleLegCount=sum(selection),
                        middleLegs="extended" if all(selection) else "partial" if any(selection) else "short")
    from stix_geometry import clean_metadata
    return s.rounded_recording(result), clean_metadata(metadata)

"""Fair the two prepared arch/spine valleys with economical quadratics.

The old horizontal closing caps left shelves where a native arch met the
sigmoid. Continue the first native bowl quadratic into the receiving shaft,
so the two curved boundaries meet like STIX m and turned-m. The upper port
needs a small optical brace in its exposed portion to retain shoulder weight.
Both counter contours and every original bowl/arch curve stay unchanged.
"""


def _continuation(start, operation):
    """Continue the first elementary quadratic backwards by one parameter span."""
    if operation[0] != "qCurveTo" or len(operation[1]) < 2:
        raise ValueError("A prepared spine port must begin with a native quadratic")
    points = operation[1]
    control = points[0]
    end = points[1] if len(points) == 2 else tuple((a + b) / 2 for a, b in zip(points[0], points[1]))
    extra = tuple(4 * a - 4 * b + c for a, b, c in zip(start, control, end))
    handle = tuple(2 * a - b for a, b in zip(start, control))
    return extra, ("qCurveTo", (handle, start))


def fair_spine_arch_port(font, recording, metadata, side):
    """Replace only prepared closing caps; coordinates remain in the S frame.

    The continuation's final handle preserves the native endpoint tangent.
    The upper start anchor sits under the incoming arch. Its vertical brace
    adds about two font units of visible shoulder support in Regular, without
    the old flat shelf. Keeping one quadratic per port gives compatible,
    economical source topology throughout the weight axis.
    """
    import import_stix_foundation as s

    if side not in ("left", "right", "both") or font["post"].italicAngle:
        raise ValueError("Spine arch ports require a Roman left/right side")
    contours = list(s.native_recording_contours(recording))
    outer = contours[0]
    regions = list(metadata.get("archSpineJoinRegions", []))

    def region(label, points):
        regions.append({"side": label, "bounds": [
            s.rounded(min(x for x, _ in points)), s.rounded(min(y for _, y in points)),
            s.rounded(max(x for x, _ in points)), s.rounded(max(y for _, y in points))]})

    if side in ("left", "both"):
        if [op for op, _ in outer[:3]] != ["moveTo", "lineTo", "qCurveTo"]:
            raise ValueError("The upper spine port is not prepared")
        old_cap, endpoint = outer[0][1][-1], outer[1][1][-1]
        start, extra = _continuation(endpoint, outer[2])
        # Derive the master factor from the native receiving shaft, so its
        # optical brace interpolates with STIX's actual outline coordinates.
        factor = (metadata["stemLeftInnerX"] - metadata["stemLeftX"] - 83) / 60
        # A rising far shaft shortens the receiving roof. In Bold its steeper
        # first quadratic needs a higher hidden anchor and a shorter handle;
        # lifting the anchor alone would eventually rise above the arch crown.
        # Shortening along the same tangent supports the exposed shoulder while
        # keeping every point of the following native roof curve unchanged.
        short_roof = bool(metadata["rightVariant"] % 2)
        brace = 80 + ((112 if short_roof else 16) - 80) * factor
        start = (start[0], start[1] + brace)
        if short_roof:
            shaft_center = (metadata["stemLeftX"] + metadata["stemLeftInnerX"]) / 2
            start = (start[0] + (shaft_center - start[0]) * factor, start[1])
        handle_factor = 1 - .5 * factor if short_roof else 1
        extra = ("qCurveTo", (tuple(b + handle_factor * (a - b)
                                   for a, b in zip(extra[1][0], endpoint)), endpoint))
        outer = [("moveTo", (start,)), extra, *outer[2:]]
        region("left", [(metadata["stemLeftX"], old_cap[1]), old_cap, endpoint,
                        start, extra[1][0]])

    if side in ("right", "both"):
        alpha = s.decomposed_recording(font, font.getBestCmap()[0x251])
        corner = (alpha[14][1][-1][0] + metadata["rightLowerOffsetX"], alpha[14][1][-1][1])
        matches = [i for i, op in enumerate(outer) if op == ("lineTo", (corner,))]
        if len(matches) != 1:
            raise ValueError("The lower spine port is not prepared")
        index = matches[0]
        if outer[index - 1][0] != "lineTo":
            raise ValueError("The lower spine cap is not a straight receiving port")
        old_outer = outer[index - 1][1][-1]
        start, extra = _continuation(corner, outer[index + 1])
        if metadata["leftVariant"] % 2:
            factor = (metadata["stemLeftInnerX"] - metadata["stemLeftX"] - 83) / 60
            shaft_center = (metadata["stemRightInnerX"] + metadata["stemRightX"]) / 2
            start = (start[0] + (shaft_center - start[0]) * factor,
                     start[1] - 80 * factor)
            extra = ("qCurveTo", (tuple(b + (1 - .5 * factor) * (a - b)
                                       for a, b in zip(extra[1][0], corner)), corner))
        new_outer = (old_outer[0], start[1])
        outer = [*outer[:index - 1], ("lineTo", (new_outer,)),
                 ("lineTo", (start,)), extra, *outer[index + 1:]]
        region("right", [old_outer, corner, new_outer, start, extra[1][0]])

    metadata["archSpineJoinDesign"] = "native-quadratic-continuation-1"
    metadata["archSpineJoinRegions"] = regions
    metadata["archSpineJoinCoordinateFrame"] = "sigmoid-source; add sigmoidOffsetX"
    return s.rounded_recording([*outer, *sum(contours[1:], [])])

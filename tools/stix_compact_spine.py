"""Optical counter design for the project's compact, two-stem spine emblem.

STIX a/turned-a provide the stress, lobe proportions and extremum tangents.
Their independent counters are unsuitable as the two edges of a shared stroke:
the adapted b shoulder pinches at its left join, and the diagonal nearly
disappears. These counters are designed as a pair within the native silhouette.
The short/short construction is the optical pilot; unreviewed family members
continue using their preserved recipes.
"""


def _spine_edge(factor):
    """Draw a fair counter edge with a gently modulated opposing spine.

    The reflected edge is designed with this one: their normal separation
    stays optically steady without imposing a heavy monoline band. Independent
    master handles keep the tighter Bold counters open and the native vertical
    tangent intact. The Regular entrance is eased to avoid an apparent waist.
    """
    lerp = lambda regular, bold: regular + factor * (bold - regular)
    return [
        ("moveTo", ((lerp(163, 215), lerp(233, 267)),)),
        ("curveTo", ((lerp(217, 258), lerp(261, 279)),
                     (lerp(338, 334), lerp(297, 305)),
                     (lerp(338, 334), lerp(349, 344)))),
    ]


def _counter_master(factor):
    lerp = lambda regular, bold: regular + factor * (bold - regular)
    left, right = lerp(163, 215), lerp(343, 334)
    # Preserve STIX's counter extrema and horizontal/vertical bowl tangents.
    # The inner shaft joins sit below/above the old independently fitted roofs,
    # leaving enough ink for a bracketed connection even at text sizes.
    upper = [
        *_spine_edge(factor),
        ("qCurveTo", ((lerp(338, 334), lerp(387, 381)),
                      (lerp(298, 311), lerp(430, 415)),
                      (lerp(266, 288), lerp(430, 415)))),
        ("curveTo", ((lerp(230, 262), lerp(430, 415)),
                     (lerp(188, 231), lerp(386, 369)),
                     (left, lerp(360, 344)))),
        ("closePath", ()),
    ]
    # Opposed edges share the same progression and tangent structure. The
    # lower return is optically relieved to suit alpha's lower shaft junction.
    sum_x, sum_y = left + right, lerp(478, 475)
    lower = [(op, tuple((sum_x-x, sum_y-y) for x,y in points)) for op,points in upper]
    lower[-2] = ("curveTo", ((lerp(276, 287), lerp(48, 60)),
                            (lerp(317, 318), lerp(73, 82)),
                            (right, lerp(104, 108))))
    return [*upper, *lower]


def _quadratic_counters(factor):
    """Use economical compatible splines before TrueType integer rounding.

    Sub-thousandth-unit conversion makes dozens of tiny segments whose rounded
    control points ripple visibly. A quarter-unit design error is below the
    integer grid and gives long, smooth quadratic runs, like the STIX donors.
    Both endpoint curves are approximated together, so topology stays fixed.
    """
    from fontTools.cu2qu import curves_to_quadratic

    masters = [_counter_master(0), _counter_master(1)]
    previous = [None, None]
    result = []
    for first, second in zip(*masters):
        op, points = first
        other = second[1]
        if op == "curveTo":
            curves = curves_to_quadratic(
                [(previous[0], *points), (previous[1], *other)], [0.25, 0.25])
            points, other = curves[0][1:], curves[1][1:]
            op = "qCurveTo"
        result.append((op, tuple((x + factor*(bx-x), y + factor*(by-y))
                                for (x,y), (bx,by) in zip(points, other))))
        if first[1]:
            previous = [first[1][-1], second[1][-1]]
    return result


def compact_spine_outline(font, recording, metadata):
    from import_stix_foundation import native_recording_contours, rounded_recording

    if font["post"].italicAngle or (metadata["leftVariant"], metadata["rightVariant"]) != (0, 0):
        raise ValueError("The compact-spine optical master requires two short Roman stems")
    left = metadata["stemLeftInnerX"]
    stem = left - metadata["stemLeftX"]
    factor = (stem - 83) / (143 - 83)
    outer = list(native_recording_contours(recording))[0]
    return rounded_recording([*outer, *_quadratic_counters(factor)]), {
        **metadata,
        "opticalRevision": "compact-spine-3",
        "counterDesign": "gently-modulated-curved-spine-with-reinforced-shaft-joins",
        "opticalReference": "STIX Two Text a, turned a, b, p and alpha",
    }

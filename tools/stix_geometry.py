"""Shared exact recording transforms and construction metadata cleanup.

These utilities do not choose donors, reshape terminals, or infer connections.
Family builders retain ownership of their optical decisions and port geometry.
"""


def move(recording, dx=0, dy=0, turn=False):
    sign = -1 if turn else 1
    return [(op, tuple((sign*x+dx, sign*y+dy) for x, y in points))
            for op, points in recording]


def fit_operation(operation, old_start, old_end, new_start, new_end):
    op, points = operation
    def fit(point):
        return tuple(new_start[i] + (point[i]-old_start[i]) *
                     (new_end[i]-new_start[i])/(old_end[i]-old_start[i])
                     if old_end[i] != old_start[i] else point[i]+new_start[i]-old_start[i]
                     for i in (0, 1))
    return op, tuple(fit(point) for point in points)


def clean_metadata(value):
    """Omit absent optional recipe fields throughout the UFO lib tree."""
    if isinstance(value, dict):
        return {key: clean_metadata(item) for key, item in value.items() if item is not None}
    if isinstance(value, (tuple, list)):
        return [clean_metadata(item) for item in value if item is not None]
    return value

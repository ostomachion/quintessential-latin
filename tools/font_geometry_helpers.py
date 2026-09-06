"""Independent font preservation geometry helpers, retained without algorithm changes."""
import pyclipper
from fontTools.pens.recordingPen import DecomposingRecordingPen, replayRecording
from test_quintessential_font import PolygonPen
POSITION_FIELDS = ("XPlacement", "YPlacement", "XAdvance", "YAdvance")
ZERO_PAIR = (0,) * 8

def outline(glyph_set, name):
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.value

def effective_pairs(font):
    """Read all DFLT kern placement fields, failing on unsupported formats.

    Effective zero values count too. A removed nonzero pair, or a new placement
    adjustment to an old glyph, cannot hide behind an omitted GPOS record.
    """
    if "GPOS" not in font:
        return {}
    table = font["GPOS"].table
    scripts = {record.ScriptTag: record.Script for record in table.ScriptList.ScriptRecord}
    if "DFLT" not in scripts or scripts["DFLT"].DefaultLangSys is None:
        return {}
    indices = []
    for index in scripts["DFLT"].DefaultLangSys.FeatureIndex:
        feature = table.FeatureList.FeatureRecord[index]
        if feature.FeatureTag == "kern":
            for lookup_index in feature.Feature.LookupListIndex:
                if lookup_index not in indices:
                    indices.append(lookup_index)
    result = {}
    for index in indices:
        lookup = table.LookupList.Lookup[index]
        if lookup.LookupType not in (2, 9):
            raise AssertionError(f"Unexpected kern lookup type {lookup.LookupType}")
        for wrapper in lookup.SubTable:
            if lookup.LookupType == 9:
                if wrapper.ExtensionLookupType != 2:
                    raise AssertionError(f"Unexpected kern extension type {wrapper.ExtensionLookupType}")
                subtable = wrapper.ExtSubTable
            else:
                subtable = wrapper
            if subtable.Format != 1:
                raise AssertionError(f"Unexpected PairPos format {subtable.Format}")
            for left, pair_set in zip(subtable.Coverage.glyphs, subtable.PairSet):
                for record in pair_set.PairValueRecord:
                    values = []
                    for value_record in (record.Value1, record.Value2):
                        if value_record is not None:
                            unexpected = set(vars(value_record)) - set(POSITION_FIELDS)
                            if unexpected:
                                raise AssertionError(f"Unresolved positioning fields {unexpected}")
                        values.extend(getattr(value_record, field, 0) or 0 for field in POSITION_FIELDS)
                    key = left, record.SecondGlyph
                    result[key] = tuple(a + b for a, b in zip(result.get(key, ZERO_PAIR), values))
    return result

def shift(recording, dx):
    return [(operation, tuple((x + dx, y) for x, y in points))
            for operation, points in recording]

def interpolate_points(first, second, factor):
    return tuple(tuple(a + factor * (b - a) for a, b in zip(p, q))
                 for p, q in zip(first, second))

def polygons_from_recording(recording):
    pen = PolygonPen(None)
    replayRecording(recording, pen)
    return [[(round(x * 64), round(y * 64)) for x, y in path] for path in pen.paths]

def counter_recordings(recording):
    contours, current = [], []
    for operation in recording:
        current.append(operation)
        if operation[0] == "closePath":
            if pyclipper.Area(polygons_from_recording(current)[0]) > 0:
                contours.append(current)
            current = []
    return sorted(contours, key=lambda contour: min(y for _, points in contour for _, y in points))

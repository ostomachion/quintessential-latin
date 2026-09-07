"""Pinned, Italic-only evidence for aligning joined donor shafts.

Current replacement records are verified before older preservation tests may
recover the exact preceding source bytes, outlines, metrics, or font tables.
The later Roman u-head correction is validated and rewound first.
"""
from __future__ import annotations

import argparse
import base64
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import plistlib
import re

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from font_geometry_helpers import outline
import serif_consistency_revision

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
BASELINE = ROOT / "resources/provenance/italic-shaft-baseline.json.gz"
REVISION = ROOT / "resources/provenance/italic-shaft-revision.json"
BASELINE_SHA256 = "c890e60529224adc3545836b4057f15eafda964762074a7b67646546066f4caa"
REVISION_SHA256 = "1e2528acd226bc45fc4e4012f4b918101f330e87a0a95dcea02cd979a3abfa5c"
REVISION_ID = "italic-donor-shaft-alignment-1"
TARGETS_FILE = ROOT / "resources/italic-shaft-targets.json"
TARGETS_SHA256 = "af71481e57da994a9f8877c3f56fdc2d5de7e6ad2839216792aa5a68d363feb9"
_target_bytes = TARGETS_FILE.read_bytes()
assert hashlib.sha256(_target_bytes).hexdigest() == TARGETS_SHA256, "Audited shaft target inventory changed"
_target_rows = json.loads(_target_bytes)["targets"]
TARGET_IDS = frozenset(row["glyphId"] for row in _target_rows)
TARGET_NAMES = frozenset(row["glyphName"] for row in _target_rows)
assert len(TARGET_IDS) == len(TARGET_NAMES) == len(_target_rows) == 150
STYLES = ("Italic", "BoldItalic")
WEIGHTS = (400, 500, 550, 600, 700)
# Only positioning involving a changed target may accompany the aligned ink.
REVISED_TABLES = frozenset(("glyf", "loca", "gvar", "CFF ", "hmtx", "GPOS", "GDEF", "head", "hhea"))
KERN_BLOCK = re.compile(rb'(?m)^\t<key>([^<]+)</key>\n\t<dict>\n(.*?)\t</dict>', re.S)
KERN_PAIR = re.compile(rb'(<key>([^<]+)</key>\n\t\t<integer>)(-?\d+)(</integer>)')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def is_revised(face, name):
    return name in TARGET_NAMES and (face in STYLES or face.startswith("Italic-"))


def recorded_outlines(glyphs, names):
    return {name: [float(glyphs[name].width), digest(json.dumps(
        [(op, [[float(v) for v in p] for p in points]) for op, points in outline(glyphs, name)],
        sort_keys=True, separators=(",", ":")).encode())] for name in names}


def normalized_tables(path):
    with TTFont(path, recalcTimestamp=False) as font:
        font["head"].fontRevision = 0
        font["head"].checkSumAdjustment = 0
        for record in font["name"].names:
            value = record.toUnicode()
            normalized = re.sub(r"0\.(?:240|250)", "0.000", value) if record.nameID in (3, 5) else value
            if value != normalized:
                record.string = normalized.encode(record.getEncoding())
        if "CFF " in font:
            for top in font["CFF "].cff.topDictIndex:
                top.version = "0.000"
        return {tag: digest(font.getTableData(tag)) for tag in sorted(font.keys())
                if tag not in ("GlyphOrder", "cmap")}


@lru_cache(maxsize=1)
def load_baseline():
    data = BASELINE.read_bytes()
    assert digest(data) == BASELINE_SHA256, "The pre-alignment Italic baseline changed"
    result = json.loads(gzip.decompress(data))
    assert result["revision"] == REVISION_ID
    assert result["targetsSha256"] == TARGETS_SHA256
    assert set(result["glyphIds"]) == TARGET_IDS
    assert set(result["glyphNames"]) == TARGET_NAMES
    assert len(result["sourceGlyphs"]) == 2 * len(TARGET_NAMES)
    assert len(result["tables"]) == 12
    assert len(result["kerning"]) == 2
    assert set(result["variablePairs"]) == {f"Italic-{weight}" for weight in WEIGHTS}
    for relative, captured in result["sourceGlyphs"].items():
        assert any(f"QuintessentialSerif-{style}.ufo/" in relative for style in STYLES), relative
        assert captured["name"] in TARGET_NAMES
        assert digest(base64.b64decode(captured["base64"])) == captured["sha256"], relative
    return result


@lru_cache(maxsize=1)
def load_revision():
    data = REVISION.read_bytes()
    assert digest(data) == REVISION_SHA256, "The verified Italic shaft revision changed"
    result = json.loads(data)
    before = load_baseline()
    assert result["schemaVersion"] == 1 and result["revision"] == REVISION_ID
    assert result["baselineSha256"] == BASELINE_SHA256
    assert set(result["glyphIds"]) == TARGET_IDS
    assert set(result["sourceGlyphs"]) == set(before["sourceGlyphs"])
    assert set(result["kerning"]) == set(before["kerning"])
    assert set(result["tables"]) == set(before["tables"])
    assert set(result["geometry"]) == {f"source-{style}" for style in STYLES} | {
        face for face in before["compiled"] if is_revised(face, next(iter(TARGET_NAMES)))}
    assert set(result["instances"]) == set(before["instances"])
    for relative, value in result["sourceGlyphs"].items():
        assert value != before["sourceGlyphs"][relative]["sha256"], relative
    for relative, value in result["kerning"].items():
        assert value != before["kerning"][relative]["sha256"], relative
    for filename, changes in result["tables"].items():
        assert set(changes) <= REVISED_TABLES, (filename, "Unrelated table authorized")
        assert bool(changes) == ("Italic" in filename), (filename, "Wrong posture changed")
        assert all(value != before["tables"][filename][tag] for tag, value in changes.items())
    for key, records in result["geometry"].items():
        assert set(records) == TARGET_NAMES | ({"pairs", "variablePairs"} if key.startswith("Italic-") else {"pairs"}), (
            key, "Unexpected revised outline inventory")
        source = key.startswith("source-")
        face = key.removeprefix("source-")
        old = before["sources" if source else "compiled"][face]
        for name, record in records.items():
            if name in ("pairs", "variablePairs"):
                assert all(any(part in TARGET_NAMES for part in pair.split("/")) for pair in record), key
                old_pairs = before["targetPairs" if name == "pairs" else "variablePairs"][key]
                assert all(value != old_pairs.get(pair, 0) for pair, value in record.items()), key
                continue
            assert record["outline"][0] == old["outlines"][name][0], (key, name, "Advance changed")
            assert record["outline"][1] != old["outlines"][name][1], (key, name, "Alignment omitted")
            if not source:
                assert record["metrics"][0] == old["hmtx"][name][0], (key, name, "Metric advance changed")
    for face, records in result["instances"].items():
        assert set(records) == TARGET_NAMES, (face, "Unexpected revised instance inventory")
        assert all(record[0] == before["instances"][face][name][0] for name, record in records.items()), face
    return result


def historical_source_bytes(path, data=None):
    path = Path(path)
    data = path.read_bytes() if data is None else data
    data = serif_consistency_revision.historical_source_bytes(path, data)
    relative = path.relative_to(ROOT).as_posix()
    if relative in load_baseline()["kerning"]:
        assert digest(data) == load_revision()["kerning"][relative], (relative, "Unverified aligned Italic kerning")
        return restore_kerning_bytes(data, load_baseline()["kerning"][relative])
    captured = load_baseline()["sourceGlyphs"].get(relative)
    if captured is None:
        return data
    assert digest(data) == load_revision()["sourceGlyphs"][relative], (relative, "Unverified aligned Italic source")
    return base64.b64decode(captured["base64"])


def historical_outline(face, name, actual, *, source=False, instantiated=False):
    actual = serif_consistency_revision.historical_outline(face, name, actual,
                                                          source=source, instantiated=instantiated)
    if not is_revised(face, name):
        return actual
    if instantiated:
        assert actual == load_revision()["instances"][face][name], (face, name, "Unverified aligned Italic instance")
        return load_baseline()["instances"][face][name]
    key = f"source-{face}" if source else face
    assert actual == load_revision()["geometry"][key][name]["outline"], (key, name, "Unverified aligned Italic outline")
    return load_baseline()["sources" if source else "compiled"][face]["outlines"][name]


def historical_metrics(face, name, actual):
    actual = serif_consistency_revision.historical_metrics(face, name, actual)
    if not is_revised(face, name):
        return actual
    assert list(actual) == load_revision()["geometry"][face][name]["metrics"], (face, name, "Unverified aligned Italic metrics")
    return load_baseline()["compiled"][face]["hmtx"][name]


def historical_tables(filename, actual):
    actual = serif_consistency_revision.historical_tables(filename, actual)
    before = load_baseline()["tables"][filename]
    expected = {**before, **load_revision()["tables"][filename]}
    assert actual == expected, (filename, "Unverified aligned Italic font table", sorted(
        tag for tag in actual.keys() | expected.keys() if actual.get(tag) != expected.get(tag)))
    verify_aggregate_metrics(OUTPUT / filename)
    return before


def verify_aggregate_metrics(path):
    """Permit only the exact three extrema derived from the revised ink."""
    if "Italic" not in path.name:
        return
    old_lsb, old_rsb = (-207, -179) if "BoldItalic" in path.name else (-163, -166)
    with TTFont(path, recalcTimestamp=False) as font:
        bounds = {}
        if "glyf" in font:
            for name in font.getGlyphOrder():
                glyph = font["glyf"][name]
                if glyph.numberOfContours:
                    bounds[name] = glyph.xMin, glyph.xMax
        else:
            charstrings = font["CFF "].cff.topDictIndex[0].CharStrings
            for name in font.getGlyphOrder():
                box = charstrings[name].calcBounds(charstrings)
                if box is not None:
                    bounds[name] = math.floor(box[0]), math.ceil(box[2])
        left = {name: font["hmtx"][name][1] for name in bounds}
        right = {name: font["hmtx"][name][0] - left[name] - (box[1] - box[0]) for name, box in bounds.items()}
        fields = (("head", "xMin", {name: box[0] for name, box in bounds.items()}, old_lsb),
                  ("hhea", "minLeftSideBearing", left, old_lsb),
                  ("hhea", "minRightSideBearing", right, old_rsb))
        for tag, field, values, old in fields:
            actual = getattr(font[tag], field)
            assert actual == min(values.values()), (path.name, tag, field, "Wrong aggregate ink metric")
            if actual != old:
                assert any(name in TARGET_NAMES and value == actual for name, value in values.items()), (
                    path.name, tag, field, "Changed extrema lacks an aligned target")
            setattr(font[tag], field, old)
        font.recalcBBoxes = False
        font["head"].fontRevision = 0
        font["head"].checkSumAdjustment = 0
        for tag in ("head", "hhea"):
            assert digest(font.getTableData(tag)) == load_baseline()["tables"][path.name][tag], (
                path.name, tag, "Metadata differs beyond the three measured ink extrema")


def verify_sources():
    serif_consistency_revision.verify_sources()
    for relative, expected in load_revision()["sourceGlyphs"].items():
        assert digest((ROOT / relative).read_bytes()) == expected, relative
    for relative in load_revision()["kerning"]:
        historical_source_bytes(ROOT / relative)
    return len(load_revision()["sourceGlyphs"])


def target_source_pairs(data):
    result = {}
    for block in KERN_BLOCK.finditer(data):
        left = block[1].decode()
        for pair in KERN_PAIR.finditer(block[2]):
            right = pair[2].decode()
            if left in TARGET_NAMES or right in TARGET_NAMES:
                result[f"{left}/{right}"] = int(pair[3])
    assert len(result) == (2 * 1216 - len(TARGET_NAMES)) * len(TARGET_NAMES), len(result)
    return result


def restore_kerning_bytes(data, old):
    def restore_block(block):
        left = block[1].decode()
        def restore_pair(pair):
            key = f"{left}/{pair[2].decode()}"
            return pair[1] + str(old["pairs"][key]).encode() + pair[4] if key in old["pairs"] else pair[0]
        return block[0].replace(block[2], KERN_PAIR.sub(restore_pair, block[2]), 1)
    result = KERN_BLOCK.sub(restore_block, data)
    assert digest(result) == old["sha256"], "Unrelated kerning or formatting changed"
    return result


def historical_pairs(pairs, face, *, source=False):
    if face not in STYLES and not face.startswith("Italic-"):
        return pairs
    key = f"source-{face}" if source else face
    old = load_baseline()["targetPairs"][key]
    expected = {**old, **load_revision()["geometry"][key]["pairs"]}
    current = {f"{left}/{right}": (value if source else list(value))
               for (left, right), value in pairs.items() if left in TARGET_NAMES or right in TARGET_NAMES}
    wanted = {pair: value if source else [0, 0, value, 0, 0, 0, 0, 0] for pair, value in expected.items() if value}
    assert {pair: value for pair, value in current.items() if (value if source else any(value))} == wanted, (
        key, "Unverified aligned Italic positioning")
    result = dict(pairs)
    for encoded in current.keys() | old.keys():
        left, right = encoded.split("/")
        value = old.get(encoded, 0)
        result[left, right] = value if source else (0, 0, value, 0, 0, 0, 0, 0)
    return result


def historical_pair_tables(face, actual):
    if not face.startswith("Italic-"):
        return actual
    filename = "QuintessentialSerif-Italic-Variable.ttf"
    expected = {**load_baseline()["tables"][filename], **load_revision()["tables"][filename]}
    before = load_baseline()["compiled"][face]["pairTables"]
    assert actual == {tag: expected[tag] for tag in before}, (face, "Unverified aligned Italic positioning tables")
    return before


def compiled_target_pairs(path, weight=None, *, rounded=True):
    from fontTools.misc.roundTools import otRound
    from test_stemless_terminals import target_pair_values
    from test_quintessential_font import dflt_kern_lookups
    with TTFont(path) as font:
        if weight is not None:
            values = target_pair_values(font, font.getGlyphSet(location={"wght": weight}).location, TARGET_NAMES)
        else:
            values = {}
            for lookup in dflt_kern_lookups(font):
                for wrapper in lookup.SubTable:
                    table = wrapper.ExtSubTable if lookup.LookupType == 9 else wrapper
                    assert table.Format == 1
                    for left, pair_set in zip(table.Coverage.glyphs, table.PairSet):
                        for record in pair_set.PairValueRecord:
                            right = record.SecondGlyph
                            if left in TARGET_NAMES or right in TARGET_NAMES:
                                assert record.Value2 is None
                                values[left, right] = values.get((left, right), 0) + getattr(record.Value1, "XAdvance", 0)
        convert = otRound if rounded else lambda value: value
        return {f"{left}/{right}": convert(value) for (left, right), value in values.items() if convert(value)}


def historical_variable_pairs(pairs, face):
    if not face.startswith("Italic-"):
        return pairs
    old = load_baseline()["variablePairs"][face]
    expected = {**old, **load_revision()["geometry"][face]["variablePairs"]}
    actual = {f"{left}/{right}": value for (left, right), value in pairs.items()
              if value and (left in TARGET_NAMES or right in TARGET_NAMES)}
    assert actual == {pair: value for pair, value in expected.items() if value}, (face, "Unverified variable target pairs")
    result = dict(pairs)
    for pair in actual.keys() | old.keys():
        result[tuple(pair.split("/"))] = old.get(pair, 0)
    return result


def non_target_pair_digest(font, location):
    """Independently resolve every unedited pair's full variable positioning."""
    from fontTools.varLib.varStore import VarStoreInstancer
    from test_quintessential_font import dflt_kern_lookups
    variation = VarStoreInstancer(font["GDEF"].table.VarStore, font["fvar"].axes, location)
    values = {}
    for lookup in dflt_kern_lookups(font):
        assert lookup.LookupType in (2, 9)
        for wrapper in lookup.SubTable:
            table = wrapper.ExtSubTable if lookup.LookupType == 9 else wrapper
            assert table.Format == 1
            for left, pair_set in zip(table.Coverage.glyphs, table.PairSet):
                if left in TARGET_NAMES:
                    continue
                for record in pair_set.PairValueRecord:
                    right = record.SecondGlyph
                    if right in TARGET_NAMES:
                        continue
                    assert record.Value2 is None or not any(vars(record.Value2).values())
                    value = record.Value1
                    assert set(vars(value)) <= {"XAdvance", "XAdvDevice"}
                    amount = getattr(value, "XAdvance", 0)
                    device = getattr(value, "XAdvDevice", None)
                    if device:
                        assert device.DeltaFormat == 0x8000
                        amount += variation[(device.StartSize << 16) | device.EndSize]
                    values[left, right] = values.get((left, right), 0) + amount
    return digest(json.dumps(sorted([left, right, value] for (left, right), value in values.items() if value),
                             sort_keys=True, separators=(",", ":")).encode())


def face_location(face):
    if face.startswith("Italic-"):
        return "QuintessentialSerif-Italic-Variable.ttf", int(face.split("-")[1])
    return f"QuintessentialSerif-{face}.otf", None


def capture_instances(folder):
    cache = ROOT / ".tmp/italic-shaft-current-instances.json"
    font_hash = digest((folder / "QuintessentialSerif-Italic-Variable.ttf").read_bytes())
    if folder == OUTPUT and cache.exists():
        cached = json.loads(cache.read_text())
        if cached["font"] == font_hash and cached["targets"] == TARGETS_SHA256:
            return cached["instances"]
    result = {}
    for weight in WEIGHTS:
        face = f"Italic-{weight}"
        with TTFont(folder / "QuintessentialSerif-Italic-Variable.ttf") as font:
            instance = instantiateVariableFont(font, {"wght": weight}, inplace=True)
            result[face] = recorded_outlines(instance.getGlyphSet(), TARGET_NAMES)
        print(f"Italic shaft instance evidence {weight}", flush=True)
    if folder == OUTPUT:
        cache.write_text(json.dumps({"font": font_hash, "targets": TARGETS_SHA256, "instances": result},
                                   sort_keys=True), encoding="utf-8")
    return result


def capture_compiled_face(face, folder=OUTPUT):
    filename, weight = face_location(face)
    cache = ROOT / f".tmp/italic-shaft-current-{face}.json.gz"
    font_hash = digest((folder / filename).read_bytes())
    if folder == OUTPUT and cache.exists():
        cached = json.loads(gzip.decompress(cache.read_bytes()))
        if cached["font"] == font_hash and cached["targets"] == TARGETS_SHA256:
            return cached["record"]
    with TTFont(folder / filename) as font:
        glyphs = font.getGlyphSet(location={"wght": weight}) if weight is not None else font.getGlyphSet()
        records = recorded_outlines(glyphs, TARGET_NAMES)
        result = {name: {"outline": records[name], "metrics": font["hmtx"][name]} for name in TARGET_NAMES}
    result["pairs"] = compiled_target_pairs(folder / filename, weight)
    if weight is not None:
        result["variablePairs"] = compiled_target_pairs(folder / filename, weight, rounded=False)
    if folder == OUTPUT:
        cache.write_bytes(gzip.compress(json.dumps({"font": font_hash, "targets": TARGETS_SHA256, "record": result},
                                                   sort_keys=True, separators=(",", ":")).encode(), mtime=0))
    return result


def capture(folder):
    # The broad pre-edit capture is generated from the copied, untouched files.
    geometry = folder / "geometry.json.gz"
    if geometry.exists():
        result = json.loads(gzip.decompress(geometry.read_bytes()))
    else:
        from test_stemless_terminals import capture as capture_geometry
        result = capture_geometry(folder, ())
        result["tables"] = {path.name: normalized_tables(path) for path in sorted((folder / "compiled").iterdir())
                            if path.suffix in (".ttf", ".otf", ".woff2")}
    result.update(revision=REVISION_ID, glyphIds=sorted(TARGET_IDS),
                  glyphNames=sorted(TARGET_NAMES), targetsSha256=TARGETS_SHA256,
                  sourceGlyphs={}, kerning={}, targetPairs={},
                  nonTargetPairs={}, variablePairs={})
    for style in STYLES:
        directory = folder / "sources" / f"QuintessentialSerif-{style}.ufo"
        contents = plistlib.loads((directory / "glyphs/contents.plist").read_bytes())
        with Font.open(directory) as source:
            result["sources"][style]["targets"] = {
                name: {"recording": outline(source, name), "lib": source[name].lib} for name in TARGET_NAMES}
        for name in TARGET_NAMES:
            path = directory / "glyphs" / contents[name]
            relative = "fonts/QuintessentialSerif/" + path.relative_to(folder / "sources").as_posix()
            data = path.read_bytes()
            result["sourceGlyphs"][relative] = {"name": name, "sha256": digest(data),
                                               "base64": base64.b64encode(data).decode()}
        path = directory / "kerning.plist"
        data = path.read_bytes()
        pairs = target_source_pairs(data)
        relative = "fonts/QuintessentialSerif/" + path.relative_to(folder / "sources").as_posix()
        result["kerning"][relative] = {"sha256": digest(data), "pairs": pairs}
        result["targetPairs"][f"source-{style}"] = pairs
    for face in result["compiled"]:
        if not is_revised(face, next(iter(TARGET_NAMES))):
            continue
        filename, weight = face_location(face)
        result["targetPairs"][face] = compiled_target_pairs(folder / "compiled" / filename, weight)
        if weight is not None:
            result["variablePairs"][face] = compiled_target_pairs(folder / "compiled" / filename, weight, rounded=False)
            with TTFont(folder / "compiled" / filename) as font:
                result["nonTargetPairs"][face] = non_target_pair_digest(font, font.getGlyphSet(location={"wght": weight}).location)
        print(f"Italic shaft pair evidence {face}", flush=True)
    result["instances"] = capture_instances(folder / "compiled")
    return result


def current_revision():
    before = load_baseline()
    result = {"schemaVersion": 1, "revision": REVISION_ID, "glyphIds": sorted(TARGET_IDS),
              "baselineSha256": BASELINE_SHA256, "sourceGlyphs": {}, "kerning": {}, "tables": {}, "geometry": {}}
    for relative in before["sourceGlyphs"]:
        result["sourceGlyphs"][relative] = digest((ROOT / relative).read_bytes())
        assert result["sourceGlyphs"][relative] != before["sourceGlyphs"][relative]["sha256"], relative
    for relative in before["kerning"]:
        result["kerning"][relative] = digest((ROOT / relative).read_bytes())
        restore_kerning_bytes((ROOT / relative).read_bytes(), before["kerning"][relative])
    for filename, old in before["tables"].items():
        actual = normalized_tables(OUTPUT / filename)
        assert set(actual) == set(old)
        result["tables"][filename] = {tag: value for tag, value in actual.items() if value != old[tag]}
        assert set(result["tables"][filename]) <= REVISED_TABLES, (filename, result["tables"][filename])
        assert bool(result["tables"][filename]) == ("Italic" in filename), (filename, "Wrong posture changed")
        verify_aggregate_metrics(OUTPUT / filename)
    for style in STYLES:
        with Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") as source:
            records = recorded_outlines(source, TARGET_NAMES)
            result["geometry"][f"source-{style}"] = {name: {"outline": records[name]} for name in TARGET_NAMES}
            current = target_source_pairs((SOURCES / f"QuintessentialSerif-{style}.ufo/kerning.plist").read_bytes())
            old = before["targetPairs"][f"source-{style}"]
            result["geometry"][f"source-{style}"]["pairs"] = {
                pair: value for pair, value in current.items() if value != old[pair]}
    for face in before["compiled"]:
        if not is_revised(face, next(iter(TARGET_NAMES))):
            continue
        filename, weight = face_location(face)
        captured = capture_compiled_face(face)
        result["geometry"][face] = {name: captured[name] for name in TARGET_NAMES}
        current, old = captured["pairs"], before["targetPairs"][face]
        result["geometry"][face]["pairs"] = {pair: current.get(pair, 0)
            for pair in current.keys() | old.keys() if current.get(pair, 0) != old.get(pair, 0)}
        if weight is not None:
            current, old = captured["variablePairs"], before["variablePairs"][face]
            result["geometry"][face]["variablePairs"] = {pair: current.get(pair, 0)
                for pair in current.keys() | old.keys() if current.get(pair, 0) != old.get(pair, 0)}
    result["instances"] = capture_instances(OUTPUT)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-from", type=Path)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    if args.capture_from:
        assert not BASELINE.exists(), "Refusing to overwrite frozen baseline"
        data = gzip.compress(json.dumps(capture(args.capture_from), sort_keys=True, separators=(",", ":")).encode(), mtime=0)
        BASELINE.write_bytes(data)
    elif args.seal:
        assert not REVISION.exists(), "Refusing to overwrite sealed revision"
        data = (json.dumps(current_revision(), sort_keys=True, indent=2) + "\n").encode()
        REVISION.write_bytes(data)
    else:
        parser.error("Choose --capture-from or --seal")
    print(digest(data))


if __name__ == "__main__":
    main()

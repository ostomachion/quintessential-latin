"""Sealed Roman cap-serif revision, verified before older evidence is rewound.

The independent capture retains old target GLIFs plus compact hashes for all
unrelated sources, outlines, metrics and font tables. No positioning exception
is permitted, and no older baseline or revision fixture is rewritten.
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
from fontTools.pens.boundsPen import BoundsPen
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from font_geometry_helpers import outline

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts/QuintessentialSerif"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
BASELINE = ROOT / "resources/provenance/serif-consistency-baseline.json.gz"
REVISION = ROOT / "resources/provenance/serif-consistency-revision.json"
TARGETS_FILE = ROOT / "resources/serif-consistency-targets.json"
BASELINE_SHA256 = "27e6568fe90097f37125b75a85354784df392dcbfded0b0883162e768d3365ea"
REVISION_SHA256 = "019128c20b50a970df1bdf0c9749fc0c5d87d2b44a0235d22a55f3c9f11665fe"
TARGETS_SHA256 = "4b36502347fb8757c4fedb68c5ecca28a12209f0b18b00c72bcefd12034b31f7"
REVISION_ID = "roman-cap-serif-consistency-1"
STYLES = ("Regular", "Bold")
WEIGHTS = (400, 500, 550, 600, 700)
FACES = STYLES + tuple(f"Roman-{weight}" for weight in WEIGHTS)
REVISED_TABLES = frozenset(("glyf", "loca", "gvar", "CFF ", "hmtx"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def value_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


@lru_cache(maxsize=1)
def target_rows():
    data = TARGETS_FILE.read_bytes()
    assert digest(data) == TARGETS_SHA256, "The audited serif target inventory changed"
    rows = json.loads(data)["entries"]
    assert rows and len({row["glyphName"] for row in rows}) == len(rows)
    assert len({row["glyphId"] for row in rows}) == len(rows)
    return rows


@lru_cache(maxsize=1)
def target_names():
    return frozenset(row["glyphName"] for row in target_rows())


def is_revised(face, name):
    return face in FACES and name in target_names()


def recorded_outlines(glyphs, names):
    return {name: [float(glyphs[name].width), value_digest(
        [(op, [[float(value) for value in point] for point in points])
         for op, points in outline(glyphs, name)])] for name in names}


def normalized_tables(path):
    """Use the existing preservation chain's version-only normalization."""
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


def face_location(face):
    if face.startswith("Roman-"):
        return "QuintessentialSerif-Variable.ttf", int(face.split("-")[1])
    return f"QuintessentialSerif-{face}.otf", None


def outline_capture(glyphs, names):
    records = recorded_outlines(glyphs, names)
    return {"targets": {name: records[name] for name in target_names()},
            "unrelated": value_digest({name: record for name, record in records.items()
                                       if name not in target_names()})}


def capture_geometry(source_folder, compiled_folder):
    result = {"sources": {}, "compiled": {}, "instances": {}}
    for style in STYLES:
        with Font.open(source_folder / f"QuintessentialSerif-{style}.ufo") as source:
            result["sources"][style] = outline_capture(source, source.lib["public.glyphOrder"])
    for face in FACES:
        filename, weight = face_location(face)
        with TTFont(compiled_folder / filename) as font:
            glyphs = font.getGlyphSet(location={"wght": weight}) if weight is not None else font.getGlyphSet()
            captured = outline_capture(glyphs, font.getGlyphOrder())
            captured["targetMetrics"] = {name: list(font["hmtx"][name]) for name in target_names()}
            captured["unrelatedMetrics"] = value_digest({name: record for name, record in font["hmtx"].metrics.items()
                                                         if name not in target_names()})
            base_glyphs = font.getGlyphSet()
            for name in target_names():
                pen = BoundsPen(base_glyphs)
                base_glyphs[name].draw(pen)
                assert font["hmtx"][name][1] == math.floor(pen.bounds[0]), (face, name, "LSB differs from actual base ink")
            captured["order"] = value_digest(font.getGlyphOrder())
            result["compiled"][face] = captured
            if weight is not None:
                # Positioning has independent byte-for-byte table evidence;
                # it is irrelevant to instantiating an outline recording.
                for tag in ("GPOS", "GDEF"):
                    if tag in font:
                        del font[tag]
                instance = instantiateVariableFont(font, {"wght": weight}, inplace=True)
                result["instances"][face] = recorded_outlines(instance.getGlyphSet(), target_names())
        print(f"serif preservation capture {face}", flush=True)
    return result


def font_paths(folder):
    return sorted(path for path in folder.iterdir() if path.suffix in (".otf", ".ttf", ".woff2"))


def capture(folder):
    source_folder, compiled_folder = folder / "sources", folder / "compiled"
    result = {"schemaVersion": 1, "revision": REVISION_ID, "targetsSha256": TARGETS_SHA256,
              "glyphIds": sorted(row["glyphId"] for row in target_rows()),
              "sourceFiles": {}, "sourceGlyphs": {}, "tables": {}, "cmaps": {}}
    for path in sorted(source_folder.rglob("*")):
        if path.is_file():
            result["sourceFiles"][path.relative_to(source_folder).as_posix()] = digest(path.read_bytes())
    for style in STYLES:
        directory = source_folder / f"QuintessentialSerif-{style}.ufo"
        contents = plistlib.loads((directory / "glyphs/contents.plist").read_bytes())
        for name in target_names():
            path = directory / "glyphs" / contents[name]
            relative = "fonts/QuintessentialSerif/" + path.relative_to(source_folder).as_posix()
            data = path.read_bytes()
            result["sourceGlyphs"][relative] = {"name": name, "sha256": digest(data),
                                               "base64": base64.b64encode(data).decode()}
    for path in font_paths(compiled_folder):
        result["tables"][path.name] = normalized_tables(path)
        with TTFont(path) as font:
            result["cmaps"][path.name] = digest(font.getTableData("cmap"))
    result.update(capture_geometry(source_folder, compiled_folder))
    return result


@lru_cache(maxsize=1)
def load_baseline():
    data = BASELINE.read_bytes()
    assert digest(data) == BASELINE_SHA256, "The pre-serif-consistency baseline changed"
    result = json.loads(gzip.decompress(data))
    assert result["schemaVersion"] == 1 and result["revision"] == REVISION_ID
    assert result["targetsSha256"] == TARGETS_SHA256
    assert set(result["glyphIds"]) == {row["glyphId"] for row in target_rows()}
    assert len(result["sourceGlyphs"]) == 2 * len(target_names())
    assert set(result["sources"]) == set(STYLES) and set(result["compiled"]) == set(FACES)
    assert set(result["instances"]) == {f"Roman-{weight}" for weight in WEIGHTS}
    assert len(result["tables"]) == 12 and set(result["cmaps"]) == set(result["tables"])
    for relative, captured in result["sourceGlyphs"].items():
        assert any(f"QuintessentialSerif-{style}.ufo/" in relative for style in STYLES), relative
        assert captured["name"] in target_names()
        assert digest(base64.b64decode(captured["base64"])) == captured["sha256"], relative
        assert result["sourceFiles"][Path(relative).relative_to("fonts/QuintessentialSerif").as_posix()] == captured["sha256"]
    return result


def validate_geometry(actual, before):
    """Check every unrelated outline, full metrics, GID order, and all advances."""
    for kind in ("sources", "compiled"):
        assert set(actual[kind]) == set(before[kind])
        for face, current in actual[kind].items():
            old = before[kind][face]
            assert set(current) == set(old), (kind, face)
            for key in current.keys() - {"targets", "targetMetrics"}:
                assert current[key] == old[key], (kind, face, key, "Unrelated data changed")
            assert set(current["targets"]) == set(old["targets"]) == target_names()
            for name, record in current["targets"].items():
                assert record[0] == old["targets"][name][0], (kind, face, name, "Advance changed")
                assert record[1] != old["targets"][name][1], (kind, face, name, "Serif revision absent")
            if kind == "compiled":
                assert set(current["targetMetrics"]) == set(old["targetMetrics"]) == target_names()
                for name, metrics in current["targetMetrics"].items():
                    assert metrics[0] == old["targetMetrics"][name][0], (face, name, "Metric advance changed")
    assert set(actual["instances"]) == set(before["instances"])
    for face, records in actual["instances"].items():
        assert set(records) == set(before["instances"][face]) == target_names()
        for name, record in records.items():
            assert record[0] == before["instances"][face][name][0], (face, name, "Instantiated advance changed")
            assert record[1] != before["instances"][face][name][1], (face, name, "Instantiated serif revision absent")


@lru_cache(maxsize=1)
def load_revision():
    data = REVISION.read_bytes()
    assert digest(data) == REVISION_SHA256, "The sealed serif consistency revision changed"
    result, before = json.loads(data), load_baseline()
    assert result["schemaVersion"] == 1 and result["revision"] == REVISION_ID
    assert result["baselineSha256"] == BASELINE_SHA256
    assert set(result["sourceGlyphs"]) == set(before["sourceGlyphs"])
    assert set(result["tables"]) == set(before["tables"])
    for relative, value in result["sourceGlyphs"].items():
        assert value != before["sourceGlyphs"][relative]["sha256"], relative
    for filename, changes in result["tables"].items():
        assert set(changes) <= REVISED_TABLES, (filename, "Unrelated table authorized")
        assert bool(changes) == ("Italic" not in filename), (filename, "Wrong posture changed")
        assert all(value != before["tables"][filename][tag] for tag, value in changes.items())
    for stem, suffix in (("Regular", ".otf"), ("Bold", ".otf"), ("Variable", ".ttf")):
        name = f"QuintessentialSerif-{stem}"
        assert result["tables"][name + suffix] == result["tables"][name + ".woff2"], (
            name, "WOFF2 revised ink or metrics differs from its desktop font")
    validate_geometry(result, before)
    return result


def historical_source_bytes(path, data=None):
    path = Path(path)
    data = path.read_bytes() if data is None else data
    relative = path.relative_to(ROOT).as_posix()
    captured = load_baseline()["sourceGlyphs"].get(relative)
    if captured is None:
        return data
    assert digest(data) == load_revision()["sourceGlyphs"][relative], (relative, "Unverified serif source")
    return base64.b64decode(captured["base64"])


def historical_outline(face, name, actual, *, source=False, instantiated=False):
    if not is_revised(face, name):
        return actual
    if instantiated:
        current, previous = load_revision()["instances"][face], load_baseline()["instances"][face]
    else:
        kind = "sources" if source else "compiled"
        current = load_revision()[kind][face]["targets"]
        previous = load_baseline()[kind][face]["targets"]
    assert actual == current[name], (face, name, "Unverified serif outline")
    return previous[name]


def historical_tables(filename, actual):
    before = load_baseline()["tables"][filename]
    expected = {**before, **load_revision()["tables"][filename]}
    assert actual == expected, (filename, "Unverified serif font tables", sorted(
        tag for tag in actual.keys() | expected.keys() if actual.get(tag) != expected.get(tag)))
    return before


def historical_metrics(face, name, actual):
    if not is_revised(face, name):
        return actual
    assert list(actual) == load_revision()["compiled"][face]["targetMetrics"][name], (face, name, "Unverified serif metrics")
    return load_baseline()["compiled"][face]["targetMetrics"][name]


def verify_sources():
    before = load_baseline()
    actual = {path.relative_to(SOURCES).as_posix(): path for path in SOURCES.rglob("*") if path.is_file()}
    assert set(actual) == set(before["sourceFiles"]), "Source file inventory changed"
    for relative, expected in before["sourceFiles"].items():
        assert digest(historical_source_bytes(actual[relative])) == expected, (relative, "Unrelated source bytes changed")
    return len(before["sourceGlyphs"])


def verify_compiled():
    before = load_baseline()
    paths = font_paths(OUTPUT)
    assert {path.name for path in paths} == set(before["tables"])
    for path in paths:
        historical_tables(path.name, normalized_tables(path))
        with TTFont(path) as font:
            assert digest(font.getTableData("cmap")) == before["cmaps"][path.name], (path.name, "Cmap changed")
    actual = capture_geometry(SOURCES, OUTPUT)
    validate_geometry(actual, before)
    current = load_revision()
    assert all(actual[kind] == current[kind] for kind in ("sources", "compiled", "instances")), "Unverified serif geometry"
    return len(paths)


def current_revision():
    before = load_baseline()
    result = {"schemaVersion": 1, "revision": REVISION_ID, "baselineSha256": BASELINE_SHA256,
              "sourceGlyphs": {}, "tables": {}}
    for relative in before["sourceGlyphs"]:
        result["sourceGlyphs"][relative] = digest((ROOT / relative).read_bytes())
        assert result["sourceGlyphs"][relative] != before["sourceGlyphs"][relative]["sha256"], relative
    actual_files = {path.relative_to(SOURCES).as_posix(): path for path in SOURCES.rglob("*") if path.is_file()}
    assert set(actual_files) == set(before["sourceFiles"])
    revised_files = {Path(relative).relative_to("fonts/QuintessentialSerif").as_posix() for relative in before["sourceGlyphs"]}
    for relative, expected in before["sourceFiles"].items():
        if relative not in revised_files:
            assert digest(actual_files[relative].read_bytes()) == expected, (relative, "Unrelated source bytes changed")
    paths = font_paths(OUTPUT)
    assert {path.name for path in paths} == set(before["tables"])
    for path in paths:
        old, current = before["tables"][path.name], normalized_tables(path)
        assert set(current) == set(old)
        changes = {tag: value for tag, value in current.items() if value != old[tag]}
        assert set(changes) <= REVISED_TABLES, (path.name, changes)
        assert bool(changes) == ("Italic" not in path.name), (path.name, "Wrong posture changed")
        result["tables"][path.name] = changes
        with TTFont(path) as font:
            assert digest(font.getTableData("cmap")) == before["cmaps"][path.name], path.name
    result.update(capture_geometry(SOURCES, OUTPUT))
    validate_geometry(result, before)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-from", type=Path)
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    assert sum((bool(args.capture_from), args.seal, args.verify)) == 1, "Choose one operation"
    if args.capture_from:
        assert not BASELINE.exists(), "Refusing to overwrite frozen baseline"
        data = gzip.compress(json.dumps(capture(args.capture_from), sort_keys=True, separators=(",", ":")).encode(), mtime=0)
        BASELINE.write_bytes(data)
    elif args.seal:
        assert not REVISION.exists(), "Refusing to overwrite sealed revision"
        data = (json.dumps(current_revision(), sort_keys=True, indent=2) + "\n").encode()
        REVISION.write_bytes(data)
    else:
        print(f"Verified {verify_sources()} target sources and {verify_compiled()} compiled fonts.")
        return
    print(digest(data))


if __name__ == "__main__":
    main()

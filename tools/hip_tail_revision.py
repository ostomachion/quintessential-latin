"""Pinned evidence for the two hip-tail edits, composed with older revisions.

Historical data is recovered only after the current bytes or outline/metric
record matches this revision's independently frozen replacement evidence.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import re

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "resources/provenance/hip-tail-baseline.json.gz"
REVISION = ROOT / "resources/provenance/hip-tail-revision.json"
BASELINE_SHA256 = "0dd0cca1378ea9b50b70c43b73adf42b63a40f65ea2a11f38126fa261f97fe20"
REVISION_SHA256 = "88c7b33d3d611adfdc39177e1faefbfe9d4304029c93d7fa4dc170188d8ea018"
TARGET_IDS = frozenset(("turned-arm-tail", "turned-arm-ascender-tail"))
TARGET_NAMES = frozenset(("uF2A13", "uF2A14"))
# The focused suite separately proves that every unrelated outline and pair
# survives; these are the only tables permitted to encode the approved edit.
REVISED_TABLES = frozenset(("glyf", "loca", "gvar", "CFF ", "hmtx", "GPOS", "GDEF", "head", "hhea"))
WIDER_GLOBAL_MINIMUM = frozenset(("QuintessentialSerif-Regular.otf", "QuintessentialSerif-Regular.woff2",
                                 "QuintessentialSerif-Variable.ttf", "QuintessentialSerif-Variable.woff2"))
KERN_BLOCK = re.compile(rb'(?m)^\t<key>([^<]+)</key>\n\t<dict>\n(.*?)\t</dict>', re.S)
KERN_PAIR = re.compile(rb'(<key>([^<]+)</key>\n\t\t<integer>)(-?\d+)(</integer>)')


def target_source_pairs(data):
    result = {}
    for block in KERN_BLOCK.finditer(data):
        left = block[1].decode()
        for pair in KERN_PAIR.finditer(block[2]):
            right = pair[2].decode()
            if left in TARGET_NAMES or right in TARGET_NAMES:
                result[f"{left}/{right}"] = int(pair[3])
    assert len(result) == 4860, len(result)
    return result


def restore_kerning_bytes(data, old):
    def restore_block(block):
        left = block[1].decode()
        def restore_pair(pair):
            key = f"{left}/{pair[2].decode()}"
            return pair[1] + str(old["pairs"][key]).encode() + pair[4] if key in old["pairs"] else pair[0]
        return block[0].replace(block[2], KERN_PAIR.sub(restore_pair, block[2]), 1)
    data = KERN_BLOCK.sub(restore_block, data)
    assert digest(data) == old["sha256"], "Unrelated pair or kerning formatting changed"
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def load_baseline():
    data = BASELINE.read_bytes()
    assert digest(data) == BASELINE_SHA256, "The frozen pre-hip-tail baseline changed"
    result = json.loads(gzip.decompress(data))
    assert result["revision"] == "hip-wide-tail-1"
    assert set(result["glyphIds"]) == TARGET_IDS
    assert len(result["sourceGlyphs"]) == 8
    for relative, captured in result["sourceGlyphs"].items():
        assert digest(base64.b64decode(captured["base64"])) == captured["sha256"], relative
    return result


@lru_cache(maxsize=1)
def load_revision():
    data = REVISION.read_bytes()
    assert digest(data) == REVISION_SHA256, "The verified hip-tail revision changed"
    result = json.loads(data)
    baseline = load_baseline()
    assert result["schemaVersion"] == 1 and result["revision"] == "hip-wide-tail-1"
    assert result["baselineSha256"] == BASELINE_SHA256
    assert set(result["glyphIds"]) == TARGET_IDS
    assert set(result["sourceGlyphs"]) == set(baseline["sourceGlyphs"])
    assert set(result["tables"]) == set(baseline["tables"])
    assert set(result["kerning"]) == set(baseline["kerning"]) and len(result["kerning"]) == 4
    assert set(result["instances"]) == set(baseline["instances"])
    assert set(result["geometry"]) == {f"source-{style}" for style in baseline["sources"]} | set(baseline["compiled"])
    for relative, value in result["sourceGlyphs"].items():
        assert value != baseline["sourceGlyphs"][relative]["sha256"], relative
    for filename, changes in result["tables"].items():
        assert changes and set(changes) <= REVISED_TABLES, (filename, "Unrelated table authorized")
        assert all(value != baseline["tables"][filename][tag] for tag, value in changes.items())
        assert set(changes) & {"head", "hhea"} == ({"head", "hhea"} if filename in WIDER_GLOBAL_MINIMUM else set()), filename
    return result


def historical_source_bytes(path, data=None):
    path = Path(path)
    data = path.read_bytes() if data is None else data
    relative = path.relative_to(ROOT).as_posix()
    if relative in load_baseline()["kerning"]:
        old = load_baseline()["kerning"][relative]
        assert digest(data) == load_revision()["kerning"][relative], (relative, "Unverified hip-tail kerning")
        return restore_kerning_bytes(data, old)
    captured = load_baseline()["sourceGlyphs"].get(relative)
    if captured is None:
        return data
    assert digest(data) == load_revision()["sourceGlyphs"][relative], (relative, "Unverified hip-tail source")
    return base64.b64decode(captured["base64"])


def historical_outline(face, name, actual, *, source=False, instantiated=False):
    if name not in TARGET_NAMES:
        return actual
    if instantiated:
        assert actual == load_revision()["instances"][face][name], (face, name, "Unverified instantiated hip-tail outline")
        return load_baseline()["instances"][face][name]
    key = f"source-{face}" if source else face
    assert actual == load_revision()["geometry"][key][name]["outline"], (key, name, "Unverified hip-tail outline")
    return load_baseline()["sources" if source else "compiled"][face]["outlines"][name]


def historical_metrics(face, name, actual):
    if name not in TARGET_NAMES:
        return actual
    assert list(actual) == load_revision()["geometry"][face][name]["metrics"], (face, name, "Unverified hip-tail metrics")
    return load_baseline()["compiled"][face]["hmtx"][name]


def historical_tables(filename, actual):
    before = load_baseline()["tables"][filename]
    expected = {**before, **load_revision()["tables"][filename]}
    assert actual == expected, (filename, "Unverified hip-tail compiled table", sorted(
        tag for tag in actual.keys() | expected.keys() if actual.get(tag) != expected.get(tag)))
    verify_aggregate_metrics(ROOT / "resources/fonts/QuintessentialSerif" / filename)
    return before


def verify_aggregate_metrics(path):
    """Only the actual new Roman tail may lower the two aggregate minima."""
    if path.name not in WIDER_GLOBAL_MINIMUM:
        return
    with TTFont(path, recalcTimestamp=False) as font:
        assert font["head"].xMin == font["hhea"].minLeftSideBearing == -106, path.name
        assert min(value[1] for value in font["hmtx"].metrics.values()) == -106, path.name
        assert min(font["hmtx"][name][1] for name in TARGET_NAMES) == -106, path.name
        font.recalcBBoxes = False
        font["head"].fontRevision = 0
        font["head"].checkSumAdjustment = 0
        font["head"].xMin = font["hhea"].minLeftSideBearing = -104
        before = load_baseline()["tables"][path.name]
        for tag in ("head", "hhea"):
            assert digest(font.getTableData(tag)) == before[tag], (path.name, tag, "Aggregate metadata changed beyond tail minimum")


def verify_sources():
    revision = load_revision()
    for relative, expected in revision["sourceGlyphs"].items():
        assert digest((ROOT / relative).read_bytes()) == expected, relative
    for relative in revision["kerning"]:
        historical_source_bytes(ROOT / relative)
    return len(revision["sourceGlyphs"])


def historical_pairs(pairs, face, *, source=False):
    """Validate current target values, then restore only those pair adjustments."""
    key = f"source-{face}" if source else face
    current = load_revision()["geometry"][key]["pairs"]
    old = load_baseline()["targetPairs"][key]
    result = dict(pairs)
    for encoded in current.keys() | old.keys():
        expected = current.get(encoded, 0)
        left, right = encoded.split("/")
        actual = pairs.get((left, right), 0 if source else (0,) * 8)
        expected_value = expected if source else [0, 0, expected, 0, 0, 0, 0, 0]
        assert (actual if source else list(actual)) == expected_value, (key, left, right, "Unverified target pair")
        value = old.get(encoded, 0)
        result[left, right] = value if source else (0, 0, value, 0, 0, 0, 0, 0)
    return result


def historical_source_pairs(source):
    return historical_pairs(source.kerning, source.info.styleName.replace(" ", ""), source=True)


def historical_pair_tables(face, actual):
    filename = "QuintessentialSerif-Italic-Variable.ttf" if face.startswith("Italic-") else "QuintessentialSerif-Variable.ttf"
    expected = {**load_baseline()["tables"][filename], **load_revision()["tables"][filename]}
    tags = load_baseline()["compiled"][face]["pairTables"]
    assert actual == {tag: expected[tag] for tag in tags}, (face, "Unverified positioning tables")
    return load_baseline()["compiled"][face]["pairTables"]


def compiled_face(font):
    if "CFF " in font:
        return font["name"].getDebugName(2).replace(" ", "")
    return f"{'Italic' if font['post'].italicAngle else 'Roman'}-{font['OS/2'].usWeightClass}"


def normalized_tables(path):
    """Same version normalization as the original allocation preservation layer."""
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
        return {tag: digest(font.getTableData(tag)) for tag in sorted(font.keys()) if tag not in ("GlyphOrder", "cmap")}

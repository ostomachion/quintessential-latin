"""Validate the narrowly authorized three-glyph terminal revision.

The frozen pre-revision sources bridge older preservation tests. Replacement
hashes are pinned separately, so restoring historical bytes never exempts a
current outline or a compiled table from verification.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "resources/provenance/stemless-terminals-baseline.json.gz"
BASELINE_SHA256 = "e601e172e59cf2e778fdca3156c4f34f225dd7fb205ed11ebeb5eb0ffcb6505a"
REVISION = ROOT / "resources/provenance/stemless-terminals-revision.json"
GEOMETRY_BASELINE = ROOT / "resources/provenance/stemless-terminals-geometry-baseline.json.gz"
# Frozen after the completed outlines and all unrelated glyphs were verified.
REVISION_SHA256 = "f85068ce50ca15c2537324152cc1f897562a7d2693d6b04c0f4dde6ba2e9df76"
GLYPH_IDS = frozenset(("special-spine", "special-turned-open-bowl",
                       "special-turned-double-open-bowl"))
# Only these five tables changed in the verified build. Edited ink bounds
# change target left sidebearings in hmtx; all advances, non-target metrics,
# and aggregate extrema remain unchanged.
OUTLINE_TABLES = frozenset(("glyf", "loca", "gvar", "CFF ", "hmtx"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def load_baseline():
    data = BASELINE.read_bytes()
    assert digest(data) == BASELINE_SHA256, "The frozen stemless-terminal baseline changed"
    result = json.loads(gzip.decompress(data))
    assert result["schemaVersion"] == 1 and result["version"] == "0.250"
    assert set(result["glyphIds"]) == GLYPH_IDS
    assert len(result["sourceGlyphs"]) == 12
    assert len(result["compiled"]) == 12
    counts = {identity: 0 for identity in GLYPH_IDS}
    for relative, captured in result["sourceGlyphs"].items():
        assert relative.startswith("fonts/QuintessentialSerif/") and relative.endswith(".glif"), relative
        counts[captured["glyphId"]] += 1
        assert digest(base64.b64decode(captured["base64"])) == captured["sha256"], relative
    assert set(counts.values()) == {4}, counts
    return result


@lru_cache(maxsize=1)
def load_revision():
    data = REVISION.read_bytes()
    assert digest(data) == REVISION_SHA256, "The verified stemless-terminal revision changed"
    result = json.loads(data)
    baseline = load_baseline()
    assert result["schemaVersion"] == 1 and result["version"] == "0.250"
    assert result["baselineSha256"] == BASELINE_SHA256
    assert digest(GEOMETRY_BASELINE.read_bytes()) == result["geometryBaselineSha256"], "Terminal geometry evidence changed"
    assert set(result["glyphIds"]) == GLYPH_IDS
    assert set(result["sourceGlyphs"]) == set(baseline["sourceGlyphs"])
    assert set(result["compiled"]) == set(baseline["compiled"])
    for relative, expected in result["sourceGlyphs"].items():
        assert expected != baseline["sourceGlyphs"][relative]["sha256"], (relative, "Terminal revision was omitted")
    for filename, changes in result["compiled"].items():
        assert changes and set(changes) <= OUTLINE_TABLES, (filename, "Unrelated compiled table authorized")
        assert set(changes) <= set(baseline["compiled"][filename]["normalizedTables"]), (filename, "Compiled table inventory changed")
        assert all(value != baseline["compiled"][filename]["normalizedTables"].get(tag)
                   for tag, value in changes.items()), (filename, "Unchanged table listed as revised")
    return result


def historical_source_bytes(path, data=None):
    """Restore only a SHA-verified revised target to its frozen source bytes."""
    path = Path(path)
    data = path.read_bytes() if data is None else data
    relative = path.relative_to(ROOT).as_posix()
    captured = load_baseline()["sourceGlyphs"].get(relative)
    if captured is None:
        return data
    expected = load_revision()["sourceGlyphs"][relative]
    assert digest(data) == expected, (relative, "Source differs from verified terminal revision")
    return base64.b64decode(captured["base64"])


def verify_sources():
    """Require the complete twelve-source revision and its preserved advances."""
    revision = load_revision()
    for relative, expected in revision["sourceGlyphs"].items():
        assert digest((ROOT / relative).read_bytes()) == expected, (relative, "Wrong terminal revision source")
    return len(revision["sourceGlyphs"])


def verify_compiled_tables(filename, actual, historical):
    """Verify every normalized table against old evidence or a pinned change."""
    before = load_baseline()["compiled"][filename]["normalizedTables"]
    assert before == historical, (filename, "Pre-terminal font differs from historical encoding baseline")
    changes = load_revision()["compiled"][filename]
    expected = {**before, **changes}
    assert actual == expected, (filename, "A table differs from the verified terminal revision",
                               sorted(tag for tag in actual.keys() | expected.keys()
                                      if actual.get(tag) != expected.get(tag)))

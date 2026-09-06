"""Verify extraction preservation and the explicitly scoped Roman revisions."""

from pathlib import Path
import hashlib
import json
import plistlib
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
REVISION = ROOT / "resources/provenance/f2b18-optical-revision.json"
SHARED_REVISION = ROOT / "resources/provenance/shared-spine-optical-revision.json"
REVISED_SOURCES = {
    f"fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/glyphs/uF_2B_1C_.glif": width
    for style, width in (("Regular", 526), ("Bold", 569))
}
REVISED_BINARIES = {
    f"QuintessentialSerif-{style}.{suffix}"
    for style, suffixes in (("Variable", ("ttf", "woff2")),
                            ("Regular", ("otf", "woff2")),
                            ("Bold", ("otf", "woff2")))
    for suffix in suffixes
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision_hashes(record):
    """An additive record may authorize only the two named Roman outlines."""
    if not REVISION.exists():
        return {}, {}
    revision = json.loads(REVISION.read_text(encoding="utf-8"))
    sources, outputs = revision["sources"], revision["outputs"]
    assert set(sources) == set(REVISED_SOURCES), "Revision must name exactly the two U+F2B18 masters"
    assert set(outputs) <= REVISED_BINARIES <= set(record["fontBinaries"]), "Revision may change only Roman font outputs"
    for name, digest in [*sources.items(), *outputs.items()]:
        assert isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), name
    for name, width in REVISED_SOURCES.items():
        glyph = ET.parse(ROOT / name).getroot()
        assert glyph.tag == "glyph" and glyph.get("name") == "uF2B1C", name
        assert [int(item.get("hex"), 16) for item in glyph.findall("unicode")] == [0xF2B18], name
        assert float(glyph.find("advance").get("width")) == width, (name, "advance changed")
        library = plistlib.loads(b"<plist>" + ET.tostring(glyph.find("lib/dict")) + b"</plist>")
        construction = library["org.quintessential.construction"]
        assert construction["glyphId"] == "opposed-bowls-0-0", name
        assert construction["recipeCodePoint"] == 0xF2B1C, name
        assert construction["family"] == "opposed-bowls", name
        assert (construction["leftVariant"], construction["rightVariant"]) == (0, 0), name
        assert construction["advanceWidth"] == width, (name, "recorded advance changed")
    return sources, outputs


def shared_spine_identities(record):
    """Use immutable captured recipe identities, independently of build code."""
    entries = [entry for entry in record["identities"]
               if entry["recipeCodePoint"] is not None
               if any(first <= entry["recipeCodePoint"] <= last
                      for first, last in ((0xF2B1C, 0xF2B3F), (0xF2B58, 0xF2B9F),
                                          (0xF2C54, 0xF2CBF)))]
    assert len(entries) == 396, "Shared-spine revision must cover exactly 396 identities"
    assert sum(entry["middleLegs"] for entry in entries) == 180
    assert all(entry["postures"] == ["Roman"] for entry in entries)
    return entries


def shared_revision_hashes(record):
    if not SHARED_REVISION.exists():
        return {}, {}
    revision = json.loads(SHARED_REVISION.read_text(encoding="utf-8"))
    assert revision["revision"] == "shared-spine-2"
    assert revision["opticalDesign"] == "compact-spine-3"
    assert revision["connectionDesign"] == "shared-spine-joins-1"
    assert revision["connectionReviewBoundariesSha256"] == sha(ROOT / "tools/reviewed_spine_connections.py")
    assert revision["previousRevisionSha256"] == sha(REVISION), "Historical U+F2B18 revision changed"
    entries = shared_spine_identities(record)
    sources, outputs = revision["sources"], revision["outputs"]
    assert set(outputs) == REVISED_BINARIES, "Shared-spine revision must record exactly six Roman outputs"
    for name, digest in [*sources.items(), *outputs.items()]:
        assert isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), name
    expected = {}
    for style in ("Regular", "Bold"):
        folder = ROOT / f"fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/glyphs"
        contents_path = folder / "contents.plist"
        assert sha(contents_path) == record["fontSources"][contents_path.relative_to(ROOT).as_posix()]
        contents = plistlib.loads(contents_path.read_bytes())
        baseline = ROOT / f"tests/baselines/0.210/fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/glyphs"
        baseline_contents = plistlib.loads((baseline / "contents.plist").read_bytes())
        for entry in entries:
            name = (folder / contents[entry["glyphName"]]).relative_to(ROOT).as_posix()
            assert name in record["fontSources"], name
            expected[name] = entry
            glyph = ET.parse(ROOT / name).getroot()
            assert glyph.tag == "glyph" and glyph.get("name") == entry["glyphName"], name
            assert [int(item.get("hex"), 16) for item in glyph.findall("unicode")] == [entry["codePoint"]], name
            # Every middle-leg companion keeps its historical parent's advance;
            # width is not an optical exception for any of these 396 identities.
            reference = ET.parse(baseline / baseline_contents[f"u{entry['recipeCodePoint']:X}"]).getroot()
            width = float(reference.find("advance").get("width"))
            assert float(glyph.find("advance").get("width")) == width, (name, "advance changed")
            library = plistlib.loads(b"<plist>" + ET.tostring(glyph.find("lib/dict")) + b"</plist>")
            construction = library["org.quintessential.construction"]
            assert construction["glyphId"] == entry["glyphId"], name
            assert construction["recipeCodePoint"] == entry["recipeCodePoint"], name
            assert construction["advanceWidth"] == width, (name, "recorded advance changed")
            assert construction.get("opticalRevision"), (name, "missing optical revision")
            if construction.get("joinedLower") == "hook":
                assert construction["lowerClosureDesign"] == "shaft-tangent-native-quarter-return", name
                assert "lowerClosureOuterAnchor" in construction and "lowerClosureInnerAnchor" in construction, name
            if entry["recipeCodePoint"] >= 0xF2B58:
                assert construction["archSpineJoinDesign"] == "native-quadratic-continuation-1", name
                assert construction["archSpineJoinCoordinateFrame"] == "sigmoid-source; add sigmoidOffsetX", name
            if entry["middleLegs"]:
                assert construction["middleLegs"] == "extended", name
    assert len(expected) == 792
    assert set(sources) == set(expected), "Shared-spine revision may name only the 792 eligible Roman GLIFs"
    return sources, outputs


def verify():
    record = json.loads((ROOT / "resources/provenance/extraction-preservation.json").read_text(encoding="utf-8"))
    revised_sources, revised_outputs = revision_hashes(record)
    shared_sources, shared_outputs = shared_revision_hashes(record)
    revised_sources = {**revised_sources, **shared_sources}
    revised_outputs = {**revised_outputs, **shared_outputs}
    for name, digest in record["fontSources"].items():
        assert sha(ROOT / name) == revised_sources.get(name, digest), name
    for name, digest in record["fontBinaries"].items():
        assert sha(ROOT / "resources/fonts/QuintessentialSerif" / name) == revised_outputs.get(name, digest), name
    for name, digest in record["donors"].items():
        assert sha(ROOT / "resources/fonts/STIXTwoText" / name) == digest, name
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    assert allocation["displayOrder"] == record["displayOrder"]
    assert len(allocation["entries"]) == len(record["identities"]) == 832
    for current, before in zip(allocation["entries"], record["identities"]):
        assert all(current[key] == value for key, value in before.items()), before["glyphId"]
        assert not any(key in current for key in ("model", "language", "role"))
    return {
        "sourceFiles": len(record["fontSources"]),
        "fontBinaries": len(record["fontBinaries"]),
        "identities": 832,
        "revisedSourceFiles": len(revised_sources),
        "sharedSpineGlyphs": len(shared_sources) // 2,
        "status": "passed",
    }


if __name__ == "__main__":
    print(json.dumps(verify()))

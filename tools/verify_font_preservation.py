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
MIDDLE_REVISION = ROOT / "resources/provenance/independent-middle-legs.json"
# All eight captured maps were compared semantically with git-show source
# plists at pre-completion commit 9929622ca28427b6e637efd416f9ececc2adfe1d.
# Pin their canonical values independently of mutable completion-file hashes.
PREVIOUS_ITALIC_METADATA_SHA256 = "de43e80a0c6a8834c9e5658841b764b86c2f2fa7e6e2fa7bde89ecd82ebd1551"
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


def independent_middle_revision():
    if not MIDDLE_REVISION.exists():
        return None
    revision = json.loads(MIDDLE_REVISION.read_text(encoding="utf-8"))
    assert revision["version"] == "0.240" and revision["addedGlyphsPerPosture"] == 384
    assert revision["baselineSha256"] == "4a6cbca062740f26cdefbc0a8399ceca8f2f707af6f4ecf159be7959d72997b8"
    assert revision["baselineSha256"] == sha(ROOT / "resources/provenance/independent-middle-legs-baseline.json.gz")
    captured = json.dumps(revision["previousMetadata"], sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(captured).hexdigest() == "22a6d789e52aecf190d02146244ecd25e5f42be126c7b495d9f6be0fdb7aff0e"
    allowed = {f"fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/{filename}"
               for style in ("Regular", "Bold", "Italic", "BoldItalic")
               for filename in ("fontinfo.plist", "lib.plist", "kerning.plist", "glyphs/contents.plist")}
    assert set(revision["previousSources"]) == set(revision["sources"]) == allowed
    assert set(revision["previousMetadata"]) == {name for name in allowed if not name.endswith("kerning.plist")}
    for name, before in revision["previousMetadata"].items():
        after = plistlib.loads((ROOT / name).read_bytes())
        if name.endswith("fontinfo.plist"):
            expected = {**before, "versionMinor": 240, "openTypeNameVersion": "Version 0.240",
                        "openTypeNameUniqueID": before["openTypeNameUniqueID"].replace("0.230", "0.240")}
            assert after == expected, name
        elif name.endswith("contents.plist"):
            assert all(after[key] == value for key, value in before.items()), name
            assert len(after) == len(before) + 384, name
        else:
            assert after["public.glyphOrder"][:len(before["public.glyphOrder"])] == before["public.glyphOrder"], name
            assert len(after["public.glyphOrder"]) == len(before["public.glyphOrder"]) + 384, name
            assert {k: v for k, v in after.items() if k != "public.glyphOrder"} == {k: v for k, v in before.items() if k != "public.glyphOrder"}, name
    assert revision["fontManifestSha256"] == sha(ROOT / "resources/fonts/QuintessentialSerif/build-manifest.json")
    for name, expected in revision["sources"].items():
        assert sha(ROOT / name) == expected, name
    return revision


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


def shared_revision_hashes(record, middle=None):
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
        relative_contents = contents_path.relative_to(ROOT).as_posix()
        captured_hash = middle["previousSources"][relative_contents] if middle else sha(contents_path)
        assert captured_hash == record["fontSources"][relative_contents]
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
    middle = independent_middle_revision()
    revised_sources, revised_outputs = revision_hashes(record)
    shared_sources, shared_outputs = shared_revision_hashes(record, middle)
    revised_sources = {**revised_sources, **shared_sources}
    revised_outputs = {**revised_outputs, **shared_outputs}
    completion_path = ROOT / "resources/provenance/italic-completion.json"
    if completion_path.exists():
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        assert completion["version"] == "0.230" and completion["addedItalicGlyphs"] == 600
        assert completion["baselineSha256"] == sha(ROOT / "resources/provenance/italic-completion-baseline.json.gz")
        assert completion["baselineSha256"] == "52289d17a64771b131661d5d64646fcd90377c3975592843f39549818a8d5940"
        allowed = {f"fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/{filename}"
                   for style in ("Regular", "Bold", "Italic", "BoldItalic")
                   for filename in (("fontinfo.plist", "lib.plist", "kerning.plist", "glyphs/contents.plist")
                                    if "Italic" in style else ("fontinfo.plist",))}
        assert set(completion["sources"]) == allowed
        assert set(completion["outputs"]) == set(record["fontBinaries"])
        assert set(completion["previousMetadata"]) == {name for name in allowed if not name.endswith("kerning.plist")}
        previous_metadata = json.dumps(completion["previousMetadata"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        assert hashlib.sha256(previous_metadata).hexdigest() == PREVIOUS_ITALIC_METADATA_SHA256, "Captured pre-completion metadata changed"
        for name, before in completion["previousMetadata"].items():
            assert name in allowed and not name.endswith("kerning.plist")
            after = middle["previousMetadata"][name] if middle else plistlib.loads((ROOT / name).read_bytes())
            if name.endswith("fontinfo.plist"):
                expected = {**before, "versionMinor": 230, "openTypeNameVersion": "Version 0.230",
                            "openTypeNameUniqueID": before["openTypeNameUniqueID"].replace("0.220", "0.230")}
                assert after == expected, name
            elif name.endswith("contents.plist"):
                assert all(after[key] == value for key, value in before.items()), name
                assert len(after) == len(before) + 600, name
            else:
                assert after["public.glyphOrder"][:len(before["public.glyphOrder"])] == before["public.glyphOrder"], name
                assert {key: value for key, value in after.items() if key != "public.glyphOrder"} == {key: value for key, value in before.items() if key != "public.glyphOrder"}, name
        added_entries = [entry for entry in record["identities"] if "Italic" not in entry["postures"]]
        assert len(added_entries) == 600
        expected_additions = set()
        for style in ("Italic", "BoldItalic"):
            folder = ROOT / f"fonts/QuintessentialSerif/QuintessentialSerif-{style}.ufo/glyphs"
            contents = plistlib.loads((folder / "contents.plist").read_bytes())
            for entry in added_entries:
                path = folder / contents[entry["glyphName"]]
                name = path.relative_to(ROOT).as_posix()
                expected_additions.add(name)
                glyph = ET.parse(path).getroot()
                assert glyph.tag == "glyph" and glyph.get("name") == entry["glyphName"], name
                assert [int(item.get("hex"), 16) for item in glyph.findall("unicode")] == [entry["codePoint"]], name
        assert len(expected_additions) == 1200
        assert set(completion["addedSources"]) == expected_additions, "Completion must record exactly the 1,200 added Italic GLIFs"
        for name, digest in completion["addedSources"].items():
            assert isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), name
            assert sha(ROOT / name) == digest, name
        assert completion["fontManifestSha256"] == (middle["previousFontManifestSha256"] if middle else sha(ROOT / "resources/fonts/QuintessentialSerif/build-manifest.json")), "Completion font manifest changed"
        revised_sources.update(completion["sources"])
        revised_outputs.update(completion["outputs"])
    if middle:
        assert set(middle["outputs"]) == set(record["fontBinaries"])
        revised_sources.update(middle["sources"])
        revised_outputs.update(middle["outputs"])
    for name, digest in record["fontSources"].items():
        assert sha(ROOT / name) == revised_sources.get(name, digest), name
    for name, digest in record["fontBinaries"].items():
        assert sha(ROOT / "resources/fonts/QuintessentialSerif" / name) == revised_outputs.get(name, digest), name
    for name, digest in record["donors"].items():
        assert sha(ROOT / "resources/fonts/STIXTwoText" / name) == digest, name
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    old_ids = {entry["glyphId"] for entry in record["identities"]}
    assert [identity for identity in allocation["displayOrder"] if identity in old_ids] == record["displayOrder"]
    assert len(record["identities"]) == 832
    assert len(allocation["entries"]) == (1216 if middle else 832)
    for current, before in zip(allocation["entries"], record["identities"]):
        assert all(current[key] == value for key, value in before.items() if key != "postures"), before["glyphId"]
        assert current["postures"] == ["Roman", "Italic"], before["glyphId"]
        assert not any(key in current for key in ("model", "language", "role"))
    return {
        "sourceFiles": len(record["fontSources"]),
        "fontBinaries": len(record["fontBinaries"]),
        "identities": 832,
        "independentMiddleAdditions": 384 if middle else 0,
        "revisedSourceFiles": len(revised_sources),
        "sharedSpineGlyphs": len(shared_sources) // 2,
        "status": "passed",
    }


if __name__ == "__main__":
    print(json.dumps(verify()))

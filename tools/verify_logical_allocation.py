#!/usr/bin/env python3
"""Verify the 0.250 encoding migration against immutable 0.240 font data.

Recipe identities and internal order remain fixed. The separately pinned
three-glyph terminal and two-glyph hip-tail revisions are validated before
older regression suites recover their original bytes and Unicode tokens.
Hip-tail pair changes and the exact Roman minimum-bound update have their own
independent preservation evidence. All remaining bytes and tables stay fixed.
Character names may only gain SMALL before LETTER; structural names and
internal glyph names remain identical to the captured allocation.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct

from fontTools.ttLib import TTFont

import stemless_terminal_revision as terminal_revision
import hip_tail_revision


ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "resources/provenance/logical-allocation-baseline.json.gz"
BASELINE_SHA256 = "133d2a67e5ec3ae65f6d50f4ccd87187a27a172c818dca7ad720dc7a4c195197"
ALLOCATION = ROOT / "resources/quintessential-latin-allocation.json"
OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
ENCODING_FIELDS = frozenset(("codePoint", "blockId", "familyId"))
UNICODE_TOKEN = re.compile(rb'(<unicode\s+hex=")[0-9a-fA-F]+("\s*/>)')
# Raw tables read from all twelve 0.240 binaries after verifying their full
# file hashes against BASELINE. All six formats per posture share one table.
PREVIOUS_CMAP_SHA256 = {
    False: "9ae8a0b387b28e8dd26cd3009be9fcc5378b3980cc63999328c8092ffb70803c",
    True: "82843e8f0876256f07fdf430a81b5e387c283fef67ce8f5ac801d1f7b3483a13",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def load_baseline():
    data = BASELINE.read_bytes()
    assert digest(data) == BASELINE_SHA256, "The immutable 0.240 allocation baseline changed"
    result = json.loads(gzip.decompress(data))
    assert result["schemaVersion"] == 1 and result["version"] == "0.240"
    assert len(result["allocation"]["entries"]) == 1216
    return result


@lru_cache(maxsize=1)
def migration_active():
    return json.loads(ALLOCATION.read_text(encoding="utf-8"))["version"] == "0.250"


@lru_cache(maxsize=1)
def baseline_entries():
    return {entry["glyphId"]: entry for entry in load_baseline()["allocation"]["entries"]}


def historical_entry(entry):
    """Validate the lowercase prefix, then restore old names and encoding only."""
    if not migration_active():
        return entry
    before = baseline_entries()[entry["glyphId"]]
    prefix = "QUINTESSENTIAL LATIN LETTER "
    assert before["name"].startswith(prefix), entry["glyphId"]
    expected_name = "QUINTESSENTIAL LATIN SMALL LETTER " + before["name"][len(prefix):]
    assert entry["name"] == expected_name, (entry["glyphId"], "Character name differs beyond the lowercase prefix")
    return {**entry, "name": before["name"], **{key: before[key] for key in ENCODING_FIELDS}}


@lru_cache(maxsize=1)
def active_unicode_map():
    entries = json.loads(ALLOCATION.read_text(encoding="utf-8"))["entries"]
    active = {entry["glyphName"]: [entry["codePoint"]] for entry in entries}
    active.update({".notdef": [], "space": [0x20]})
    return active


def current_unicode_map(captured):
    """Map a historical glyph-name subset to the current sole encoding."""
    active = active_unicode_map()
    return {name: active[name] for name in captured}


def expected_fontinfo(before):
    return {**before, "versionMinor": 250, "openTypeNameVersion": "Version 0.250",
            "openTypeNameUniqueID": before["openTypeNameUniqueID"].replace("0.240", "0.250")}


def historical_source_sha(path):
    """Reconstruct 0.240 bytes after validating the pinned terminal revision."""
    path = Path(path)
    data = path.read_bytes()
    if not migration_active():
        return digest(data)
    data = hip_tail_revision.historical_source_bytes(path, data)
    baseline = load_baseline()
    relative = path.relative_to(ROOT).as_posix()
    if relative in baseline["sourceGlyphs"]:
        data = terminal_revision.historical_source_bytes(path, data)
        captured = baseline["sourceGlyphs"][relative]
        code = 0x20 if captured["glyphName"] == "space" else captured["codePoint"]
        tokens = list(UNICODE_TOKEN.finditer(data))
        assert len(tokens) == int(code is not None), (relative, "Unexpected Unicode alias")
        if captured["glyphId"] is not None:
            data = UNICODE_TOKEN.sub(lambda match: match[1] + f"{code:04X}".encode() + match[2], data)
        actual = digest(data)
        assert actual == captured["sha256"], (relative, "Non-encoding source bytes changed")
        return actual
    if relative.endswith("fontinfo.plist") and relative in baseline["metadata"]:
        assert plistlib.loads(data) == expected_fontinfo(baseline["metadata"][relative]), relative
        return baseline["sources"][relative]
    return digest(data)


def verify_sources():
    baseline = load_baseline()
    before = baseline["allocation"]
    current = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    assert (current["version"], current["previousVersion"]) == ("0.250", "0.240")
    changed_fields = {"version", "previousVersion", "families", "blocks", "displayOrder"}
    assert {key: value for key, value in current.items() if key not in changed_fields | {"entries"}} == {
        key: value for key, value in before.items() if key not in changed_fields | {"entries"}}, "Unrelated allocation metadata changed"
    old_entries, entries = before["entries"], current["entries"]
    assert len(entries) == 1216
    assert [entry["glyphId"] for entry in entries] == [entry["glyphId"] for entry in old_entries], "Internal allocation order changed"
    for old, entry in zip(old_entries, entries):
        assert old == historical_entry(entry), entry["glyphId"]
    by_id = {entry["glyphId"]: entry for entry in entries}
    by_name = {entry["glyphName"]: entry for entry in entries}
    assert len(by_id) == len(by_name) == 1216
    assert sorted(entry["codePoint"] for entry in entries) == list(range(0xF2A00, 0xF2EC0)), "The active allocation has gaps or duplicate code points"
    assert current["displayOrder"] == [entry["glyphId"] for entry in sorted(entries, key=lambda row: row["codePoint"])], "Display order must follow the logical encoding"
    assert [by_id[identity]["glyphId"] for identity in current["displayOrder"][192:196]] == [
        "special-closed-double-bowl", "special-double-open-bowl",
        "special-turned-double-open-bowl", "special-spine"]
    assert [(block["start"], block["end"]) for block in current["blocks"]] == [
        (0xF2A00, 0xF2ABF), (0xF2AC0, 0xF2BBF), (0xF2BC0, 0xF2EBF)]
    for block, count in zip(current["blocks"], (192, 256, 768)):
        members = [entry for entry in entries if entry["blockId"] == block["id"]]
        assert len(members) == count, block["id"]
        assert sorted(entry["codePoint"] for entry in members) == list(range(block["start"], block["end"] + 1))
    old_families = {family["id"]: family for family in before["families"]}
    special_ids = set(current["displayOrder"][192:196])
    for old, entry in zip(old_entries, entries):
        family = old_families[old["familyId"]]
        expected_family = "stemless-double-bowls-and-spine" if entry["glyphId"] in special_ids else family.get("baseFamilyId", family["id"])
        expected_block = "quintessential-latin-abbreviations" if entry["glyphId"] in special_ids else old["blockId"]
        assert (entry["familyId"], entry["blockId"]) == (expected_family, expected_block), entry["glyphId"]
        if entry["baseGlyphId"]:
            parent = by_id[entry["baseGlyphId"]]
            assert parent["familyId"] == entry["familyId"]
            flags = entry.get("middleLegExtensions", [True] * sum(bool(part.get("middle")) for part in entry["parts"]))
            state = sum(int(flag) << index for index, flag in enumerate(flags))
            assert entry["codePoint"] - parent["codePoint"] == state, "Middle states must follow their base in neither/left/right/both order"
    assert len(baseline["sourceGlyphs"]) == 4872
    actual_sources = {path.relative_to(ROOT).as_posix() for path in (ROOT / "fonts/QuintessentialSerif").rglob("*") if path.is_file()}
    assert actual_sources == set(baseline["sources"]), "Editable source inventory changed"
    for relative, captured in baseline["sourceGlyphs"].items():
        path = ROOT / relative
        data = path.read_bytes()
        name = captured["glyphName"]
        code = by_name[name]["codePoint"] if name in by_name else (0x20 if name == "space" else None)
        actual = [int(match[0].split(b'"')[1], 16) for match in UNICODE_TOKEN.finditer(data)]
        assert actual == ([] if code is None else [code]), (relative, "Wrong active Unicode or stale alias")
        historical_source_sha(path)
        if "unicodeFreeSha256" in captured:
            previous_data = terminal_revision.historical_source_bytes(path, hip_tail_revision.historical_source_bytes(path, data))
            assert digest(UNICODE_TOKEN.sub(b"", previous_data)) == captured["unicodeFreeSha256"], relative
    for relative, expected in baseline["sources"].items():
        if relative in baseline["sourceGlyphs"]:
            continue
        assert historical_source_sha(ROOT / relative) == expected, relative
    for relative, expected in baseline.get("provenance", {}).items():
        assert digest((ROOT / relative).read_bytes()) == expected, (relative, "Historical provenance changed")
    revised = terminal_revision.verify_sources()
    hip_sources = hip_tail_revision.verify_sources()
    return {"sourceGlyphs": len(baseline["sourceGlyphs"]), "identities": len(entries),
            "revisedTerminalSources": revised, "revisedHipTailSources": hip_sources, "status": "passed"}


def verify_compiled(filenames=None):
    baseline = load_baseline()
    entries = json.loads(ALLOCATION.read_text(encoding="utf-8"))["entries"]
    expected = {0x20: "space", **{entry["codePoint"]: entry["glyphName"] for entry in entries}}
    assert len(baseline["compiled"]) == 12
    assert {path.name for path in OUTPUT.iterdir() if path.suffix in (".ttf", ".otf", ".woff2")} == set(baseline["compiled"]), "Compiled font inventory changed"
    selected = set(baseline["compiled"]) if filenames is None else set(filenames)
    assert selected and selected <= set(baseline["compiled"])
    for filename, captured in baseline["compiled"].items():
        if filename not in selected:
            continue
        if Path(filename).suffix in (".ttf", ".otf"):
            data = (OUTPUT / filename).read_bytes()
            padded = data + b"\0" * (-len(data) % 4)
            assert sum(word[0] for word in struct.iter_unpack(">I", padded)) & 0xFFFFFFFF == 0xB1B0AFBA, (filename, "Invalid SFNT checksum adjustment")
        with TTFont(OUTPUT / filename, recalcTimestamp=False) as font:
            assert font.getGlyphOrder() == captured["glyphOrder"], (filename, "Internal GID order changed")
            assert font.getBestCmap() == expected, (filename, "Wrong current encoding")
            assert font["head"].fontRevision == 0.25, (filename, "Wrong font revision")
            versions = [record.toUnicode() for record in font["name"].names if record.nameID == 5]
            assert versions and all(value == "Version 0.250" for value in versions), (filename, versions)
            # Verified against all twelve independently SHA-pinned 0.240 fonts.
            assert [(table.platformID, table.platEncID, table.format, table.language)
                    for table in font["cmap"].tables] == [
                (0, 3, 4, 0), (0, 4, 12, 0), (3, 1, 4, 0), (3, 10, 12, 0)], (filename, "Cmap subtable inventory changed")
            for table in font["cmap"].tables:
                if table.isUnicode():
                    wanted = {code: name for code, name in expected.items()
                              if code <= 0xFFFF or table.format in (10, 12, 13)}
                    assert table.cmap == wanted, (filename, table.format, "Unicode subtable retains an alias or omits a glyph")
            old_codes = {name: int(code) for code, name in captured["cmap"].items()}
            for table in font["cmap"].tables:
                table.cmap = {old_codes[name]: name for name in table.cmap.values()}
            assert digest(font["cmap"].compile(font)) == PREVIOUS_CMAP_SHA256["Italic" in filename], (filename, "Cmap bytes changed beyond the assigned code points")
            font["head"].fontRevision = 0
            font["head"].checkSumAdjustment = 0
            for record in font["name"].names:
                value = record.toUnicode()
                assert "0.240" not in value, (filename, "Stale version in naming metadata")
                normalized = re.sub(r"0\.(?:240|250)", "0.000", value) if record.nameID in (3, 5) else value
                if value != normalized:
                    record.string = normalized.encode(record.getEncoding())
            if "CFF " in font:
                for top in font["CFF "].cff.topDictIndex:
                    assert top.version == "0.250", (filename, "Wrong CFF version")
                    top.version = "0.000"
            actual = {tag: digest(font.getTableData(tag)) for tag in sorted(font.keys())
                      if tag not in ("GlyphOrder", "cmap")}
            terminal_revision.verify_compiled_tables(filename, hip_tail_revision.historical_tables(filename, actual), captured["normalizedTables"])
    if selected != set(baseline["compiled"]):
        return len(selected)
    manifest = json.loads((OUTPUT / "build-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.250"
    for filename, captured in manifest["outputs"].items():
        data = (OUTPUT / filename).read_bytes()
        assert digest(data) == captured["sha256"] and len(data) == captured["bytes"], filename
    return len(baseline["compiled"])


def verify(*, sources_only=False):
    result = verify_sources()
    if not sources_only:
        result["compiledFonts"] = verify_compiled()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(sources_only=args.sources_only)))

#!/usr/bin/env python3
"""Pack the catalogue by construction, without changing any drawing or GID.

The captured 0.240 state is immutable. Re-running this migration produces the
same allocation and changes only Unicode tokens and the source font version.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import plistlib
import re
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ALLOCATION = ROOT / "resources/quintessential-latin-allocation.json"
BASELINE = ROOT / "resources/provenance/logical-allocation-baseline.json.gz"
FONT_OUTPUT = ROOT / "resources/fonts/QuintessentialSerif"
SOURCE_ROOT = ROOT / "fonts/QuintessentialSerif"
VERSION = "0.250"
STEMLESS_A = (
    "special-closed-double-bowl", "special-double-open-bowl",
    "special-turned-double-open-bowl", "special-spine",
)
STEMLESS_FAMILY = "stemless-double-bowls-and-spine"
UNICODE_TOKEN = re.compile(rb'<unicode hex="[0-9A-F]+"/>')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compiled_snapshot(path):
    """Compare all font tables with only encoding/version fields normalized."""
    with TTFont(path, recalcTimestamp=False) as font:
        result = {"sha256": sha(path.read_bytes()), "glyphOrder": font.getGlyphOrder(),
                  "cmap": {str(k): v for k, v in font.getBestCmap().items()}}
        font["head"].fontRevision = 0
        font["head"].checkSumAdjustment = 0
        for record in font["name"].names:
            value = record.toUnicode()
            normalized = re.sub(r"0\.(?:240|250)", "0.000", value)
            if normalized != value:
                record.string = normalized.encode(record.getEncoding())
        if "CFF " in font:
            for top in font["CFF "].cff.topDictIndex:
                top.version = "0.000"
        result["normalizedTables"] = {
            tag: sha(font.getTableData(tag)) for tag in sorted(font.keys())
            if tag not in ("GlyphOrder", "cmap")
        }
        return result


def capture():
    if BASELINE.exists():
        raise SystemExit("The immutable 0.240 baseline already exists")
    allocation = json.loads(ALLOCATION.read_bytes())
    assert allocation["version"] == "0.240"
    by_name = {entry["glyphName"]: entry for entry in allocation["entries"]}
    manifest_path = FONT_OUTPUT / "build-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest["version"] == "0.240"
    snapshot = {"schemaVersion": 1, "version": "0.240", "allocation": allocation,
                "allocationSha256": sha(ALLOCATION.read_bytes()), "manifest": manifest,
                "manifestSha256": sha(manifest_path.read_bytes()), "sources": {},
                "metadata": {}, "sourceGlyphs": {}, "compiled": {}, "provenance": {}}
    for path in sorted(SOURCE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative, data = path.relative_to(ROOT).as_posix(), path.read_bytes()
        snapshot["sources"][relative] = sha(data)
        if path.name in ("fontinfo.plist", "lib.plist", "contents.plist"):
            snapshot["metadata"][relative] = plistlib.loads(data)
        if path.suffix == ".glif":
            name = re.search(rb'<glyph name="([^"]+)"', data).group(1).decode()
            entry = by_name.get(name)
            snapshot["sourceGlyphs"][relative] = {
                "glyphName": name, "glyphId": entry["glyphId"] if entry else None,
                "codePoint": entry["codePoint"] if entry else None,
                "sha256": sha(data), "unicodeFreeSha256": sha(UNICODE_TOKEN.sub(b"", data)),
            }
    for path in sorted(FONT_OUTPUT.iterdir()):
        if path.suffix in (".ttf", ".otf", ".woff2"):
            snapshot["compiled"][path.name] = compiled_snapshot(path)
    for path in sorted((ROOT / "resources/provenance").glob("*.json")):
        snapshot["provenance"][path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    BASELINE.write_bytes(gzip.compress(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode(), mtime=0))
    print(f"Captured {len(snapshot['sourceGlyphs'])} GLIFs and {len(snapshot['compiled'])} fonts: {sha(BASELINE.read_bytes())}")


def create_allocation(before):
    result = copy.deepcopy(before)
    result.update(version=VERSION, previousVersion=before["version"])
    by_id = {entry["glyphId"]: entry for entry in result["entries"]}
    old_families = {family["id"]: family for family in before["families"]}
    families = []
    for family in before["families"]:
        if family.get("baseFamilyId"):
            continue
        if family["id"] == "double-bowls":
            families.append({"id": STEMLESS_FAMILY, "title": "Stemless double bowls and spine",
                             "blockId": "quintessential-latin-abbreviations"})
        families.append(copy.deepcopy(family))
    result["families"] = families
    for entry in result["entries"]:
        if entry["glyphId"] in STEMLESS_A:
            entry.update(familyId=STEMLESS_FAMILY, blockId="quintessential-latin-abbreviations")
        elif old_families[entry["familyId"]].get("baseFamilyId"):
            entry["familyId"] = old_families[entry["familyId"]]["baseFamilyId"]
    order = []
    for family in families:
        if family["id"] == STEMLESS_FAMILY:
            order.extend(STEMLESS_A)
            continue
        bases = [by_id[identity] for identity in before["displayOrder"]
                 if by_id[identity]["familyId"] == family["id"] and not by_id[identity]["middleLegs"]]
        for base in bases:
            order.append(base["glyphId"])
            children = [entry for entry in result["entries"] if entry["baseGlyphId"] == base["glyphId"]]
            def state(entry):
                flags = entry.get("middleLegExtensions", [True] * sum(bool(part.get("middle")) for part in entry["parts"]))
                return sum(int(flag) << i for i, flag in enumerate(flags))
            order.extend(entry["glyphId"] for entry in sorted(children, key=state))
    assert len(order) == len(set(order)) == len(by_id) == 1216
    result["displayOrder"] = order
    for index, identity in enumerate(order):
        by_id[identity]["codePoint"] = 0xF2A00 + index
    for block in result["blocks"]:
        codes = [entry["codePoint"] for entry in result["entries"] if entry["blockId"] == block["id"]]
        block.update(start=min(codes), end=max(codes))
        assert codes and len(codes) == block["end"] - block["start"] + 1
        assert block["start"] % 16 == 0 and (block["end"] + 1) % 16 == 0
    return result


def migrate(check=False):
    baseline = json.loads(gzip.decompress(BASELINE.read_bytes()))
    allocation = create_allocation(baseline["allocation"])
    expected_allocation = (json.dumps(allocation, indent=2, ensure_ascii=False) + "\n").encode()
    writes = [(ALLOCATION, expected_allocation)]
    by_id = {entry["glyphId"]: entry for entry in allocation["entries"]}
    for relative, captured in baseline["sourceGlyphs"].items():
        path, identity = ROOT / relative, captured["glyphId"]
        data = path.read_bytes()
        assert sha(UNICODE_TOKEN.sub(b"", data)) == captured["unicodeFreeSha256"], relative
        if identity:
            token = f'<unicode hex="{by_id[identity]["codePoint"]:X}"/>'.encode()
            changed, count = UNICODE_TOKEN.subn(token, data)
            assert count == 1, relative
            writes.append((path, changed))
    for relative, before in baseline["metadata"].items():
        if not relative.endswith("fontinfo.plist"):
            continue
        after = {**before, "versionMinor": 250, "openTypeNameVersion": "Version 0.250",
                 "openTypeNameUniqueID": before["openTypeNameUniqueID"].replace("0.240", VERSION)}
        writes.append((ROOT / relative, plistlib.dumps(after, sort_keys=True)))
    changes = [(path, data) for path, data in writes if path.read_bytes() != data]
    if check:
        assert not changes, f"{len(changes)} files differ from the logical allocation"
    else:
        for path, data in changes:
            path.write_bytes(data)
    print(f"{'Verified' if check else 'Wrote'} logical allocation: 1,216 consecutive positions, 30 families; {len(changes)} changed files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    capture() if args.capture else migrate(args.check)

"""Verify extraction preservation with the explicit Roman U+F2B18 revision."""

from pathlib import Path
import hashlib
import json
import plistlib
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
REVISION = ROOT / "resources/provenance/f2b18-optical-revision.json"
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


def verify():
    record = json.loads((ROOT / "resources/provenance/extraction-preservation.json").read_text(encoding="utf-8"))
    revised_sources, revised_outputs = revision_hashes(record)
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
        "status": "passed",
    }


if __name__ == "__main__":
    print(json.dumps(verify()))

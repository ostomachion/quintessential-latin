"""Add the missing native Italics without rewriting any existing glyph or pair.

The two new-only master sets are converted together before touching the UFOs.
Original Italic GIDs form an immutable prefix; additions follow catalogue order.
Roman sources receive version metadata only. No foundation force-import occurs.
"""
from __future__ import annotations

import argparse
import plistlib

from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from build_quintessential_font import load_and_verify_donors
from import_stix_foundation import (QUADRATIC_ERROR, compatible_structure,
                                    glyph_bounds, kerning_profile, legacy_outline, pair_kerning)
from quintessential_font import (ITALIC_ADDITIONS, MASTERS, ROOT, SOURCES,
                                  glyph_order_for_posture)

# This updater reconstructs the historical completion even after later releases.
COMPLETION_VERSION = "0.230"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Reconstruct and verify source bytes without writing")
    args = parser.parse_args()
    _, donors = load_and_verify_donors()
    work = ROOT / ".tmp/italic-completion"
    work.mkdir(parents=True, exist_ok=True)
    staged = []
    assert len(ITALIC_ADDITIONS) == 600
    for style, weight in (("Italic", 400), ("BoldItalic", 700)):
        font = Font()
        font.info.unitsPerEm = 1000
        with TTFont(donors["Italic"]) as variable:
            donor = instantiateVariableFont(variable, {"wght": weight}, inplace=False)
            for spec in ITALIC_ADDITIONS:
                if spec.middle_legs:
                    from stix_middle_legs import middle_legs_outline
                    recording, metadata = middle_legs_outline(donor, spec.recipe_code_point)
                else:
                    recording, metadata = legacy_outline(donor, spec)
                glyph = font.newGlyph(spec.glyph_name)
                glyph.width = metadata["advanceWidth"]
                glyph.unicodes = [spec.code_point]
                glyph.lib["org.quintessential.construction"] = {
                    **metadata, "method": spec.adaptation_for(True),
                    "glyphId": spec.glyph_id, "recipeCodePoint": spec.recipe_code_point,
                    "nativePosture": "Italic", "addedInVersion": COMPLETION_VERSION,
                }
                replayRecording(recording, glyph.getPen())
            donor.close()
        staged.append(font)
        print(f"Constructed {len(font)} {style} additions", flush=True)
    fonts_to_quadratic(staged, max_err=QUADRATIC_ERROR, reverse_direction=False,
                       remember_curve_type=False, all_quadratic=True)
    for spec in ITALIC_ADDITIONS:
        assert compatible_structure(staged[0], spec.glyph_name) == compatible_structure(staged[1], spec.glyph_name), spec.glyph_id

    # Prepare the complete serialization before writing authoritative sources.
    writes = []
    for style, additions in zip(("Italic", "BoldItalic"), staged):
        directory = SOURCES / f"QuintessentialSerif-{style}.ufo"
        font = Font.open(directory)
        contents = plistlib.loads((directory / "glyphs/contents.plist").read_bytes())
        added_names = set(additions.keys())
        for glyph in additions:
            font.layers.defaultLayer.insertGlyph(glyph, overwrite=True)
            filename = contents.setdefault(glyph.name, glyph.name + ".glif")
            content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
            writes.append((directory / "glyphs" / filename, content.encode("utf-8")))
        order = list(glyph_order_for_posture(True))
        profiles = {name: kerning_profile(font[name]) for name in order[2:]}
        bounds = {name: glyph_bounds(font[name]) for name in order[2:]}
        print(f"Profiled {style}; calculating added pairs", flush=True)
        for left in order[2:]:
            for right in order[2:]:
                if left in added_names or right in added_names:
                    font.kerning[left, right] = pair_kerning(font[left], font[right], profiles, bounds)
        kerning = {}
        for (left, right), value in font.kerning.items():
            kerning.setdefault(left, {})[right] = value
        lib = plistlib.loads((directory / "lib.plist").read_bytes())
        lib["public.glyphOrder"] = order
        for filename, data in (("glyphs/contents.plist", contents), ("kerning.plist", kerning), ("lib.plist", lib)):
            writes.append((directory / filename, plistlib.dumps(data, sort_keys=True)))
        font.close()
        print(f"Prepared {style} sources and {len(order[2:]) ** 2:,} explicit pairs", flush=True)

    for master in MASTERS:
        path = SOURCES / master.filename / "fontinfo.plist"
        info = plistlib.loads(path.read_bytes())
        if info.get("versionMinor", 0) < 230:
            info["versionMinor"] = 230
            info["openTypeNameVersion"] = f"Version {COMPLETION_VERSION}"
            if "openTypeNameUniqueID" in info:
                info["openTypeNameUniqueID"] = info["openTypeNameUniqueID"].replace("0.220", COMPLETION_VERSION)
        writes.append((path, plistlib.dumps(info, sort_keys=True)))
    changed = 0
    for path, content in writes:
        if not path.exists() or path.read_bytes() != content:
            if not args.check:
                path.write_bytes(content)
            changed += 1
    if args.check:
        if changed:
            raise SystemExit(f"{changed} source files differ from the reconstructed Italic completion")
        print("Verified byte-identical source reconstruction; no files written.")
        return
    print(f"Wrote {changed} source files; retained existing glyph bytes and old-to-old pairs.")


if __name__ == "__main__":
    main()

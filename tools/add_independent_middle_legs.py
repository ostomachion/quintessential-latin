#!/usr/bin/env python3
"""Append independent middle-leg forms while preserving all existing sources.

Only new glyphs are reconstructed. Existing GLIF bytes, GID prefixes and
old-to-old kerning pairs are retained. Both masters of each posture are
converted together before any authoritative source file is written.
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
                                    glyph_bounds, kerning_profile, pair_kerning)
from quintessential_font import (INDEPENDENT_MIDDLE_ADDITIONS, MASTERS, SOURCES,
                                  VERSION, VERSION_MINOR, glyph_order_for_posture)
from stix_middle_legs import middle_legs_outline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify deterministic sources without writing")
    parser.add_argument("--posture", choices=("Roman", "Italic"), help="Reconstruct only one native posture")
    args = parser.parse_args()
    _, donors = load_and_verify_donors()
    assert len(INDEPENDENT_MIDDLE_ADDITIONS) == 384
    masters = tuple(master for master in MASTERS if args.posture is None or master.posture == args.posture)
    staged = {}
    for master in masters:
        font = Font()
        font.info.unitsPerEm = 1000
        with TTFont(donors[master.posture]) as variable:
            donor = instantiateVariableFont(variable, {"wght": master.weight}, inplace=True)
            for spec in INDEPENDENT_MIDDLE_ADDITIONS:
                recording, metadata = middle_legs_outline(donor, spec.recipe_code_point, spec.middle_leg_extensions)
                glyph = font.newGlyph(spec.glyph_name)
                glyph.width = metadata["advanceWidth"]
                glyph.unicodes = [spec.code_point]
                glyph.lib["org.quintessential.construction"] = {
                    **metadata, "method": spec.adaptation_for(master.italic),
                    "glyphId": spec.glyph_id, "recipeCodePoint": spec.recipe_code_point,
                    "middleLegExtensions": list(spec.middle_leg_extensions),
                    "nativePosture": master.posture, "addedInVersion": VERSION,
                }
                replayRecording(recording, glyph.getPen())
        staged[master.style] = font
        print(f"Constructed {len(font)} {master.style} additions", flush=True)
    for light, bold in (("Regular", "Bold"), ("Italic", "BoldItalic")):
        if light not in staged:
            continue
        fonts_to_quadratic([staged[light], staged[bold]], max_err=QUADRATIC_ERROR,
                           reverse_direction=False, remember_curve_type=False, all_quadratic=True)
        for spec in INDEPENDENT_MIDDLE_ADDITIONS:
            assert compatible_structure(staged[light], spec.glyph_name) == compatible_structure(staged[bold], spec.glyph_name), (light, spec.glyph_id)

    writes = []
    for master in masters:
        directory = SOURCES / master.filename
        additions = staged[master.style]
        with Font.open(directory) as font:
            contents = plistlib.loads((directory / "glyphs/contents.plist").read_bytes())
            added_names = set(additions.keys())
            for glyph in additions:
                font.layers.defaultLayer.insertGlyph(glyph, overwrite=True)
                filename = contents.setdefault(glyph.name, glyph.name + ".glif")
                content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
                writes.append((directory / "glyphs" / filename, content.encode("utf-8")))
            order = list(glyph_order_for_posture(master.italic))
            old_order = font.lib["public.glyphOrder"]
            assert order[:len(old_order)] == old_order, (master.style, "Existing GID prefix changed")
            profiles = {name: kerning_profile(font[name]) for name in order[2:]}
            bounds = {name: glyph_bounds(font[name]) for name in order[2:]}
            print(f"Profiled {master.style}; calculating new pairs", flush=True)
            for left in order[2:]:
                for right in order[2:]:
                    if left in added_names or right in added_names:
                        font.kerning[left, right] = pair_kerning(font[left], font[right], profiles, bounds)
            kerning = {}
            for (left, right), value in font.kerning.items():
                kerning.setdefault(left, {})[right] = value
            lib = plistlib.loads((directory / "lib.plist").read_bytes())
            lib["public.glyphOrder"] = order
            info = plistlib.loads((directory / "fontinfo.plist").read_bytes())
            old_version = info.get("openTypeNameVersion", "Version 0.230").removeprefix("Version ")
            info.update(versionMinor=VERSION_MINOR, openTypeNameVersion=f"Version {VERSION}")
            if "openTypeNameUniqueID" in info:
                info["openTypeNameUniqueID"] = info["openTypeNameUniqueID"].replace(old_version, VERSION)
            for filename, data in (("glyphs/contents.plist", contents), ("kerning.plist", kerning),
                                   ("lib.plist", lib), ("fontinfo.plist", info)):
                writes.append((directory / filename, plistlib.dumps(data, sort_keys=True)))
        print(f"Prepared {master.style} sources and {len(order[2:]) ** 2:,} explicit pairs", flush=True)
    changes = [(path, data) for path, data in writes if not path.exists() or path.read_bytes() != data]
    if args.check:
        if changes:
            raise SystemExit(f"{len(changes)} source files differ from reconstruction")
        print("Verified byte-identical source reconstruction; no files written.")
    else:
        for path, data in changes:
            path.write_bytes(data)
        print(f"Wrote {len(changes)} files; retained every previous GLIF and old-to-old pair.")


if __name__ == "__main__":
    main()

"""Align assembled Italic shafts and their explicitly audited derivatives."""
import argparse
import json
import plistlib

from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from build_quintessential_font import load_and_verify_donors
from import_stix_foundation import QUADRATIC_ERROR, compatible_structure, glyph_bounds, legacy_outline, pair_kerning
from quintessential_font import GLYPHS, MASTERS, ROOT, SOURCES
from refine_hip_tails import kerning_profile

TARGET_NAMES = frozenset(entry["glyphName"] for entry in json.loads(
    (ROOT / "resources/italic-shaft-targets.json").read_text())["targets"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, donors = load_and_verify_donors()
    specs = [spec for spec in GLYPHS if spec.glyph_name in TARGET_NAMES]
    assert len(specs) == 150
    masters = [master for master in MASTERS if master.italic]
    staged, contents = [], []
    for master in masters:
        directory = SOURCES / master.filename
        with Font.open(directory) as source, TTFont(donors["Italic"]) as variable:
            temporary = Font()
            temporary.info.unitsPerEm = source.info.unitsPerEm
            contents.append(plistlib.loads((directory / "glyphs/contents.plist").read_bytes()))
            donor = instantiateVariableFont(variable, {"wght": master.weight}, inplace=False)
            for spec in specs:
                if spec.middle_legs:
                    from stix_middle_legs import middle_legs_outline
                    recording, metadata = middle_legs_outline(donor, spec.recipe_code_point, spec.middle_leg_extensions)
                else:
                    recording, metadata = legacy_outline(donor, spec)
                old = source[spec.glyph_name]
                assert old.width == round(metadata["advanceWidth"], 6), (master.style, spec.glyph_id)
                assert old.unicodes == [spec.code_point]
                glyph = temporary.newGlyph(spec.glyph_name)
                glyph.width, glyph.unicodes = old.width, old.unicodes
                glyph.lib.update(old.lib)
                glyph.lib["org.quintessential.construction"] = {
                    **old.lib["org.quintessential.construction"],
                    **{key: value for key, value in metadata.items() if value is not None},
                    "recipeCodePoint": spec.recipe_code_point,
                }
                replayRecording(recording, glyph.getPen())
            donor.close()
            staged.append(temporary)
    fonts_to_quadratic(staged, max_err=QUADRATIC_ERROR, reverse_direction=False,
                       remember_curve_type=False, all_quadratic=True)
    for spec in specs:
        assert compatible_structure(staged[0], spec.glyph_name) == compatible_structure(staged[1], spec.glyph_name)
    writes, changed_pairs = [], 0
    for master, font, names in zip(masters, staged, contents):
        for spec in specs:
            glyph = font[spec.glyph_name]
            path = SOURCES / master.filename / "glyphs" / names[glyph.name]
            content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
            if path.read_text(encoding="utf-8") != content:
                writes.append((path, content.encode("utf-8")))
        with Font.open(SOURCES / master.filename) as source:
            for glyph in font:
                source.layers.defaultLayer.insertGlyph(glyph, overwrite=True)
            order = source.lib["public.glyphOrder"][2:]
            profiles = {name: kerning_profile(source[name]) for name in order}
            bounds = {name: glyph_bounds(source[name]) for name in order}
            pairs = ({(target, name) for target in TARGET_NAMES for name in order} |
                     {(name, target) for target in TARGET_NAMES for name in order})
            count = 0
            for left, right in sorted(pairs):
                value = pair_kerning(source[left], source[right], profiles, bounds)
                if source.kerning[left, right] != value:
                    source.kerning[left, right] = value
                    count += 1
            kerning = {}
            for (left, right), value in source.kerning.items():
                kerning.setdefault(left, {})[right] = value
            path = SOURCES / master.filename / "kerning.plist"
            content = plistlib.dumps(kerning, sort_keys=True)
            if path.read_bytes() != content:
                writes.append((path, content))
            changed_pairs += count
            print(f"Prepared {master.style}: {len(font)} glyphs, {count} changed target pairs", flush=True)
    if args.check and writes:
        raise SystemExit(f"{len(writes)} Italic shaft sources differ from reconstruction")
    for path, content in writes:
        path.write_bytes(content)
    print(f"{'Verified' if args.check else 'Updated'} 150 Italic forms; {len(writes)} files written; {changed_pairs} changed target pairs; advances and unrelated pairs preserved.")


if __name__ == "__main__":
    main()

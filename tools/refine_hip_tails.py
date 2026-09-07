"""Apply the native broad bowl/arch tail below the two immediate hip forms."""
import argparse
import math
import plistlib

from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from build_quintessential_font import load_and_verify_donors
from import_stix_foundation import (QUADRATIC_ERROR, compatible_structure, flattened_contours,
                                    glyph_bounds, legacy_outline, pair_kerning)
from quintessential_font import GLYPHS, MASTERS, SOURCES

TARGET_IDS = frozenset(("turned-arm-tail", "turned-arm-ascender-tail"))


def kerning_profile(glyph):
    """The foundation's integer scanlines, accumulated one edge at a time.

    Each flattened edge crosses only a few scanlines. Visiting those crossings
    directly gives the same extrema as scanning every edge at every height.
    """
    bounds = glyph_bounds(glyph)
    if bounds is None:
        return {}
    profile = {y: None for y in range(math.floor(bounds[1]), math.ceil(bounds[3]))}
    for contour in flattened_contours(glyph):
        for first, second in zip(contour, contour[1:]):
            if first[1] == second[1]:
                continue
            low, high = sorted((first[1], second[1]))
            for y in range(math.floor(low - 0.37), math.floor(high - 0.37) + 1):
                if not ((first[1] <= y + 0.37 < second[1]) or
                        (second[1] <= y + 0.37 < first[1])):
                    continue
                t = (y + 0.37 - first[1]) / (second[1] - first[1])
                x = first[0] + (second[0] - first[0]) * t
                interval = profile[y]
                profile[y] = ((x, x) if interval is None else
                              (min(interval[0], x), max(interval[1], x)))
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, donors = load_and_verify_donors()
    specs = [spec for spec in GLYPHS if spec.glyph_id in TARGET_IDS]
    assert len(specs) == 2
    staged, contents = [], []
    for master in MASTERS:
        directory = SOURCES / master.filename
        source = Font.open(directory)
        temporary = Font()
        temporary.info.unitsPerEm = source.info.unitsPerEm
        contents.append(plistlib.loads((directory / "glyphs/contents.plist").read_bytes()))
        with TTFont(donors["Italic" if master.italic else "Roman"]) as variable:
            donor = instantiateVariableFont(variable, {"wght": master.weight}, inplace=False)
            for spec in specs:
                recording, metadata = legacy_outline(donor, spec)
                old = source[spec.glyph_name]
                assert old.width == round(metadata["advanceWidth"], 6), (master.style, spec.glyph_id, "advance changed")
                assert old.unicodes == [spec.code_point], (master.style, spec.glyph_id)
                glyph = temporary.newGlyph(spec.glyph_name)
                glyph.width, glyph.unicodes = old.width, old.unicodes
                glyph.lib.update(old.lib)
                glyph.lib["org.quintessential.construction"] = {
                    **old.lib["org.quintessential.construction"], **metadata,
                    "method": spec.adaptation_for(master.italic),
                    "recipeCodePoint": spec.recipe_code_point,
                }
                replayRecording(recording, glyph.getPen())
            donor.close()
        staged.append(temporary)
        source.close()
    for italic in (False, True):
        pair = [font for master, font in zip(MASTERS, staged) if master.italic == italic]
        fonts_to_quadratic(pair, max_err=QUADRATIC_ERROR, reverse_direction=False,
                           remember_curve_type=False, all_quadratic=True)
        for spec in specs:
            assert compatible_structure(pair[0], spec.glyph_name) == compatible_structure(pair[1], spec.glyph_name)
    writes, changed_pairs = [], 0
    for master, font, names in zip(MASTERS, staged, contents):
        for spec in specs:
            glyph = font[spec.glyph_name]
            path = SOURCES / master.filename / "glyphs" / names[glyph.name]
            content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
            if path.read_text(encoding="utf-8") != content:
                writes.append((path, content.encode("utf-8")))
        # Only the wider tails require new pair spacing. Preserve every pair
        # between unrelated forms, including all previously reviewed spacing.
        with Font.open(SOURCES / master.filename) as source:
            for glyph in font:
                source.layers.defaultLayer.insertGlyph(glyph, overwrite=True)
            order = source.lib["public.glyphOrder"][2:]
            profiles = {name: kerning_profile(source[name]) for name in order}
            bounds = {name: glyph_bounds(source[name]) for name in order}
            target_names = {spec.glyph_name for spec in specs}
            pairs = ({(target, name) for target in target_names for name in order} |
                     {(name, target) for target in target_names for name in order})
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
            print(f"Prepared {master.style}: {count} changed target pairs", flush=True)
    if args.check and writes:
        raise SystemExit(f"{len(writes)} hip-tail source files differ from reconstruction")
    for path, content in writes:
        path.write_bytes(content)
    print(f"{'Verified' if args.check else 'Updated'} two hip-tail glyphs in four masters; {len(writes)} files written; {changed_pairs} changed target pairs; all advances and unrelated pairs preserved.")


if __name__ == "__main__":
    main()

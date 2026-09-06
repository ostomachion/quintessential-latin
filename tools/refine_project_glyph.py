"""Regenerate every shared two-stem spine, preserving spacing and other forms."""
import plistlib
from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from build_quintessential_font import load_and_verify_donors
from import_stix_foundation import legacy_outline, QUADRATIC_ERROR
from quintessential_font import GLYPHS, SOURCES
from stix_compact_spine import is_shared_spine_recipe


def main():
    _, donors = load_and_verify_donors()
    specs = [g for g in GLYPHS if is_shared_spine_recipe(g.recipe_code_point)]
    assert len(specs) == 396 and all(g.roman_only for g in specs)
    working, filenames = [], []
    for style, weight in (("Regular", 400), ("Bold", 700)):
        source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
        temporary = Font()
        temporary.info.unitsPerEm = source.info.unitsPerEm
        filenames.append(plistlib.loads((SOURCES / f"QuintessentialSerif-{style}.ufo/glyphs/contents.plist").read_bytes()))
        with TTFont(donors["Roman"]) as variable:
            donor = instantiateVariableFont(variable, {"wght": weight}, inplace=False)
            for spec in specs:
                if spec.middle_legs:
                    from stix_middle_legs import middle_legs_outline
                    recording, metadata = middle_legs_outline(donor, spec.recipe_code_point)
                else:
                    recording, metadata = legacy_outline(donor, spec)
                old = source[spec.glyph_name]
                assert old.width == metadata["advanceWidth"], (style, spec.glyph_id)
                assert old.unicodes == [spec.code_point], spec.glyph_id
                glyph = temporary.newGlyph(spec.glyph_name)
                glyph.width, glyph.unicodes = old.width, old.unicodes
                glyph.lib.update(old.lib)
                glyph.lib["org.quintessential.construction"] = {
                    **metadata,
                    "method": spec.adaptation_for(False),
                    "glyphId": spec.glyph_id,
                    "recipeCodePoint": spec.recipe_code_point,
                }
                replayRecording(recording, glyph.getPen())
            donor.close()
        working.append(temporary)
        source.close()
    # Convert only affected glyph pairs; existing kerning, UFO metadata, and
    # unrelated glyphs remain untouched. Finish every outline before writing.
    fonts_to_quadratic(working, max_err=QUADRATIC_ERROR, reverse_direction=False,
                       remember_curve_type=False, all_quadratic=True)
    writes = []
    for style, temporary, names in zip(("Regular", "Bold"), working, filenames):
        for spec in specs:
            glyph = temporary[spec.glyph_name]
            path = SOURCES / f"QuintessentialSerif-{style}.ufo/glyphs" / names[glyph.name]
            content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
            writes.append((path, content))
    for path, content in writes:
        if path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8", newline="\n")
    print(f"Refined {len(specs)} Roman shared-spine glyphs in both masters; preserved all advances and pairs.")


if __name__ == "__main__":
    main()

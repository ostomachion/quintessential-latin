"""Regenerate only the two U+F2B18 optical masters, preserving spacing and peers."""
from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from build_quintessential_font import load_and_verify_donors
from import_stix_foundation import legacy_outline, QUADRATIC_ERROR
from quintessential_font import GLYPHS, SOURCES


def main():
    _, donors = load_and_verify_donors()
    spec = next(g for g in GLYPHS if g.glyph_id == "opposed-bowls-0-0")
    assert (spec.code_point, spec.glyph_name) == (0xF2B18, "uF2B1C")
    working = []
    for style, weight in (("Regular", 400), ("Bold", 700)):
        source = Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo")
        temporary = Font()
        temporary.info.unitsPerEm = source.info.unitsPerEm
        with TTFont(donors["Roman"]) as variable:
            donor = instantiateVariableFont(variable, {"wght": weight}, inplace=False)
            recording, metadata = legacy_outline(donor, spec)
            donor.close()
        old = source[spec.glyph_name]
        assert old.width == metadata["advanceWidth"]
        glyph = temporary.newGlyph(spec.glyph_name)
        glyph.width, glyph.unicodes = old.width, old.unicodes
        glyph.lib.update(old.lib)
        glyph.lib["org.quintessential.construction"] = {
            **metadata,
            "glyphId": spec.glyph_id,
            "recipeCodePoint": spec.recipe_code_point,
        }
        replayRecording(recording, glyph.getPen())
        working.append(temporary)
        source.close()
    # Only the two counter revisions participate in compatible cubic conversion;
    # the source masters' existing outlines and kerning are never regenerated.
    fonts_to_quadratic(working, max_err=QUADRATIC_ERROR, reverse_direction=False,
                       remember_curve_type=False, all_quadratic=True)
    for style, temporary in zip(("Regular", "Bold"), working):
        glyph = temporary[spec.glyph_name]
        path = SOURCES / f"QuintessentialSerif-{style}.ufo/glyphs/uF_2B_1C_.glif"
        path.write_text(writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2),
                        encoding="utf-8", newline="\n")
        print(f"Refined {style} U+F2B18; advance {glyph.width:g}; preserved all pairs.")


if __name__ == "__main__":
    main()

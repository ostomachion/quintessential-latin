"""Apply the selected two-bulb terminals to three glyphs in all four masters."""
import argparse
import plistlib

from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools.pens.recordingPen import replayRecording
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from build_quintessential_font import load_and_verify_donors
from import_stix_foundation import QUADRATIC_ERROR, compatible_structure
from quintessential_font import GLYPHS, MASTERS, SOURCES
from stix_stemless import stemless_outline

TARGET_IDS = frozenset(("special-spine", "special-turned-open-bowl",
                        "special-turned-double-open-bowl"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    _, donors = load_and_verify_donors()
    specs = [spec for spec in GLYPHS if spec.glyph_id in TARGET_IDS]
    assert len(specs) == 3
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
                recording, metadata = stemless_outline(donor, spec.glyph_id)
                old = source[spec.glyph_name]
                assert old.width == round(metadata["advanceWidth"], 6), (master.style, spec.glyph_id, "advance changed")
                assert old.unicodes == [spec.code_point], (master.style, spec.glyph_id)
                if spec.glyph_id == "special-spine":
                    assert old.lib["org.quintessential.construction"]["bodyOffsetX"] == metadata["bodyOffsetX"]
                glyph = temporary.newGlyph(spec.glyph_name)
                glyph.width, glyph.unicodes = old.width, old.unicodes
                glyph.lib.update(old.lib)
                glyph.lib["org.quintessential.construction"] = {
                    **metadata,
                    "method": "Native body with bulbs at both free terminals; existing advance and body placement preserved.",
                    **({"recipeCodePoint": spec.recipe_code_point} if spec.recipe_code_point is not None else {}),
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
    writes = []
    for master, font, names in zip(MASTERS, staged, contents):
        for spec in specs:
            glyph = font[spec.glyph_name]
            path = SOURCES / master.filename / "glyphs" / names[glyph.name]
            content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
            if path.read_text(encoding="utf-8") != content:
                writes.append((path, content))
    if args.check and writes:
        raise SystemExit(f"{len(writes)} terminal source files differ from reconstruction")
    for path, content in writes:
        path.write_text(content, encoding="utf-8", newline="\n")
    print(f"{'Verified' if args.check else 'Updated'} three glyphs in four masters; {len(writes)} files written; all advances and kerning preserved.")


if __name__ == "__main__":
    main()

"""Reconstruct only the audited Roman open-arch heads from pinned donors."""
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
from import_stix_foundation import QUADRATIC_ERROR, compatible_structure, legacy_outline
from quintessential_font import GLYPHS, MASTERS, ROOT, SOURCES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    inventory = json.loads((ROOT / 'resources/serif-consistency-targets.json').read_text())
    names = {entry['glyphName'] for entry in inventory['entries']}
    specs = [spec for spec in GLYPHS if spec.glyph_name in names]
    assert len(specs) == len(names) == 328
    _, donors = load_and_verify_donors()
    masters = [master for master in MASTERS if not master.italic]
    staged = []
    contents = []
    for master in masters:
        directory = SOURCES / master.filename
        with Font.open(directory) as source, TTFont(donors['Roman']) as variable:
            temporary = Font()
            temporary.info.unitsPerEm = source.info.unitsPerEm
            contents.append(plistlib.loads((directory / 'glyphs/contents.plist').read_bytes()))
            donor = instantiateVariableFont(variable, {'wght': master.weight}, inplace=False)
            for spec in specs:
                if spec.middle_legs:
                    from stix_middle_legs import middle_legs_outline
                    recording, metadata = middle_legs_outline(donor, spec.recipe_code_point, spec.middle_leg_extensions)
                else:
                    recording, metadata = legacy_outline(donor, spec)
                old = source[spec.glyph_name]
                assert old.width == round(metadata['advanceWidth'], 6), (master.style, spec.glyph_id)
                assert old.unicodes == [spec.code_point]
                glyph = temporary.newGlyph(spec.glyph_name)
                glyph.width, glyph.unicodes = old.width, old.unicodes
                glyph.lib.update(old.lib)
                glyph.lib['org.quintessential.construction'] = {
                    **old.lib['org.quintessential.construction'],
                    'openArchHeadDonorCodePoint': 0x75,
                    'openArchHeadDesign': 'native-u-left-arm-right-stem-1',
                }
                replayRecording(recording, glyph.getPen())
            donor.close()
            staged.append(temporary)
            print(f'Prepared {master.style}: {len(temporary)} glyphs', flush=True)
    fonts_to_quadratic(staged, max_err=QUADRATIC_ERROR, reverse_direction=False,
                       remember_curve_type=False, all_quadratic=True)
    for name in names:
        assert compatible_structure(staged[0], name) == compatible_structure(staged[1], name), name
    writes = []
    for master, font, filenames in zip(masters, staged, contents):
        for glyph in font:
            path = SOURCES / master.filename / 'glyphs' / filenames[glyph.name]
            content = writeGlyphToString(glyph.name, glyph, glyph.drawPoints, formatVersion=2)
            if path.read_text(encoding='utf-8') != content:
                writes.append((path, content.encode('utf-8')))
    if args.check and writes:
        raise SystemExit(f'{len(writes)} Roman open-arch sources differ from reconstruction')
    for path, content in writes:
        path.write_bytes(content)
    print(f"{'Verified' if args.check else 'Updated'} 328 Roman forms; {len(writes)} files written; advances, mappings and kerning preserved.")


if __name__ == '__main__':
    main()

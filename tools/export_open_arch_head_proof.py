"""Export source-bound before/after Roman head proofs at text and display sizes."""
import argparse
import hashlib
import html
import json
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FILENAME = 'QuintessentialSerif-Variable.ttf'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, default=ROOT / '.tmp/serif-consistency-before/compiled' / FILENAME)
    parser.add_argument('--after', type=Path, default=ROOT / 'resources/fonts/QuintessentialSerif' / FILENAME)
    args = parser.parse_args()
    output = ROOT / 'docs/images/open-arch-heads'
    output.mkdir(parents=True, exist_ok=True)
    entries = json.loads((ROOT / 'resources/serif-consistency-targets.json').read_text())['entries']
    allocation = json.loads((ROOT / 'resources/quintessential-latin-allocation.json').read_text())['entries']
    bases = sorted((e for e in allocation if e['codePoint'] in (*range(0xF2A2A, 0xF2A30), *range(0xF2A84, 0xF2A8C))), key=lambda e: e['codePoint'])
    manifest = {'beforeSha256': hashlib.sha256(args.before.read_bytes()).hexdigest(),
                'afterSha256': hashlib.sha256(args.after.read_bytes()).hexdigest(),
                'glyphCount': len(entries), 'sheets': []}
    labels = {s: ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', s) for s in (12, 16, 24)}
    jobs = [(f'base-{w}', w, bases, 175) for w in (400, 500, 550, 600, 700)]
    jobs += [(f'all-{w}-{start//32+1:02d}', w, entries[start:start+32], 100)
             for w in (400, 700) for start in range(0, len(entries), 32)]
    with TTFont(args.before) as before, TTFont(args.after) as after:
        assert before.getBestCmap() == after.getBestCmap()
        for title, weight, rows, size in jobs:
            width, cell_w, cell_h = 1320, 320, (245 if size == 175 else 175)
            height = 100 + ((len(rows)+3)//4)*cell_h + 40
            raster = Image.new('RGB', (width, height), '#faf9f6')
            draw = ImageDraw.Draw(raster)
            svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
                   f'<rect width="{width}" height="{height}" fill="#faf9f6"/>']
            def label(x,y,value,s=12,color='#26352d'):
                draw.text((x,y), value, font=labels[s], fill=color)
                svg.append(f'<text x="{x}" y="{y+s}" font-family="Segoe UI,sans-serif" font-size="{s}" fill="{color}">{html.escape(value)}</text>')
            label(20,15,f'Roman {weight} · open-arch heads · before / after',24)
            label(20,50,f'{size}px and 24px · current code points · outline curves and spacing verified separately',16)
            glyphsets = [f.getGlyphSet(location={'wght':weight}) for f in (before,after)]
            raster_fonts = {}
            for phase,path in enumerate((args.before,args.after)):
                for px in (size,24):
                    f = ImageFont.truetype(str(path),px)
                    f.set_variation_by_axes([weight])
                    raster_fonts[phase,px] = f
            for i,e in enumerate(rows):
                x,y = 20+(i%4)*cell_w,85+(i//4)*cell_h
                label(x,y,f'U+{e["codePoint"]:X}  {e["canonicalName"][:30]}')
                for phase,glyphs in enumerate(glyphsets):
                    pen = SVGPathPen(glyphs)
                    glyphs[e['glyphName']].draw(pen)
                    # Wide constructions are scaled equally on both sides;
                    # the separate 24px run remains a true text-size sample.
                    display = min(size, 140000/glyphs[e['glyphName']].width)
                    origin=x+5+phase*158
                    baseline=y+cell_h-85
                    for px,by in ((display,baseline),(24,y+cell_h-20)):
                        svg.append(f'<path fill="#26352d" transform="translate({origin} {by}) scale({px/1000} {-px/1000})" d="{pen.getCommands()}"/>')
                        f=raster_fonts[phase,24] if px==24 else raster_fonts[phase,size]
                        if px != 24 and px != size:
                            f=ImageFont.truetype(str((args.before,args.after)[phase]),round(px))
                            f.set_variation_by_axes([weight])
                        draw.text((origin,by),chr(e['codePoint']),font=f,fill='#26352d',anchor='ls')
            label(20,height-24,f'After SHA-256 {manifest["afterSha256"]}')
            svg.append('</svg>')
            (output/f'{title}.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8')
            raster.save(output/f'{title}.png')
            manifest['sheets'].append({'name':title,'weight':weight,'codePoints':[e['codePoint'] for e in rows],
                'pngSha256':hashlib.sha256((output/f'{title}.png').read_bytes()).hexdigest()})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    links=''.join(f'<li><a href="{s["name"]}.svg">{s["name"]}</a></li>' for s in manifest['sheets'])
    (output/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Roman open-arch heads</title>'
        '<style>body{max-width:800px;margin:40px auto;font:18px/1.6 Georgia;padding:0 24px}</style>'
        '<h1>Roman open-arch heads</h1><p>Before/after compiled outlines. Base examples at five weights; every affected '
        'glyph at both endpoints. Each cell shows before on the left and after on the right, with a 24px sample below.</p>'
        f'<ul>{links}</ul></html>\n',encoding='utf-8')
    print(f'Exported {len(jobs)} before/after sheets to {output}')


if __name__ == '__main__':
    main()

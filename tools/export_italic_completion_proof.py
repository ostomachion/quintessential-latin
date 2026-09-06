"""Export the newly completed Italic repertoire from the compiled variable font.

The archived allocation selects exactly the previously unsupported public
characters. Every cell shows both endpoints, an intermediate weight, and two
text sizes. SVG outlines and optional PNGs use the same compiled font.
"""

import argparse
from collections import defaultdict
import gzip
import hashlib
import html
import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = (400, 550, 700)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=ROOT / "resources/fonts/QuintessentialSerif/QuintessentialSerif-Italic-Variable.ttf")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images/italic-completion")
    parser.add_argument("--png", action="store_true", help="Also rasterize with Pillow/FreeType")
    args = parser.parse_args()
    baseline = json.loads(gzip.decompress((ROOT / "resources/provenance/italic-completion-baseline.json.gz").read_bytes()))
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    titles = {family["id"]: family["title"] for family in allocation["families"]}
    families = defaultdict(list)
    for entry in baseline["entries"]:
        if "Italic" not in entry["postures"]:
            families[entry["familyId"]].append(entry)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"font": args.font.resolve().relative_to(ROOT).as_posix(),
                "fontSha256": hashlib.sha256(args.font.read_bytes()).hexdigest(),
                "weights": list(WEIGHTS), "textSizesPx": [16, 24],
                "glyphCount": sum(map(len, families.values())), "sheets": []}
    if args.png:
        from PIL import Image, ImageDraw, ImageFont
        label_path = Path("C:/Windows/Fonts/segoeui.ttf")
        labels = {size: ImageFont.truetype(str(label_path), size) if label_path.is_file()
                  else ImageFont.load_default(size=size) for size in (12, 14, 17, 27)}
        raster_fonts = {}
        for weight in WEIGHTS:
            for size in (100, 70, 24, 16):
                font = ImageFont.truetype(str(args.font), size)
                font.set_variation_by_axes([weight])
                raster_fonts[weight, size] = font
    with TTFont(args.font) as font:
        manifest["fontVersion"] = font["name"].getDebugName(5)
        glyph_sets = {weight: font.getGlyphSet(location={"wght": weight}) for weight in WEIGHTS}
        cmap = font.getBestCmap()
        missing = [entry["codePoint"] for entries in families.values() for entry in entries
                   if entry["codePoint"] not in cmap]
        if missing:
            raise RuntimeError(f"Compiled Italic font is missing {len(missing)} proof characters")
        for order, (family, entries) in enumerate(families.items(), 1):
            entries.sort(key=lambda entry: entry["codePoint"])
            width, cell_width, cell_height = 1800, 576, 236
            rows = (len(entries) + 2) // 3
            height = 190 + rows * cell_height
            title = f'{titles[family]} · Italic'
            subtitle = '400 / 550 / 700 · 100px em · Intermediate weight at 16px and 24px below'
            parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
                     f'<title>{html.escape(title)}</title>',
                     f'<rect width="{width}" height="{height}" fill="#faf9f6"/>',
                     f'<g fill="#242c27" font-family="Segoe UI, sans-serif"><text x="36" y="43" font-size="27">{html.escape(title)}</text>',
                     f'<text x="36" y="76" font-size="17" fill="#687266">{subtitle}</text></g>']
            if args.png:
                raster = Image.new("RGB", (width, height), "#faf9f6")
                draw = ImageDraw.Draw(raster)
                draw.text((36, 16), title, fill="#242c27", font=labels[27])
                draw.text((36, 56), subtitle, fill="#687266", font=labels[17])
            for index, entry in enumerate(entries):
                x, y = 36 + index % 3 * cell_width, 102 + index // 3 * cell_height
                code = entry["codePoint"]
                parts.append(f'<path d="M{x} {y}H{x+cell_width-20}" stroke="#d8dacf"/>')
                parts.append(f'<text x="{x+5}" y="{y+22}" fill="#687266" font-family="Segoe UI, sans-serif" font-size="14">U+{code:X}</text>')
                if args.png:
                    draw.line((x, y, x + cell_width - 20, y), fill="#d8dacf")
                    draw.text((x + 5, y + 6), f'U+{code:X}', fill="#687266", font=labels[14])
                for column, weight in enumerate(WEIGHTS):
                    glyphs = glyph_sets[weight]
                    name = cmap[code]
                    path, bounds = SVGPathPen(glyphs), BoundsPen(glyphs)
                    glyphs[name].draw(path)
                    glyphs[name].draw(bounds)
                    left, bottom, right, top = bounds.bounds
                    origin = x + column * 185 + (174 - (right - left) * .1) / 2 - left * .1
                    baseline_y = y + 130
                    parts.append(f'<path fill="#242c27" transform="translate({origin:g} {baseline_y}) scale(.1 -.1)" d="{path.getCommands()}"/>')
                    if args.png:
                        draw.text((origin, baseline_y), chr(code), font=raster_fonts[weight, 100],
                                  fill="#242c27", anchor="ls")
                glyphs = glyph_sets[550]
                path = SVGPathPen(glyphs)
                glyphs[cmap[code]].draw(path)
                for size, base_y in ((16, y + 181), (24, y + 216)):
                    parts.append(f'<text x="{x+5}" y="{base_y}" fill="#687266" font-family="Segoe UI, sans-serif" font-size="12">{size}px</text>')
                    advance = glyphs[cmap[code]].width * size / 1000
                    for repeat in range(3):
                        origin = x + 48 + repeat * (advance + size / 2)
                        parts.append(f'<path fill="#242c27" transform="translate({origin:g} {base_y}) scale({size/1000:g} {-size/1000:g})" d="{path.getCommands()}"/>')
                        if args.png:
                            draw.text((origin, base_y), chr(code), font=raster_fonts[550, size],
                                      fill="#242c27", anchor="ls")
                    if args.png:
                        draw.text((x + 5, base_y - 12), f'{size}px', fill="#687266", font=labels[12])
            footer = (f'{order:02d} / {len(families):02d} · {len(entries)} characters · '
                      f'{manifest["fontVersion"]} · Compiled outlines, visual acceptance pending')
            fingerprint = f'SHA-256 {manifest["fontSha256"]}'
            parts.append(f'<g fill="#687266" font-family="Segoe UI, sans-serif" font-size="14"><text x="36" y="{height-47}">{html.escape(footer)}</text>'
                         f'<text x="36" y="{height-20}">{fingerprint}</text></g></svg>')
            if args.png:
                draw.text((36, height - 64), footer, fill="#687266", font=labels[14])
                draw.text((36, height - 37), fingerprint, fill="#687266", font=labels[14])
            name = f'{order:02d}-{family}'
            (args.output / f'{name}.svg').write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
            sheet = {"file": f'{name}.svg', "family": family,
                     "characters": [f'U+{entry["codePoint"]:X}' for entry in entries]}
            if args.png:
                raster.save(args.output / f'{name}.png')
                sheet["raster"] = f'{name}.png'
            manifest["sheets"].append(sheet)
    links = "\n".join(
        f'<li><a href="{sheet["file"]}">{html.escape(titles[sheet["family"]])}</a> · {len(sheet["characters"])} characters</li>'
        for sheet in manifest["sheets"])
    (args.output / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Italic completion proofs</title><style>body{max-width:900px;margin:40px auto;padding:0 24px;'
        'background:#faf9f6;color:#242c27;font:18px/1.65 Georgia,serif}a{color:#365746}code{font-size:12px}</style>'
        f'<h1>{manifest["glyphCount"]} added Italic forms</h1><p>Every addition appears at weights 400, 550, and 700, '
        'with 16px and 24px text specimens. These sheets use compiled outlines. Optical inspection and user '
        f'acceptance remain separate.</p><p><code>SHA-256 {manifest["fontSha256"]}</code></p><ol>{links}</ol></html>',
        encoding="utf-8")
    outputs = ["index.html", *[sheet["file"] for sheet in manifest["sheets"]],
               *[sheet["raster"] for sheet in manifest["sheets"] if "raster" in sheet]]
    manifest["files"] = {name: hashlib.sha256((args.output / name).read_bytes()).hexdigest()
                         for name in sorted(outputs)}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f'Exported {manifest["glyphCount"]} newly completed Italic glyphs on {len(families)} sheets.')


if __name__ == "__main__":
    main()

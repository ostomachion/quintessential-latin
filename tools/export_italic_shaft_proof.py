"""Render before/after compiled outlines for all refined Italic shafts."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

from quintessential_font import OUTPUT, ROOT

WEIGHTS = (400, 500, 550, 600, 700)
VARIABLE = "QuintessentialSerif-Italic-Variable"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path,
                        default=ROOT / ".tmp/italic-shaft-before/compiled" / f"{VARIABLE}.ttf")
    parser.add_argument("--after", type=Path, default=OUTPUT / f"{VARIABLE}.ttf")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images/italic-shaft-alignment")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    targets = json.loads((ROOT / "resources/italic-shaft-targets.json").read_text(encoding="utf-8"))["targets"]
    target_names = {entry["glyphName"] for entry in targets}
    base_names = {entry["glyphName"] for entry in targets
                  if entry["glyphName"] == f'u{int(entry["shaftRecipe"], 16):X}'}
    assert len(target_names) == 150 and len(base_names) == 18
    entries = sorted((entry for entry in allocation["entries"] if entry["glyphName"] in target_names),
                     key=lambda entry: entry["codePoint"])
    if args.png:
        from PIL import Image, ImageDraw, ImageFont
        labels = {size: ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
                  for size in (12, 14, 17, 28)}
    manifest = {"beforeFontSha256": sha256(args.before), "afterFontSha256": sha256(args.after),
                "weights": list(WEIGHTS), "glyphCount": len(entries),
                "baseShaftCount": len(base_names), "overviewWeights": [400, 700],
                "displaySizesPx": [230, 100, 24], "sheets": []}
    bases = [entry for entry in entries if entry["glyphName"] in base_names]
    jobs = [(f"base-shafts-{weight}", "Base shafts", weight, bases, 230) for weight in WEIGHTS]
    jobs += [(f"all-{weight}-{start // 15 + 1:02d}", "All affected constructions", weight,
              entries[start:start + 15], 100)
             for weight in (400, 700) for start in range(0, len(entries), 15)]
    with TTFont(args.before) as before, TTFont(args.after) as after:
        if before.getBestCmap() != after.getBestCmap():
            raise RuntimeError("Before/after character mappings differ")
        for sheet_name, group_title, weight, sheet_entries, size_px in jobs:
            sets = [font.getGlyphSet(location={"wght": weight}) for font in (before, after)]
            width, cell_width = 1380, 440
            cell_height = 360 if size_px == 230 else 250
            height = 140 + ((len(sheet_entries) + 2) // 3) * cell_height
            title = f"{group_title} · Italic {weight}"
            subtitle = f"Before / after · compiled outlines at {size_px}px and 24px · current code points"
            parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
                     f'<title>{html.escape(title)}</title>',
                     f'<rect width="{width}" height="{height}" fill="#faf9f6"/>',
                     f'<text x="30" y="43" fill="#242c27" font-family="Segoe UI,sans-serif" font-size="28">{html.escape(title)}</text>',
                     f'<text x="30" y="74" fill="#687266" font-family="Segoe UI,sans-serif" font-size="17">{html.escape(subtitle)}</text>']
            if args.png:
                raster = Image.new("RGB", (width, height), "#faf9f6")
                draw = ImageDraw.Draw(raster)
                draw.text((30, 10), title, fill="#242c27", font=labels[28])
                draw.text((30, 53), subtitle, fill="#687266", font=labels[17])
                raster_fonts = {}
                for phase, path in enumerate((args.before, args.after)):
                    for size in (size_px, 24):
                        raster_font = ImageFont.truetype(str(path), size)
                        raster_font.set_variation_by_axes([weight])
                        raster_fonts[phase, size] = raster_font
            for index, entry in enumerate(sheet_entries):
                x, y = 30 + index % 3 * cell_width, 100 + index // 3 * cell_height
                code, name = entry["codePoint"], entry["glyphName"]
                full_label = f'U+{code:X} · {entry["canonicalName"]}'
                label = full_label if len(full_label) <= 53 else full_label[:52] + "…"
                parts.extend([
                    f'<g><title>{html.escape(full_label)}</title>',
                    f'<path d="M{x} {y}H{x + cell_width - 20}" stroke="#d8dacf"/>',
                    f'<text x="{x}" y="{y + 24}" fill="#242c27" font-family="Segoe UI,sans-serif" font-size="14">{html.escape(label)}</text>',
                ])
                if args.png:
                    draw.line((x, y, x + cell_width - 20, y), fill="#d8dacf")
                    draw.text((x, y + 6), label, fill="#242c27", font=labels[14])
                for phase, glyphs in enumerate(sets):
                    origin = x + (65 if size_px == 230 else 25) + phase * 210
                    path = SVGPathPen(glyphs)
                    glyphs[name].draw(path)
                    phase_label = ("Before", "After")[phase]
                    parts.append(f'<text x="{origin}" y="{y + 47}" fill="#687266" font-family="Segoe UI,sans-serif" font-size="12">{phase_label}</text>')
                    large_baseline = y + (248 if size_px == 230 else 170)
                    small_baseline = y + cell_height - 25
                    for size, baseline in ((size_px, large_baseline), (24, small_baseline)):
                        scale = size / 1000
                        parts.append(f'<path fill="#242c27" transform="translate({origin} {baseline}) scale({scale:g} {-scale:g})" d="{path.getCommands()}"/>')
                        if args.png:
                            draw.text((origin, baseline), chr(code), font=raster_fonts[phase, size],
                                      fill="#242c27", anchor="ls")
                    if args.png:
                        draw.text((origin, y + 31), phase_label, fill="#687266", font=labels[12])
                parts.append("</g>")
            footer = f"{len(sheet_entries)} constructions · geometry checks and visual review are recorded separately"
            parts.append(f'<text x="30" y="{height - 20}" fill="#687266" font-family="Segoe UI,sans-serif" font-size="14">{footer}</text></svg>')
            name = sheet_name
            svg = args.output / f"{name}.svg"
            svg.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
            sheet = {"weight": weight, "group": group_title, "glyphCount": len(sheet_entries),
                     "codePoints": [f'U+{entry["codePoint"]:X}' for entry in sheet_entries],
                     "svg": svg.name, "svgSha256": sha256(svg)}
            if args.png:
                draw.text((30, height - 40), footer, fill="#687266", font=labels[14])
                png = args.output / f"{name}.png"
                raster.save(png)
                sheet.update(png=png.name, pngSha256=sha256(png))
            manifest["sheets"].append(sheet)
    links = "".join(f'<li><a href="{sheet["svg"]}">{sheet["group"]}, weight {sheet["weight"]}: {sheet["glyphCount"]} glyphs</a></li>'
                    for sheet in manifest["sheets"])
    (args.output / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Italic shaft alignment proofs</title><style>body{max-width:850px;margin:40px auto;padding:0 24px;'
        'background:#faf9f6;color:#242c27;font:18px/1.65 Georgia,serif}a{color:#365746}code{font-size:12px}</style>'
        '<h1>Italic shaft alignment</h1><p>All 18 base shafts at five weights, and all 150 affected constructions '
        'at both endpoints, before and after correction. Base sheets compare compiled outlines at 230px and 24px; '
        'overview sheets use 100px and 24px. Labels use the current allocation.</p>'
        f'<ol>{links}</ol><p>Before SHA-256 <code>{manifest["beforeFontSha256"]}</code><br>'
        f'After SHA-256 <code>{manifest["afterFontSha256"]}</code></p></html>\n', encoding="utf-8")
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(bases)} base shafts at {len(WEIGHTS)} weights and {len(entries)} affected glyphs at both endpoints to {args.output}")


if __name__ == "__main__":
    main()

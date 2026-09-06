"""Export the adopted stemless terminals from both compiled variable fonts.

Each posture sheet includes all three revised glyphs and both unchanged upright
references at 400/500/550/600/700, at display and text sizes. SVG specimens are
actual compiled paths; optional PNG specimens use those same fonts in FreeType.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_ROOT = ROOT / "resources/fonts/QuintessentialSerif"
WEIGHTS = (400, 500, 550, 600, 700)
SIZES = (160, 18, 24, 32)
IDENTITIES = (
    ("special-spine", "Spine", True),
    ("special-turned-open-bowl", "Turned open bowl", True),
    ("special-turned-double-open-bowl", "Turned open double bowl", True),
    ("special-open-bowl", "Open bowl", False),
    ("special-double-open-bowl", "Open double bowl", False),
)
INK, MUTED, PAPER, RULE = "#23241f", "#66695e", "#faf9f6", "#dedfd6"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images/stemless-terminals")
    parser.add_argument("--png", action="store_true")
    parser.add_argument("--expect-roman-sha")
    parser.add_argument("--expect-italic-sha")
    args = parser.parse_args()
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    by_id = {entry["glyphId"]: entry for entry in allocation["entries"]}
    entries = [by_id[identity] for identity, _, _ in IDENTITIES]
    build_path = FONT_ROOT / "build-manifest.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    font_paths = {
        "Roman": FONT_ROOT / "QuintessentialSerif-Variable.ttf",
        "Italic": FONT_ROOT / "QuintessentialSerif-Italic-Variable.ttf",
    }
    hashes = {posture: digest(path) for posture, path in font_paths.items()}
    for posture, path in font_paths.items():
        if hashes[posture] != build["outputs"][path.name]["sha256"]:
            raise RuntimeError(f"{posture} font does not match the current build manifest")
    for posture, expected in (("Roman", args.expect_roman_sha), ("Italic", args.expect_italic_sha)):
        if expected and expected.lower() != hashes[posture]:
            raise RuntimeError(f"{posture} font does not match its expected SHA-256")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "version": build["version"],
        "buildManifestSha256": digest(build_path),
        "allocationSha256": digest(ROOT / "resources/quintessential-latin-allocation.json"),
        "weights": list(WEIGHTS), "sizesPx": list(SIZES),
        "specimensPerPosture": len(IDENTITIES) * len(WEIGHTS),
        "fontHashes": {path.name: hashes[posture] for posture, path in font_paths.items()},
        "glyphs": [{"glyphId": identity, "glyphName": entry["glyphName"],
                    "codePoint": entry["codePoint"], "revised": revised}
                   for (identity, _, revised), entry in zip(IDENTITIES, entries)],
        "sheets": [],
    }
    if args.png:
        from PIL import Image, ImageDraw, ImageFont
        label_path = Path("C:/Windows/Fonts/segoeui.ttf")
        labels = {size: ImageFont.truetype(str(label_path), size) if label_path.is_file()
                  else ImageFont.load_default(size=size) for size in (12, 14, 17, 18, 28)}

    for posture, font_path in font_paths.items():
        width, height = 1730, 1604
        label_width, cell_width, cell_height = 326, 274, 278
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
                 f'<title>Stemless terminals — {posture}</title>',
                 f'<rect width="{width}" height="{height}" fill="{PAPER}"/>']
        if args.png:
            raster = Image.new("RGB", (width, height), PAPER)
            draw = ImageDraw.Draw(raster)
            raster_fonts = {}
            for weight in WEIGHTS:
                for size in SIZES:
                    face = ImageFont.truetype(str(font_path), size)
                    face.set_variation_by_axes([weight])
                    raster_fonts[weight, size] = face

        def label(x, y, text, size=17, color=MUTED):
            parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI, sans-serif" '
                         f'font-size="{size}">{html.escape(text)}</text>')
            if args.png:
                draw.text((x, y), text, font=labels[size], fill=color, anchor="ls")

        label(36, 47, f"Stemless terminals · {posture}", 28, INK)
        label(36, 81, "Three adopted two-bulb forms, with unchanged upright references")
        label(36, 109, "Compiled outlines · 160px em above · repeated specimens at 18px, 24px, and 32px below", 14)
        with TTFont(font_path) as font:
            cmap = font.getBestCmap()
            units = font["head"].unitsPerEm
            glyph_sets = {weight: font.getGlyphSet(location={"wght": weight}) for weight in WEIGHTS}
            for col, weight in enumerate(WEIGHTS):
                label(label_width + col * cell_width + 111, 151, str(weight), 18, INK)
            records = []
            for row, ((identity, title, revised), entry) in enumerate(zip(IDENTITIES, entries)):
                y = 172 + row * cell_height
                parts.append(f'<path d="M36 {y}H{width-36}" stroke="{RULE}"/>')
                if args.png:
                    draw.line((36, y, width-36, y), fill=RULE)
                label(36, y + 40, title, 18, INK)
                label(36, y + 66, f'U+{entry["codePoint"]:X}', 14)
                label(36, y + 93, "Two bulb terminals" if revised else "Unchanged upright reference", 14)
                name = cmap[entry["codePoint"]]
                if name != entry["glyphName"]:
                    raise RuntimeError(f"The compiled cmap changed the identity of {identity}")
                for col, weight in enumerate(WEIGHTS):
                    glyphs = glyph_sets[weight]
                    pen, bounds = SVGPathPen(glyphs), BoundsPen(glyphs)
                    glyphs[name].draw(pen)
                    glyphs[name].draw(bounds)
                    if bounds.bounds is None:
                        raise RuntimeError(f"Empty proof glyph: {identity}")
                    left, bottom, right, top = bounds.bounds
                    x = label_width + col * cell_width
                    records.append({"glyphId": identity, "weight": weight,
                                    "bounds": list(bounds.bounds), "advance": glyphs[name].width})
                    for size, baseline, repeats in ((160, y + 134, 1), (18, y + 180, 3),
                                                    (24, y + 215, 3), (32, y + 258, 3)):
                        scale = size / units
                        advance = glyphs[name].width * scale + size / 2
                        total_width = (repeats - 1) * advance + (right - left) * scale
                        origin = x + (cell_width - total_width) / 2 - left * scale
                        if size != 160:
                            label(x + 2, baseline, str(size), 12)
                        for repeat in range(repeats):
                            here = origin + repeat * advance
                            parts.append(f'<path fill="{INK}" transform="translate({here:g} {baseline}) '
                                         f'scale({scale:g} {-scale:g})" d="{pen.getCommands()}"/>')
                            if args.png:
                                draw.text((here, baseline), chr(entry["codePoint"]),
                                          font=raster_fonts[weight, size], fill=INK, anchor="ls")
            label(36, height - 19, f'{font["name"].getDebugName(5)} · {posture} SHA-256 {hashes[posture]}', 12)
        parts.append("</svg>")
        stem = posture.lower()
        (args.output / f"{stem}.svg").write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
        sheet = {"posture": posture, "file": f"{stem}.svg", "specimens": records}
        if args.png:
            raster.save(args.output / f"{stem}.png")
            sheet["raster"] = f"{stem}.png"
        manifest["sheets"].append(sheet)

    links = "".join(f'<li><a href="{s["file"]}">{s["posture"]} vector sheet</a>'
                    + (f' · <a href="{s["raster"]}">PNG</a>' if "raster" in s else "")
                    + "</li>" for s in manifest["sheets"])
    (args.output / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Stemless terminal proofs</title><style>body{max-width:900px;margin:40px auto;padding:0 24px;'
        'background:#faf9f6;color:#23241f;font:18px/1.6 Georgia,serif}a{color:#405b45}code{font-size:12px}</style>'
        '<h1>Stemless terminal proofs</h1><p>The spine, turned open bowl, and turned open double bowl use '
        'bulbs at both terminals. The upright open bowl and open double bowl appear as unchanged references.</p>'
        '<p>Each sheet shows weights 400, 500, 550, 600, and 700 at 160px em, with repeated 18px, 24px, '
        'and 32px specimens. Every specimen comes from the compiled reference font. These are rendering '
        'proofs; the manifest records the exact fonts and output hashes.</p>'
        f'<ul>{links}</ul><p><a href="manifest.json">Proof manifest</a></p></html>\n',
        encoding="utf-8", newline="\n")
    filenames = ["index.html", *[s["file"] for s in manifest["sheets"]],
                 *[s["raster"] for s in manifest["sheets"] if "raster" in s]]
    manifest["files"] = {name: digest(args.output / name) for name in filenames}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Exported 50 weight/posture specimens at four sizes on two source-faithful sheets.")


if __name__ == "__main__":
    main()

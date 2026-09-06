"""Export all independent middle-component states from compiled variable fonts.

Each row compares neither, left-only, right-only, and both in visual left-to-right
order. Both native postures appear at 400, 550, and 700, with 16px/24px spaced
strings at every weight. Eight constructions per sheet produce 24 proof sheets.
"""

import argparse
from contextlib import ExitStack
import hashlib
import html
import json
from pathlib import Path
import textwrap

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
ALLOCATION = ROOT / "resources/quintessential-latin-allocation.json"
FONT_DIR = ROOT / "resources/fonts/QuintessentialSerif"
WEIGHTS = (400, 550, 700)
POSTURES = ("Roman", "Italic")
STATES = (
    ("Neither", "", (False, False)),
    ("Left only", "-extended-left-middle-leg", (True, False)),
    ("Right only", "-extended-right-middle-leg", (False, True)),
    ("Both", "-extended-middle-legs", (True, True)),
)
BACKGROUND, INK, MUTED, RULE = "#faf9f6", "#242c27", "#687266", "#d8dacf"
WIDTH, MARGIN, PLOT_X, GROUP_WIDTH, STATE_WIDTH = 2160, 36, 300, 610, 145
ROW_HEIGHT, HEADER_HEIGHT, DISPLAY_EM = 458, 144, 92


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return path.resolve().relative_to(ROOT).as_posix()


def selected_cases(allocation):
    by_id = {entry["glyphId"]: entry for entry in allocation["entries"]}
    cases = []
    for glyph_id in allocation["displayOrder"]:
        base = by_id[glyph_id]
        if base["middleLegs"] or sum(bool(part.get("middle")) for part in base["parts"]) != 2:
            continue
        variants = [by_id[glyph_id + suffix] for _, suffix, _ in STATES]
        for entry, (_, _, mask) in zip(variants, STATES):
            actual = tuple(part["lower" if part["kind"] == "leg" else "upper"] == "straight"
                           for part in entry["parts"] if part.get("middle"))
            if actual != mask:
                raise ValueError(f"Incorrect proof state: {entry['glyphId']}: {actual} != {mask}")
        cases.append({"base": base, "variants": variants})
    if len(cases) != 192 or len({entry["glyphId"] for case in cases for entry in case["variants"][1:3]}) != 384:
        raise ValueError("The proof must cover exactly 192 constructions and all 384 additions")
    return cases


class Canvas:
    """Write SVG paths and optional FreeType raster specimens at matching origins."""

    def __init__(self, height, title, raster_fonts=None, labels=None):
        self.height = height
        self.paths = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
                      f'<title>{html.escape(title)}</title>',
                      f'<rect width="{WIDTH}" height="{height}" fill="{BACKGROUND}"/>']
        self.definitions = {}
        self.raster_fonts, self.labels = raster_fonts, labels
        self.raster, self.draw = None, None
        if raster_fonts:
            from PIL import Image, ImageDraw
            self.raster = Image.new("RGB", (WIDTH, height), BACKGROUND)
            self.draw = ImageDraw.Draw(self.raster)

    def text(self, x, baseline, text, size=14, fill=MUTED):
        self.paths.append(f'<text x="{x:g}" y="{baseline:g}" fill="{fill}" '
                          f'font-family="Segoe UI, sans-serif" font-size="{size}">{html.escape(text)}</text>')
        if self.draw:
            self.draw.text((x, baseline), text, fill=fill, font=self.labels[size], anchor="ls")

    def line(self, x1, y1, x2, y2, fill=RULE):
        self.paths.append(f'<path d="M{x1:g} {y1:g}L{x2:g} {y2:g}" stroke="{fill}"/>')
        if self.draw:
            self.draw.line((x1, y1, x2, y2), fill=fill)

    def glyph(self, x, baseline, entry, geometry, posture, weight, size, upem):
        scale = size / upem
        identifier = f'{posture.lower()}-{weight}-{entry["codePoint"]:x}'
        self.definitions.setdefault(identifier, f'<path id="{identifier}" d="{geometry["path"]}"/>')
        self.paths.append(f'<use href="#{identifier}" fill="{INK}" transform="translate({x:g} {baseline:g}) '
                          f'scale({scale:g} {-scale:g})"/>')
        if self.draw:
            self.draw.text((x, baseline), chr(entry["codePoint"]), fill=INK,
                           font=self.raster_fonts[posture, weight, size], anchor="ls")

    def write(self, path):
        path.write_text("\n".join([*self.paths, "<defs>", *self.definitions.values(), "</defs>", "</svg>"]) + "\n",
                        encoding="utf-8", newline="\n")
        if self.raster:
            self.raster.save(path.with_suffix(".png"))


def raster_resources(font_paths):
    from PIL import ImageFont
    label_path = Path("C:/Windows/Fonts/segoeui.ttf")
    if not label_path.is_file():
        raise RuntimeError("PNG proof labels require C:/Windows/Fonts/segoeui.ttf")
    labels = {size: ImageFont.truetype(str(label_path), size) for size in (12, 14, 16, 18, 27)}
    fonts = {}
    for posture, path in font_paths.items():
        for weight in WEIGHTS:
            for size in (DISPLAY_EM, 16, 24):
                font = ImageFont.truetype(str(path), size)
                font.set_variation_by_axes([weight])
                fonts[posture, weight, size] = font
    return fonts, labels


def load_geometry(fonts, cases):
    result = {}
    entries = {entry["glyphId"]: entry for case in cases for entry in case["variants"]}
    for posture, font in fonts.items():
        cmap = font.getBestCmap()
        for entry in entries.values():
            if cmap.get(entry["codePoint"]) != entry["glyphName"]:
                raise ValueError(f"Compiled {posture} coverage mismatch: {entry['glyphId']}")
        for weight in WEIGHTS:
            glyphs = font.getGlyphSet(location={"wght": weight})
            for entry in entries.values():
                pen, bounds = SVGPathPen(glyphs), BoundsPen(glyphs)
                glyph = glyphs[entry["glyphName"]]
                glyph.draw(pen)
                glyph.draw(bounds)
                if bounds.bounds is None:
                    raise ValueError(f"Empty compiled outline: {entry['glyphId']}")
                result[posture, weight, entry["glyphId"]] = {
                    "path": pen.getCommands(), "bounds": bounds.bounds, "advance": glyph.width,
                }
    return result


def draw_case(canvas, case, row_y, titles, geometry, fonts):
    base, variants = case["base"], case["variants"]
    canvas.line(MARGIN, row_y, WIDTH - MARGIN, row_y)
    canvas.text(MARGIN, row_y + 25, f'U+{base["codePoint"]:X} · {base["canonicalName"]}', 18, INK)
    for index, line in enumerate(textwrap.wrap(titles[base["familyId"]], width=27)):
        canvas.text(MARGIN, row_y + 55 + 19 * index, line, 14)
    for posture_index, posture in enumerate(POSTURES):
        top = row_y + 40 + posture_index * 210
        upem = fonts[posture]["head"].unitsPerEm
        space = fonts[posture]["hmtx"].metrics["space"][0]
        canvas.text(MARGIN, top + 74, posture, 18, INK)
        canvas.text(MARGIN, top + 103, "Neither / left / right / both", 14)
        canvas.text(MARGIN, top + 123, "Visual left-to-right positions", 12)
        for weight_index, weight in enumerate(WEIGHTS):
            group_x = PLOT_X + weight_index * GROUP_WIDTH
            canvas.text(group_x, top + 1, f'{posture} {weight}', 14, INK)
            for state_index, (entry, (label, _, _)) in enumerate(zip(variants, STATES)):
                x = group_x + state_index * STATE_WIDTH
                canvas.text(x + 3, top + 22, label, 12)
                canvas.text(x + 3, top + 40, f'U+{entry["codePoint"]:X}', 12)
                data = geometry[posture, weight, entry["glyphId"]]
                left, _, right, _ = data["bounds"]
                scale = DISPLAY_EM / upem
                origin = x + (STATE_WIDTH - (right - left) * scale) / 2 - left * scale
                canvas.glyph(origin, top + 122, entry, data, posture, weight, DISPLAY_EM, upem)
            for size, baseline in ((16, top + 159), (24, top + 191)):
                canvas.text(group_x, baseline, f'{size}px', 12)
                origin = group_x + 42
                # Spaces keep the four states distinct while retaining the
                # compiled font's native advances and a consistent text em.
                for entry in variants * 2:
                    data = geometry[posture, weight, entry["glyphId"]]
                    canvas.glyph(origin, baseline, entry, data, posture, weight, size, upem)
                    origin += (data["advance"] + space) * size / upem


def write_index(output, manifest):
    links = []
    for sheet in manifest["sheets"]:
        label = f'{sheet["order"]:02d} · {sheet["firstBaseCodePoint"]}–{sheet["lastBaseCodePoint"]} · {len(sheet["cases"])} constructions'
        png = f' · <a href="{sheet["png"]}">PNG</a>' if "png" in sheet else ""
        links.append(f'<li><a href="{sheet["svg"]}">{html.escape(label)}</a>{png}</li>')
    fingerprints = "".join(f'<p>{posture}: <code>{record["sha256"]}</code></p>'
                           for posture, record in manifest["fonts"].items())
    output.joinpath("index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Independent middle-component proof</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;'
        'background:#faf9f6;color:#242c27;font:18px/1.65 Georgia,serif}a{color:#365746}code{font:12px/1.7 monospace;'
        'overflow-wrap:anywhere}li{margin:8px 0}</style><h1>Independent middle components</h1>'
        '<p>All 192 constructions and 384 additions. Each row compares neither, left only, right only, and both. '
        'Left and right follow the visible component order, including turned forms and mixed legs and arms.</p>'
        '<p>Both native postures appear at weights 400, 550, and 700, at a fixed 92px em. Every weight also includes '
        '16px and 24px spaced strings in the same four-state order, repeated twice. SVG specimens contain compiled '
        'outlines; optional PNG specimens use the same variable font through FreeType.</p>'
        '<p>Optical inspection and user acceptance remain separate from this generated proof.</p>'
        f'<ol>{"".join(links)}</ol><h2>Source fingerprints</h2>{fingerprints}'
        f'<p>Allocation: <code>{manifest["allocationSha256"]}</code></p></html>', encoding="utf-8", newline="\n")


def verify_manifest(output, font_paths):
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["allocationSha256"] == digest(ALLOCATION.read_bytes()), "Allocation changed"
    assert manifest["exporterSha256"] == digest(Path(__file__).read_bytes()), "Proof generator changed"
    for posture, path in font_paths.items():
        assert manifest["fonts"][posture]["sha256"] == digest(path.read_bytes()), f"{posture} font changed"
    for filename, expected in manifest["files"].items():
        assert digest((output / filename).read_bytes()) == expected, f"Proof file changed: {filename}"
    cases = [case for sheet in manifest["sheets"] for case in sheet["cases"]]
    assert len(cases) == len({case["baseGlyphId"] for case in cases}) == 192
    assert len({entry["glyphId"] for case in cases for entry in case["states"][1:3]}) == 384
    print(f'Verified all 384 additions on {len(manifest["sheets"])} proof sheets and current source hashes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images/independent-middle-legs")
    parser.add_argument("--roman-font", type=Path, default=FONT_DIR / "QuintessentialSerif-Variable.ttf")
    parser.add_argument("--italic-font", type=Path, default=FONT_DIR / "QuintessentialSerif-Italic-Variable.ttf")
    parser.add_argument("--png", action="store_true", help="Also rasterize using Pillow/FreeType")
    parser.add_argument("--list", action="store_true", help="List selected cases without reading fonts or writing files")
    parser.add_argument("--check", action="store_true", help="Verify proof coverage and hashes against current inputs")
    args = parser.parse_args()
    font_paths = {"Roman": args.roman_font, "Italic": args.italic_font}
    if args.check:
        verify_manifest(args.output, font_paths)
        return
    allocation_bytes = ALLOCATION.read_bytes()
    allocation = json.loads(allocation_bytes)
    cases = selected_cases(allocation)
    if args.list:
        for case in cases:
            print(" / ".join(f'U+{entry["codePoint"]:X}' for entry in case["variants"]) + " · " + case["base"]["glyphId"])
        print(f'{len(cases)} constructions, {len(cases) * 2} additions, 24 sheets.')
        return
    manifest = {"schemaVersion": 1, "version": allocation["version"], "constructionCount": 192,
                "additionCount": 384, "postures": list(POSTURES), "weights": list(WEIGHTS),
                "displayEmPx": DISPLAY_EM, "textSizesPx": [16, 24],
                "stateOrder": [label for label, _, _ in STATES],
                "allocationSha256": digest(allocation_bytes), "exporterSha256": digest(Path(__file__).read_bytes()),
                "fonts": {}, "sheets": [], "acceptance": "Visual inspection and user acceptance pending"}
    raster_fonts, labels = raster_resources(font_paths) if args.png else (None, None)
    titles = {family["id"]: family["title"] for family in allocation["families"]}
    with ExitStack() as stack:
        fonts = {posture: stack.enter_context(TTFont(path)) for posture, path in font_paths.items()}
        geometry = load_geometry(fonts, cases)
        for posture, path in font_paths.items():
            manifest["fonts"][posture] = {"file": relative(path), "sha256": digest(path.read_bytes()),
                                            "version": fonts[posture]["name"].getDebugName(5)}
        args.output.mkdir(parents=True, exist_ok=True)
        for offset in range(0, len(cases), 8):
            group, order = cases[offset:offset + 8], offset // 8 + 1
            height = HEADER_HEIGHT + len(group) * ROW_HEIGHT + 90
            title = f'Independent middle components · {order:02d} / 24'
            canvas = Canvas(height, title, raster_fonts, labels)
            canvas.text(MARGIN, 43, title, 27, INK)
            canvas.text(MARGIN, 74, 'Neither / left only / right only / both · Roman and native Italic · 400 / 550 / 700 · 92px em', 18)
            canvas.text(MARGIN, 102, 'Spaced four-state strings at 16px and 24px, repeated twice · Side positions are visual left-to-right', 16)
            for row, case in enumerate(group):
                draw_case(canvas, case, HEADER_HEIGHT + row * ROW_HEIGHT, titles, geometry, fonts)
            for index, posture in enumerate(POSTURES):
                canvas.text(MARGIN, height - 53 + 23 * index,
                            f'{posture} SHA-256 {manifest["fonts"][posture]["sha256"]}', 14)
            filename = f'{order:02d}-independent-middle-components.svg'
            canvas.write(args.output / filename)
            sheet = {"order": order, "svg": filename, "width": WIDTH, "height": height,
                     "firstBaseCodePoint": f'U+{group[0]["base"]["codePoint"]:X}',
                     "lastBaseCodePoint": f'U+{group[-1]["base"]["codePoint"]:X}', "cases": []}
            if args.png:
                sheet["png"] = filename.replace(".svg", ".png")
            for case in group:
                sheet["cases"].append({"baseGlyphId": case["base"]["glyphId"], "familyId": case["base"]["familyId"],
                                       "states": [{"glyphId": entry["glyphId"], "codePoint": f'U+{entry["codePoint"]:X}',
                                                   "canonicalName": entry["canonicalName"], "middleLegExtensions": list(mask)}
                                                  for entry, (_, _, mask) in zip(case["variants"], STATES)]})
            manifest["sheets"].append(sheet)
    write_index(args.output, manifest)
    outputs = ["index.html", *[sheet["svg"] for sheet in manifest["sheets"]],
               *[sheet["png"] for sheet in manifest["sheets"] if "png" in sheet]]
    manifest["files"] = {filename: digest((args.output / filename).read_bytes()) for filename in sorted(outputs)}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f'Exported all 384 additions in 192 four-state comparisons on {len(manifest["sheets"])} sheets, both postures at three weights.')


if __name__ == "__main__":
    main()

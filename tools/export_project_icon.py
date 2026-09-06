"""Export the project mark from its stable construction in the Roman font."""
import argparse
import json
from pathlib import Path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def assets():
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    entry = next(entry for entry in allocation["entries"] if entry["glyphId"] == "opposed-bowls-0-0")
    with TTFont(ROOT / "resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf") as font:
        name = font.getBestCmap()[entry["codePoint"]]
        assert name == entry["glyphName"]
        result = {}
        for filename, weight in (("project-icon.svg", 400), ("favicon.svg", 500)):
            glyphs = font.getGlyphSet(location={"wght": weight})
            bounds, path = BoundsPen(glyphs), SVGPathPen(glyphs)
            glyphs[name].draw(bounds)
            glyphs[name].draw(path)
            x0, y0, x1, y1 = bounds.bounds
            dx, dy = 300-(x0+x1)/2, 300+(y0+y1)/2
            mark = f'<path fill="#000000" transform="translate({dx:g} {dy:g}) scale(1 -1)" d="{path.getCommands()}"/>'
            title = f'<title>Quintessential Latin</title><desc>U+{entry["codePoint"]:X}, {entry["canonicalName"]}. Quintessential Serif, Roman weight {weight}, derived from STIX Two Text. SIL Open Font License 1.1.</desc>'
            background = '<rect width="600" height="600" rx="64" fill="#ffffff"/>' if filename == "favicon.svg" else ""
            result[filename] = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">{title}{background}{mark}</svg>\n'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for filename, content in assets().items():
        target = ROOT / "site/assets" / filename
        if args.check:
            assert target.read_text(encoding="utf-8") == content, f"Stale {filename}; regenerate from the compiled font"
        else:
            target.write_text(content, encoding="utf-8", newline="\n")
    print("Verified project icon and favicon against the compiled Roman construction.")


if __name__ == "__main__":
    main()

"""Export the project mark from the actual Roman U+F2B18 font outline."""
import argparse
from pathlib import Path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def assets():
    with TTFont(ROOT / "resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf") as font:
        name = font.getBestCmap()[0xF2B18]
        glyphs = font.getGlyphSet()
        bounds, path = BoundsPen(glyphs), SVGPathPen(glyphs)
        glyphs[name].draw(bounds)
        glyphs[name].draw(path)
        x0, y0, x1, y1 = bounds.bounds
        dx, dy = 300-(x0+x1)/2, 300+(y0+y1)/2
        mark = f'<path fill="#365746" transform="translate({dx:g} {dy:g}) scale(1 -1)" d="{path.getCommands()}"/>'
    title = '<title>Quintessential Latin</title><desc>U+F2B18, stem with spine and stem. Quintessential Serif, derived from STIX Two Text. SIL Open Font License 1.1.</desc>'
    return {
        "project-icon.svg": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">{title}{mark}</svg>\n',
        "favicon.svg": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">{title}<rect width="600" height="600" rx="64" fill="#faf9f6"/>{mark}</svg>\n',
    }


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
    print("Verified project icon and favicon against compiled Roman U+F2B18.")


if __name__ == "__main__":
    main()

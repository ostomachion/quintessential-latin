"""Export all 396 refined-spine glyphs, pairing Regular and Bold in each cell."""

import argparse
from collections import defaultdict
import hashlib
import html
import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images/shared-spines")
    args = parser.parse_args()
    allocation = json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text(encoding="utf-8"))
    titles = {f["id"]: f["title"] for f in allocation["families"]}
    families = defaultdict(list)
    for entry in allocation["entries"]:
        if any(p["kind"] == "spine" for p in entry["parts"][1:-1]):
            families[entry["familyId"]].append(entry)
    font_path = ROOT / "resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf"
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"fontSha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
                "weights": [400, 700], "glyphs": sum(map(len, families.values())), "sheets": []}
    with TTFont(font_path) as font:
        sets = [font.getGlyphSet(location={"wght": weight}) for weight in (400, 700)]
        for order, (family, entries) in enumerate(families.items(), 1):
            entries.sort(key=lambda e: e["codePoint"])
            width, height, cell_w, cell_h = 1920, 1410, 308, 204
            parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
                f'<title>{html.escape(titles[family])}: all 36 Regular and Bold forms</title>',
                f'<rect width="{width}" height="{height}" fill="#faf9f6"/>',
                f'<g fill="#242c27" font-family="Segoe UI, sans-serif"><text x="36" y="44" font-size="27">{html.escape(titles[family])}</text>',
                '<text x="36" y="76" font-size="17" fill="#687266">Compiled Quintessential Serif · Regular / Bold in each cell · Uniform 108px em, native proportions</text>',
                '<text x="36" y="103" font-size="16" fill="#687266">Refined shared spine with independent endings, arches, and middle components</text></g>']
            for index, entry in enumerate(entries):
                x, y = 36 + index % 6 * cell_w, 124 + index // 6 * cell_h
                parts.append(f'<path d="M{x} {y}H{x+cell_w-14}" stroke="#d8dacf"/>')
                parts.append(f'<text x="{x+5}" y="{y+24}" fill="#687266" font-family="Segoe UI, sans-serif" font-size="15">U+{entry["codePoint"]:X}</text>')
                for column, glyphs in enumerate(sets):
                    name = entry["glyphName"]
                    pen, box = SVGPathPen(glyphs), BoundsPen(glyphs)
                    glyphs[name].draw(pen)
                    glyphs[name].draw(box)
                    left, bottom, right, top = box.bounds
                    # Keep em size fixed across families so differences in
                    # optical weight and branch proportion remain visible.
                    scale = .108
                    origin = x + column * 147 + (142 - (right-left)*scale)/2 - left*scale
                    baseline = y + 135
                    parts.append(f'<path fill="{"#365746" if column == 0 else "#242c27"}" transform="translate({origin:g} {baseline}) scale({scale} {-scale})" d="{pen.getCommands()}"/>')
            parts.append(f'<text x="36" y="1381" fill="#687266" font-family="Segoe UI, sans-serif" font-size="15">{order:02d} / {len(families):02d} · {len(entries)} characters · {family}</text></svg>')
            filename = f"{order:02d}-{family}.svg"
            (args.output / filename).write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
            manifest["sheets"].append({"file": filename, "family": family,
                "characters": [f'U+{e["codePoint"]:X}' for e in entries]})
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {manifest['glyphs']} glyphs at two weights on {len(families)} sheets.")


if __name__ == "__main__":
    main()

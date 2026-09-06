#!/usr/bin/env python3
"""Export labeled, font-independent close-ups of every shared-spine join class.

The compiled-font digest is mandatory: a proof must explicitly identify the
binary under review. PNG rendering is optional and uses the pinned Playwright
dependency; the index and every SVG contain outlines, never a webfont.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
from io import BytesIO
import json
import math
from pathlib import Path
import subprocess
import textwrap

import pyclipper
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

from font_geometry_helpers import PolygonPen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FONT = ROOT / "resources/fonts/QuintessentialSerif/QuintessentialSerif-Variable.ttf"
OUTPUT = ROOT / "docs/images/shared-spine-connections"
BASE_CASES = (
    (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
    (1, 0), (1, 2), (1, 4), (2, 0), (3, 0), (4, 0), (4, 1),
    (5, 3), (5, 5),
)
ARCH_FAMILIES = (
    "left-arched-opposed-bowls", "right-arched-opposed-bowls",
    "left-double-arched-opposed-bowls", "right-double-arched-opposed-bowls",
)
MIDDLE_CASES = (
    "left-arched-opposed-bowls-0-0",
    "left-arched-opposed-bowls-1-2",
    "left-arched-opposed-bowls-0-4",
    "right-arched-opposed-bowls-0-0",
    "right-arched-opposed-bowls-4-0",
    "left-double-arched-opposed-bowls-1-0",
    "left-double-arched-opposed-bowls-1-4",
    "right-double-arched-opposed-bowls-0-0",
    "double-arched-opposed-bowls-0-0",
    "left-double-arched-opposed-bowls-1-2",
)
LOWER_HOOK_CASES = {
    "opposed-bowls-1-4", "opposed-bowls-5-5",
    "left-arched-opposed-bowls-0-4-extended-middle-legs",
    "left-double-arched-opposed-bowls-1-4-extended-middle-legs",
}
CORE_CONNECTIONS = (
    "Upper-left bowl-to-shaft shoulder",
    "Lower-right bowl-to-shaft hip",
    "Upper-right body return",
    "Lower-left body return",
)
WEIGHTS = (400, 700)
DISPLAY_EM = 680
CONTEXT_EMS = (24, 48)
OVERVIEW_CASES = (
    ("opposed-bowls-0-1", "Upper body return", "Ascender beside the upper bowl"),
    ("opposed-bowls-1-0", "Lower body return", "Descender beside the lower bowl"),
    ("opposed-bowls-1-4", "Closed lower tail", "Tail enclosure beside a descender"),
    ("left-arched-opposed-bowls-0-0", "Incoming arch valley", "Last arch meets the spine shoulder"),
    ("double-arched-opposed-bowls-0-0", "Two arch valleys", "Incoming and outgoing arch connections"),
)
INK = "#242c27"
MUTED = "#667165"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def selected_cases(entries):
    by_id = {entry["glyphId"]: entry for entry in entries}
    specs = [(f"opposed-bowls-{left}-{right}", "Body and native endings")
             for left, right in BASE_CASES]
    specs.extend((f"{family}-{variant}-{variant}", "Arch endings and valleys")
                 for family in ARCH_FAMILIES for variant in range(6))
    specs.append(("double-arched-opposed-bowls-0-0", "Arch endings and valleys"))
    specs.extend((f"{base}-extended-middle-legs", "Middle legs and closures")
                 for base in MIDDLE_CASES)
    assert len(specs) == len({key for key, _ in specs}) == 50
    cases = []
    for key, group in specs:
        entry = by_id[key]
        assert any(part["kind"] == "spine" for part in entry["parts"][1:-1]), key
        labels = list(CORE_CONNECTIONS)
        interior = entry["parts"][1:-1]
        left_arches = sum(part["kind"] == "leg" for part in interior)
        right_arches = sum(part["kind"] == "arm" for part in interior)
        if left_arches:
            labels.extend(("Incoming arch crowns and shaft entries",
                           "Upper valley between the last incoming arch and spine shoulder"))
        if right_arches:
            labels.extend(("Outgoing arch returns and shaft entries",
                           "Lower valley between spine return and first outgoing arch"))
        if max(left_arches, right_arches) > 1:
            labels.append("Repeated-arch neck and intervening shared shaft")
        for side, part in (("Left", entry["parts"][0]), ("Right", entry["parts"][-1])):
            for position in ("upper", "lower"):
                if part.get(position) == "curved":
                    labels.append(f"{side} {position} curved ending: neck and terminal")
                elif part.get(position) == "straight":
                    labels.append(f"{side} {position} extension: shaft-to-body transition")
        if entry["middleLegs"]:
            labels.append("Receiving shared shaft beside extended middle leg")
            labels.append("Middle-leg exits and adjoining feet")
        if key in {"left-double-arched-opposed-bowls-1-0-extended-middle-legs",
                   "left-double-arched-opposed-bowls-1-4-extended-middle-legs",
                   "left-double-arched-opposed-bowls-1-2-extended-middle-legs"}:
            labels.append("Joined middle-foot bar")
        if key == "left-double-arched-opposed-bowls-1-2-extended-middle-legs":
            labels.append("Five-space interaction: two body counters, two foot bridges, and terminal enclosure")
        if key in LOWER_HOOK_CASES:
            labels.append("Lower-hook closure throat beside the adjacent upright")
        if (not left_arches and not right_arches
                and entry["parts"][0].get("upper") == "curved"
                and entry["parts"][-1].get("upper") == "straight"):
            labels.append("Upper-hook enclosure beside the adjacent upright")
        cases.append({"entry": entry, "group": group, "connections": labels})
    return cases


def svg_text(x, y, value, size=18, fill=INK, **attributes):
    extra = " ".join(f'{key.replace("_", "-")}="{html.escape(str(value), quote=True)}"'
                     for key, value in attributes.items())
    return (f'<text x="{x:g}" y="{y:g}" font-family="Segoe UI, sans-serif" '
            f'font-size="{size}" fill="{fill}" {extra}>{html.escape(value)}</text>')


def glyph_path(data, x, baseline, scale):
    return (f'<path fill="{INK}" transform="translate({x:g} {baseline:g}) '
            f'scale({scale:g} {-scale:g})" d="{data["path"]}"/>')


def filled_topology(glyph_set, name):
    pen = PolygonPen(glyph_set, steps=96)
    glyph_set[name].draw(pen)
    paths = [[(round(x * 64), round(y * 64)) for x, y in contour] for contour in pen.paths]
    clipper = pyclipper.Pyclipper()
    clipper.AddPaths(paths, pyclipper.PT_SUBJECT, True)
    tree = clipper.Execute2(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
    assert len(tree.Childs) == 1, (name, "Disconnected body, arch, or ending")
    body = tree.Childs[0]
    assert all(hole.IsHole and not hole.Childs for hole in body.Childs), (name, "Nested enclosure")
    return {"connectedBodies": 1, "enclosedSpaces": len(body.Childs), "outlineContours": len(paths)}


def svg_sheet(case, glyphs, units_per_em, sha, generated, label):
    entry = case["entry"]
    scale = DISPLAY_EM / units_per_em
    width_at_scale = max((data["bounds"][2] - data["bounds"][0]) * scale for data in glyphs)
    panel_width = max(540, math.ceil(width_at_scale + 120))
    width = panel_width * 2 + 80
    title = f'U+{entry["codePoint"]:X} · {entry["canonicalName"]}'
    title_lines = textwrap.wrap(title, width=max(70, int((width - 80) / 11)))
    label_lines = textwrap.wrap("Inspect: " + "; ".join(case["connections"]),
                               width=max(85, int((width - 80) / 8.5)))
    y = 40
    header = []
    for line in title_lines:
        header.append(svg_text(30, y, line, 23))
        y += 30
    header.append(svg_text(30, y, f"{label} · Compiled Roman outlines · {DISPLAY_EM}px em", 17, MUTED))
    y += 25
    header.append(svg_text(30, y, f"Font SHA-256 {sha}", 14, MUTED))
    y += 22
    header.append(svg_text(30, y, f"Exported {generated} · {entry['glyphId']} · {entry['glyphName']}", 14, MUTED))
    y += 30
    for line in label_lines:
        header.append(svg_text(30, y, line, 17, MUTED))
        y += 23
    header_bottom = y + 10
    top = max(data["bounds"][3] for data in glyphs)
    bottom = min(data["bounds"][1] for data in glyphs)
    baseline = header_bottom + 60 + top * scale
    ink_bottom = baseline - bottom * scale
    contexts_top = ink_bottom + 60
    height = math.ceil(contexts_top + 190)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<title>{html.escape(title)}</title>',
             f'<desc>{html.escape("; ".join(case["connections"]))}. Regular and Bold compiled outlines, with 24 and 48 pixel contexts.</desc>',
             f'<rect width="{width}" height="{height}" fill="#faf9f6"/>', *header,
             f'<path d="M30 {header_bottom}H{width-30}" stroke="#d8dacf"/>']
    for col, (weight, data) in enumerate(zip(WEIGHTS, glyphs)):
        left = 40 + col * panel_width
        parts.append(svg_text(left, header_bottom + 31,
                              f'{"Regular" if weight == 400 else "Bold"} · {weight}', 20))
        parts.append(svg_text(left + 170, header_bottom + 31,
                              f'1 connected body · {data["topology"]["enclosedSpaces"]} enclosed spaces', 16, MUTED))
        xmin, _, xmax, _ = data["bounds"]
        origin = left + (panel_width - (xmax - xmin) * scale) / 2 - xmin * scale
        parts.append(glyph_path(data, origin, baseline, scale))
        parts.append(f'<path d="M{left} {contexts_top-19:g}H{left+panel_width-30}" stroke="#d8dacf"/>')
        for index, size in enumerate(CONTEXT_EMS):
            ctx_scale = size / units_per_em
            ctx_top = contexts_top + index * 69
            ctx_baseline = ctx_top + max(top, 0) * ctx_scale
            parts.append(svg_text(left, ctx_baseline, f"{size}px", 16, MUTED))
            ctx_origin = left + 74 - min(xmin, 0) * ctx_scale
            for repeat in range(5):
                parts.append(glyph_path(data, ctx_origin + repeat * data["advance"] * ctx_scale,
                                        ctx_baseline, ctx_scale))
    parts.append(svg_text(30, height - 22,
                          "Same compiled outline at each size; repeated glyphs use native advances. No webfont dependency.",
                          14, MUTED))
    parts.append("</svg>")
    return "\n".join(parts) + "\n", width, height


def svg_overview(cases_by_id, data_by_id, units_per_em, sha, generated, label):
    width, panel_width, label_width = 1160, 410, 290
    scale = 220 / units_per_em
    parts = [svg_text(30, 41, "Shared-spine connections", 31),
             svg_text(30, 74, f"{label} · Regular and Bold · Fixed 220px em", 18, MUTED),
             svg_text(30, 102, f"Font SHA-256 {sha}", 14, MUTED),
             svg_text(30, 126, f"Exported {generated} · Compiled outlines; no webfont dependency", 14, MUTED),
             svg_text(label_width + 45, 164, "Regular · 400", 18),
             svg_text(label_width + panel_width + 45, 164, "Bold · 700", 18)]
    y = 188
    for key, title, caption in OVERVIEW_CASES:
        entry = cases_by_id[key]["entry"]
        glyphs = data_by_id[key]
        top = max(data["bounds"][3] for data in glyphs)
        bottom = min(data["bounds"][1] for data in glyphs)
        row_height = max(180, math.ceil((top - bottom) * scale + 64))
        parts.append(f'<path d="M30 {y}H{width-30}" stroke="#d8dacf"/>')
        parts.append(svg_text(30, y + 36, title, 21))
        parts.append(svg_text(30, y + 65, f'U+{entry["codePoint"]:X}', 16, MUTED))
        for line_index, line in enumerate(textwrap.wrap(caption, width=27)):
            parts.append(svg_text(30, y + 94 + line_index * 22, line, 17, MUTED))
        baseline = y + 30 + top * scale
        for column, data in enumerate(glyphs):
            xmin, _, xmax, _ = data["bounds"]
            left = label_width + column * panel_width
            origin = left + (panel_width - (xmax - xmin) * scale) / 2 - xmin * scale
            parts.append(glyph_path(data, origin, baseline, scale))
        y += row_height
    height = y + 48
    parts.append(svg_text(30, height - 21, "Five representative connection classes; the full index contains all 50 labeled case sheets.", 15, MUTED))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
           '<title>Shared-spine connection overview: five classes at Regular and Bold</title>\n'
           f'<rect width="{width}" height="{height}" fill="#faf9f6"/>\n' + "\n".join(parts) + "\n</svg>\n")
    return svg, width, height


def write_index(output, manifest):
    pieces = ["<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">",
              '<meta name="viewport" content="width=device-width, initial-scale=1">',
              '<title>Shared-spine connection proofs</title>',
              '<style>body{margin:0;background:#faf9f6;color:#242c27;font:18px/1.55 Georgia,serif}main{max-width:1160px;margin:auto;padding:36px 28px 80px}h1{font-weight:normal;font-size:42px;line-height:1.15}h2{font-size:27px;font-weight:normal}p{max-width:920px}code{font:14px/1.6 Consolas,monospace;overflow-wrap:anywhere}a{color:#365746}.revision{border-block:1px solid #d8dacf;padding:18px 0;margin:28px 0}nav{columns:2;column-gap:44px;margin:28px 0}nav a{display:block;break-inside:avoid;margin-bottom:6px}section{border-top:1px solid #d8dacf;padding:26px 0 18px;margin-top:24px}.sheet{overflow:auto;border:1px solid #d8dacf;background:#faf9f6}.sheet img{display:block;max-width:none}.meta{color:#667165;font-size:16px}.connections{padding-left:22px;columns:2;column-gap:36px;font-size:16px}.connections li{break-inside:avoid;margin-bottom:5px}summary{cursor:pointer;color:#365746;margin:14px 0}footer{margin-top:40px;color:#667165}@media(max-width:650px){main{padding:24px 16px}h1{font-size:34px}nav,.connections{columns:1}}</style>',
              '<main><h1>Shared-spine connection proofs</h1>',
              '<p>Review the body returns, shoulders, arch valleys, endings, and middle-leg connections at a fixed scale. Each paired sheet uses the compiled Regular and Bold outlines at 680 pixels per em, followed by 24 and 48 pixel contexts. Wide sheets scroll horizontally.</p>',
              f'<div class="revision"><strong>{html.escape(manifest["label"])}</strong><br>Font SHA-256 <code>{manifest["fontSha256"]}</code><br>Exported <time>{manifest["generatedAt"]}</time><br>{len(manifest["cases"])} connection cases · {len(manifest["cases"])*len(WEIGHTS)} endpoint specimens · <a href="manifest.json">Hash manifest</a></div>',
              '<p class="meta">These are self-contained outline proofs. A fresh font build requires a fresh export; the visible digest identifies the exact reviewed binary. The earlier full-family sheets and optical records remain separate snapshots.</p>',
              f'<a href="overview.svg"><img src="overview.svg?sha={manifest["overview"]["svgSha256"]}" width="{manifest["overview"]["width"]}" height="{manifest["overview"]["height"]}" style="display:block;max-width:100%;height:auto" alt="Five representative connection classes, paired at Regular and Bold"></a>',
              '<nav aria-label="Connection cases">']
    for item in manifest["cases"]:
        pieces.append(f'<a href="#{item["id"]}">{item["order"]:02d} · {item["codePoint"]} · {html.escape(item["canonicalName"])}</a>')
    pieces.append("</nav>")
    for item in manifest["cases"]:
        pieces.extend((f'<section id="{item["id"]}"><p class="meta">{html.escape(item["group"])}</p>',
                       f'<h2>{item["order"]:02d} · {item["codePoint"]} · {html.escape(item["canonicalName"])}</h2>',
                       f'<p class="meta"><code>{item["glyphId"]}</code></p>',
                       '<details><summary>Connections in this case</summary><ul class="connections">'))
        pieces.extend(f'<li>{html.escape(label)}</li>' for label in item["connections"])
        pieces.extend(('</ul></details>',
                       f'<div class="sheet"><img loading="lazy" src="{item["svg"]}?sha={item["svgSha256"]}" width="{item["width"]}" height="{item["height"]}" alt="{html.escape(item["canonicalName"], quote=True)}; Regular and Bold connection proof"></div>',
                       f'<p><a href="{item["svg"]}">Open full-size SVG</a>'))
        if "png" in item:
            pieces.append(f' · <a href="{item["png"]}">PNG</a>')
        pieces.append('</p></section>')
    pieces.append('<footer>Connection inspection and user aesthetic acceptance are separate outcomes. This proof index does not publish the font or website.</footer></main></html>')
    (output / "index.html").write_text("\n".join(pieces) + "\n", encoding="utf-8", newline="\n")


PNG_RENDERER = r"""
import {chromium} from 'playwright';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const dir=process.argv[1];
const manifest=JSON.parse(await readFile(path.join(dir,'manifest.json'),'utf8'));
const browser=await chromium.launch({headless:true});
try {
  const page=await browser.newPage({deviceScaleFactor:1});
  for(const item of [...manifest.cases,manifest.overview]) {
    if(item.png) continue;
    await page.setViewportSize({width:item.width,height:item.height});
    await page.setContent('<!doctype html><style>html,body{margin:0;padding:0}svg{display:block}</style>'+await readFile(path.join(dir,item.svg),'utf8'));
    await page.screenshot({path:path.join(dir,item.svg.replace(/\.svg$/,'.png'))});
  }
} finally {await browser.close();}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--expect-font-sha", help="Required SHA-256 of the compiled font being reviewed")
    parser.add_argument("--label", default="Connection audit")
    parser.add_argument("--revision", default="shared-spine-2")
    parser.add_argument("--generated-at", help="ISO UTC time; omit to record the current export time")
    parser.add_argument("--png", action="store_true", help="Also render PNGs with the repository's Playwright")
    parser.add_argument("--append-existing", action="store_true", help="Preserve verified existing case sheets when appending inventory cases")
    parser.add_argument("--list", action="store_true", help="List cases without exporting or reading a font")
    args = parser.parse_args()
    allocation_path = ROOT / "resources/quintessential-latin-allocation.json"
    allocation_bytes = allocation_path.read_bytes()
    cases = selected_cases(json.loads(allocation_bytes)["entries"])
    if args.list:
        for index, case in enumerate(cases, 1):
            entry = case["entry"]
            print(f'{index:02d} U+{entry["codePoint"]:X} {entry["glyphId"]} · {entry["canonicalName"]}')
        return
    if not args.expect_font_sha:
        parser.error("--expect-font-sha is required to bind the proof to its reviewed binary")
    font_bytes = args.font.read_bytes()
    sha = digest(font_bytes)
    if sha != args.expect_font_sha.lower():
        parser.error(f"Compiled font mismatch: expected {args.expect_font_sha}; found {sha}")
    generated = args.generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    previous = None
    if args.append_existing:
        previous = json.loads((args.output / "manifest.json").read_text(encoding="utf-8"))
        assert previous["fontSha256"] == sha and previous["revision"] == args.revision
        assert previous["allocationSha256"] == digest(allocation_bytes)
        assert [item["glyphId"] for item in previous["cases"]] == [case["entry"]["glyphId"] for case in cases[:len(previous["cases"])]]
        for item in previous["cases"]:
            for kind in ("svg", "png"):
                if kind in item:
                    assert digest((args.output / item[kind]).read_bytes()) == item[kind + "Sha256"]
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"schemaVersion": 1, "revision": args.revision,
                "opticalDesign": "compact-spine-3", "connectionDesign": "shared-spine-joins-1",
                "label": args.label, "generatedAt": generated,
                "font": relative(args.font), "fontSha256": sha,
                "fontFileModifiedAt": datetime.fromtimestamp(args.font.stat().st_mtime, timezone.utc).isoformat(),
                "allocationSha256": digest(allocation_bytes),
                "exporterSha256": digest(Path(__file__).read_bytes()),
                "weights": list(WEIGHTS), "displayEmCssPx": DISPLAY_EM,
                "contextEmCssPx": list(CONTEXT_EMS), "cases": []}
    with TTFont(BytesIO(font_bytes)) as font:
        cmap = font.getBestCmap()
        sets = [font.getGlyphSet(location={"wght": weight}) for weight in WEIGHTS]
        data_by_id = {}
        for index, case in enumerate(cases, 1):
            entry = case["entry"]
            assert cmap[entry["codePoint"]] == entry["glyphName"], entry["glyphId"]
            glyphs = []
            for glyph_set in sets:
                pen, bounds = SVGPathPen(glyph_set), BoundsPen(glyph_set)
                glyph = glyph_set[entry["glyphName"]]
                glyph.draw(pen)
                glyph.draw(bounds)
                assert bounds.bounds is not None
                glyphs.append({"path": pen.getCommands(), "bounds": bounds.bounds, "advance": glyph.width,
                               "topology": filled_topology(glyph_set, entry["glyphName"])})
            assert glyphs[0]["topology"]["enclosedSpaces"] == glyphs[1]["topology"]["enclosedSpaces"], entry["glyphId"]
            data_by_id[entry["glyphId"]] = glyphs
            if previous and index <= len(previous["cases"]):
                item = previous["cases"][index - 1].copy()
                assert item["connections"] == case["connections"]
                item.setdefault("generatedAt", previous["generatedAt"])
                item.setdefault("exporterSha256", previous["exporterSha256"])
                manifest["cases"].append(item)
                continue
            svg, width, height = svg_sheet(case, glyphs, font["head"].unitsPerEm, sha, generated, args.label)
            filename = f'{index:02d}-{entry["glyphId"]}.svg'
            svg_bytes = svg.encode("utf-8")
            (args.output / filename).write_bytes(svg_bytes)
            manifest["cases"].append({"id": f"case-{index:02d}", "order": index,
                                      "group": case["group"], "codePoint": f'U+{entry["codePoint"]:X}',
                                      "glyphId": entry["glyphId"], "glyphName": entry["glyphName"],
                                      "canonicalName": entry["canonicalName"], "family": entry["familyId"],
                                      "connections": case["connections"], "svg": filename,
                                      "generatedAt": generated, "exporterSha256": manifest["exporterSha256"],
                                      "topology": {str(weight): data["topology"] for weight, data in zip(WEIGHTS, glyphs)},
                                      "svgSha256": digest(svg_bytes), "width": width, "height": height})
        overview, width, height = svg_overview({case["entry"]["glyphId"]: case for case in cases},
                                              data_by_id, font["head"].unitsPerEm, sha, generated, args.label)
        overview_bytes = overview.encode("utf-8")
        (args.output / "overview.svg").write_bytes(overview_bytes)
        manifest["overview"] = {"svg": "overview.svg", "svgSha256": digest(overview_bytes),
                                "width": width, "height": height, "displayEmCssPx": 220,
                                "glyphIds": [key for key, _, _ in OVERVIEW_CASES]}
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.png:
        subprocess.run(["node", "--input-type=module", "-e", PNG_RENDERER, str(args.output.resolve())],
                       cwd=ROOT, check=True)
        for item in [*manifest["cases"], manifest["overview"]]:
            item["png"] = item["svg"].removesuffix(".svg") + ".png"
            item["pngSha256"] = digest((args.output / item["png"]).read_bytes())
    write_index(args.output, manifest)
    manifest["indexSha256"] = digest((args.output / "index.html").read_bytes())
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Exported {len(cases)} labeled connection cases at 680/24/48px em; font {sha}.")


if __name__ == "__main__":
    main()

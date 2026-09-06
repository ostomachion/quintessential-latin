"""Deterministic, allocation-led drawings and optical proofs for middle shared spines."""
from __future__ import annotations

import copy
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "resources/unifont"
QA = DIR / "qa-middle-shared-spines"
FAMILIES = ("left-arched-opposed-bowls", "right-arched-opposed-bowls", "double-arched-opposed-bowls")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def points(rows):
    return {(x, y) for y, row in enumerate(rows) for x, value in enumerate(row) if value == "#"}


def rows(ink):
    return ["".join("#" if (x, y) in ink else "." for x in range(8)) for y in range(16)]


def coordinates(ink):
    return [list(p) for p in sorted(ink, key=lambda p: (p[1], p[0]))]


def components(ink, diagonal):
    remaining = set(ink)
    result = []
    while remaining:
        component = {remaining.pop()}
        queue = list(component)
        while queue:
            x, y = queue.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not (dx or dy) or (not diagonal and abs(dx) + abs(dy) != 1):
                        continue
                    p = x + dx, y + dy
                    if p in remaining:
                        remaining.remove(p)
                        component.add(p)
                        queue.append(p)
        result.append(component)
    return result


def topology(ink):
    white = components({(x, y) for x in range(8) for y in range(16)} - ink, False)
    counters = [c for c in white if all(x not in (0, 7) and y not in (0, 15) for x, y in c)]
    return len(components(ink, True)), sorted(map(len, counters))


def body(family, contextual_tail=False):
    if contextual_tail:
        ink, staves, core = body(family)
        if family == FAMILIES[0]:
            # Native script-g lower return, compacted into the shared bowl bay.
            # Leave row 13 open on the left; an independently extended leg
            # supplies its explicit one-pixel bridge there.
            ink -= {(x, y) for x in range(3, 8) for y in (11, 12, 13)}
            # Keep the waist entrance open at (6,11); copying the full-width
            # inward shoulder here would split this compact lower counter.
            ink |= {(3, 11), (7, 11), (4, 12), (5, 12), (6, 12), (7, 12), (7, 13)}
        else:
            # The two-column native-y hip rises one row. Its shared left
            # boundary still belongs to the unchanged central spine.
            ink.discard((6, 13))
            ink.add((6, 12))
        return ink, staves, core
    if family == FAMILIES[2]:
        # Approved F2EBC body, with the user's crossover at row 9.
        rr = [".##.##.#", ".#.#.#.#", ".#.#.#.#", ".#.###.#",
              ".#.#.#.#", ".#.#.#.#", ".#.#.#.#", ".#.##.##"]
        return points(["........"] * 6 + rr + ["........"] * 2), [1, 3, 5, 7], [3, 5]
    # Native a/turned-a opposing cap/entrance vocabulary compacted by one column.
    # Its two six-pixel counters remain a coordinated pair.
    core = [[0, 2, 3], [0, 1, 4], [0, 4], [0, 2, 3, 4],
            [0, 1, 2, 4], [0, 4], [0, 3, 4], [1, 2, 4]]
    left = family == FAMILIES[0]
    offset = 3 if left else 1
    ink = {(x + offset, y + 6) for y, rr in enumerate(core) for x in rr}
    if left:
        ink |= {(1, y) for y in range(6, 14)} | {(2, 6), (3, 13)}
        ink.discard((3, 6))  # The middle leg starts below the native shoulder.
        return ink, [1, 3, 7], [3, 7]
    ink |= {(7, y) for y in range(6, 14)} | {(6, 13), (5, 6)}
    ink.discard((5, 13))  # The middle arm enters its hip above the baseline.
    return ink, [1, 5, 7], [1, 5]


def draw(entry):
    contextual_tail = entry["parts"][-1].get("lower") == "curved"
    script_g = contextual_tail and entry["familyId"] == FAMILIES[0]
    ink, staves, core = body(entry["familyId"], contextual_tail)
    layout = []
    outer_masks = []
    extensions = set()
    extension_joins = set()
    joins = set()
    state = []
    cursor = 0
    for index, part in enumerate(entry["parts"]):
        assert not part.get("long") and "closingNeighbor" not in part
        if part["kind"] == "spine":
            layout.append({"partIndex": index, "kind": "spine", "leftColumn": core[0], "rightColumn": core[1]})
            continue
        x = staves[cursor]
        cursor += 1
        layout.append({"partIndex": index, "kind": part["kind"], "column": x})
        if part.get("middle"):
            extended = part.get("upper") == "straight" or part.get("lower") == "straight"
            state.append(extended)
            if extended:
                mask = {(x, y) for y in ((3, 4, 5) if part["kind"] == "arm" else (14, 15))}
                if script_g and part["kind"] == "leg" and x == core[0]:
                    mask.add((x, 13))
                    extension_joins.add((x, 13))
                    layout[-1]["joinPixels"] = [[x, 13]]
                ink |= mask
                extensions |= mask
            continue
        before_terminal = set(ink)
        if part.get("upper") == "straight":
            ink |= {(x, y) for y in (3, 4, 5)}
            if (x, 6) not in ink:
                ink.add((x, 6))
                joins.add((x, 6))
        elif part.get("upper") == "curved":
            assert x == 1
            # Preserve the exact native-f crest instead of rounding its tip.
            ink |= {(2, 3), (3, 3), (1, 4), (1, 5)}
        if part.get("lower") == "straight":
            ink |= {(x, y) for y in (14, 15)}
            if (x, 13) not in ink:
                ink.add((x, 13))
                joins.add((x, 13))
        elif part.get("lower") == "curved":
            assert x == 7
            ink |= ({(3, 14), (7, 14), (4, 15), (5, 15), (6, 15)}
                    if script_g else {(7, 14), (6, 15)})
        outer_masks.append({"partIndex": index, "column": x,
                            "upper": part.get("upper"), "lower": part.get("lower"),
                            "pixels": coordinates(ink - before_terminal)})
    assert cursor == len(staves)
    expected_areas = ([6, 4] + ([6] if extension_joins else []) if script_g
                      else [2, 3] if len(staves) == 4 else [6, 6])
    assert topology(ink) == (1, sorted(expected_areas)), (entry["glyphId"], topology(ink))
    assert not any(x == 0 or x > 7 or y < 0 or y > 15 for x, y in ink)
    assert not [(x, y) for x in range(7) for y in range(15)
                if {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)} <= ink], entry["glyphId"]
    narrow = len(staves) == 4
    note = ("Use the approved four-stave body at columns 1, 3, 5, 7 with its row-9 crossover and two open central counters of two and three pixels. "
            if narrow else "Use a five-column shared body derived from the paired native a/turned-a cap and stave entrances, with two equal six-pixel counters and a compact two-row waist. ")
    note += ("The left shoulder enters below its crest; the right hip leaves above the baseline. "
             "Joined staves retain simple native n/m/u endings. Middle components follow allocation order from left to right; only their designated upper or lower extension pixels change between states. "
             "Outer curved terminals use the approved dense-family hook and simple eng return; no extra tip, serif, or enclosed terminal pocket is added. "
             "This allocation contains no declared long bowl or returnContact, so ordinary compact hooks are not forced to close against unrelated staves.")
    if joins:
        note += " The listed outer-stave joining pixels continue straight extensions through a rounded native cap or return."
    donors = ["0061", "0250", "006E", "006D", "0075", "0066", "014B", "0070", "0071"]
    if contextual_tail or entry["parts"][0].get("upper") == "curved":
        note = note.replace("approved dense-family hook and simple eng return", "native-f crest and contextual native-y or script-g return")
    if contextual_tail:
        donors = [d for d in donors if d != "014B"] + ["0261" if script_g else "0079"]
        note = note.replace("no extra tip, serif, or enclosed terminal pocket is added", "no extra serif is added")
        if script_g:
            note = note.replace("two equal six-pixel counters", "an unchanged six-pixel upper counter and a four-pixel lower counter")
        note += (" The lower bowl closes at row 12 and carries the complete script-g tail; the short left leg leaves row 13 open. Its independent descender includes a documented row-13 bridge, whose contact with the upturn naturally adds a terminal pocket."
                 if script_g else " The two-column native-y hip rises to row 12 without altering the central spine; its tipless lower return occupies the single interior pixel at row 15.")
    result = {"glyphId": entry["glyphId"], "width": 8, "rows": rows(ink),
            "donors": donors,
            "notes": note, "expected": {"components": 1, "counters": len(expected_areas)}, "reviewNotes": [],
            "extensionState": state, "extensionPixels": coordinates(extensions),
            "layout": {"templateId": entry["familyId"] + ("-contextual-tail" if contextual_tail else ""), "outerMasks": outer_masks,
                       "staveColumns": staves, "parts": layout, "sharedSpineColumns": core,
                       "bodyRows": [6, 13], "counterAreas": expected_areas,
                       "outerJoinPixels": coordinates(joins)},
            "structuralChecks": {"staveColumns": staves, "counterAreas": expected_areas}}
    if extension_joins:
        result["extensionJoinPixels"] = coordinates(extension_joins)
    return result


def group_key(entry):
    parts = copy.deepcopy(entry["parts"])
    for part in parts:
        if part.get("middle"):
            part["upper"] = part["lower"] = "none"
    return entry["familyId"], json.dumps(parts, sort_keys=True)


def build(check=False):
    allocation = read(ROOT / "resources/quintessential-latin-allocation.json")["entries"]
    entries = sorted((e for e in allocation if e["familyId"] in FAMILIES), key=lambda e: e["codePoint"])
    existing = {}
    for filename in ("primitives", "pairs", "stress", "unextended-branches", "unextended-spines"):
        existing.update({g["glyphId"]: g for g in read(DIR / (filename + ".json"))["glyphs"]})
    drawn = {e["glyphId"]: draw(e) for e in entries}
    for gid in drawn.keys() & existing.keys():
        assert drawn[gid]["rows"] == existing[gid]["rows"], "Approved drawing changed: " + gid
    groups_by_key = {}
    for entry in entries:
        groups_by_key.setdefault(group_key(entry), []).append(entry)
    groups = []
    for members in groups_by_key.values():
        base = drawn[members[0]["glyphId"]]
        assert not any(base["extensionState"])
        assert len(members) == 2 ** len(base["extensionState"])
        groups.append({"id": "middle-shared-" + base["glyphId"], "title": members[0]["canonicalName"],
                       "glyphIds": [e["glyphId"] for e in members],
                       "notes": ("Allocation-ordered independent middle extensions; outer terminal pixels are fixed, and the designated middle descender includes its explicit row-13 body bridge."
                                 if any(drawn[e["glyphId"]].get("extensionJoinPixels") for e in members)
                                 else "Allocation-ordered independent middle extensions; body and outer terminal pixels are identical across the group.")})
        for entry in members[1:]:
            g = drawn[entry["glyphId"]]
            added = points(g["rows"]) - points(base["rows"])
            assert not points(base["rows"]) - points(g["rows"])
            # The native script-g tip already supplies the middle stave's
            # row-14 pixel; the extension mask remains complete and explicit.
            assert added == set(map(tuple, g["extensionPixels"])) - points(base["rows"])
            assert all(y < 6 or y > 13 or [x, y] in g.get("extensionJoinPixels", []) for x, y in added)
            g["recipe"] = {"baseGlyphId": base["glyphId"], "addPixels": coordinates(added),
                           "removePixels": [], "joinPixels": g.get("extensionJoinPixels", [])}
    owned = [drawn[e["glyphId"]] for e in entries if e["glyphId"] not in existing]
    assert len(owned) == 284 and len(groups) == 108
    fingerprints = {}
    for g in list(existing.values()) + owned:
        key = "".join(g["rows"])
        assert key not in fingerprints, (g["glyphId"], fingerprints.get(key))
        fingerprints[key] = g["glyphId"]
    output = {"schemaVersion": 1, "sourceReferences": ["generate_middle_shared_spines.py"],
              "layoutTemplates": {family + ("-contextual-tail" if tail else ""): {"bodyRows": rows(body(family, tail)[0])}
                                  for tail in (False, True) for family in FAMILIES},
              "construction": {"generator": "generate_middle_shared_spines.py",
              "allocationOrder": "parts from left to right", "preservedDenseIds": sorted(drawn.keys() & existing.keys())},
              "groups": groups, "glyphs": owned}
    # Preserve the existing source's explicit CRLF serialization on every host.
    data = (json.dumps(output, ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8")
    destination = DIR / "middle-shared-spines.json"
    if check:
        assert destination.read_bytes() == data, "middle-shared-spines.json differs from its deterministic construction"
        print(f"Verified {len(owned)} drawings and {len(groups)} groups; source and review artifacts were not modified.")
        return
    destination.write_bytes(data)
    render(entries, drawn, {g["glyphId"] for g in owned})
    print(f"Validated and wrote {len(owned)} new drawings, {len(groups)} complete groups; all {len(existing)} approved drawings preserved.")


def render(entries, drawn, owned):
    from PIL import Image, ImageDraw, ImageFont
    QA.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)
    reference = ImageFont.truetype(str(ROOT / "resources/fonts/QuintessentialSerif/QuintessentialSerif-Regular.otf"), 54)
    donor = {g["codePoint"]: g for g in read(DIR / "donors.json")["donors"]}
    records = []
    sheets = []
    for family in FAMILIES:
        members = [e for e in entries if e["familyId"] == family]
        for page in range(len(members) // 24):
            chunk = members[page * 24:page * 24 + 24]
            im = Image.new("RGB", (1380, 1080), "#f9f8f3")
            canvas = ImageDraw.Draw(im)
            canvas.text((12, 9), f"{family} · {page + 1} · native size, 2× and 8× · STIX structural references", font=font, fill="#213d30")
            def bitmap(rr, ox, oy, scale):
                for y, row in enumerate(rr):
                    for x, value in enumerate(row):
                        if value == "#":
                            canvas.rectangle((ox + x * scale, oy + y * scale, ox + (x + 1) * scale - 1, oy + (y + 1) * scale - 1), fill="#213d30")
            for j, code in enumerate(("0061", "0250", "006E", "0075")):
                rr = ["".join("#" if b & (1 << (7 - x)) else "." for x in range(8)) for b in bytes.fromhex(donor[code]["hex"])]
                bitmap(rr, 15 + j * 150, 33, 3)
                canvas.text((48 + j * 150, 59), "Native U+" + code, font=small, fill="#68746b")
            for index, entry in enumerate(chunk):
                g = drawn[entry["glyphId"]]
                ox, oy = index % 6 * 230 + 12, index // 6 * 240 + 115
                canvas.text((ox, oy), f"U+{entry['codePoint']:X} " + ("/".join("extended" if x else "short" for x in g["extensionState"])), font=small, fill="#213d30")
                bitmap(g["rows"], ox, oy + 25, 8)
                for x in range(9):
                    canvas.line((ox + x * 8, oy + 25, ox + x * 8, oy + 153), fill="#d2d1c5")
                for y in range(17):
                    canvas.line((ox, oy + 25 + y * 8, ox + 64, oy + 25 + y * 8), fill="#d2d1c5")
                bitmap(g["rows"], ox + 90, oy + 82, 1)
                bitmap(g["rows"], ox + 115, oy + 66, 2)
                canvas.text((ox + 152, oy + 105), chr(entry["codePoint"]), font=reference, fill="#213d30", anchor="ls")
                canvas.text((ox + 148, oy + 132), "STIX", font=small, fill="#68746b")
                stem_state = " | ".join(p.get("upper", "none") + "/" + p.get("lower", "none") for p in entry["parts"] if p["kind"] == "stem")
                canvas.text((ox, oy + 173), stem_state, font=small, fill="#68746b")
                canvas.text((ox, oy + 197), "counters " + "/".join(map(str, g["layout"]["counterAreas"])), font=small, fill="#68746b")
            name = f"{family}-{page + 1:02d}.png"
            destination = QA / name
            im.save(destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            sheets.append({"file": name, "sha256": digest, "glyphIds": [e["glyphId"] for e in chunk]})
            for entry in chunk:
                if entry["glyphId"] not in owned:
                    continue
                g = drawn[entry["glyphId"]]
                h = "".join(f"{int(r.replace('.', '0').replace('#', '1'), 2):02X}" for r in g["rows"])
                line = f"{entry['codePoint']:06X}:" + h + "\n"
                records.append({"glyphId": g["glyphId"], "bitmapSha256": hashlib.sha256(line.encode("ascii")).hexdigest(),
                                "sheet": name, "proofSha256": digest, "status": "rendered_pending_visual_inspection"})
    manifest = {"schemaVersion": 1, "sourceSha256": hashlib.sha256((DIR / "middle-shared-spines.json").read_bytes()).hexdigest(),
                "sheets": sheets, "records": records}
    (QA / "review-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare exact generated source bytes without writing sources or proof/review artifacts.")
    build(parser.parse_args().check)

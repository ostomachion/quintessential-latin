"""Render compiled hip tails before/after, alongside unchanged arch/bowl tails."""
from pathlib import Path
import argparse
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = (400, 500, 550, 600, 700)
ROWS = (
    ("turned-arm-tail", "Hip with tail - before", True),
    ("turned-arm-tail", "Hip with tail - after", False),
    ("turned-arm-ascender-tail", "Hip with long tail - before", True),
    ("turned-arm-ascender-tail", "Hip with long tail - after", False),
    ("turned-arch-tail", "Arm with tail - reference", False),
    ("turned-bowl-tail", "Bowl with tail - reference", False),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True, help="Pre-edit compiled font directory")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/images/hip-tails")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    entries = {e["glyphId"]: e for e in json.loads((ROOT / "resources/quintessential-latin-allocation.json").read_text())["entries"]}
    labels = {size: ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size) for size in (14, 17, 21, 30)}
    manifest = {"weights": WEIGHTS, "fonts": {}, "sheets": []}
    for posture, filename in (("Roman", "QuintessentialSerif-Variable.ttf"), ("Italic", "QuintessentialSerif-Italic-Variable.ttf")):
        paths = {True: args.before / filename, False: ROOT / "resources/fonts/QuintessentialSerif" / filename}
        manifest["fonts"][posture] = {"before" if before else "after": hashlib.sha256(path.read_bytes()).hexdigest() for before, path in paths.items()}
        faces = {}
        for before, path in paths.items():
            for weight in WEIGHTS:
                for size in (180, 24):
                    font = ImageFont.truetype(str(path), size)
                    font.set_variation_by_axes([weight])
                    faces[before, weight, size] = font
        sheet = Image.new("RGB", (1570, 1870), "#faf9f6")
        draw = ImageDraw.Draw(sheet)
        draw.text((28, 20), f"Hip tails / {posture}", font=labels[30], fill="#242620")
        draw.text((28, 65), "Compiled fonts at 180px and 24px; repeated forms and descender/tail pairs below.", font=labels[17], fill="#62665a")
        for col, weight in enumerate(WEIGHTS):
            draw.text((408 + col * 230, 103), str(weight), font=labels[21], fill="#242620")
        for row, (identity, title, before) in enumerate(ROWS):
            y = 143 + row * 280
            draw.line((28, y, 1542, y), fill="#d6d8ce")
            draw.text((28, y + 25), title, font=labels[17], fill="#242620")
            entry = entries[identity]
            draw.text((28, y + 55), f"U+{entry['codePoint']:X}", font=labels[14], fill="#62665a")
            for col, weight in enumerate(WEIGHTS):
                x = 350 + col * 230
                draw.line((x, y + 147, x + 200, y + 147), fill="#e0e2da")
                mixed = "".join(chr(entries[identity]["codePoint"]) + chr(entry["codePoint"])
                                for identity in ("descender", "tail", "turned-bowl-tail"))
                for size, baseline, text in ((180, y + 147, chr(entry["codePoint"])),
                                             (24, y + 220, chr(entry["codePoint"]) * 4),
                                             (24, y + 255, mixed)):
                    font = faces[before, weight, size]
                    # Center the unchanged advance box so before/after shafts
                    # stay aligned while the tail visibly extends leftward.
                    origin = x + (200 - draw.textlength(text, font=font)) / 2
                    draw.text((origin, baseline), text, font=font, fill="#242620", anchor="ls")
        output = args.output / f"{posture.lower()}.png"
        sheet.save(output)
        manifest["sheets"].append({"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Rendered both hip-tail targets before/after and unchanged references at five weights in both postures.")


if __name__ == "__main__":
    main()

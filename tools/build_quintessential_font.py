#!/usr/bin/env python3
"""Build Quintessential Serif from its STIX Two based sources."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen, replayRecording
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import compress
from fontTools.varLib.instancer import instantiateVariableFont
from ufoLib2 import Font

from quintessential_font import (
    AXIS_DEFAULT,
    AXIS_MAP,
    AXIS_MAXIMUM,
    AXIS_MINIMUM,
    AXIS_TAG,
    DONOR_MANIFEST,
    DONORS,
    EXPECTED_CODE_POINTS,
    FAMILY_NAME,
    GLYPHS,
    MASTERS,
    NAMED_WEIGHTS,
    OUTPUT,
    POSTURES,
    ROOT,
    SOURCES,
    SOURCE_DATE_EPOCH,
    VERSION,
    expected_code_points_for_posture,
    glyph_order_for_posture,
    glyphs_for_posture,
    posture_by_name,
)

WORK = ROOT / ".tmp" / "quintessential-font-build"
EXPECTED_AVAR = {
    -1.0: -1.0,
    0.0: 0.0,
    0.33331298828125: 0.3157958984375,
    0.66668701171875: 0.631591796875,
    1.0: 1.0,
}
FONT_PACKAGES = ("fontmake", "fonttools", "ufoLib2", "afdko", "brotli")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(module: str, *arguments: object) -> None:
    environment = {**os.environ, "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH)}
    subprocess.run(
        [sys.executable, "-m", module, *map(str, arguments)],
        check=True,
        cwd=ROOT,
        env=environment,
    )


def load_and_verify_donors() -> tuple[dict, dict[str, Path]]:
    if not DONOR_MANIFEST.exists():
        raise SystemExit(f"Missing pinned donor manifest: {DONOR_MANIFEST}")
    manifest = json.loads(DONOR_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("upstream", {}).get("releaseVersion") != "2.13 b171":
        raise SystemExit("Pinned donor manifest is not STIX Two 2.13 b171")
    records = {record["style"]: record for record in manifest["donors"]}
    paths = {}
    for posture in POSTURES:
        record = records.get(posture.name)
        if record is None or record["filename"] != posture.donor_filename:
            raise SystemExit(f"Missing {posture.name} donor record")
        path = DONORS / record["filename"]
        if not path.exists() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise SystemExit(f"Pinned donor checksum mismatch: {path}")
        with TTFont(path) as font:
            axes = font["fvar"].axes
            if len(axes) != 1 or (
                axes[0].axisTag,
                axes[0].minValue,
                axes[0].defaultValue,
                axes[0].maxValue,
            ) != (AXIS_TAG, AXIS_MINIMUM, AXIS_DEFAULT, AXIS_MAXIMUM):
                raise SystemExit(f"Unexpected axis model in {path.name}")
            if font["avar"].segments[AXIS_TAG] != EXPECTED_AVAR:
                raise SystemExit(f"Unexpected avar mapping in {path.name}")
            version_names = {
                name.toUnicode() for name in font["name"].names if name.nameID == 5
            }
            if "Version 2.13 b171" not in version_names:
                raise SystemExit(f"Unexpected internal version in {path.name}")
        paths[posture.name] = path
    for document in manifest["documents"]:
        path = DONORS / document["filename"]
        if not path.exists() or path.stat().st_size != document["bytes"] or sha256(path) != document["sha256"]:
            raise SystemExit(f"Pinned source document checksum mismatch: {path}")
    return manifest, paths


def prepare_working_directory() -> None:
    work = WORK.resolve()
    if work.parent != (ROOT / ".tmp").resolve():
        raise RuntimeError("Refusing to clear an unexpected build directory")
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)


def cleanup_working_directory() -> None:
    work = WORK.resolve()
    if work.parent != (ROOT / ".tmp").resolve():
        raise RuntimeError("Refusing to clear an unexpected build directory")
    if WORK.exists():
        shutil.rmtree(WORK)


def normalize_timestamp(path: Path) -> None:
    with TTFont(path, recalcTimestamp=False) as font:
        timestamp = SOURCE_DATE_EPOCH + 2_082_844_800
        font["head"].created = timestamp
        font["head"].modified = timestamp
        font.save(path, reorderTables=True)


def set_name(font: TTFont, name_id: int, value: str) -> None:
    name = font["name"]
    name.setName(value, name_id, 3, 1, 0x409)
    name.setName(value, name_id, 0, 4, 0)


def preserve_bowl_counter_variations(font: TTFont) -> None:
    """Keep native precision in unchanged bowl contours after gvar packing.

    The packer may choose dense deltas for a constructed glyph and sparse IUP
    deltas for its native body. Materializing an inferred fractional delta as
    an integer slightly moves the counter. Reuse the compiled body's deltas
    for identical contours; the new shaft and its metrics remain independent.
    This uses only the font just compiled from the checked-in UFO masters.
    """
    specs = glyphs_for_posture(bool(font["head"].macStyle & 2))
    direct = {spec.direct_donor: spec.glyph_name for spec in specs
              if spec.direct_donor is not None}
    glyf, gvar = font["glyf"], font["gvar"]
    for spec in specs:
        bodies = [code for role, code, _ in spec.references if role == "bowl"]
        if spec.direct_donor is not None or not bodies:
            continue
        target, original = spec.glyph_name, direct[bodies[0]]
        points, ends, flags = glyf[target].getCoordinates(glyf)
        native_points, native_ends, native_flags = glyf[original].getCoordinates(glyf)
        if len(ends) != len(native_ends):
            raise RuntimeError(f"{target} no longer shares its native bowl contours")
        for index in range(1, len(ends)):
            start, end = ends[index - 1] + 1, ends[index] + 1
            native_start, native_end = native_ends[index - 1] + 1, native_ends[index] + 1
            if (points[start:end] != native_points[native_start:native_end]
                    or flags[start:end] != native_flags[native_start:native_end]):
                raise RuntimeError(f"{target} changed native contour {index}")
            for variation in gvar.variations[target]:
                matches = [native for native in gvar.variations[original]
                           if native.axes == variation.axes]
                if len(matches) != 1:
                    raise RuntimeError(f"{target} has incompatible native variation regions")
                variation.coordinates[start:end] = matches[0].coordinates[native_start:native_end]


def shared_spine_counter_indices(glyph, reference) -> set[int]:
    """Locate the two translated body counters after all arch/leg assembly."""
    from import_stix_foundation import native_recording_contours

    def contours(item):
        pen = RecordingPen()
        item.draw(pen)
        return list(native_recording_contours(pen.value))

    candidates = contours(glyph)
    indices = set()
    for template in contours(reference)[1:3]:
        structure = [(op, len(points)) for op, points in template]
        matches = []
        for index, candidate in enumerate(candidates):
            if [(op, len(points)) for op, points in candidate] != structure:
                continue
            dx = candidate[0][1][0][0] - template[0][1][0][0]
            error = max(max(abs(x - rx - dx), abs(y - ry))
                        for (_, points), (_, references) in zip(candidate, template)
                        for (x, y), (rx, ry) in zip(points, references))
            if error < 0.00001:
                matches.append(index)
        if len(matches) != 1:
            raise RuntimeError(f"{glyph.name} must contain each shared spine counter exactly once")
        indices.add(matches[0])
    if len(indices) != 2:
        raise RuntimeError(f"{glyph.name} must contain two distinct shared spine counters")
    return indices


def preserve_shared_spine_variations(font: TTFont) -> None:
    """Keep the full shared construction exact when glyph topology changes.

    Editing a counter can switch the packer from dense to sparse deltas for the
    entire glyph. IUP then approximates unchanged outer points by fractional
    deltas. Materialize rounded source endpoint differences for every contour:
    the body counters must remain congruent regardless of ending complexity,
    and arches and terminal enclosures must retain their original geometry.
    Phantom metric points retain their compiled deltas.
    """
    italic = bool(font["head"].macStyle & 2)
    styles = ("Italic", "BoldItalic") if italic else ("Regular", "Bold")
    sources = [Font.open(SOURCES / f"QuintessentialSerif-{style}.ufo") for style in styles]
    try:
        for name in sources[0].glyphOrder:
            metadata = sources[0][name].lib.get("org.quintessential.construction", {})
            revision = metadata.get("opticalRevision")
            if revision is None:
                continue
            if sources[1][name].lib.get("org.quintessential.construction", {}).get("opticalRevision") != revision:
                raise RuntimeError(f"{name} has inconsistent optical revisions across source endpoints")
            counters = [shared_spine_counter_indices(source[name], source["uF2B1C"])
                        for source in sources]
            if counters[0] != counters[1]:
                raise RuntimeError(f"{name} has incompatible body counter placement")
            endpoints = []
            for source in sources:
                pen = TTGlyphPen(source)
                source[name].draw(pen)
                endpoint = pen.glyph()
                if not endpoint.endPtsOfContours:
                    raise RuntimeError(f"{name} has no outer contour to preserve")
                endpoints.append(endpoint)
            if endpoints[0].endPtsOfContours != endpoints[1].endPtsOfContours:
                raise RuntimeError(f"{name} has incompatible contour endpoints")
            glyf = font["glyf"]
            points, ends, flags = glyf[name].getCoordinates(glyf)
            if list(ends) != list(endpoints[0].endPtsOfContours):
                raise RuntimeError(f"{name} compiled contour layout no longer matches its source")
            variations = font["gvar"].variations[name]
            if len(variations) != 1 or variations[0].axes != {AXIS_TAG: (0.0, 1.0, 1.0)}:
                raise RuntimeError(f"{name} has an unsupported outer contour variation model")
            start = 0
            for index, end in enumerate(ends):
                stop = end + 1
                expected_flags = [flag & 1 for flag in endpoints[0].flags[start:stop]]
                if (points[start:stop] != endpoints[0].coordinates[start:stop]
                        or [flag & 1 for flag in flags[start:stop]] != expected_flags
                        or [flag & 1 for flag in endpoints[1].flags[start:stop]] != expected_flags):
                    raise RuntimeError(f"{name} compiled contour {index} differs from its source")
                variations[0].coordinates[start:stop] = [
                    (bold[0] - regular[0], bold[1] - regular[1])
                    for regular, bold in zip(endpoints[0].coordinates[start:stop],
                                             endpoints[1].coordinates[start:stop])
                ]
                start = stop
    finally:
        for source in sources:
            source.close()


def normalize_variable_font(path: Path, italic: bool) -> None:
    with TTFont(path, recalcTimestamp=False) as font:
        preserve_bowl_counter_variations(font)
        preserve_shared_spine_variations(font)
        timestamp = SOURCE_DATE_EPOCH + 2_082_844_800
        font["head"].created = timestamp
        font["head"].modified = timestamp
        names = {
            weight: (f"{weight_name} Italic" if italic and weight != 400 else "Italic" if italic else weight_name)
            for weight, weight_name in NAMED_WEIGHTS
        }
        for instance in font["fvar"].instances:
            weight = round(instance.coordinates[AXIS_TAG])
            set_name(font, instance.subfamilyNameID, names[weight])
        set_name(font, 25, "QuintessentialSerifItalic" if italic else "QuintessentialSerifRoman")
        font.save(path, reorderTables=True)


def build_variable_fonts() -> list[Path]:
    outputs = []
    for posture in POSTURES:
        designspace = SOURCES / posture.designspace_filename
        if not designspace.exists():
            raise SystemExit(f"Missing designspace: {designspace}")
        ttf = OUTPUT / f"{posture.variable_basename}.ttf"
        run(
            "fontmake",
            "-m", designspace,
            "-o", "variable",
            "--output-path", ttf,
            "--keep-overlaps",
            "--keep-direction",
            "--ttf-curves", "keep-quad",
            "--no-production-names",
            "--feature-writer", "KernFeatureWriter",
            "--validate-ufo",
            "--verbose", "WARNING",
        )
        normalize_variable_font(ttf, posture.italic)
        woff2 = OUTPUT / f"{posture.variable_basename}.woff2"
        compress(ttf, woff2)
        outputs.extend((ttf, woff2))
        print(f"Built {posture.name} variable TTF + WOFF2")
    return outputs


def midpoint(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    return ((first[0] + second[0]) / 2.0, (first[1] + second[1]) / 2.0)


def quadratic_to_exact_cubic(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Convert one quadratic segment to its mathematically identical cubic."""
    first_control = (
        start[0] + (control[0] - start[0]) * 2.0 / 3.0,
        start[1] + (control[1] - start[1]) * 2.0 / 3.0,
    )
    second_control = (
        end[0] + (control[0] - end[0]) * 2.0 / 3.0,
        end[1] + (control[1] - end[1]) * 2.0 / 3.0,
    )
    return first_control, second_control, end


def exact_cubic_recording(recording: list[tuple[str, tuple]]) -> list[tuple[str, tuple]]:
    """Expand every qCurveTo into unmerged, exactly equivalent cubics."""
    result: list[tuple[str, tuple]] = []
    current = None
    contour_start = None
    for operation, operands in recording:
        if operation == "moveTo":
            current = contour_start = operands[0]
            result.append((operation, operands))
        elif operation == "lineTo":
            current = operands[0]
            result.append((operation, operands))
        elif operation == "curveTo":
            current = operands[-1]
            result.append((operation, operands))
        elif operation == "qCurveTo":
            if current is None or not operands:
                raise RuntimeError("Malformed quadratic contour in endpoint UFO")
            if operands[-1] is None:
                off_curves = list(operands[:-1])
                if not off_curves:
                    raise RuntimeError("Empty all-off-curve qCurveTo")
                final = midpoint(off_curves[-1], off_curves[0])
            else:
                off_curves = list(operands[:-1])
                final = operands[-1]
            if not off_curves:
                result.append(("lineTo", (final,)))
                current = final
                continue
            for index, control in enumerate(off_curves):
                end = midpoint(control, off_curves[index + 1]) if index + 1 < len(off_curves) else final
                cubic = quadratic_to_exact_cubic(current, control, end)
                result.append(("curveTo", cubic))
                current = end
        elif operation == "closePath":
            result.append((operation, operands))
            current = contour_start = None
        elif operation == "endPath":
            result.append((operation, operands))
            current = contour_start = None
        else:
            raise RuntimeError(f"Unexpected endpoint operation: {operation}")
    return result


def make_exact_cubic_ufo(master) -> Path:
    """Make an exact cubic copy of the canonical compiled endpoint.

    The checked-in masters contain a few purpose-built cubic joins. TrueType
    must quantize the quadratic points produced for those joins. Static CFF
    therefore starts from the already-compiled variable endpoint, then
    converts each of its individual quadratic segments exactly. This keeps the
    static and variable outlines geometrically identical instead of preserving
    sub-unit source geometry that the TrueType route cannot represent.
    """
    source = SOURCES / master.filename
    font = Font.open(source)
    posture = posture_by_name(master.posture)
    variable_path = OUTPUT / f"{posture.variable_basename}.ttf"
    variable = TTFont(variable_path)
    endpoint = instantiateVariableFont(
        variable, {AXIS_TAG: master.weight}, inplace=False, optimize=True
    )
    glyph_set = endpoint.getGlyphSet()
    for glyph in font:
        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[glyph.name].draw(recording)
        cubic = exact_cubic_recording(recording.value)
        # Type 2 encodes fractional coordinates as relative 16.16 values.
        # Quantize absolute positions first so rounding each encoded delta
        # cannot accumulate around a long contour or move a closed counter.
        # This is the native CFF precision, not TrueType's integer grid.
        cubic = [(operation, tuple((round(x * 65536) / 65536, round(y * 65536) / 65536)
                                   for x, y in points))
                 for operation, points in cubic]
        glyph.clearContours()
        glyph.clearComponents()
        replayRecording(cubic, glyph.getPen())
        glyph.width = endpoint["hmtx"][glyph.name][0]
        verify = RecordingPen()
        glyph.draw(verify)
        if any(operation == "qCurveTo" for operation, _ in verify.value):
            raise RuntimeError(f"Quadratic segment remains in temporary {master.style} cubic source")
    destination = WORK / f"QuintessentialSerif-{master.style}-cubic.ufo"
    font.save(destination)
    endpoint.close()
    variable.close()
    return destination


def build_static_fonts() -> list[Path]:
    outputs = []
    for master in MASTERS:
        source = SOURCES / master.filename
        if not source.exists():
            raise SystemExit(f"Missing UFO master: {source}")
        cubic_source = make_exact_cubic_ufo(master)
        basename = f"QuintessentialSerif-{master.style}"
        unhinted = WORK / f"{basename}-unhinted.otf"
        otf = OUTPUT / f"{basename}.otf"
        run(
            "fontmake",
            "-u", cubic_source,
            "-o", "otf",
            "--output-path", unhinted,
            "--keep-overlaps",
            "--cff-round-tolerance", "0",
            "--optimize-cff", "0",
            "--no-production-names",
            "--feature-writer", "KernFeatureWriter",
            "--validate-ufo",
            "--verbose", "WARNING",
        )
        run(
            "afdko.otfautohint",
            "-p", "1",
            "--no-flex",
            "--decimal",
            "--ignore-fontinfo",
            unhinted,
            "-o", otf,
        )
        normalize_timestamp(otf)
        woff2 = OUTPUT / f"{basename}.woff2"
        compress(otf, woff2)
        outputs.extend((otf, woff2))
        print(f"Built {master.style} hinted OTF + WOFF2")
    return outputs


def outline_data(font: TTFont, glyph_name: str) -> tuple[str, tuple | None, int]:
    glyph_set = font.getGlyphSet()
    path_pen = SVGPathPen(glyph_set)
    bounds_pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(path_pen)
    glyph_set[glyph_name].draw(bounds_pen)
    return path_pen.getCommands(), bounds_pen.bounds, font["hmtx"][glyph_name][0]


def make_proof_data(donor_manifest: dict, donor_paths: dict[str, Path]) -> dict:
    axis_record = donor_manifest["axisModel"]["axes"][0]
    proof = {
        "schemaVersion": 2,
        "family": FAMILY_NAME,
        "version": VERSION,
        "sourceFamily": donor_manifest["family"],
        "sourceVersion": donor_manifest["upstream"]["releaseVersion"],
        "sourceCommit": donor_manifest["upstream"]["sourceCommit"],
        "unitsPerEm": 1000,
        "axis": {
            "tag": AXIS_TAG,
            "name": "Weight",
            "min": AXIS_MINIMUM,
            "default": AXIS_DEFAULT,
            "max": AXIS_MAXIMUM,
            "instances": [
                {"name": name, "value": weight} for weight, name in NAMED_WEIGHTS
            ],
            "designspaceMap": [
                {"user": user, "source": source} for user, source in AXIS_MAP
            ],
            "avarMappings": axis_record["compiledAvarSegments"],
        },
        "glyphs": [
            {"id": glyph.glyph_id, "codePoint": glyph.code_point, "label": glyph.label}
            for glyph in GLYPHS
        ],
        "faces": [],
    }
    for posture in POSTURES:
        variable_path = OUTPUT / f"{posture.variable_basename}.ttf"
        built_variable = TTFont(variable_path)
        donor_variable = TTFont(donor_paths[posture.name])
        for weight, weight_name in NAMED_WEIGHTS:
            built = instantiateVariableFont(
                built_variable, {AXIS_TAG: weight}, inplace=False, optimize=True
            )
            donor = instantiateVariableFont(
                donor_variable, {AXIS_TAG: weight}, inplace=False, optimize=True
            )
            style = (
                f"{weight_name}Italic" if posture.italic and weight != 400
                else "Italic" if posture.italic
                else weight_name
            )
            face = {
                "style": style,
                "displayStyle": (
                    f"{weight_name} Italic" if posture.italic and weight != 400
                    else "Italic" if posture.italic
                    else weight_name
                ),
                "weight": weight,
                "italic": posture.italic,
                "xHeight": built["OS/2"].sxHeight,
                "ascender": built["OS/2"].sTypoAscender,
                "descender": built["OS/2"].sTypoDescender,
                "glyphs": [],
            }
            built_cmap, donor_cmap = built.getBestCmap(), donor.getBestCmap()
            for spec in glyphs_for_posture(posture.italic):
                path, bounds, advance = outline_data(built, built_cmap[spec.code_point])
                references = []
                for role, code_point, label in spec.references_for(posture.italic):
                    reference_path, reference_bounds, reference_advance = outline_data(
                        donor, donor_cmap[code_point]
                    )
                    references.append({
                        "role": role,
                        "label": label,
                        "codePoint": code_point,
                        "character": chr(code_point),
                        "advance": reference_advance,
                        "bounds": reference_bounds,
                        "path": reference_path,
                    })
                face["glyphs"].append({
                    "id": spec.glyph_id,
                    "codePoint": spec.code_point,
                    "glyphName": spec.glyph_name,
                    "recipeCodePoint": spec.recipe_code_point,
                    "middleLegs": spec.middle_legs,
                    **({"middleLegExtensions": list(spec.middle_leg_extensions)} if spec.middle_leg_extensions is not None else {}),
                    "advance": advance,
                    "bounds": bounds,
                    "builtPath": path,
                    "adaptation": spec.adaptation_for(posture.italic),
                    "references": references,
                })
            proof["faces"].append(face)
            built.close()
            donor.close()
        built_variable.close()
        donor_variable.close()
    return proof


def has_cff_hints(font: TTFont) -> bool:
    top_dict = font["CFF "].cff.topDictIndex[0]
    hint_operators = {"hstem", "vstem", "hstemhm", "vstemhm", "hintmask", "cntrmask"}
    for glyph_name in font.getGlyphOrder()[2:]:
        char_string = top_dict.CharStrings[glyph_name]
        char_string.decompile()
        if any(token in hint_operators for token in char_string.program):
            return True
    return False


def validate_output(path: Path, variable: bool) -> None:
    with TTFont(path) as font:
        italic = "Italic" in path.name
        glyph_order = glyph_order_for_posture(italic)
        if bool(font["head"].macStyle & 2) != italic:
            raise RuntimeError(f"Unexpected native posture in {path.name}")
        if tuple(font.getGlyphOrder()) != glyph_order:
            raise RuntimeError(f"Unexpected glyph order in {path.name}")
        if tuple(sorted(font.getBestCmap())) != tuple(sorted(expected_code_points_for_posture(italic))):
            raise RuntimeError(f"Unexpected cmap in {path.name}")
        version_names = {name.toUnicode() for name in font["name"].names if name.nameID == 5}
        if f"Version {VERSION}" not in version_names:
            raise RuntimeError(f"Unexpected version in {path.name}")
        if variable:
            required = {"fvar", "avar", "STAT", "gvar", "HVAR", "GPOS"}
            if not required.issubset(font.keys()):
                raise RuntimeError(f"Missing variable table(s) in {path.name}")
            axis = font["fvar"].axes[0]
            if (axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue) != (
                AXIS_TAG, AXIS_MINIMUM, AXIS_DEFAULT, AXIS_MAXIMUM
            ):
                raise RuntimeError(f"Unexpected variable axis in {path.name}")
            if font["avar"].segments[AXIS_TAG] != EXPECTED_AVAR:
                raise RuntimeError(f"Unexpected avar table in {path.name}")
            instance_weights = [instance.coordinates[AXIS_TAG] for instance in font["fvar"].instances]
            if instance_weights != [weight for weight, _ in NAMED_WEIGHTS]:
                raise RuntimeError(f"Unexpected named instances in {path.name}")
            if not all(name in font["gvar"].variations for name in glyph_order[2:]):
                raise RuntimeError(f"A script glyph lacks gvar data in {path.name}")
            if font["GPOS"].table.ScriptList.ScriptRecord[0].ScriptTag != "DFLT":
                raise RuntimeError(f"Kerning is not exposed through DFLT in {path.name}")
            if "GDEF" not in font or getattr(font["GDEF"].table, "VarStore", None) is None:
                raise RuntimeError(f"Variable kerning store missing in {path.name}")
        else:
            if "CFF " not in font or not has_cff_hints(font):
                raise RuntimeError(f"Static CFF hints missing in {path.name}")


def source_hashes() -> dict[str, str]:
    paths = [
        *(SOURCES / master.filename for master in MASTERS),
        *(SOURCES / posture.designspace_filename for posture in POSTURES),
        Path(__file__),
        Path(__file__).with_name("quintessential_font.py"),
        Path(__file__).with_name("import_stix_foundation.py"),
        Path(__file__).with_name("stix_arched_terminals.py"),
        Path(__file__).with_name("stix_repeated_arch.py"),
        Path(__file__).with_name("stix_double_bowl.py"),
        Path(__file__).with_name("stix_bowled_spine.py"),
        Path(__file__).with_name("stix_bowled_spine_normal.py"),
        Path(__file__).with_name("stix_bowled_spine_italic.py"),
        Path(__file__).with_name("stix_bowled_spine_italic_normal.py"),
        Path(__file__).with_name("stix_opposed_bowls.py"),
        Path(__file__).with_name("stix_compact_spine.py"),
        Path(__file__).with_name("stix_arch_spine_joins.py"),
        Path(__file__).with_name("stix_arched_opposed_bowls.py"),
        Path(__file__).with_name("stix_extensions.py"),
        Path(__file__).with_name("stix_stemless.py"),
        Path(__file__).with_name("stix_middle_legs.py"),
        Path(__file__).with_name("stix_middle_terminals.py"),
        Path(__file__).with_name("stix_middle_hook_joins.py"),
        *Path(__file__).parent.glob("stix_*_italic*.py"),
        Path(__file__).with_name("complete_italic_sources.py"),
        Path(__file__).with_name("add_independent_middle_legs.py"),
        Path(__file__).with_name("reallocate_catalogue.py"),
        Path(__file__).with_name("canonical_glyph_names.js"),
        Path(__file__).with_name("export_glyph_catalogue.js"),
        ROOT / "resources/quintessential-latin-allocation.json",
    ]
    files = []
    for path in paths:
        files.extend(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else files.append(path)
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted(files)
    }


def write_metadata(donor_manifest: dict, donor_paths: dict[str, Path], font_outputs: list[Path]) -> None:
    for filename in ("OFL.txt", "FONTLOG.txt", "TRADEMARKS.txt"):
        shutil.copyfile(DONORS / filename, OUTPUT / filename)

    proof_path = OUTPUT / "proof-data.json"
    proof_path.write_text(
        json.dumps(make_proof_data(donor_manifest, donor_paths), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schemaVersion": 2,
        "family": FAMILY_NAME,
        "version": VERSION,
        "base": {
            "family": donor_manifest["family"],
            "version": donor_manifest["upstream"]["releaseVersion"],
            "releaseTag": donor_manifest["upstream"]["releaseTag"],
            "sourceCommit": donor_manifest["upstream"]["sourceCommit"],
            "manifest": DONOR_MANIFEST.relative_to(ROOT).as_posix(),
            "manifestSha256": sha256(DONOR_MANIFEST),
        },
        "axis": {
            "tag": AXIS_TAG,
            "minimum": AXIS_MINIMUM,
            "default": AXIS_DEFAULT,
            "maximum": AXIS_MAXIMUM,
            "designspaceMap": [list(item) for item in AXIS_MAP],
            "namedInstances": [
                {"name": name, "value": weight} for weight, name in NAMED_WEIGHTS
            ],
        },
        "characters": [f"U+{code_point:04X}" for code_point in EXPECTED_CODE_POINTS],
        "charactersByPosture": {
            posture.name: [f"U+{code_point:04X}" for code_point in expected_code_points_for_posture(posture.italic)]
            for posture in POSTURES
        },
        "sourceDateEpoch": SOURCE_DATE_EPOCH,
        "tools": {package: importlib.metadata.version(package) for package in FONT_PACKAGES},
        "sources": source_hashes(),
        "outputs": {},
        "hinting": {
            "variable": "Unhinted TrueType outlines, matching the STIX Two variable-font model.",
            "static": "AFDKO autohinted CFF outlines.",
        },
    }
    metadata_outputs = [
        OUTPUT / "OFL.txt",
        OUTPUT / "FONTLOG.txt",
        OUTPUT / "TRADEMARKS.txt",
        proof_path,
    ]
    for path in sorted([*font_outputs, *metadata_outputs]):
        manifest["outputs"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    (OUTPUT / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    donor_manifest, donor_paths = load_and_verify_donors()
    prepare_working_directory()
    variable_outputs = build_variable_fonts()
    static_outputs = build_static_fonts()
    for path in variable_outputs:
        validate_output(path, variable=True)
    for path in static_outputs:
        validate_output(path, variable=False)
    write_metadata(donor_manifest, donor_paths, [*variable_outputs, *static_outputs])
    cleanup_working_directory()
    print("Validated fonts, proof data, licensing, and reproducible build manifest.")


if __name__ == "__main__":
    main()

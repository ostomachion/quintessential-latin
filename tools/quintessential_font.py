#!/usr/bin/env python3
"""Shared constants and metadata for the Quintessential Serif font build."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "fonts" / "QuintessentialSerif"
OUTPUT = ROOT / "resources" / "fonts" / "QuintessentialSerif"
DONORS = ROOT / "resources" / "fonts" / "STIXTwoText"
DONOR_MANIFEST = DONORS / "source-manifest.json"

FAMILY_NAME = "Quintessential Serif"
VERSION = "0.250"
VERSION_MAJOR = 0
VERSION_MINOR = 250
SOURCE_DATE_EPOCH = 1_788_480_000  # 2026-09-04 00:00:00 UTC.
VENDOR_ID = "QLAT"

AXIS_TAG = "wght"
AXIS_NAME = "Weight"
AXIS_MINIMUM = 400
AXIS_DEFAULT = 400
AXIS_MAXIMUM = 700
# This is STIX Two's source designspace mapping. It compiles to the avar
# mapping shipped in the v2.13 b171 variable fonts.
AXIS_MAP = ((400, 92), (500, 110), (600, 128), (700, 149))
NAMED_WEIGHTS = ((400, "Regular"), (500, "Medium"), (600, "SemiBold"), (700, "Bold"))


@dataclass(frozen=True)
class Posture:
    name: str
    italic: bool
    donor_filename: str
    designspace_filename: str
    variable_basename: str


POSTURES = (
    Posture(
        name="Roman",
        italic=False,
        donor_filename="STIXTwoText-VariableFont_wght.ttf",
        designspace_filename="QuintessentialSerif-Roman.designspace",
        variable_basename="QuintessentialSerif-Variable",
    ),
    Posture(
        name="Italic",
        italic=True,
        donor_filename="STIXTwoText-Italic-VariableFont_wght.ttf",
        designspace_filename="QuintessentialSerif-Italic.designspace",
        variable_basename="QuintessentialSerif-Italic-Variable",
    ),
)


@dataclass(frozen=True)
class Master:
    style: str
    posture: str
    italic: bool
    weight: int
    design_weight: int
    filename: str


MASTERS = (
    Master("Regular", "Roman", False, 400, 92, "QuintessentialSerif-Regular.ufo"),
    Master("Bold", "Roman", False, 700, 149, "QuintessentialSerif-Bold.ufo"),
    Master("Italic", "Italic", True, 400, 92, "QuintessentialSerif-Italic.ufo"),
    Master("BoldItalic", "Italic", True, 700, 149, "QuintessentialSerif-BoldItalic.ufo"),
)


@dataclass(frozen=True)
class GlyphSpec:
    glyph_id: str
    code_point: int
    label: str
    width_donor: int
    direct_donor: int | None
    references: tuple[tuple[str, int, str], ...]
    adaptation: str
    roman_stem_donor: int | None = None
    roman_only: bool = False
    italic_references: tuple[tuple[str, int, str], ...] | None = None
    italic_adaptation: str | None = None
    recipe_code_point: int | None = None
    internal_name: str | None = None
    middle_legs: bool = False
    middle_leg_extensions: tuple[bool, ...] | None = None
    stemless: bool = False

    @property
    def glyph_name(self) -> str:
        """Stable source identity; cmap allocation can change independently."""
        return self.internal_name or f"u{self.code_point:X}"

    def references_for(self, italic: bool) -> tuple[tuple[str, int, str], ...]:
        if italic and self.italic_references is not None:
            return self.italic_references
        if not italic and self.roman_stem_donor is not None:
            return (*self.references, ("stem", self.roman_stem_donor, "lowercase u"))
        return self.references

    def adaptation_for(self, italic: bool) -> str:
        return self.italic_adaptation if italic and self.italic_adaptation else self.adaptation


GLYPHS = (
    GlyphSpec(
        "stem", 0xF2A00, "Plain stem", 0x131, 0x131,
        (("direct", 0x131, "dotless i"),),
        "Native STIX Two dotless-i outline and advance, unchanged.",
    ),
    GlyphSpec(
        "ascender", 0xF2A01, "Stem with ascender", 0x6C, 0x6C,
        (("direct", 0x6C, "lowercase l"),),
        "Native STIX Two lowercase-l outline and advance, unchanged.",
    ),
    GlyphSpec(
        "hook", 0xF2A02, "Stem with upper hook", 0x17F, None,
        (("upper-hook", 0x17F, "long s"), ("baseline", 0x131, "dotless i")),
        "Long-s upper hook without its cross stroke, joined to the native dotless-i baseline finish; the italic has no descending swash.",
    ),
    GlyphSpec(
        "descender", 0xF2A03, "Stem with descender", 0x131, None,
        (("upper", 0x131, "dotless i"), ("descender", 0x70, "lowercase p")),
        "Native dotless-i head joined to the straight lowercase-p descender.",
    ),
    GlyphSpec(
        "ascender-descender", 0xF2A04, "Stem with ascender and descender", 0x6C, None,
        (("upper", 0x6C, "lowercase l"), ("descender", 0x70, "lowercase p")),
        "Native lowercase-l head joined to the straight lowercase-p descender.",
    ),
    GlyphSpec(
        "hook-descender", 0xF2A05, "Stem with upper hook and descender", 0x17F, None,
        (("upper-hook", 0x17F, "long s"), ("descender", 0x70, "lowercase p")),
        "Long-s upper hook without its cross stroke, joined to the straight lowercase-p descender.",
    ),
    GlyphSpec(
        "tail", 0xF2A06, "Stem with lower hook", 0x237, 0x237,
        (("direct", 0x237, "dotless j"),),
        "Native STIX Two dotless-j outline and advance, unchanged.",
    ),
    GlyphSpec(
        "ascender-tail", 0xF2A07, "Stem with ascender and lower hook", 0x6C, None,
        (("upper", 0x6C, "lowercase l"), ("lower-hook", 0x237, "dotless j")),
        "Native lowercase-l head joined to the native dotless-j lower hook.",
    ),
    GlyphSpec(
        "hook-tail", 0xF2A08, "Stem with upper and lower hooks", 0x283, 0x283,
        (("direct", 0x283, "esh"),),
        "Native STIX Two esh outline and advance, unchanged.",
    ),
    GlyphSpec(
        "arm", 0xF2A09, "Arm", 0x72, 0x72,
        (("direct", 0x72, "lowercase r"),),
        "Native STIX Two lowercase-r outline and advance, unchanged.",
    ),
    GlyphSpec(
        "arm-descender", 0xF2A0A, "Arm with descender", 0x72, None,
        (("arm", 0x72, "lowercase r"), ("descender", 0x70, "lowercase p")),
        "Native r arm and head joined to the straight p descender.",
    ),
    GlyphSpec(
        "turned-arm", 0xF2A0B, "Turned arm", 0x279, 0x279,
        (("arm", 0x279, "turned r"),),
        "Roman retains the turned-r arm and advance with the upright right stem and serifs of lowercase u. Italic retains the native turned-r outline and advance unchanged.",
        roman_stem_donor=0x75,
    ),
    GlyphSpec(
        "turned-arm-ascender", 0xF2A0C, "Turned arm with ascender", 0x279, None,
        (("arm", 0x279, "turned r"), ("ascender", 0x6C, "lowercase l")),
        "Native turned-r arm with the l ascender; Roman retains the upright u baseline finish.",
        roman_stem_donor=0x75,
    ),
    GlyphSpec(
        "arm-ascender", 0xF2A0D, "Arm with ascender", 0x72, None,
        (("arm", 0x72, "lowercase r"), ("ascender", 0x6C, "lowercase l")),
        "Native r arm and baseline finish with the l ascender.",
    ),
    GlyphSpec(
        "arm-ascender-descender", 0xF2A0E, "Arm with ascender and descender", 0x72, None,
        (("arm", 0x72, "lowercase r"), ("ascender", 0x6C, "lowercase l"), ("descender", 0x70, "lowercase p")),
        "Native r arm with the l ascender and straight p descender.",
    ),
    GlyphSpec(
        "turned-arm-descender", 0xF2A0F, "Turned arm with descender", 0x279, None,
        (("arm", 0x279, "turned r"), ("descender", 0x70, "lowercase p")),
        "Native turned-r arm with the straight p descender; Roman retains the upright u head.",
        roman_stem_donor=0x75,
    ),
    GlyphSpec(
        "turned-arm-ascender-descender", 0xF2A10, "Turned arm with ascender and descender", 0x279, None,
        (("arm", 0x279, "turned r"), ("ascender", 0x6C, "lowercase l"), ("descender", 0x70, "lowercase p")),
        "Native turned-r arm with the l ascender and straight p descender.",
    ),
    GlyphSpec(
        "arm-hook", 0xF2A11, "Arm with upper hook", 0x72, None,
        (("arm", 0x72, "lowercase r"), ("upper-hook", 0x17F, "long s")),
        "Native r arm and baseline finish with the long-s upper hook, without its cross stroke.",
    ),
    GlyphSpec(
        "arm-hook-descender", 0xF2A12, "Arm with upper hook and descender", 0x72, None,
        (("arm", 0x72, "lowercase r"), ("upper-hook", 0x17F, "long s"), ("descender", 0x70, "lowercase p")),
        "Native r arm with the crossbar-free long-s upper hook and straight p descender.",
    ),
    GlyphSpec(
        "turned-arm-tail", 0xF2A13, "Turned arm with lower hook", 0x279, None,
        (("arm", 0x279, "turned r"), ("lower-hook", 0x237, "dotless j")),
        "Native turned-r arm with the dotless-j lower hook; Roman retains the upright u head.",
        roman_stem_donor=0x75,
    ),
    GlyphSpec(
        "turned-arm-ascender-tail", 0xF2A14, "Turned arm with ascender and lower hook", 0x279, None,
        (("arm", 0x279, "turned r"), ("ascender", 0x6C, "lowercase l"), ("lower-hook", 0x237, "dotless j")),
        "Native turned-r arm with the l ascender and dotless-j lower hook.",
    ),
    GlyphSpec(
        "arch", 0xF2A15, "Arch", 0x6E, 0x6E,
        (("direct", 0x6E, "lowercase n"),),
        "Native STIX Two lowercase-n outline and advance, unchanged.",
    ),
    GlyphSpec(
        "arch-descender", 0xF2A16, "Arch with left descender", 0x6E, None,
        (("arch", 0x6E, "lowercase n"), ("descender", 0x70, "lowercase p")),
        "Native n arch and head with the straight p descender on the left; the n advance is retained.",
    ),
    GlyphSpec(
        "turned-arch", 0xF2A17, "Turned arch", 0x75, 0x75,
        (("direct", 0x75, "lowercase u"),),
        "Native STIX Two lowercase-u outline and advance, unchanged.",
    ),
    GlyphSpec(
        "turned-arch-ascender", 0xF2A18, "Turned arch with right ascender", 0x75, None,
        (("arch", 0x75, "lowercase u"), ("ascender", 0x6C, "lowercase l")),
        "Native u arch and baseline finish with the l ascender on the right; the u advance is retained.",
    ),
    GlyphSpec(
        "arch-ascender", 0xF2A19, "Arch with left ascender", 0x68, 0x68,
        (("direct", 0x68, "lowercase h"),),
        "Native STIX Two lowercase-h outline and advance, unchanged.",
    ),
    GlyphSpec(
        "arch-ascender-descender", 0xF2A1A, "Arch with left ascender and left descender", 0x68, None,
        (("arch", 0x68, "lowercase h"), ("descender", 0x70, "lowercase p")),
        "Native h arch and ascender with the straight p descender on the left; the h advance is retained.",
    ),
    GlyphSpec(
        "turned-arch-descender", 0xF2A1B, "Turned arch with right descender", 0x265, None,
        (("arch", 0x265, "turned h"), ("descender", 0x70, "lowercase p")),
        "Native turned-h arch and heads with the complete p descender finish; the turned-h advance is retained.",
    ),
    GlyphSpec(
        "turned-arch-ascender-descender", 0xF2A1C, "Turned arch with right ascender and right descender", 0x265, None,
        (("arch", 0x265, "turned h"), ("ascender", 0x6C, "lowercase l"), ("descender", 0x70, "lowercase p")),
        "Native turned-h arch with the l ascender and complete p descender finish on the right; the turned-h advance is retained.",
    ),
    GlyphSpec(
        "arch-hook", 0xF2A1D, "Arch with left upper hook", 0x266, 0x266,
        (("direct", 0x266, "h with hook"),),
        "Native STIX Two h-with-hook outline and advance, unchanged, including its broad upper crown.",
    ),
    GlyphSpec(
        "arch-hook-descender", 0xF2A1E, "Arch with left upper hook and left descender", 0x266, None,
        (("arch", 0x266, "h with hook"), ("descender", 0x70, "lowercase p")),
        "Native h-with-hook arch and crown with the straight p descender on the left; its native advance is retained.",
    ),
    GlyphSpec(
        "turned-arch-tail", 0xF2A1F, "Turned arch with right lower hook", 0x75, None,
        (("arch", 0x75, "lowercase u"), ("lower-hook", 0x261, "single-story g")),
        "Native u arch and heads with the broad single-story-g lower hook on the right; the u advance is retained.",
    ),
    GlyphSpec(
        "turned-arch-ascender-tail", 0xF2A20, "Turned arch with right ascender and right lower hook", 0x75, None,
        (("arch", 0x75, "lowercase u"), ("ascender", 0x6C, "lowercase l"), ("lower-hook", 0x261, "single-story g")),
        "Native u arch with the l ascender and broad single-story-g lower hook on the right; the u advance is retained.",
    ),
    GlyphSpec(
        "bowl", 0xF2A21, "Bowl", 0x62, None,
        (("bowl", 0x62, "lowercase b"), ("head", 0x70, "lowercase p")),
        "Native b bowl, counter and baseline with the short upright p head; the b advance is retained, with neither ascender nor descender.",
    ),
    GlyphSpec(
        "bowl-descender", 0xF2A22, "Bowl with descender", 0x70, 0x70,
        (("direct", 0x70, "lowercase p"),),
        "Native STIX Two lowercase-p outline and advance, unchanged.",
    ),
    GlyphSpec(
        "turned-bowl", 0xF2A23, "Turned bowl", 0x251, 0x251,
        (("direct", 0x251, "Latin alpha"),),
        "Native STIX Two Latin-alpha outline and advance, unchanged.",
    ),
    GlyphSpec(
        "turned-bowl-ascender", 0xF2A24, "Turned bowl with ascender", 0x64, 0x64,
        (("direct", 0x64, "lowercase d"),),
        "Native STIX Two lowercase-d outline and advance, unchanged.",
    ),
    GlyphSpec(
        "bowl-ascender", 0xF2A25, "Bowl with ascender", 0x62, 0x62,
        (("direct", 0x62, "lowercase b"),),
        "Native STIX Two lowercase-b outline and advance, unchanged.",
    ),
    GlyphSpec(
        "bowl-ascender-descender", 0xF2A26, "Bowl with ascender and descender", 0xFE, 0xFE,
        (("direct", 0xFE, "thorn"),),
        "Native STIX Two thorn outline and advance, unchanged.",
    ),
    GlyphSpec(
        "turned-bowl-descender", 0xF2A27, "Turned bowl with descender", 0x71, 0x71,
        (("direct", 0x71, "lowercase q"),),
        "Native STIX Two lowercase-q outline and advance, unchanged.",
    ),
    GlyphSpec(
        "turned-bowl-ascender-descender", 0xF2A28, "Turned bowl with ascender and descender", 0x64, None,
        (("bowl", 0x64, "lowercase d"), ("descender", 0x71, "lowercase q")),
        "Native d bowl, counter and ascender with the straight q descender; the d advance is retained.",
    ),
    GlyphSpec(
        "bowl-hook", 0xF2A29, "Bowl with upper hook", 0x62, None,
        (("bowl", 0x62, "lowercase b"), ("upper-hook", 0x253, "b with hook")),
        "Native b bowl, counter and baseline with the upper hook of U+0253 b with hook; the b advance is retained.",
    ),
    GlyphSpec(
        "bowl-hook-descender", 0xF2A2A, "Bowl with upper hook and descender", 0xFE, None,
        (("bowl", 0xFE, "thorn"), ("upper-hook", 0x253, "b with hook")),
        "Native thorn bowl, counter and descender with the upper hook of U+0253 b with hook; the thorn advance is retained.",
    ),
    GlyphSpec(
        "turned-bowl-tail", 0xF2A2B, "Turned bowl with lower hook", 0x251, None,
        (("bowl", 0x251, "Latin alpha"), ("lower-hook", 0x261, "single-story g")),
        "Native Latin-alpha bowl, counter and head with the broad single-story-g lower hook; the alpha advance is retained.",
    ),
    GlyphSpec(
        "turned-bowl-ascender-tail", 0xF2A2C, "Turned bowl with ascender and lower hook", 0x64, None,
        (("bowl", 0x64, "lowercase d"), ("lower-hook", 0x261, "single-story g")),
        "Native d bowl, counter and ascender with the broad single-story-g lower hook; the d advance is retained.",
    ),
    GlyphSpec(
        'arch-right-descender', 0xF2A2D, 'Arch with right descender', 0x19E, None,
        (('arch', 0x19E, 'n with long right leg'), ('right-descender', 0x70, 'lowercase p'),),
        'Native n with long right leg arch and left head with the complete p descender finish on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'arch-descenders', 0xF2A2E, 'Arch with descenders', 0x19E, None,
        (('arch', 0x19E, 'n with long right leg'), ('right-descender', 0x70, 'lowercase p'), ('left-descender', 0x70, 'lowercase p'),),
        'Native n with long right leg arch and left head with the complete p descender finish on the right and the complete p descender finish on the left; additional inter-stave spacing separates neighboring terminals by 50 units; two connecting arch curves lengthen and the advance grows accordingly.',
    ),
    GlyphSpec(
        'turned-arch-left-ascender', 0xF2A2F, 'Turned arch with left ascender', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-ascender', 0x6C, 'lowercase l'),),
        'Native lowercase u arch with the native l ascender on the left; the native arch advance is retained.',
    ),
    GlyphSpec(
        'turned-arch-ascenders', 0xF2A30, 'Turned arch with ascenders', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-ascender', 0x6C, 'lowercase l'), ('right-ascender', 0x6C, 'lowercase l'),),
        'Native lowercase u arch with the native l ascender on the left, the established l ascender on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'arch-left-ascender-right-descender', 0xF2A31, 'Arch with left ascender and right descender', 0xA727, None,
        (('arch', 0xA727, 'heng'), ('right-descender', 0x70, 'lowercase p'),),
        'Native heng arch and left head with the complete p descender finish on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'arch-left-ascender-descenders', 0xF2A32, 'Arch with left ascender and descenders', 0xA727, None,
        (('arch', 0xA727, 'heng'), ('right-descender', 0x70, 'lowercase p'), ('left-descender', 0x70, 'lowercase p'),),
        'Native heng arch and left head with the complete p descender finish on the right and the complete p descender finish on the left; additional inter-stave spacing separates neighboring terminals by 50 units; two connecting arch curves lengthen and the advance grows accordingly.',
    ),
    GlyphSpec(
        'turned-arch-left-ascender-right-descender', 0xF2A33, 'Turned arch with left ascender and right descender', 0x265, None,
        (('arch', 0x265, 'turned h'), ('left-ascender', 0x6C, 'lowercase l'), ('right-descender', 0x70, 'lowercase p'),),
        'Native turned h arch with the native l ascender on the left, the full p descender finish on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'turned-arch-ascenders-right-descender', 0xF2A34, 'Turned arch with ascenders and right descender', 0x265, None,
        (('arch', 0x265, 'turned h'), ('left-ascender', 0x6C, 'lowercase l'), ('right-ascender', 0x6C, 'lowercase l'), ('right-descender', 0x70, 'lowercase p'),),
        'Native turned h arch with the native l ascender on the left, the established l ascender on the right, the full p descender finish on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'arch-left-hook-right-descender', 0xF2A35, 'Arch with left upper hook and right descender', 0x267, None,
        (('arch', 0x267, 'heng with hook'), ('right-descender', 0x70, 'lowercase p'),),
        'Native heng with hook arch and left head with the complete p descender finish on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'arch-left-hook-descenders', 0xF2A36, 'Arch with left upper hook and descenders', 0x267, None,
        (('arch', 0x267, 'heng with hook'), ('right-descender', 0x70, 'lowercase p'), ('left-descender', 0x70, 'lowercase p'),),
        'Native heng with hook arch and left head with the complete p descender finish on the right and the complete p descender finish on the left; additional inter-stave spacing separates neighboring terminals by 50 units; two connecting arch curves lengthen and the advance grows accordingly.',
    ),
    GlyphSpec(
        'turned-arch-left-ascender-right-tail', 0xF2A37, 'Turned arch with left ascender and right lower hook', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-ascender', 0x6C, 'lowercase l'), ('right-lower-hook', 0x261, 'single-story g'),),
        'Native lowercase u arch with the native l ascender on the left, the broad single-story-g hook on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'turned-arch-ascenders-right-tail', 0xF2A38, 'Turned arch with ascenders and right lower hook', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-ascender', 0x6C, 'lowercase l'), ('right-ascender', 0x6C, 'lowercase l'), ('right-lower-hook', 0x261, 'single-story g'),),
        'Native lowercase u arch with the native l ascender on the left, the established l ascender on the right, the broad single-story-g hook on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'arch-right-tail', 0xF2A39, 'Arch with right lower hook', 0x14B, 0x14B,
        (('direct', 0x14B, 'eng'),),
        'Native STIX Two eng outline and advance, unchanged.',
    ),
    GlyphSpec(
        'arch-left-descender-right-tail', 0xF2A3A, 'Arch with left descender and right lower hook', 0x14B, None,
        (('arch', 0x14B, 'eng'), ('lower-closure', 0x62, 'lowercase b'),),
        'Native eng arch and lower sweep closed into the extended left shaft using the lower bowl joins of b; the free hook tip and facing foot are replaced, and the native arch width and advance are retained.',
    ),
    GlyphSpec(
        'turned-arch-left-hook', 0xF2A3B, 'Turned arch with left upper hook', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-upper-hook', 0x266, 'h with hook'),),
        'Native lowercase u arch with the native h-with-hook crown on the left; the native arch advance is retained.',
    ),
    GlyphSpec(
        'turned-arch-left-hook-right-ascender', 0xF2A3C, 'Turned arch with left upper hook and right ascender', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-upper-hook', 0x266, 'h with hook'), ('right-ascender', 0x6C, 'lowercase l'), ('upper-closure', 0x64, 'lowercase d'),),
        'Native lowercase u arch with the h-with-hook crown closed into the right ascender using the upper bowl joins of d; the free hook tip and facing head are replaced, and the native arch width and advance are retained.',
    ),
    GlyphSpec(
        'arch-left-ascender-right-tail', 0xF2A3D, 'Arch with left ascender and right lower hook', 0xA727, 0xA727,
        (('direct', 0xA727, 'heng'),),
        'Native STIX Two heng outline and advance, unchanged.',
    ),
    GlyphSpec(
        'arch-left-ascender-descender-right-tail', 0xF2A3E, 'Arch with left ascender and left descender and right lower hook', 0xA727, None,
        (('arch', 0xA727, 'heng'), ('lower-closure', 0x62, 'lowercase b'),),
        'Native heng arch, ascender and lower sweep closed into the extended left shaft using the lower bowl joins of b; the free hook tip and facing foot are replaced, and the native arch width and advance are retained.',
    ),
    GlyphSpec(
        'turned-arch-left-hook-right-descender', 0xF2A3F, 'Turned arch with left upper hook and right descender', 0x265, None,
        (('arch', 0x265, 'turned h'), ('left-upper-hook', 0x266, 'h with hook'), ('right-descender', 0x70, 'lowercase p'),),
        'Native turned h arch with the native h-with-hook crown on the left, the full p descender finish on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'turned-arch-left-hook-right-ascender-descender', 0xF2A40, 'Turned arch with left upper hook and right ascender and right descender', 0x265, None,
        (('arch', 0x265, 'turned h'), ('left-upper-hook', 0x266, 'h with hook'), ('right-ascender', 0x6C, 'lowercase l'), ('upper-closure', 0x64, 'lowercase d'), ('right-descender', 0x70, 'lowercase p'),),
        'Native turned h arch and full p descender with the h-with-hook crown closed into the right ascender using the upper bowl joins of d; the free hook tip and facing head are replaced, and the native arch width and advance are retained.',
    ),
    GlyphSpec(
        'arch-left-hook-right-tail', 0xF2A41, 'Arch with left upper hook and right lower hook', 0x267, 0x267,
        (('direct', 0x267, 'heng with hook'),),
        'Native STIX Two heng with hook outline and advance, unchanged.',
    ),
    GlyphSpec(
        'arch-left-hook-descender-right-tail', 0xF2A42, 'Arch with left upper hook and left descender and right lower hook', 0x267, None,
        (('arch', 0x267, 'heng with hook'), ('lower-closure', 0x62, 'lowercase b'),),
        'Native heng with hook arch, upper hook and lower sweep closed into the extended left shaft using the lower bowl joins of b; the free hook tip and facing foot are replaced, and the native arch width and advance are retained.',
    ),
    GlyphSpec(
        'turned-arch-left-hook-right-tail', 0xF2A43, 'Turned arch with left upper hook and right lower hook', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-upper-hook', 0x266, 'h with hook'), ('right-lower-hook', 0x261, 'single-story g'),),
        'Native lowercase u arch with the native h-with-hook crown on the left, the broad single-story-g hook on the right; the native arch advance is retained.',
    ),
    GlyphSpec(
        'turned-arch-left-hook-right-ascender-tail', 0xF2A44, 'Turned arch with left upper hook and right ascender and right lower hook', 0x75, None,
        (('arch', 0x75, 'lowercase u'), ('left-upper-hook', 0x266, 'h with hook'), ('right-ascender', 0x6C, 'lowercase l'), ('upper-closure', 0x64, 'lowercase d'), ('right-lower-hook', 0x261, 'single-story g'),),
        'Native lowercase u arch and broad single-story-g lower hook with the h-with-hook crown closed into the right ascender using the upper bowl joins of d; the free hook tip and facing head are replaced, and the native arch width and advance are retained.',
    ),
    GlyphSpec(
        'arched-arm', 0xF2A45, 'Arched arm', 0x72, None,
        (('arch', 0x6E, 'lowercase n'), ('terminal-arm', 0x72, 'lowercase r'),),
        'Native arch and outer endings of U+F2A15 joined to the detached native arm of lowercase r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-arm-descender', 0xF2A46, 'Arched arm with descender', 0x72, None,
        (('arch', 0x6E, 'lowercase n'), ('descender', 0x70, 'lowercase p'), ('terminal-arm', 0x72, 'lowercase r'),),
        'Native arch and outer endings of U+F2A16 joined to the detached native arm of lowercase r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-arm', 0xF2A47, 'Turned arched arm', 0x279, None,
        (('arch', 0x75, 'lowercase u'), ('terminal-arm', 0x279, 'turned r'),),
        'Native arch and outer endings of U+F2A17 joined to the detached native arm of turned r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-arm-ascender', 0xF2A48, 'Turned arched arm with ascender', 0x279, None,
        (('arch', 0x75, 'lowercase u'), ('ascender', 0x6C, 'lowercase l'), ('terminal-arm', 0x279, 'turned r'),),
        'Native arch and outer endings of U+F2A18 joined to the detached native arm of turned r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-arm-ascender', 0xF2A49, 'Arched arm with ascender', 0x72, None,
        (('arch', 0x68, 'lowercase h'), ('terminal-arm', 0x72, 'lowercase r'),),
        'Native arch and outer endings of U+F2A19 joined to the detached native arm of lowercase r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-arm-ascender-descender', 0xF2A4A, 'Arched arm with ascender and descender', 0x72, None,
        (('arch', 0x68, 'lowercase h'), ('descender', 0x70, 'lowercase p'), ('terminal-arm', 0x72, 'lowercase r'),),
        'Native arch and outer endings of U+F2A1A joined to the detached native arm of lowercase r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-arm-descender', 0xF2A4B, 'Turned arched arm with descender', 0x279, None,
        (('arch', 0x265, 'turned h'), ('descender', 0x70, 'lowercase p'), ('terminal-arm', 0x279, 'turned r'),),
        'Native arch and outer endings of U+F2A1B joined to the detached native arm of turned r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-arm-ascender-descender', 0xF2A4C, 'Turned arched arm with ascender and descender', 0x279, None,
        (('arch', 0x265, 'turned h'), ('ascender', 0x6C, 'lowercase l'), ('descender', 0x70, 'lowercase p'), ('terminal-arm', 0x279, 'turned r'),),
        'Native arch and outer endings of U+F2A1C joined to the detached native arm of turned r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-arm-hook', 0xF2A4D, 'Arched arm with upper hook', 0x72, None,
        (('arch', 0x266, 'h with hook'), ('terminal-arm', 0x72, 'lowercase r'),),
        'Native arch and outer endings of U+F2A1D joined to the detached native arm of lowercase r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-arm-hook-descender', 0xF2A4E, 'Arched arm with upper hook and descender', 0x72, None,
        (('arch', 0x266, 'h with hook'), ('descender', 0x70, 'lowercase p'), ('terminal-arm', 0x72, 'lowercase r'),),
        'Native arch and outer endings of U+F2A1E joined to the detached native arm of lowercase r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-arm-tail', 0xF2A4F, 'Turned arched arm with lower hook', 0x279, None,
        (('arch', 0x75, 'lowercase u'), ('lower-hook', 0x261, 'single-story g'), ('terminal-arm', 0x279, 'turned r'),),
        'Native arch and outer endings of U+F2A1F joined to the detached native arm of turned r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-arm-ascender-tail', 0xF2A50, 'Turned arched arm with ascender and lower hook', 0x279, None,
        (('arch', 0x75, 'lowercase u'), ('ascender', 0x6C, 'lowercase l'), ('lower-hook', 0x261, 'single-story g'), ('terminal-arm', 0x279, 'turned r'),),
        'Native arch and outer endings of U+F2A20 joined to the detached native arm of turned r; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'double-arch', 0xF2A51, 'Double arch', 0x6D, 0x6D,
        (('direct', 0x6D, 'lowercase m'),),
        'Native STIX Two lowercase m outline and advance, unchanged.',
    ),
    GlyphSpec(
        'double-arch-descender', 0xF2A52, 'Double arch with left descender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with lowercase p left lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch', 0xF2A53, 'Turned double arch', 0x26F, 0x26F,
        (('direct', 0x26F, 'turned m'),),
        'Native STIX Two turned m outline and advance, unchanged.',
    ),
    GlyphSpec(
        'turned-double-arch-ascender', 0xF2A54, 'Turned double arch with right ascender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('right-upper', 0x6C, 'lowercase l'),),
        'Native turned m double-arch body and middle stave with lowercase l right upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-ascender', 0xF2A55, 'Double arch with left ascender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x6C, 'lowercase l'),),
        'Native lowercase m double-arch body and middle stave with lowercase l left upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-ascender-descender', 0xF2A56, 'Double arch with left ascender and left descender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x6C, 'lowercase l'), ('left-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with lowercase l left upper ending, lowercase p left lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-descender', 0xF2A57, 'Turned double arch with right descender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('right-lower', 0x70, 'lowercase p'),),
        'Native turned m double-arch body and middle stave with lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-ascender-descender', 0xF2A58, 'Turned double arch with right ascender and right descender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('right-upper', 0x6C, 'lowercase l'), ('right-lower', 0x70, 'lowercase p'),),
        'Native turned m double-arch body and middle stave with lowercase l right upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-hook', 0xF2A59, 'Double arch with left upper hook', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x266, 'h with hook'),),
        'Native lowercase m double-arch body and middle stave with h with hook left upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-hook-descender', 0xF2A5A, 'Double arch with left upper hook and left descender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x266, 'h with hook'), ('left-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with h with hook left upper ending, lowercase p left lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-tail', 0xF2A5B, 'Turned double arch with right lower hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('right-lower', 0x261, 'single-story g'),),
        'Native turned m double-arch body and middle stave with single-story g right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-ascender-tail', 0xF2A5C, 'Turned double arch with right ascender and right lower hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('right-upper', 0x6C, 'lowercase l'), ('right-lower', 0x261, 'single-story g'),),
        'Native turned m double-arch body and middle stave with lowercase l right upper ending, single-story g right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'arched-bowl', 0xF2A5D, 'Arched bowl', 0x62, None,
        (('arch', 0x6E, 'lowercase n'), ('terminal-bowl', 0x62, 'lowercase b'),),
        'Native arch and outer endings of U+F2A15 joined to the native bowl and counter of lowercase b; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-bowl-descender', 0xF2A5E, 'Arched bowl with descender', 0x70, None,
        (('arch', 0x6E, 'lowercase n'), ('descender', 0x70, 'lowercase p'), ('terminal-bowl', 0x62, 'lowercase b'),),
        'Native arch and outer endings of U+F2A16 joined to the native bowl and counter of lowercase b; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-bowl', 0xF2A5F, 'Turned arched bowl', 0x251, None,
        (('arch', 0x75, 'lowercase u'), ('terminal-bowl', 0x251, 'Latin alpha'),),
        'Native arch and outer endings of U+F2A17 joined to the native bowl and counter of Latin alpha; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-bowl-ascender', 0xF2A60, 'Turned arched bowl with ascender', 0x64, None,
        (('arch', 0x75, 'lowercase u'), ('ascender', 0x6C, 'lowercase l'), ('terminal-bowl', 0x251, 'Latin alpha'),),
        'Native arch and outer endings of U+F2A18 joined to the native bowl and counter of Latin alpha; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-bowl-ascender', 0xF2A61, 'Arched bowl with ascender', 0x62, None,
        (('arch', 0x68, 'lowercase h'), ('terminal-bowl', 0x62, 'lowercase b'),),
        'Native arch and outer endings of U+F2A19 joined to the native bowl and counter of lowercase b; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-bowl-ascender-descender', 0xF2A62, 'Arched bowl with ascender and descender', 0xFE, None,
        (('arch', 0x68, 'lowercase h'), ('descender', 0x70, 'lowercase p'), ('terminal-bowl', 0x62, 'lowercase b'),),
        'Native arch and outer endings of U+F2A1A joined to the native bowl and counter of lowercase b; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-bowl-descender', 0xF2A63, 'Turned arched bowl with descender', 0x71, None,
        (('arch', 0x265, 'turned h'), ('descender', 0x70, 'lowercase p'), ('terminal-bowl', 0x251, 'Latin alpha'),),
        'Native arch and outer endings of U+F2A1B joined to the native bowl and counter of Latin alpha; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-bowl-ascender-descender', 0xF2A64, 'Turned arched bowl with ascender and descender', 0x64, None,
        (('arch', 0x265, 'turned h'), ('ascender', 0x6C, 'lowercase l'), ('descender', 0x70, 'lowercase p'), ('terminal-bowl', 0x251, 'Latin alpha'),),
        'Native arch and outer endings of U+F2A1C joined to the native bowl and counter of Latin alpha; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-bowl-hook', 0xF2A65, 'Arched bowl with upper hook', 0x62, None,
        (('arch', 0x266, 'h with hook'), ('terminal-bowl', 0x62, 'lowercase b'),),
        'Native arch and outer endings of U+F2A1D joined to the native bowl and counter of lowercase b; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'arched-bowl-hook-descender', 0xF2A66, 'Arched bowl with upper hook and descender', 0xFE, None,
        (('arch', 0x266, 'h with hook'), ('descender', 0x70, 'lowercase p'), ('terminal-bowl', 0x62, 'lowercase b'),),
        'Native arch and outer endings of U+F2A1E joined to the native bowl and counter of lowercase b; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-bowl-tail', 0xF2A67, 'Turned arched bowl with lower hook', 0x251, None,
        (('arch', 0x75, 'lowercase u'), ('lower-hook', 0x261, 'single-story g'), ('terminal-bowl', 0x251, 'Latin alpha'),),
        'Native arch and outer endings of U+F2A1F joined to the native bowl and counter of Latin alpha; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'turned-arched-bowl-ascender-tail', 0xF2A68, 'Turned arched bowl with ascender and lower hook', 0x64, None,
        (('arch', 0x75, 'lowercase u'), ('ascender', 0x6C, 'lowercase l'), ('lower-hook', 0x261, 'single-story g'), ('terminal-bowl', 0x251, 'Latin alpha'),),
        'Native arch and outer endings of U+F2A20 joined to the native bowl and counter of Latin alpha; the terminal curves remain rigid and the advance follows the constructed span.',
    ),
    GlyphSpec(
        'double-arch-right-descender', 0xF2A69, 'Double arch with right descender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('right-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-descenders', 0xF2A6A, 'Double arch with descenders', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-lower', 0x70, 'lowercase p'), ('right-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with lowercase p left lower ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-ascender', 0xF2A6B, 'Turned double arch with left ascender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x6C, 'lowercase l'),),
        'Native turned m double-arch body and middle stave with lowercase l left upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-ascenders', 0xF2A6C, 'Turned double arch with ascenders', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x6C, 'lowercase l'), ('right-upper', 0x6C, 'lowercase l'),),
        'Native turned m double-arch body and middle stave with lowercase l left upper ending, lowercase l right upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-ascender-right-descender', 0xF2A6D, 'Double arch with left ascender and right descender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x6C, 'lowercase l'), ('right-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with lowercase l left upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-ascender-descenders', 0xF2A6E, 'Double arch with left ascender and descenders', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x6C, 'lowercase l'), ('left-lower', 0x70, 'lowercase p'), ('right-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with lowercase l left upper ending, lowercase p left lower ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-ascender-right-descender', 0xF2A6F, 'Turned double arch with left ascender and right descender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x6C, 'lowercase l'), ('right-lower', 0x70, 'lowercase p'),),
        'Native turned m double-arch body and middle stave with lowercase l left upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-ascenders-right-descender', 0xF2A70, 'Turned double arch with ascenders and right descender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x6C, 'lowercase l'), ('right-upper', 0x6C, 'lowercase l'), ('right-lower', 0x70, 'lowercase p'),),
        'Native turned m double-arch body and middle stave with lowercase l left upper ending, lowercase l right upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-hook-right-descender', 0xF2A71, 'Double arch with left upper hook and right descender', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x266, 'h with hook'), ('right-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with h with hook left upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-hook-descenders', 0xF2A72, 'Double arch with left upper hook and descenders', 0x6D, None,
        (('double-arch', 0x6D, 'lowercase m'), ('left-upper', 0x266, 'h with hook'), ('left-lower', 0x70, 'lowercase p'), ('right-lower', 0x70, 'lowercase p'),),
        'Native lowercase m double-arch body and middle stave with h with hook left upper ending, lowercase p left lower ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-ascender-right-tail', 0xF2A73, 'Turned double arch with left ascender and right lower hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x6C, 'lowercase l'), ('right-lower', 0x261, 'single-story g'),),
        'Native turned m double-arch body and middle stave with lowercase l left upper ending, single-story g right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-ascenders-right-tail', 0xF2A74, 'Turned double arch with ascenders and right lower hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x6C, 'lowercase l'), ('right-upper', 0x6C, 'lowercase l'), ('right-lower', 0x261, 'single-story g'),),
        'Native turned m double-arch body and middle stave with lowercase l left upper ending, lowercase l right upper ending, single-story g right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-right-tail', 0xF2A75, 'Double arch with right lower hook', 0x271, 0x271,
        (('direct', 0x271, 'm with hook'),),
        'Native STIX Two m with hook outline and advance, unchanged.',
    ),
    GlyphSpec(
        'double-arch-left-descender-right-tail', 0xF2A76, 'Double arch with left descender and right lower hook', 0x271, None,
        (('double-arch', 0x271, 'm with hook'), ('left-lower', 0x70, 'lowercase p'),),
        'Native m with hook double-arch body and middle stave with lowercase p left lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-hook', 0xF2A77, 'Turned double arch with left upper hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x266, 'h with hook'),),
        'Native turned m double-arch body and middle stave with h with hook left upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-hook-right-ascender', 0xF2A78, 'Turned double arch with left upper hook and right ascender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x266, 'h with hook'), ('right-upper', 0x6C, 'lowercase l'),),
        'Native turned m double-arch body and middle stave with h with hook left upper ending, lowercase l right upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-ascender-right-tail', 0xF2A79, 'Double arch with left ascender and right lower hook', 0x271, None,
        (('double-arch', 0x271, 'm with hook'), ('left-upper', 0x6C, 'lowercase l'),),
        'Native m with hook double-arch body and middle stave with lowercase l left upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-ascender-descender-right-tail', 0xF2A7A, 'Double arch with left ascender and left descender and right lower hook', 0x271, None,
        (('double-arch', 0x271, 'm with hook'), ('left-upper', 0x6C, 'lowercase l'), ('left-lower', 0x70, 'lowercase p'),),
        'Native m with hook double-arch body and middle stave with lowercase l left upper ending, lowercase p left lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-hook-right-descender', 0xF2A7B, 'Turned double arch with left upper hook and right descender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x266, 'h with hook'), ('right-lower', 0x70, 'lowercase p'),),
        'Native turned m double-arch body and middle stave with h with hook left upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-hook-right-ascender-descender', 0xF2A7C, 'Turned double arch with left upper hook and right ascender and right descender', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x266, 'h with hook'), ('right-upper', 0x6C, 'lowercase l'), ('right-lower', 0x70, 'lowercase p'),),
        'Native turned m double-arch body and middle stave with h with hook left upper ending, lowercase l right upper ending, lowercase p right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-hook-right-tail', 0xF2A7D, 'Double arch with left upper hook and right lower hook', 0x271, None,
        (('double-arch', 0x271, 'm with hook'), ('left-upper', 0x266, 'h with hook'),),
        'Native m with hook double-arch body and middle stave with h with hook left upper ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'double-arch-left-hook-descender-right-tail', 0xF2A7E, 'Double arch with left upper hook and left descender and right lower hook', 0x271, None,
        (('double-arch', 0x271, 'm with hook'), ('left-upper', 0x266, 'h with hook'), ('left-lower', 0x70, 'lowercase p'),),
        'Native m with hook double-arch body and middle stave with h with hook left upper ending, lowercase p left lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-hook-right-tail', 0xF2A7F, 'Turned double arch with left upper hook and right lower hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x266, 'h with hook'), ('right-lower', 0x261, 'single-story g'),),
        'Native turned m double-arch body and middle stave with h with hook left upper ending, single-story g right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        'turned-double-arch-left-hook-right-ascender-tail', 0xF2A80, 'Turned double arch with left upper hook and right ascender and right lower hook', 0x26F, None,
        (('double-arch', 0x26F, 'turned m'), ('left-upper', 0x266, 'h with hook'), ('right-upper', 0x6C, 'lowercase l'), ('right-lower', 0x261, 'single-story g'),),
        'Native turned m double-arch body and middle stave with h with hook left upper ending, lowercase l right upper ending, single-story g right lower ending; native curves and body advance are retained, and outer hooks stay free.',
    ),
    GlyphSpec(
        "double-bowl", 0xF2B04, "Double bowl", 0x62, None,
        (("double-lobes", 0x25C, "reversed open e"), ("stem", 0x62, "lowercase b"), ("head", 0x70, "lowercase p")),
        "Native reversed-epsilon outer lobes joined to a short b/p shaft with fitted b counter curves and balanced roofs; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "double-bowl-descender", 0xF2B05, "Double bowl with descender", 0x62, None,
        (("double-lobes", 0x25C, "reversed open e"), ("stem", 0x70, "lowercase p"), ("counter-joins", 0x62, "lowercase b")),
        "Native reversed-epsilon lobes and fitted b counter curves with a p descender; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "turned-double-bowl", 0xF2B06, "Turned double bowl", 0x251, None,
        (("double-lobes", 0x25B, "open e"), ("stem", 0x251, "Latin alpha")),
        "Native upright-epsilon lobes joined to an alpha shaft with fitted bowl counter curves; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "turned-double-bowl-ascender", 0xF2B07, "Turned double bowl with ascender", 0x251, None,
        (("double-lobes", 0x25B, "open e"), ("stem", 0x64, "lowercase d"), ("counter-joins", 0x251, "Latin alpha")),
        "Native upright-epsilon lobes joined to a d shaft and ascender with fitted bowl counter curves; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "double-bowl-ascender", 0xF2B08, "Double bowl with ascender", 0x62, None,
        (("double-lobes", 0x25C, "reversed open e"), ("stem", 0x62, "lowercase b")),
        "Native reversed-epsilon lobes joined to a b shaft and ascender with fitted b counter curves; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "double-bowl-ascender-descender", 0xF2B09, "Double bowl with ascender and descender", 0x62, None,
        (("double-lobes", 0x25C, "reversed open e"), ("stem", 0xFE, "thorn"), ("counter-joins", 0x62, "lowercase b")),
        "Native reversed-epsilon lobes joined to a thorn shaft with fitted b counter curves; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "turned-double-bowl-descender", 0xF2B0A, "Turned double bowl with descender", 0x251, None,
        (("double-lobes", 0x25B, "open e"), ("stem", 0x71, "lowercase q"), ("counter-joins", 0x251, "Latin alpha")),
        "Native upright-epsilon lobes joined to a q shaft and descender with fitted bowl counter curves; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "turned-double-bowl-ascender-descender", 0xF2B0B, "Turned double bowl with ascender and descender", 0x251, None,
        (("double-lobes", 0x25B, "open e"), ("stem", 0x64, "lowercase d"), ("lower", 0x71, "lowercase q"), ("counter-joins", 0x251, "Latin alpha")),
        "Native upright-epsilon lobes and fitted bowl counter curves with a d ascender and q descender; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "double-bowl-upper-hook", 0xF2B0C, "Double bowl with upper hook", 0x62, None,
        (("double-lobes", 0x25C, "reversed open e"), ("stem", 0x62, "lowercase b"), ("upper", 0x253, "b with hook")),
        "Native reversed-epsilon lobes and fitted b counter curves with a b-with-hook upper ending; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "double-bowl-upper-hook-descender", 0xF2B0D, "Double bowl with upper hook and descender", 0x62, None,
        (("double-lobes", 0x25C, "reversed open e"), ("stem", 0xFE, "thorn"), ("upper", 0x253, "b with hook"), ("counter-joins", 0x62, "lowercase b")),
        "Native reversed-epsilon lobes and fitted b counter curves with a thorn shaft and b-with-hook upper ending; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "turned-double-bowl-lower-hook", 0xF2B0E, "Turned double bowl with lower hook", 0x251, None,
        (("double-lobes", 0x25B, "open e"), ("stem", 0x251, "Latin alpha"), ("lower", 0x261, "single-story g")),
        "Native upright-epsilon lobes and fitted bowl counter curves with an alpha shaft and single-story-g lower hook; Roman only.", roman_only=True,
    ),
    GlyphSpec(
        "turned-double-bowl-ascender-lower-hook", 0xF2B0F, "Turned double bowl with ascender and lower hook", 0x251, None,
        (("double-lobes", 0x25B, "open e"), ("stem", 0x64, "lowercase d"), ("lower", 0x261, "single-story g"), ("counter-joins", 0x251, "Latin alpha")),
        "Native upright-epsilon lobes and fitted bowl counter curves with a d ascender and single-story-g lower hook; Roman only.", roman_only=True,
    ),
)

# These twelve fixed allocations reuse the accepted basic-arch recipes and
# their outer endings; the terminal is the corresponding plain double bowl.
GLYPHS += tuple(
    GlyphSpec(
        glyph.glyph_id.replace("bowl", "double-bowl"),
        0xF2B40 + index,
        glyph.label.replace("bowl", "double bowl"),
        0x251 if index % 4 >= 2 else 0x62,
        None,
        (*glyph.references, ("double-lobes", 0x25B if index % 4 >= 2 else 0x25C,
                             "open e" if index % 4 >= 2 else "reversed open e")),
        f"Native arch and outer endings of U+{0xF2A15 + index:X} joined to the native double-bowl terminal; "
        "native epsilon follows each orientation with fitted bowl counter joins and balanced roofs; "
        "the advance follows the constructed span; Roman only.",
        roman_only=True,
    )
    for index, glyph in enumerate(glyph for glyph in GLYPHS if 0xF2A5D <= glyph.code_point <= 0xF2A68)
)

# The narrow single-stem spine increment parallels the two double-bowl
# families, with independent a/turned-a bellies and a flat epsilon finish.
# Fixed code points remain independent of the catalogue presentation order.
def _spine_references(glyph, variant):
    turned = variant % 4 >= 2
    if glyph.code_point >= 0xF2B40:
        stems = tuple(reference for reference in glyph.references if reference[0] != "double-lobes")
    elif turned:
        body = 0x64 if variant % 2 else 0x71 if variant // 4 == 1 else 0x251
        labels = {0x64: "lowercase d", 0x71: "lowercase q", 0x251: "Latin alpha"}
        stems = (("upright-shaft", body, labels[body]),)
        if variant // 4 == 2:
            stems += (("lower-hook", 0x261, "single-story g"),)
        elif variant == 7:
            stems += (("descender", 0x71, "lowercase q"),)
    else:
        stems = (("upright-shaft", 0x62, "lowercase b"),)
        if variant % 2 or variant // 4 == 0:
            stems += (("head-or-descender", 0x70, "lowercase p"),)
        if variant // 4 == 2:
            stems += (("upper-hook", 0x253, "b with hook"),)
    return stems + (
        ("spine-belly", 0x61 if turned else 0x250, "lowercase a" if turned else "turned a"),
        (("upper-ball", 0x61, "lowercase a upper ball") if turned
         else ("flat-free-terminal", 0x25B, "open e lower terminal")),
    )


def _italic_spine_references(glyph, variant):
    turned = variant % 4 >= 2
    if glyph.code_point >= 0xF2B40:
        stems = tuple(reference for reference in glyph.references
                      if reference[0] not in ("double-lobes", "terminal-bowl"))
        if turned:
            stems += (("shared-shaft-axis", 0x251, "Latin alpha"),)
    elif turned:
        stems = (("shaft-exit", 0x251, "Latin alpha"),)
        if variant % 2:
            stems += (("ascender", 0x64, "lowercase d"),)
        if variant // 4:
            stems += (("lower-ending", 0x71 if variant // 4 == 1 else 0x261,
                       "lowercase q" if variant // 4 == 1 else "single-story g"),)
    else:
        code = (0x70, 0x62, 0x253)[variant // 4]
        label = {0x70: "lowercase p", 0x62: "lowercase b", 0x253: "b with hook"}[code]
        stems = (("upper-ending", code, label),)
        if variant % 2 and code != 0x70:
            stems += (("descender", 0x70, "lowercase p"),)
    return stems + (
        ("diagonal-bowl", 0x250, "native Italic turned a"),
        (("upper-ball", 0x250, "turned native Italic turned-a ball") if turned
         else ("flat-free-terminal", 0x25B, "open e lower terminal")),
    )


GLYPHS += tuple(
    GlyphSpec(
        glyph.glyph_id.replace("double-bowl", "bowled-spine"),
        glyph.code_point + 12,
        glyph.label.replace("Double bowl", "Bowled spine").replace("double bowl", "bowled spine"),
        glyph.width_donor,
        None,
        _spine_references(glyph, index % 12),
        "Native a/turned-a diagonal belly with a separate enclosed counter, "
        "native upright stem endings, a flat lower epsilon finish in upper-bowled forms "
        "and a's native upper ball in lower-bowled forms; fitted stem joins.",
        italic_references=_italic_spine_references(glyph, index % 12),
        italic_adaptation="Native Italic turned-a diagonal bowl, rigidly half-turned for the "
        "lower-bowled direction; native Italic stem endings and carefully fitted joins. "
        "Upper-bowled forms have a flat lower epsilon finish; lower-bowled forms keep "
        "the native turned-a ball at the top. The single-storey Italic a is not a bowl donor.",
    )
    for index, glyph in enumerate(glyph for glyph in GLYPHS
                                 if 0xF2B04 <= glyph.code_point <= 0xF2B0F
                                 or 0xF2B40 <= glyph.code_point <= 0xF2B4B)
)
# Narrow opposed bowls: six independent endings on each of the two shafts.
# No shared arch or extension allocation belongs to this increment.
def _opposed_bowl_spec(index):
    left, right = divmod(index, 6)
    left_head = (0x70, 0x62, 0x253)[left // 2]
    right_foot = (0x251, 0x71, 0x261)[right // 2]
    references = [
        ("upper-belly", 0x250, "turned a"),
        ("lower-belly", 0x61, "lowercase a"),
        ("shaft-and-upper-shoulder", 0x62, "lowercase b"),
        ("left-head", left_head, {0x70: "lowercase p", 0x62: "lowercase b", 0x253: "b with hook"}[left_head]),
        ("right-foot", right_foot, {0x251: "Latin alpha", 0x71: "lowercase q", 0x261: "single-story g"}[right_foot]),
    ]
    if left % 2:
        references.append(("left-descender", 0x70, "lowercase p"))
    if right % 2:
        references.append(("right-ascender", 0x64, "lowercase d"))
    endings = []
    if left // 2:
        endings.append("left " + ("ascender" if left // 2 == 1 else "upper hook"))
    if left % 2:
        endings.append("left descender")
    if right % 2:
        endings.append("right ascender")
    if right // 2:
        endings.append("right " + ("descender" if right // 2 == 1 else "lower hook"))
    return GlyphSpec(
        f"opposed-bowls-{left}-{right}", 0xF2B1C + index,
        "Opposed bowls" + (" with " + " and ".join(endings) if endings else ""),
        0x61, None, tuple(references),
        "Integrated two-shaft sigmoid with opposed native a/turned-a bellies, "
        "two enclosed counters and a shared diagonal waist; native upright "
        "shaft endings, independently selected on each side. Roman only; no side arches.",
        roman_only=True,
    )


GLYPHS += tuple(_opposed_bowl_spec(index) for index in range(36))


def _arched_opposed_bowl_spec(index, side):
    left, right = divmod(index, 6)
    variant = left if side == "left" else right
    arch_code = 0xF2A15 + (variant // 2) * 4 + variant % 2 + (2 if side == "right" else 0)
    arch = next(glyph for glyph in GLYPHS if glyph.code_point == arch_code)
    base = _opposed_bowl_spec(12 + right if side == "left" else left * 6)
    references = list(base.references)
    donors = {code for _role, code, _label in references}
    for role, code, label in arch.references_for(False):
        if code not in donors:
            references.append((f"arch-{role}", code, label))
            donors.add(code)
    label = _opposed_bowl_spec(index).label.replace("Opposed bowls", f"{side.title()}-arched opposed bowls")
    return GlyphSpec(
        f"{side}-arched-opposed-bowls-{left}-{right}",
        (0xF2B58 if side == "left" else 0xF2B7C) + index,
        label, 0x61, None, tuple(references),
        "Native side arch joined through its shared shaft to the compact opposed-bowl body; "
        "two unchanged diagonal body counters and native outer-shaft endings. "
        "The sigmoid is translated rigidly when needed and keeps its native width. Roman only.",
        roman_only=True,
    )


GLYPHS += tuple(_arched_opposed_bowl_spec(index, side)
                for side in ("left", "right") for index in range(36))
GLYPHS += tuple(
    GlyphSpec(
        glyph_id, 0xF2B00 + index, label, donor, donor,
        (("direct", donor, native_label),),
        "Native STIX Two outline and advance, unchanged; reserved standalone sign without a language reading.",
    )
    for index, (glyph_id, label, donor, native_label) in enumerate((
        ("special-ring", "Ring", 0x6F, "lowercase o"),
        ("special-open-bowl", "Open bowl", 0x63, "lowercase c"),
        ("special-double-open-bowl", "Double open bowl", 0x25B, "open e"),
        ("special-spine", "Spine", 0x73, "lowercase s"),
    ))
)
# Fixed Extensions allocations reuse the completed three-stave families.
# The catalogue's presentation order remains independent of these code points.
EXTENSION_BASES = (
    (0xF2C00, 12, 0xF2A45, "arched", "double-arched"),
    (0xF2C0C, 12, 0xF2A51, "double-arch", "triple-arch"),
    (0xF2C18, 12, 0xF2A5D, "arched", "double-arched"),
    (0xF2C24, 12, 0xF2A69, "double-arch", "triple-arch"),
    (0xF2C30, 12, 0xF2A75, "double-arch", "triple-arch"),
    (0xF2C3C, 12, 0xF2B40, "arched", "double-arched"),
    (0xF2C48, 12, 0xF2B4C, "arched", "double-arched"),
    (0xF2C54, 36, 0xF2B58, "left-arched", "left-double-arched"),
    (0xF2C78, 36, 0xF2B7C, "right-arched", "right-double-arched"),
    (0xF2C9C, 36, 0xF2B58, "left-arched", "double-arched"),
)


def _extension_specs():
    existing = {glyph.code_point: glyph for glyph in GLYPHS}
    for start, count, base, old, new in EXTENSION_BASES:
        for index in range(count):
            glyph = existing[base + index]
            label = glyph.label.lower().replace("-", " ").replace(
                old.replace("-", " "), new.replace("-", " "), 1).capitalize()
            if start in (0xF2C0C, 0xF2C24, 0xF2C30):
                ribbon = 0x26F if index % 4 >= 2 else 0x6D
                parts = [*glyph.references, ("additional-arch", ribbon,
                         "turned m" if ribbon == 0x26F else "lowercase m")]
            elif count == 12:
                turned = index % 4 >= 2
                terminal_base = {0xF2C00: 0xF2A09, 0xF2C18: 0xF2A21,
                                 0xF2C3C: 0xF2B04, 0xF2C48: 0xF2B10}[start]
                terminal = existing[terminal_base + (2 if turned else 0 if start == 0xF2C00 else 4)]
                parts = [*existing[0xF2A51 + index].references, *terminal.references]
            else:
                left, right = divmod(index, 6)
                left_variant = left // 2 * 4 + left % 2
                right_variant = right // 2 * 4 + right % 2 + 2
                if start == 0xF2C9C:
                    parts = [*_opposed_bowl_spec(12).references,
                             *existing[0xF2A15 + left_variant].references,
                             *existing[0xF2A15 + right_variant].references]
                else:
                    right_arch = start == 0xF2C78
                    terminal = _opposed_bowl_spec(left * 6 if right_arch else 12 + right)
                    parts = [*terminal.references,
                             *existing[0xF2A51 + (right_variant if right_arch else left_variant)].references]
            references, donors = [], set()
            for role, code, native_label in parts:
                if code not in donors:
                    references.append(("component" if role == "direct" else role, code, native_label))
                    donors.add(code)
            yield GlyphSpec(
                glyph.glyph_id.replace(old, new), start + index, label,
                glyph.width_donor, None, tuple(references),
                "Extension of four-stave width using native arch curves and established shared-shaft joins; "
                "the completed body and terminal retain their native width, with catalogue endings "
                "on the outer shafts. Roman only; no language reading.",
                roman_only=True,
            )


GLYPHS += tuple(_extension_specs())
GLYPHS = tuple(sorted(GLYPHS, key=lambda glyph: glyph.code_point))
LEGACY_GLYPHS = GLYPHS
LEGACY_GLYPH_BY_CODE = {glyph.code_point: glyph for glyph in LEGACY_GLYPHS}
ALLOCATION_PATH = ROOT / "resources/quintessential-latin-allocation.json"


def _allocated_specs():
    allocation = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
    rows = allocation["entries"]
    by_id = {row["glyphId"]: row for row in rows}
    originals = {glyph.glyph_id: glyph for glyph in LEGACY_GLYPHS}
    if len(by_id) != len(rows) or len({row["codePoint"] for row in rows}) != len(rows):
        raise ValueError("Catalogue allocation identities and code points must be unique")
    for glyph in LEGACY_GLYPHS:
        row = by_id[glyph.glyph_id]
        spine = glyph.glyph_id == "special-spine"
        yield replace(glyph, code_point=row["codePoint"], recipe_code_point=glyph.code_point,
                      internal_name=row["glyphName"], stemless=glyph.glyph_id.startswith("special-"),
                      direct_donor=None if spine else glyph.direct_donor,
                      references=(("body", 0x73, "lowercase s"), ("upper-terminal", 0x25B, "epsilon"),
                                  ("lower-terminal", 0x25C, "reversed epsilon")) if spine else glyph.references,
                      italic_references=(("body", 0x73, "lowercase s"),
                                         ("terminal", 0x25B, "epsilon")) if spine else glyph.italic_references,
                      adaptation=("Native diagonal s body with a curved upper bulb and thin lower terminal."
                                  if spine else glyph.adaptation))
    # Source order is independent of the public code chart's allocation order.
    for row in sorted((row for row in rows if row["glyphId"] not in originals), key=lambda row: row["legacyIndex"]):
        if row["middleLegs"]:
            base = originals[row["baseGlyphId"]]
            yield replace(base, glyph_id=row["glyphId"], code_point=row["codePoint"],
                          recipe_code_point=row["recipeCodePoint"], internal_name=row["glyphName"],
                          label=base.label + " with extended middle legs", direct_donor=None,
                          roman_stem_donor=None, middle_legs=True,
                          middle_leg_extensions=tuple(row["middleLegExtensions"]) if "middleLegExtensions" in row else None,
                          references=(*base.references, ("middle-descender", 0x70, "lowercase p"),
                                      ("middle-ascender", 0x6C, "lowercase l")),
                          adaptation="Retain the base arch construction and outer endings; extend internal free legs with native terminal joins.")
        else:
            donor, label = {
                "special-closed-double-bowl": (0x25B, "Closed double bowl"),
                "special-turned-open-bowl": (0x254, "Turned open bowl"),
                "special-turned-double-open-bowl": (0x25C, "Turned double open bowl"),
            }[row["glyphId"]]
            closed = row["glyphId"] == "special-closed-double-bowl"
            turned_double = row["glyphId"] == "special-turned-double-open-bowl"
            references = (("left-lobes", 0x25B, "epsilon"), ("right-lobes", 0x25C, "reversed epsilon")) if closed else (
                (("body", 0x25C, "reversed epsilon"), ("lower-terminal", 0x25B, "epsilon")) if turned_double else
                (("direct", donor, label.lower()),))
            yield GlyphSpec(row["glyphId"], row["codePoint"], label, donor,
                            None if closed or turned_double else donor, references,
                            "Native stemless bowl vocabulary; no language reading.",
                            italic_references=(("direct", donor, label.lower()),) if turned_double else None,
                            internal_name=row["glyphName"], stemless=True)


# Construction labels are allocation data, independent of preserved recipe IDs.
_CANONICAL_LABELS = {
    row["glyphId"]: row["canonicalName"]
    for row in json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))["entries"]
}
GLYPHS = tuple(replace(glyph, label=_CANONICAL_LABELS[glyph.glyph_id]) for glyph in _allocated_specs())

# Preserve the complete pre-0.230 Italic GID prefix, including the later
# middle-leg companions and stemless signs. New native forms append to it.
INDEPENDENT_MIDDLE_IDS = frozenset(glyph.glyph_id for glyph in GLYPHS if glyph.middle_leg_extensions is not None)
PREVIOUS_ITALIC_IDS = frozenset(glyph.glyph_id for glyph in GLYPHS
                              if not glyph.roman_only and glyph.glyph_id not in INDEPENDENT_MIDDLE_IDS)
ITALIC_ADDITION_IDS = frozenset(glyph.glyph_id for glyph in GLYPHS
                              if glyph.roman_only and glyph.glyph_id not in INDEPENDENT_MIDDLE_IDS)
def _complete_italic_spec(glyph):
    if not glyph.roman_only:
        return glyph
    references = tuple((role, 0x250 if code == 0x61 else code,
                        "native Italic turned a" if code == 0x61 else label)
                       for role, code, label in glyph.references)
    return replace(glyph, roman_only=False, italic_references=references,
                   italic_adaptation="Native Italic STIX Two Text bodies and endings, with "
                   "independently drawn epsilon lobes for double bowls and turned-a diagonal "
                   "counters for spines. Native arch ribbons translate rigidly; shared-shaft "
                   "joins follow their receiving axes. Internal free legs retain native terminals.")


GLYPHS = tuple(_complete_italic_spec(glyph) for glyph in GLYPHS)
ITALIC_ADDITIONS = tuple(glyph for glyph in GLYPHS if glyph.glyph_id in ITALIC_ADDITION_IDS)
INDEPENDENT_MIDDLE_ADDITIONS = tuple(glyph for glyph in GLYPHS if glyph.glyph_id in INDEPENDENT_MIDDLE_IDS)

GLYPH_ORDER = (".notdef", "space", *(glyph.glyph_name for glyph in GLYPHS))
GLYPH_BY_NAME = {glyph.glyph_name: glyph for glyph in GLYPHS}
EXPECTED_CODE_POINTS = (0x20, *(glyph.code_point for glyph in GLYPHS))


def glyphs_for_posture(italic: bool) -> tuple[GlyphSpec, ...]:
    """Return the explicitly built repertoire for this native posture."""
    if italic:
        return (tuple(glyph for glyph in GLYPHS if glyph.glyph_id in PREVIOUS_ITALIC_IDS)
                + ITALIC_ADDITIONS + INDEPENDENT_MIDDLE_ADDITIONS)
    return GLYPHS


def glyph_order_for_posture(italic: bool) -> tuple[str, ...]:
    return (".notdef", "space", *(glyph.glyph_name for glyph in glyphs_for_posture(italic)))


def expected_code_points_for_posture(italic: bool) -> tuple[int, ...]:
    return (0x20, *(glyph.code_point for glyph in glyphs_for_posture(italic)))


def posture_by_name(name: str) -> Posture:
    return next(posture for posture in POSTURES if posture.name == name)


def master_by_style(style: str) -> Master:
    return next(master for master in MASTERS if master.style == style)

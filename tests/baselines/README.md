# Font preservation fixtures

These fixtures are independent captures of Quintessential Serif 0.210 and 0.150.
They are deliberately limited to font masters, designspaces, compiled static and
variable fonts, licensing notices, and a neutral 0.210 identity registry. No
language application is needed to use them.

Every copied font file retains its original bytes. Each fixture-manifest.json
records the exact included file set, byte lengths, SHA-256 hashes, and historical
capture/build hashes. The original full historical archives remain unchanged;
these directories are explicitly font-only subsets, not copies of every old
project file.

Version 0.210 preserves 481 Roman and 157 Italic identities. Its neutral registry
retains stable IDs, historical code points, internal font names, posture coverage,
family IDs, legacy indices, and visible component structures. It contains no
phonological models or reading assignments.

Version 0.150 independently preserves the original 129 font identities and all
16,641 ordered pairs. The tests compare complete source outlines and advances,
static outputs, and variable instances at 400, 500, 550, 600, and 700.

The 0.210 comparison has exactly one historical exception: the explicitly revised
special-spine outline, its metrics, and pairs involving that glyph. All other
earlier outlines, advances, and effective pair values must remain unchanged.

Run python tools/test_additions_font.py from the repository root. The default
paths are portable. Its --baseline and --baseline-0150 options can point to other
copies of these same fixture directories.

All included font software remains under the SIL Open Font License 1.1; see the
OFL.txt notices beside each set of compiled fonts.


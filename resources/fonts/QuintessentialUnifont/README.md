# Quintessential Latin Unifont

Regular · version 0.250 · based on GNU Unifont 17.0.05

Install **QuintessentialUnifont-Regular.ttf** as a desktop font. Select
**Quintessential Latin Unifont** in your application. The **WOFF2** file is
the webfont version; it is not installed through the operating system.

The font includes all **1,216 Quintessential Latin characters** at their
existing U+F2A00–U+F2EBF assignments, plus **214 unchanged native Unifont
characters** for mixed Latin text. The companion set covers printable ASCII,
Latin-1 Supplement except the soft-hyphen formatting control, and the native
Latin donor characters used in the glyph proofs. There are 1,430 encoded
characters and a visible missing-character box.

Every character uses an 8-pixel advance in a 16-pixel cell. For the native
pixel size, use **16 CSS pixels** or **12 points at 96 dpi**. Larger sizes,
such as 32 or 48 CSS pixels, scale the square outline geometry; application
hinting, smoothing, and display scaling may alter the displayed pixels.
Use the site's bitmap proofs for exact enlarged pixel inspection.

Both files contain square pixel outlines and an exact monochrome **16-ppem
embedded bitmap strike**. Applications that use the strike display the
original pixels at native size; other sizes use the scalable outlines.
The advance is half an em, ascent is 14 pixels, and descent is 2 pixels.
No kerning, ligatures, added weight, or automatic outline smoothing is applied.

```css
@font-face {
  font-family: "Quintessential Latin Unifont";
  src: url("QuintessentialUnifont-Regular.woff2") format("woff2");
  font-style: normal;
  font-weight: 400;
}
.quintessential-bitmap {
  font-family: "Quintessential Latin Unifont", monospace;
  font-size: 16px;
  line-height: 1;
  font-synthesis: none;
}
```

Use the project's character charts to copy the private-use characters. A
normal Latin keyboard does not automatically enter the Quintessential forms.

These are independent project fonts, not an official GNU Unifont release.
They are licensed under **SIL Open Font License 1.1**; attribution and the
complete license accompany these files in **OFL.txt**.

Build sources are in `tools/build_unifont_font.py` and `resources/unifont/`.
The original reviewed drawings and their HEX export remain the drawing source.
The compiler does not modify the STIX-based fonts, glyph allocation or PDFs.

The metrics follow the pinned [GNU Unifont 17.0.05 source](https://unifoundry.com/pub/unifont/unifont-17.0.05/unifont-17.0.05.tar.gz).
The strike uses OpenType [EBDT](https://learn.microsoft.com/en-us/typography/opentype/spec/ebdt)
and [EBLC](https://learn.microsoft.com/en-us/typography/opentype/spec/eblc).

# Site presentation

The whole website shares the code charts' publication style: Source Sans 3,
white paper, black ink, light headings, fine rules, compact spacing, and square
controls. Quintessential Serif remains the actual font used for script text,
including the project marks and character details.

The introduction, proposal, and downloads use a 660-pixel reading area on a
wide screen, aligned with the charts. Page titles are 30 pixels, section titles
are 20–22 pixels, and body text is 15–16 pixels. The introduction pairs its title
and explanation with a compact font specimen. The proposal has a small contents
index beside the article on wide screens, moving into normal flow below
820 pixels. Downloads retain semantic tables with wrapping cells.

At phone widths, the page margins become 16 pixels, the introduction stacks,
the construction examples use two columns, and the proposal index uses one.
The shared navigation, font controls, dialogs, notices, and footer follow the
same typography. Existing search, copying, keyboard navigation, native font
controls, and no-JavaScript content remain available.

`site/assets/style.css` contains the common foundation and page-specific rules.
The code-chart section retains the approved grid and names geometry, with
measurements generated from `resources/chart-presentation.json`. Chart printing
keeps Letter sheets; the other webpages use a compact A4 print layout.

## Verification

The [whole-site review](../resources/verification/site-presentation-review.json)
records 174 presentation checks, the existing 147 browser checks, 17 naming
tests, and 12 static-site acceptance groups. Every page was checked at 320,
375, 768, and 1440 pixels, including the formerly overflowing proposal at
320 pixels. Desktop and phone screenshots, character details, and actual
browser print output were visually inspected.

This style revision was validated against an isolated copy of the last complete
font/catalogue/PDF build while the separate native-Italic implementation was
in progress. The record identifies that exact baseline and the final stylesheet
and template changes; it does not claim to validate the unfinished font build.
The shared source styles also apply to subsequent site builds.

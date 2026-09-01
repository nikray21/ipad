# Print — posters, fliers, docs, certificates

Print (or print-destined PDF) is a fixed canvas. No scroll, no hover, no
responsive reflow — the composition is final and every millimeter is
intentional. This is the most typographic, most compositional medium.

## Two kinds of document

1. **Flowing document** (report, memo, long letter, article): write it as one
   normal HTML flow; the print engine paginates it onto the reader's paper.
   Don't hard-code page breaks or paper size — let content flow. Use running
   headers/footers that repeat per page.
2. **Fixed-layout page(s)** (poster, flier, one-page resume, certificate,
   brochure panel, social post): an explicit page box at a fixed size, content
   composed to fill it, overflow hidden. Design each page to fill the sheet.

Decide which up front. If a page count is implied (one-page resume, two-sided
flier), it's fixed-layout.

## Sizes (set explicit pixel/physical dimensions)

- Letter: 8.5×11in (816×1056px @96dpi). A4: 210×297mm.
- Poster: whatever the brief says (e.g. 18×24in, 24×36in) — set it explicitly.
- Social: IG post 1080×1080, story 1080×1920, OG image 1200×630, etc.
- For metric users default A4; give the design a size that fits both Letter and
  A4 if it must print on either (keep critical content inside the smaller safe
  area).

```css
@page { size: A4; margin: 0; }        /* fixed-layout: engine owns geometry */
.page {
  width: 210mm; height: 297mm;
  padding: 18mm; box-sizing: border-box;
  overflow: hidden;
  page-break-after: always;
}
```

For a fixed pixel canvas (poster/social), just set width/height in px on the
root element — the PDF/export sizes to your design automatically; no `@page`
needed.

## Composition for print

- **Margins are sacred.** Generous, equal optical margins. Content crammed to
  the edge looks amateur; a wide margin looks expensive. Watch the bottom
  margin especially — it usually wants to be larger than the top.
- **Strong grid + a focal hierarchy.** Poster: one dominant element (huge type
  or one image), then supporting info in a clear tier below. Don't make five
  things equally loud.
- **Type does the heavy lifting.** With no motion or color-rich UI, typographic
  contrast (scale, weight, case, tracking) is your main tool. Push it hard —
  display type on a poster can be enormous.
- **Print minimums:** body text ≥ 10–12pt; captions ≥ 8pt. Nothing smaller.
- **Alignment discipline.** Everything aligns to grid lines. Hang punctuation,
  optically align, keep a consistent baseline.
- **Bleed & safe area** for real printing: extend backgrounds ~3mm past trim;
  keep text ~5mm inside trim.

## Color for print

- CMYK-safe: very saturated RGB (especially bright blue/green) shifts in print.
  Prefer slightly muted values if it will be physically printed.
- Rich black for large black areas (not just K100) if truly printing; pure
  black text is fine.
- Ensure contrast survives grayscale if it might be photocopied.

## Resume/one-pager specifics

- One page, ruthlessly. A clear name/title header, a strong left-aligned
  hierarchy, tabular alignment of dates, consistent bullet rhythm. Whitespace
  between sections > decoration. One accent max.

## Export

- Print-based export goes through the browser print view → save as PDF. Author
  on a print-owning page structure so pagination is correct out of the box.
- Freeze any animation before exporting (export should capture the final,
  settled state).
- Fixed-size design (poster/social) → the export sizes to the canvas; you don't
  need print CSS, just the explicit dimensions.

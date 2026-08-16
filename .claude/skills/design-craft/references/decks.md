# Decks — slide presentations

A deck is not a document with bullets. It's a sequence of single-idea visuals
that support a spoken narrative. Design for the room and the story.

## Rules of the medium

- **One idea per slide.** If a slide makes two points, it's two slides.
- **Big.** 1920×1080 canvas. Body text never below 24px, ideally 32px+. Titles
  60–140px. If it fits like a document, it's too small.
- **Speaker carries the words; slide carries the image/point.** Kill bullet
  walls. A slide is a headline + one supporting visual/number, most of the time.
- **Max 1–2 background colors across the whole deck.** Consistency = polish.
- **Design a system of layouts, then vary with rhythm** (below).

## The layout system (define these once, reuse)

Give the deck a small set of slide archetypes and sequence them intentionally:

1. **Cover** — title, subtitle, minimal. Sets the tone.
2. **Section divider** — big number/label on a distinct background; signals a
   new act. Vary its background color/treatment from content slides.
3. **Statement** — one huge sentence, centered or flush-left, lots of void.
4. **Content (text)** — headline + 2–4 short supporting points, generous
   spacing. Commit to a supporting image or graphic device, never a bare list.
5. **Data** — one chart or one enormous number with a caption. Never a chart
   dump.
6. **Comparison / two-up** — split layout, clear A vs B.
7. **Full-bleed image** — imagery is the message; text overlaid with a scrim.
8. **Quote / testimonial** — large type, attribution small.
9. **Closing / CTA** — the one action or takeaway.

**Rhythm:** don't run five identical content slides. Alternate full-bleed,
statement, two-up, data. The variety is what keeps a room awake. Section
dividers reset attention between acts.

## Visual polish

- Consistent margins (a safe area — keep content ~80–120px off every edge).
- A recurring small mark: page number, running section label, a thin rule — the
  same on every content slide. Cohesion.
- Numbers as graphics: set a key stat at 200px+; it becomes the visual.
- Imagery: use real photos/placeholders; apply a consistent treatment (duotone,
  consistent crop, consistent corner radius or none).
- Motion between slides: a single consistent transition. Within a slide,
  optional build-in of elements (fade-rise, staggered) — subtle, fast.

## Structure a narrative

Hook → tension/problem → the idea → evidence → implication → ask. Every slide
advances that arc. Cut anything that doesn't.

## Minimal slide skeleton (plain HTML, 1920×1080)

```html
<section class="slide" style="width:1920px;height:1080px;display:grid;
  grid-template-columns:1fr 1fr;align-items:center;
  padding:120px;box-sizing:border-box;background:var(--bg);gap:80px">
  <div>
    <p style="font:600 24px/1 var(--label);letter-spacing:.1em;
       text-transform:uppercase;color:var(--accent)">Section 01</p>
    <h2 style="font:700 clamp(60px,7vw,120px)/0.98 var(--display);
       margin:.3em 0 0;text-wrap:balance;color:var(--text)">
       The one point this slide makes</h2>
    <p style="font:400 34px/1.5 var(--body);color:var(--muted);
       max-width:22ch;margin-top:32px">One line of support. No bullet wall.</p>
  </div>
  <figure style="aspect-ratio:4/3;background:var(--surface);border-radius:4px">
    <!-- one chart or one image placeholder -->
  </figure>
</section>
```

## Export

- Native slide sizing = fixed 1920×1080 sections. Keep each slide's content in
  its own section so it exports one-page-per-slide cleanly.
- For editable PowerPoint export, use native text/shapes; for pixel-perfect,
  screenshot mode. Diagrams that won't survive shape conversion (complex SVG,
  canvas) should be flagged to raster.
- Speaker notes travel with each slide — write them; they're half the deck.

# Data viz & infographics

A chart is an argument, not decoration. Its job is to make one relationship
instantly legible. Most "data viz slop" fails because it shows data without
making a point.

## Before drawing anything

- **What is the one takeaway?** Design the chart to deliver *that*. Title the
  chart with the takeaway ("Revenue doubled after launch"), not the dimension
  ("Revenue over time").
- **Pick the encoding that fits the question:**
  - Trend over time → line.
  - Compare categories → horizontal bar (sorted!).
  - Part-to-whole → stacked bar or a single stat; avoid pie unless 2–3 slices.
  - Correlation → scatter.
  - Distribution → histogram / strip / box.
  - One number that matters → just show the number, huge, with context.
- **Sort by value**, not alphabetically, unless order is inherent (time, size
  buckets).

## Design rules (Tufte-adjacent)

- **Maximize data-ink.** Remove chart junk: heavy gridlines, 3D, drop shadows,
  redundant legends, background fills, borders. Every pixel should encode data
  or aid reading.
- **Direct-label** series at the line's end instead of a disconnected legend
  when you can.
- **Muted axes, loud data.** Axes/gridlines in light neutral; the data in your
  accent. Gray everything except the series you're making a point about.
- **Start bar axes at zero.** Line charts may crop the y-axis if change is the
  point — but never bars.
- **Annotate the insight** directly on the chart (a callout on the peak, a
  threshold line, a "launch" marker). The annotation is often the whole point.
- **Consistent, meaningful color.** Sequential data → single-hue lightness
  ramp. Diverging → two hues around a neutral midpoint. Categorical → a small
  qualitative set; keep it ≤6.

## Number formatting

- Abbreviate on axes (12K, 1.2M), full precision in tooltips.
- `tabular-nums` for aligned figures; right-align numeric columns in tables.
- Units and currency once (axis title or caption), not on every value.
- Round to the precision that matters — false precision (3.847%) erodes trust.

## Implementation

- **Small/bespoke:** hand-build with inline SVG or a `<canvas>` — full control,
  no dependency, and it matches your design system exactly.
- **Standard charts fast:** a library like Chart.js or Recharts, then strip
  its defaults hard (remove gridlines, restyle fonts/colors to your tokens,
  kill the default legend). Library defaults are the #1 source of chart slop.
- **Bespoke/complex:** D3 for full custom scales, transitions, and layouts.

### Minimal hand-built bar (SVG, sorted, direct-labelled)

```html
<svg viewBox="0 0 400 220" style="width:100%;font:500 13px var(--body)">
  <!-- one <g> per bar; width ∝ value; label at end -->
  <g transform="translate(0,20)">
    <rect x="80" y="0" width="240" height="24" rx="2" fill="var(--accent)"/>
    <text x="76" y="16" text-anchor="end" fill="var(--muted)">Direct</text>
    <text x="326" y="16" fill="var(--text)" font-weight="600">62%</text>
  </g>
  <!-- repeat, sorted descending -->
</svg>
```

## Animating data

- Reveal on scroll (bars grow from baseline, lines draw with
  `stroke-dasharray`), staggered — see animation.md.
- Animate *transitions between states* (filter, time-step) so the eye tracks
  what changed; use FLIP/tween on the mark positions.
- Keep it fast and once — data that jiggles forever is annoying.

## Infographics

An infographic is a designed narrative made of several small viz + type +
iconography. Rules: one clear reading order (number the steps or use a strong
visual flow), consistent visual language across every module, a single accent,
and a headline that states the conclusion. Don't cram — one poster, one story.

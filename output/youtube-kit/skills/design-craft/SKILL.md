---
name: design-craft
description: >-
  Produce high-craft visual work in HTML/CSS/JS — animated motion pieces, slide
  decks, interactive prototypes, marketing pages, data viz, print, and 3D. Use
  this skill for ANY request to "make it look good", "design", "animate",
  "build a landing page / deck / prototype", or when the user wants output that
  feels intentional and designed rather than a default template. Encodes the
  taste, motion, layout, color, and workflow patterns behind polished results.
---

# Design Craft

You are not a template filler. You are an art director, motion designer, and
front-end engineer in one. Every element earns its place. The difference
between "an AI made this" and "a designer made this" is discipline: a committed
direction, restraint, rhythm, and considered motion. This skill is how you get
there.

## The prime directives

1. **Commit to a direction.** Bland is the only failure mode you cannot fix
   later. Pick a real aesthetic point of view (editorial, brutalist, technical,
   warm-organic, luxe-minimal, retro-computing, etc.) and push it fully. A
   confident wrong direction beats a timid safe one.
2. **Subtract.** One thousand no's for every yes. Empty-feeling space is a
   layout problem, not a content gap — never fill it with filler stats, dummy
   copy, or decorative icons. If an element doesn't carry meaning, delete it.
3. **Systematize before you build.** Decide the type scale, color roles,
   spacing unit, and motion language up front, then apply them consistently.
   Consistency reads as craft.
4. **Motion is meaning, not decoration.** Every animation should explain a
   relationship (where a thing came from, what it belongs to, what changed).
   Motion that just "moves" is noise.
5. **Details compound.** Optical alignment, `text-wrap: pretty`, real easing
   curves, hover states, focus rings, correct line-height — none of these is
   noticeable alone; together they are the whole game.

## The anti-slop list (memorize)

Avoid these unless the brief explicitly calls for them:

- Aggressive multi-stop gradient backgrounds (purple→pink "AI gradient").
- Emoji as UI or decoration (unless it's the brand's voice).
- Rounded card + thin left-border accent stripe (the "dashboard widget" cliché).
- Overused fonts as a default: Inter, Roboto, Arial, Poppins, Fraunces.
- Drop-shadow-on-everything; glassmorphism applied indiscriminately.
- Center-everything layouts with a big headline, subhead, two buttons, three
  feature cards, repeat.
- Data slop: numbers, badges, and stat counters that mean nothing.
- SVG-drawn illustrations of people/objects (they look wrong) — use real image
  placeholders and ask the user for assets instead.
- Fake "trusted by" logo rows, made-up testimonials.

## How to use the references

Read `references/workflow.md` first on any non-trivial job. Then load only what
the task needs — each file is self-contained:

| Task | Read |
|------|------|
| **Any job** — process, context gathering, systematizing | `references/workflow.md` |
| Choosing/holding an aesthetic direction | `references/aesthetics.md` |
| Anything that moves | `references/animation.md` |
| Layout grids, type scale, spacing, color | `references/layout-type-color.md` |
| Modern CSS: grid/subgrid, container queries, `:has()`, clip/mask, blend, filters, scroll-snap, custom props | `references/advanced-css.md` |
| Icons, diagrams, vector animation, path draw/morph | `references/svg.md` |
| Tasteful gradients, mesh, blend modes, color effects | `references/gradients-color-effects.md` |
| Sourcing/treating images, icons, texture, placeholders | `references/imagery-icons.md` |
| Words — headlines, CTAs, microcopy, voice | `references/copywriting.md` |
| Slide decks / presentations | `references/decks.md` |
| Interactive apps & prototypes | `references/prototypes.md` |
| Charts, graphs, infographics | `references/dataviz.md` |
| Posters, fliers, printable docs | `references/print.md` |
| 3D scenes | `references/three-d.md` |
| HTML email (tables, inlining, client quirks) | `references/html-email.md` |
| Accessibility — semantics, keyboard, ARIA, contrast | `references/accessibility.md` |
| Performance — smooth motion, fast load, no layout shift | `references/performance.md` |
| Exploring structure/flow before polish | `references/wireframing.md` |
| Export: PPTX, PDF, standalone HTML, video, handoff | `references/export-formats.md` |
| Obeying/extending an attached brand or design system | `references/design-system.md` |

Working, copy-adaptable HTML is in `examples/` — the highest-signal part of the
kit. Open them in a browser; steal the patterns, not the content:

- `animated-hero.html` — editorial hero: masked line reveal, stagger, scroll bar
- `card-grid-motion.html` — filterable grid: View Transitions, sliding pill, hover lift
- `timeline-motion.html` — the one-clock cue-table motion pattern (canvas)
- `scroll-story.html` — scrollytelling: pinned stage + reactive steps
- `dashboard.html` — dense-but-calm data UI, hand-built SVG charts, count-up
- `poster.html` — fixed-canvas print composition (18×24in)
- `html-email.html` — send-ready table-based email
- `effects-gallery.html` — 6 signature effects (SVG draw, icon morph, scramble,
  animated border, spring press, duotone/marquee)

## Minimum quality bar (never ship below this)

- Type: a real scale (not everything 16px), line-height ~1.4–1.6 for body,
  tighter for display; `text-wrap: pretty` on headings/paragraphs.
- Color: 1 accent, a neutral ramp, semantic roles — not a rainbow. See color
  section.
- Spacing: one base unit (e.g. 8px) and a small set of multiples; use flex/grid
  `gap`, never margins-between-siblings or whitespace text nodes.
- Motion: real easing (never linear for UI; use the curves in `animation.md`),
  durations 150–450ms for UI, respect `prefers-reduced-motion`.
- States: hover, focus-visible, active, and disabled all designed — not
  browser default.
- Responsiveness only if the medium calls for it; fixed-size media (poster,
  slide, social post) gets an explicit canvas size instead.

## Stack notes

Examples are plain HTML/CSS/JS so they run anywhere with zero build. Every
pattern translates directly: CSS custom properties → your token system,
`@keyframes`/WAAPI → Framer Motion / GSAP, layout → any framework. Where a
library earns its place (GSAP ScrollTrigger, three.js) it's called out.

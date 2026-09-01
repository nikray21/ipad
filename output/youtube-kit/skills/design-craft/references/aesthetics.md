# Aesthetics — choosing and holding a direction

The single biggest lever on quality is **committing to a point of view.** Most
mediocre output is mediocre because it hedged — it tried to be neutral and
became generic. Neutral is not a style. Pick one and push it.

## A vocabulary of directions

Use these as starting points, not a menu to average. Each has its own type,
color, space, and motion logic. Mixing two on purpose can be great; mixing five
by accident is slop.

- **Editorial / print-inspired.** High-contrast serif display (Canela, GT
  Sectra, Freight, Tiempos), generous margins, a strong baseline grid, restrained
  color, rules and hairlines instead of boxes, big confident numbers. Motion:
  subtle, typographic, slow. Feels: authoritative, considered, magazine.
- **Swiss / functionalist.** Grotesque sans (Helvetica Now, Neue Haas, Söhne,
  Untitled), strict grid, flush-left, lots of whitespace, one accent, no
  decoration. Motion: precise, minimal. Feels: rigorous, timeless.
- **Brutalist / raw.** System or mono type, visible structure, hard edges,
  high contrast, intentionally "unstyled" but carefully composed, oversized
  type, exposed borders. Feels: honest, punk, technical.
- **Technical / terminal.** Monospace (Berkeley Mono, JetBrains Mono, IBM
  Plex Mono), dark canvas, precise fine lines, data density done well, subtle
  green/amber accents, grid backgrounds. Motion: fast, mechanical, snappy.
  Feels: precise, insider, developer-native.
- **Warm / organic.** Humanist sans or soft serif, warm off-white/cream
  neutrals, earthy accent, soft (never harsh) shadows, rounded but not bubbly,
  generous line-height. Motion: gentle spring, ease-out. Feels: friendly,
  human, calm.
- **Luxe / minimal.** Very few elements, enormous whitespace, thin weights,
  tight tracking on caps, muted or monochrome palette, one hero image doing all
  the work. Motion: slow reveals, long fades. Feels: premium, quiet, confident.
- **Retro-computing / Y2K / print-90s.** Depends on era — commit to the era's
  actual palette, type, and textures rather than a vague "retro."

## How to commit

Write the one-sentence spec (see workflow). Then for every decision ask: *does
this reinforce the direction or dilute it?* A shadow on a Swiss layout dilutes.
A gradient on an editorial layout dilutes. Removing them isn't restraint for its
own sake — it's coherence.

## Contrast is the engine

Good design runs on deliberate contrast:

- **Scale contrast.** The hero should dwarf the body. Timid size jumps
  (16→18→20) read as no hierarchy. Jump hard (16 body → 72 display).
- **Weight contrast.** Pair one very heavy and one very light weight; skip the
  mushy middle.
- **Space contrast.** Tight clusters separated by big voids beat evenly-spread
  elements. Whitespace is not wasted — it's what makes the used space read.
- **Color contrast.** One saturated accent against a restrained field hits
  harder than five competing colors.
- **Density contrast.** A dense data section next to an airy statement section
  creates rhythm.

## Texture without slop

Ways to add richness that don't read as AI-default:

- Hairline rules and dividers (1px, low-contrast) to structure without boxes.
- A single subtle grain/noise overlay (very low opacity) for warmth.
- Fine dotted or line grid backgrounds for technical directions.
- Real photography or a single strong illustration placeholder — never
  auto-generated SVG figures.
- Duotone or monochrome treatment of imagery for cohesion.
- Numbers set large as graphic elements.

## Dark mode is a design, not an invert

If dark: use near-black with a hint of hue (e.g. `oklch(0.18 0.02 260)`) not
pure `#000`; reduce accent saturation slightly; borders are light-on-dark at low
opacity; shadows barely exist — use elevation via lighter surfaces instead.

## Smell test before shipping

- Could this be any brand? → too generic, push the direction.
- Does every screen look the same weight? → no hierarchy.
- More than 2 accent colors or 3 fonts? → probably slop.
- Any rounded card with a left accent stripe? → delete.
- Gradient doing the work a real idea should do? → replace with a real idea.

# Gradients & color effects — how to use them without slop

Gradients aren't banned — *lazy* gradients are. The "AI look" is a saturated
purple→pink diagonal doing the work a real idea should do. Used with restraint,
gradients and color effects add depth and light. Here's the disciplined version.

## When a gradient earns its place

- To imply **light** (a subtle lightening toward a light source, a soft vignette).
- As a **scrim** so text stays legible over an image.
- A **near-tonal** gradient (two shades of the same hue) for quiet depth on a
  surface.
- A **brand accent** used small and intentionally (a button, a highlight, a
  chart series), not a full-page background.

## How to make gradients look good

- **Stay in one hue family, or adjacent hues.** Big hue jumps (blue→pink) are
  the slop signal. Vary lightness/chroma more than hue.
- **Interpolate in OKLCH/OKLAB**, not sRGB — avoids the muddy gray dead-zone in
  the middle:
  ```css
  background:linear-gradient(in oklch, oklch(0.7 0.14 250), oklch(0.55 0.16 280));
  ```
- **Ease the stops.** A hard 0%→100% is crude. Add intermediate stops or use
  the emerging `linear-gradient(..., 0% 30% 100%)` easing hints for a natural
  falloff. Long, soft gradients read as light; short harsh ones read as UI.
- **Low contrast for backgrounds.** Background gradients should be barely
  perceptible; save contrast for content.
- **Grain over gradients** kills banding and adds warmth (see imagery-icons.md).

## Mesh & ambient color (the tasteful version)

Multiple soft radial gradients, low opacity, blurred, behind content — an
ambient "aurora" that's calm, not a rave:

```css
.ambient{position:absolute;inset:0;z-index:-1;overflow:hidden;filter:blur(60px);opacity:.5}
.ambient::before,.ambient::after{content:'';position:absolute;width:50vmax;height:50vmax;
  border-radius:50%;}
.ambient::before{background:oklch(0.75 0.12 250);top:-10%;left:-5%}
.ambient::after{background:oklch(0.72 0.11 200);bottom:-15%;right:-5%}
```
Keep chroma modest and hues close. Optionally animate positions very slowly
(20s+), respecting reduced-motion.

## Conic & special

- **Conic gradients** for pie/gauge/loaders and angular accents:
  `conic-gradient(var(--accent) var(--pct), var(--border) 0)`.
- **Animated gradient border** via `@property`-animated angle in a conic
  gradient masked to a border (see advanced-css.md).
- **Text gradient** (use rarely, on one hero word): background-clip:text with a
  restrained gradient — always keep a solid fallback color.

## Blend modes for color interaction

Often better than gradients for richness: `mix-blend-mode:multiply` for
ink-layering, `screen` for glow, `overlay` for graded photos. Colors interact
with what's behind them, which reads as intentional rather than applied.

## Checklist

- Is the gradient doing a job (light, legibility, depth) or just filling space?
- One hue family? Interpolated in OKLCH? Soft stops? Low contrast if it's a
  background?
- Would a flat color + one good idea be stronger here? Often yes — try it first.

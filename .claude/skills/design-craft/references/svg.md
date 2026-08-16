# SVG — vector graphics, icons & animation

SVG is the sharpest tool for icons, diagrams, logos, and precise vector
animation. It scales infinitely, styles with CSS, and animates on the GPU. Use
it for anything geometric and precise — but NOT for illustrating people/objects
(auto-drawn figures look wrong; use real imagery there).

## Authoring clean SVG

- Set a `viewBox` and drop fixed `width`/`height` so it scales; size via CSS.
- Use `currentColor` for fills/strokes so icons inherit text color:
  `<svg fill="none" stroke="currentColor" ...>`.
- Consistent stroke width across an icon set (e.g. 1.5 or 2), `stroke-linecap`/
  `stroke-linejoin:round` for a friendly feel or `miter` for technical.
- Group with `<g>`, name nodes with `id`/`class` for targeting/export.
- Optimize (SVGO) before shipping — strip editor cruft, round coordinates.

## Icons

- Prefer a coherent set (one grid, one stroke weight, one corner style). Good
  open sets: Lucide, Phosphor, Radix, Tabler, Heroicons. Match the set to the
  direction (rounded vs. sharp, filled vs. line).
- Inline SVG (not `<img>`) when you need to style/animate; sprite sheet or
  symbol defs for repeated use:
  ```html
  <svg style="display:none"><symbol id="i-arrow" viewBox="0 0 24 24">…</symbol></svg>
  <svg class="icon"><use href="#i-arrow"/></svg>
  ```
- Size icons in `em` so they scale with text; give interactive icons ≥44px hit
  area via padding.

## Gradients & filters (in-SVG)

```svg
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="oklch(0.7 0.15 260)"/>
    <stop offset="1" stop-color="oklch(0.6 0.18 320)"/>
  </linearGradient>
  <filter id="soft"><feGaussianBlur stdDeviation="8"/></filter>
</defs>
```
`feTurbulence` + `feDisplacementMap` = organic distortion/noise; `feColorMatrix`
= duotone/hue shifts; `feGaussianBlur` + `feColorMatrix` alpha = gooey/metaball
merge effect.

## Animation techniques

### Line drawing (the classic "self-drawing" stroke)
```css
.path{stroke-dasharray:1;stroke-dashoffset:1;
  /* set both to the real length in JS: */ }
```
```js
const len = path.getTotalLength();
path.style.strokeDasharray = len;
path.style.strokeDashoffset = len;
path.animate([{strokeDashoffset:len},{strokeDashoffset:0}],
  {duration:1600,easing:'cubic-bezier(0.16,1,0.3,1)',fill:'forwards'});
```
Pair with scroll (`animation-timeline`) for draw-on-scroll signatures.

### Motion along a path
```css
.dot{offset-path:path('M0,0 C50,0 50,100 100,100');
  animation:move 3s var(--ease) infinite;}
@keyframes move{to{offset-distance:100%}}
```

### Morphing between shapes
- Two paths with the **same number/type of points** interpolate cleanly. Use
  `flubber` (tiny lib) when point counts differ, or CSS with `d` as an
  animatable property where supported (`@property --d`).
- For icon state changes (menu↔close, play↔pause), animate individual `<line>`/
  `<path>` transforms — often simpler and crisper than a full morph.

### Transform origin gotcha
SVG transforms default to the SVG origin. Set `transform-box:fill-box;
transform-origin:center` so `scale`/`rotate` pivot around the element itself.

## Diagrams

Hand-build flow/architecture diagrams in SVG for full control and clean export:
nodes as `<rect>`/`<g>` with `<text>`, edges as `<path>` with `marker-end`
arrowheads. Keep them on the same type/color system as the rest of the design.
Flag complex SVG diagrams to raster for PPTX export (they don't survive shape
conversion).

## When NOT to use SVG

- Photographic content → real images.
- Illustrations of people/scenes → real assets or placeholders + ask the user.
- Hundreds of animating nodes → canvas/WebGL (SVG DOM gets slow past a few
  hundred animated elements).

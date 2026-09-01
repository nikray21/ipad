# Advanced CSS — the modern toolbox

The techniques that separate hand-built craft from framework defaults. All
native, no libraries. Use these deliberately, not decoratively.

## Layout you probably underuse

- **`grid-template-areas`** for readable, rearrangeable macro layouts:
  ```css
  .app{display:grid;gap:24px;
    grid-template-columns:240px 1fr;
    grid-template-areas:"nav head" "nav main";}
  .app > nav{grid-area:nav} .app > header{grid-area:head} .app > main{grid-area:main}
  ```
- **Subgrid** — align nested content to the parent grid's tracks:
  `grid-template-columns:subgrid`. Perfect for card rows whose internal rows
  must line up across cards.
- **`aspect-ratio`** instead of padding hacks: `aspect-ratio:16/9`.
- **`min()`/`max()`/`clamp()`** everywhere for fluid values without breakpoints.
- **Container queries** — style by the container's width, not the viewport, so a
  component is truly reusable:
  ```css
  .card-wrap{container-type:inline-size}
  @container (min-width:400px){ .card{grid-template-columns:1fr 1fr} }
  ```
- **`:has()`** — parent/previous-sibling selection: `.field:has(:invalid){}`,
  `.card:has(img){}`, `form:has(#toggle:checked) .panel{}`. Enables state-driven
  styling with zero JS.

## Shape, clip, mask

- **`clip-path`** for non-rectangular sections/reveals:
  `clip-path:polygon(0 0,100% 0,100% 85%,0 100%)` (angled section),
  animate it for wipes. `clip-path:inset(0 round 16px)` for animatable rounding.
- **`mask-image`** for text-through-image, gradient fades, and shape reveals:
  ```css
  .fade-edge{ -webkit-mask:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent); }
  .text-clip{ background:url(img.jpg) center/cover; -webkit-background-clip:text;
    color:transparent; }
  ```
- **`shape-outside`** to flow text around a shape/image in editorial layouts.

## Depth & light (tasteful)

- **`mix-blend-mode` / `background-blend-mode`** — `multiply` for ink-on-paper
  overlays, `screen`/`overlay` for glow, `difference` for hover inversions and
  cursor-over-text tricks. This is how you get rich color interaction without
  gradients-for-the-sake-of-it.
- **`backdrop-filter:blur()`** for real glass — but sparingly, over busy
  backgrounds only, with a semi-opaque fill behind it for contrast.
- **Layered shadows** read as real light; one big blurry shadow reads as CG:
  ```css
  --shadow: 0 1px 2px rgb(0 0 0/.04), 0 4px 8px rgb(0 0 0/.04),
            0 16px 24px rgb(0 0 0/.06);
  ```
- **`filter`**: `saturate()`, `contrast()`, `brightness()`, `hue-rotate()` on
  imagery for a consistent treatment; `drop-shadow()` (follows alpha, unlike
  `box-shadow`) for PNG/SVG.

## Scroll behavior (native)

- **`scroll-snap`** for carousels/sections:
  `scroll-snap-type:x mandatory` on the track, `scroll-snap-align:center` on
  items.
- **`position:sticky`** for headers, section labels, and scrollytelling pins.
- **`scroll-behavior:smooth`**, **`overscroll-behavior:contain`** on modals/
  scrollers to stop scroll chaining.
- **Scroll-driven animations** (`animation-timeline: view()/scroll()`) — see
  animation.md.

## Color & custom properties tricks

- **Space-separated channels** for alpha control:
  `--accent:56% 0.18 255;` then `oklch(var(--accent))` /
  `oklch(var(--accent)/.15)` for a tint of the same color.
- **`color-mix()`** to derive tints/shades/states without new tokens:
  `color-mix(in oklch, var(--accent) 15%, var(--bg))`.
- **Custom props are inherited + animatable** (with `@property`):
  ```css
  @property --a{syntax:'<angle>';inherits:false;initial-value:0deg}
  .spin{background:conic-gradient(from var(--a),...);transition:--a 1s}
  .spin:hover{--a:360deg}
  ```
- **`light-dark()`** + `color-scheme` for one-line theme switching.

## Typography niceties

- Fluid, trimmed headings: `text-wrap:balance` (headings), `pretty` (body),
  `hanging-punctuation:first`, `text-box-trim` (where supported) to kill the
  extra leading above caps.
- **Variable fonts**: animate `font-variation-settings` (weight/width/optical
  size) for reactive type. `font-optical-sizing:auto`.
- `tabular-nums`, `slashed-zero`, `case` features via `font-feature-settings`.

## Things to avoid

- `!important` walls, deep descendant selectors, magic pixel nudges instead of
  fixing the system, animating layout properties, `@media` where `clamp()` or a
  container query is cleaner.

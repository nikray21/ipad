# Imagery, icons & texture — sourcing and treatment

The fastest way to make work look generic is bad or default imagery; the fastest
way to make it look expensive is one strong, well-treated image. Imagery is a
design decision, not a fill.

## The honesty rule

- **Never auto-draw people, scenes, or objects in SVG/CSS.** They look wrong and
  read as AI slop. Use real photography, a real illustration, or a clearly-marked
  placeholder — and ask the user for the real asset.
- Don't fabricate logos, headshots, or "as seen in" rows. Placeholder them and
  request the real thing.

## Placeholders that look intentional

While waiting for real assets, use placeholders that respect the layout:

```css
.ph{aspect-ratio:4/3;border-radius:8px;
  background:
    linear-gradient(135deg, color-mix(in oklch,var(--accent) 12%,var(--surface)),
                    var(--surface));
  display:grid;place-items:center;color:var(--muted);
  font:500 13px var(--body);border:1px dashed var(--border)}
/* label it: "Product shot — replace" so intent is obvious */
```

A drag-and-drop image slot the user fills is even better when the tooling
supports it. Give each a clear label of what belongs there.

## Treating imagery for cohesion

Apply ONE consistent treatment across all images so a set of mismatched photos
becomes a system:

- **Duotone / monochrome:** map to your palette.
  ```css
  .duotone{filter:grayscale(1) contrast(1.05);}
  /* then overlay accent with mix-blend-mode:multiply/screen */
  ```
- **Consistent crop & aspect ratio** across a grid.
- **Uniform corner radius** (or none — sharp corners read editorial).
- **Grade:** a small `filter:saturate() contrast() brightness()` shift, or a
  subtle color overlay via `background-blend-mode`, unifies disparate sources.
- **Scrim** for text over images: a gradient overlay
  (`linear-gradient(transparent, rgb(0 0 0/.6))`) so text stays legible — always,
  or the text disappears on light parts of the photo.

## Icons

- One coherent set, one stroke weight, one corner style (see svg.md). Match the
  set to the aesthetic direction.
- Icons support text; they rarely replace it. Icon-only controls need
  `aria-label`.
- Size in `em` to track with text; ≥44px hit area for interactive ones.
- Don't decorate every heading/list-item with an icon — that's slop. Use icons
  where they aid scanning or action, not as ornament.

## Texture (subtle richness without gradients-for-their-own-sake)

- **Grain/noise overlay** at very low opacity warms flat color:
  a tiling PNG noise, or SVG `feTurbulence`, `opacity:.03–.06`,
  `mix-blend-mode:overlay`, `pointer-events:none`.
- **Fine grid / dot backgrounds** for technical directions:
  ```css
  background-image:radial-gradient(circle, var(--border) 1px, transparent 1px);
  background-size:24px 24px;
  ```
- **Hairline rules** (1px, low-contrast) to structure without boxes.
- **Paper/canvas tints** — an off-white with a hint of warm hue beats pure
  white.

Keep texture whisper-quiet. If you notice it consciously, it's too strong.

## Logos & marks

- If building a wordmark placeholder, set it in a strong weight of the display
  face with tight tracking — clean type reads as a mark. Real logo art comes
  from the user.

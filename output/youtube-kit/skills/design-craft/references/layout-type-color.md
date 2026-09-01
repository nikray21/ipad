# Layout, Type & Color

The three fundamentals. Get these right and even simple work looks designed;
get them wrong and no amount of animation saves it.

---

# LAYOUT

## Grid first

Everything sits on a grid, even when the grid is invisible. Decide columns and a
gutter, then place elements against column lines — not by eyeballing.

```css
.container {
  --cols: 12;
  --gutter: 24px;
  --margin: clamp(24px, 5vw, 96px);
  display: grid;
  grid-template-columns: repeat(var(--cols), 1fr);
  gap: var(--gutter);
  padding-inline: var(--margin);
  max-width: 1440px;
  margin-inline: auto;
}
/* Place spanning content on the grid, not with random widths */
.hero      { grid-column: 1 / 8; }
.aside     { grid-column: 9 / 13; }
```

Handy layout primitives:

```css
/* Auto-responsive card grid, no media queries */
.auto-grid { display:grid; gap:24px;
  grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr)); }

/* Sidebar that collapses when space runs out */
.with-sidebar { display:flex; flex-wrap:wrap; gap:32px; }
.with-sidebar > .side { flex: 1 1 240px; }
.with-sidebar > .main { flex: 999 1 60%; }

/* Center a thing with a max readable measure */
.prose { max-width: 65ch; margin-inline: auto; }
```

## Spacing system

One base unit, geometric-ish multiples. Never off-grid values like 13px or 27px.

```css
:root {
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;
  --space-9: 96px; --space-10: 128px;
}
```

**Always use flex/grid `gap`** to space sibling groups (buttons, chips, cards,
nav items). Never space with margins-between-siblings or whitespace text nodes —
`gap` survives reorder/delete/duplicate and stays consistent.

## Composition rules that read as craft

- **Whitespace is structure.** Section padding should feel generous —
  `--space-9`/`--space-10` between major sections. Cramped = cheap.
- **Alignment over centering.** Flush-left creates a strong edge the eye
  follows. Reserve centering for short hero statements and truly symmetric
  compositions.
- **Optical, not mathematical, alignment.** Round shapes, quotes, and italics
  need nudging to *look* aligned. Trust your eye over the number.
- **One focal point per view.** Establish a clear entry point (biggest,
  boldest, most isolated), then a path for the eye.
- **Break the grid deliberately.** Occasionally letting one element bleed off
  the grid/edge creates tension and interest — but only once you've established
  the grid to break.
- **Asymmetry with balance.** A big element on one side balanced by whitespace
  and small elements on the other is more dynamic than centered symmetry.

## Responsive posture

- Fluid type/space with `clamp()` beats a pile of breakpoints:
  `font-size: clamp(2rem, 1rem + 4vw, 4.5rem)`.
- Design mobile and desktop as intentional compositions, not one squished into
  the other.
- Fixed-medium work (poster, slide, social post, email) gets an explicit pixel
  canvas, not responsive rules.

---

# TYPOGRAPHY

## Scale

Pick a ratio and generate the scale. Don't hand-pick random sizes.

| Use | Ratio guide | Example (16px base) |
|-----|-------------|--------------------|
| Dense UI / dashboards | 1.2 (minor third) | 13, 16, 19, 23, 28 |
| Marketing / general | 1.25 (major third) | 16, 20, 25, 31, 39, 49 |
| Editorial | 1.333 (perfect fourth) | 16, 21, 28, 38, 50, 67 |
| Posters / display | 1.5–1.618 | huge jumps |

```css
:root {
  --step--1: clamp(0.83rem, 0.8rem + 0.15vw, 0.9rem);
  --step-0:  clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --step-1:  clamp(1.25rem, 1.1rem + 0.6vw, 1.5rem);
  --step-2:  clamp(1.6rem, 1.3rem + 1.2vw, 2.25rem);
  --step-3:  clamp(2rem, 1.5rem + 2.4vw, 3.5rem);
  --step-4:  clamp(2.6rem, 1.6rem + 4.5vw, 5.5rem);
}
```

## Pairing

- Safe, high-quality move: **one family, multiple weights** (e.g. a good
  grotesque at 700 for display + 400 for body). Coherent and modern.
- Two families: pair by contrast of category — a characterful serif display +
  a neutral sans body, or a mono for labels + a humanist sans for reading. Don't
  pair two similar sans.
- Fonts worth reaching for instead of the overused defaults: Söhne, Untitled
  Sans, Neue Haas Grotesk, ABC Diatype, GT America (grotesques); Tiempos,
  Canela, GT Sectra, Freight, Reckless (serifs); Berkeley Mono, JetBrains Mono,
  Commit Mono (mono). Free/Google alternatives: Space Grotesk, Instrument Sans,
  Newsreader, Fraunces (use sparingly), Libre Franklin, IBM Plex family.

## Setting type well

- Body line-height ~1.5–1.65; display line-height 0.95–1.15 (tight).
- Line length 45–75 characters (`max-width: 65ch`).
- Tighten letter-spacing on large display (`-0.02em` to `-0.04em`); open it on
  small caps/labels (`0.06em`+, uppercase).
- `text-wrap: balance` on headings; `text-wrap: pretty` on paragraphs.
- Real punctuation: curly quotes, en/em dashes, real ellipsis. Enable
  ligatures/kerning: `font-feature-settings: "kern","liga"; text-rendering:
  optimizeLegibility`.
- Numbers in tables/data: `font-variant-numeric: tabular-nums`.
- Never justify on the web (rivers). Never center long text.
- Establish hierarchy with size + weight + color + space — not underline/italic
  spam.

---

# COLOR

## Build a palette, not a rainbow

Roles, not a pile of hues:

```css
:root {
  --bg:        oklch(0.99 0.005 95);   /* page */
  --surface:   oklch(0.97 0.008 95);   /* cards */
  --text:      oklch(0.22 0.02 260);   /* near-black, slight hue */
  --muted:     oklch(0.55 0.02 260);   /* secondary text */
  --border:    oklch(0.90 0.01 260);
  --accent:    oklch(0.58 0.18 255);   /* the one hero color */
  --accent-ink: oklch(0.98 0.02 255);  /* text on accent */
}
```

## Why OKLCH

Perceptually uniform: equal lightness values *look* equally light across hues,
so ramps and accents stay balanced. `oklch(L C H)` = Lightness 0–1, Chroma
(saturation) 0–~0.37, Hue 0–360. To build a harmonious set, hold C and vary H
for related hues; hold H and vary L for a tint/shade ramp.

## Rules

- **One accent.** Maybe one secondary. Semantic colors (success/warn/danger)
  only when the UI needs status. That's it.
- **Neutrals carry a whisper of hue** (2–4% chroma) toward warm or cool — pure
  gray looks lifeless. Pick a temperature and commit.
- **Contrast for real.** Body text ≥ 4.5:1, large text/UI ≥ 3:1. Check it.
  Don't put mid-gray text on a light-gray surface because it "looks soft."
- **Accent is precious.** If everything is accent-colored, nothing is. Use it
  for the single most important action/mark per view.
- **Dark mode:** near-black with hue (not `#000`), slightly desaturate the
  accent, elevation via lighter surfaces + hairline borders rather than shadow.

## Generating a neutral ramp (OKLCH lightness steps)

```css
--n-50:  oklch(0.98 0.01 260);
--n-100: oklch(0.95 0.01 260);
--n-200: oklch(0.90 0.015 260);
--n-300: oklch(0.82 0.02 260);
--n-400: oklch(0.68 0.02 260);
--n-500: oklch(0.55 0.02 260);
--n-600: oklch(0.45 0.02 260);
--n-700: oklch(0.36 0.02 260);
--n-800: oklch(0.27 0.02 260);
--n-900: oklch(0.20 0.02 260);
```

Keep hue constant, march lightness. Same recipe with your accent's hue gives a
matching accent ramp.

# Export & delivery formats

Design work has to leave the browser: as a deck, a PDF, a standalone file, a
video, a component handoff. Author for the destination from the start — retrofit
is painful.

## Slides → PowerPoint (PPTX)

Two modes:
- **Editable** (native text + shapes): the export reads your DOM and emits real
  PowerPoint objects the user can edit. Best default. Keep slides as clean,
  regular HTML (real text nodes, simple shapes, images) so conversion is
  faithful. Complex SVG/canvas/CSS-diagrams won't survive shape conversion —
  mark those to rasterize (embed as image).
- **Screenshots** (one PNG per slide): pixel-perfect but not editable. Use when
  the design has effects that can't convert (heavy filters, gradients, custom
  rendering).

Author tips: one 1920×1080 section per slide; fonts that exist in PowerPoint or
provide swaps; put speaker notes in a machine-readable place so they carry over.

## Anything → PDF

PDF export is print-based (browser print → save as PDF):
- Build on a print-owning structure (a deck shell or a doc/page shell) so
  pagination is correct out of the box.
- **Fixed-size canvas** (poster, social, infographic): set explicit pixel
  `width`/`height` on the root; export sizes to it, no `@page` needed.
- **Flowing document** (report, memo): let content flow; use repeating headers/
  footers; don't hard-code paper size — the engine paginates onto the reader's
  paper (A4 for metric users).
- **Freeze animations** to their final/settled state before exporting; a
  mid-animation capture looks broken.

## HTML → standalone single file

For a design that must work offline / be emailed / handed over as one file:
inline all assets (CSS, JS, fonts as base64, images) into one self-contained
`.html`. Good for portability; watch file size (base64 fonts/images inflate).
Provide a lightweight splash/fallback for no-JS.

## Motion → video

For an animation piece delivered as video: build on a single-clock timeline (see
animation.md) so frames are deterministic and can be captured in sequence, then
encoded. Author at the target resolution/frame-rate; keep motion within a fixed
duration; avoid anything time-of-day or random so every render matches.

## Developer handoff

When engineers will rebuild it:
- Hand over the token system (colors, type scale, spacing, radius, shadows,
  motion curves) as named variables — that's the contract.
- Component inventory: states (default/hover/active/focus/disabled/loading/
  empty/error), variants, and responsive behavior documented.
- Redlines/specs only where non-obvious; a clean tokenized build documents
  itself better than a spec PDF.
- Note interactions and motion (durations, easings, triggers) — these are
  usually lost in handoff.

## Images / assets out

- Snapshot a single element to PNG at 2–4× for a crisp asset (social card,
  thumbnail).
- Export SVG diagrams/logos as SVG (keep them vector); rasterize only when the
  destination can't take vector.

## General rule

Decide the output format before you design. A poster, a deck, a prototype, and
an email have different canvases, constraints, and export paths — building for
the wrong one means rebuilding.

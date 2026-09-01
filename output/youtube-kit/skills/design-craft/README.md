# Design Craft — a portable design skill

A distilled, self-contained skill that teaches an AI coding agent (Claude Code
or similar) to produce **high-craft visual work in HTML/CSS/JS** — animated
motion, slide decks, interactive prototypes, marketing pages, data viz, print,
and 3D — instead of default-template output.

It's the *knowledge* behind polished results: aesthetic doctrine, a motion
playbook with real code, layout/type/color systems, per-medium guides, a
workflow, and working examples. Stack-agnostic core in plain HTML/CSS/JS; every
pattern maps cleanly to React / Tailwind / Framer Motion / GSAP / three.js.

## Install as a Claude Code skill

Skills live in a `SKILL.md`-anchored folder that Claude Code discovers.

1. Copy this whole `design-craft/` folder into your skills directory:
   - Project-local: `.claude/skills/design-craft/`
   - Or user-global: `~/.claude/skills/design-craft/`
2. That's it. `SKILL.md` has YAML frontmatter (`name`, `description`) so the
   agent auto-loads it when a task matches — "make it look good", "design",
   "animate", "build a landing page / deck / prototype", etc.
3. The agent reads `SKILL.md` first, then pulls in only the reference files a
   given task needs (the routing table is in `SKILL.md`).

You can also just paste `SKILL.md` into any chat as a system/style primer, or
`@`-reference the folder in a Claude Code session.

## What's inside

```
design-craft/
├─ SKILL.md                  ← entrypoint: doctrine, anti-slop list, routing
├─ references/
│  ├─ workflow.md            ← process: understand → commit → systematize → edit
│  ├─ aesthetics.md          ← choosing & holding a direction; contrast; texture
│  ├─ animation.md           ← motion playbook + copy-paste code (easing, stagger,
│  │                            scroll-driven, FLIP, View Transitions, springs,
│  │                            the one-clock timeline pattern)
│  ├─ layout-type-color.md   ← grids, spacing units, modular type scale, OKLCH color
│  ├─ advanced-css.md        ← subgrid, container queries, :has(), clip/mask, blend,
│  │                            filters, scroll-snap, @property, color-mix, light-dark
│  ├─ svg.md                 ← icons, diagrams, path draw/morph, SVG filters
│  ├─ gradients-color-effects.md ← tasteful gradients, mesh, conic, blend modes
│  ├─ imagery-icons.md       ← sourcing & treating images, texture, placeholders
│  ├─ copywriting.md         ← headlines, CTAs, microcopy, voice, anti-slop
│  ├─ decks.md               ← slide systems, layout archetypes, rhythm, export
│  ├─ prototypes.md          ← state, all the states, interaction feel, device framing
│  ├─ dataviz.md             ← encoding choice, data-ink, annotation, formatting
│  ├─ print.md               ← fixed canvas, margins, sizes, bleed, PDF export
│  ├─ three-d.md             ← studio lighting, PBR materials, camera, export
│  ├─ html-email.md          ← tables, inlining, bulletproof buttons, client quirks
│  ├─ accessibility.md       ← semantics, keyboard, ARIA, contrast, motion
│  ├─ performance.md         ← smooth motion, fast load, zero layout shift
│  ├─ wireframing.md         ← exploring structure & flow before polish
│  ├─ export-formats.md      ← PPTX, PDF, standalone HTML, video, dev handoff
│  └─ design-system.md       ← how to obey/extend an attached brand/token system
└─ examples/
   ├─ animated-hero.html     ← editorial hero: masked line reveal, stagger, scroll bar
   ├─ card-grid-motion.html  ← filterable grid: View Transitions, sliding pill, hover lift
   ├─ timeline-motion.html   ← the one-clock cue-table motion pattern, on canvas
   ├─ scroll-story.html      ← scrollytelling: pinned stage + reactive steps
   ├─ dashboard.html         ← dense-but-calm data UI, hand-built SVG charts, count-up
   ├─ poster.html            ← fixed-canvas print composition (18×24in)
   ├─ html-email.html        ← send-ready, table-based responsive email
   └─ effects-gallery.html   ← 6 signature effects to steal
```

## How to get the most from it

- **Feed the whole folder**, not just `SKILL.md` — the references are where the
  specifics live, and the examples are the highest-signal part (open them in a
  browser; steal the technique, not the content).
- **Drop in your own tokens.** The core is system-agnostic; `references/
  design-system.md` explains how to make the agent obey your brand. Replace the
  marked `:root` token block with your fonts/colors and the whole thing snaps to
  your identity.
- **Ask for a direction, not just a thing.** "Landing page, editorial direction,
  one ink accent, no shadows" gets far better output than "landing page."

## Honest scope

This is an original distillation of design craft — principles, techniques, and
code — authored to be genuinely useful in your terminal. It is not a copy of any
proprietary internal system or tooling, and it doesn't need to be: the craft is
what produces the results, and the craft is all here.

## License / use

Yours to use, edit, and extend freely. Fork it, add your house style, prune what
you don't need.

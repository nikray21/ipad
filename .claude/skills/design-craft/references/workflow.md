# Workflow — how to actually produce good work

Craft is a process, not a coat of paint at the end. Follow this on any
non-trivial job.

## 1. Understand before you design

Never start from a blank canvas guessing. Establish:

- **Purpose & audience.** A pitch deck for investors, a landing page for
  developers, and a birthday invite have nothing in common visually. Who reads
  this, in what context, on what device, in what emotional state?
- **The one job.** What must this do? A landing page exists to get one action.
  A slide exists to make one point. Name it, then cut everything that doesn't
  serve it.
- **Context assets.** Is there a brand, a design system, existing screens,
  reference images, a codebase? Use them. Copy real tokens, fonts, and
  components rather than approximating. If there's a system, its rules win over
  anything here.
- **Tone.** Serious/playful, dense/airy, warm/technical, loud/quiet. Write it
  down in three adjectives before touching layout.

If any of this is genuinely unknown and would change the design, ask — a short
structured set of questions beats building the wrong thing. Don't ask about
what you were already told.

## 2. Commit to a direction (see aesthetics.md)

Say the direction out loud in one sentence: *"Editorial, high-contrast serif
display over a warm paper neutral, generous margins, one ink-blue accent, no
shadows."* This sentence is your contract. Every later decision checks against
it.

## 3. Build the system first

Before laying out a single screen, define:

- **Type scale** — pick a ratio (1.2 minor third for dense UI, 1.333 perfect
  fourth for editorial, 1.5+ for posters). Set display / heading / body / small
  sizes and their line-heights and weights.
- **Spacing unit** — one base (8px is safe), and the multiples you'll allow
  (4, 8, 16, 24, 32, 48, 64…). Nothing off-grid.
- **Color roles** — background, surface, text, muted text, border, one accent,
  and semantic (success/warn/danger) only if needed. See color section.
- **Motion language** — default easing, default duration, and *what* animates
  (does content rise-and-fade in? slide? scale? pick one vocabulary).
- **Layout rhythm** — for multi-section pieces (decks, long pages), plan the
  sequence of layouts so it varies with intention: full-bleed, then two-column,
  then centered statement, then grid. Rhythm prevents monotony.

Vocalize this system before building. It's the single highest-leverage habit.

## 4. Build, then edit hard

- Get the whole thing standing in the committed system, then do an editing
  pass: remove one more element per screen, tighten spacing to the grid, fix
  optical misalignments, add the missing hover/focus states, run
  `text-wrap: pretty`.
- Zoom out. Squint. If everything reads at the same visual weight, you have no
  hierarchy — fix it by making the most important thing bigger/heavier/isolated
  and everything else quieter.

## 5. Verify

- Does it hold the one-sentence direction? If a section fights it, that section
  is wrong.
- Console clean? Layout stable at the target size(s)? States all present?
  Motion respects `prefers-reduced-motion`?
- Read every word. Copy is design. Vague copy makes even great layout feel
  hollow.

## Copy discipline

- Specific beats generic. "Ships in 40ms" beats "Blazing fast."
- Verbs over nouns in CTAs and headlines.
- Cut hedges, adverbs, and "solutions/leverage/empower" filler.
- Sentence case usually reads more modern and human than Title Case.
- Never pad. If you don't have content for a section, the section shouldn't
  exist — tell the user rather than inventing filler.

## When to ask vs. decide

Ask when the answer changes the design and you can't infer it (audience, scope,
which of several real directions). Decide — and state what you decided — for
everything else. Don't stall on near-equivalent choices.

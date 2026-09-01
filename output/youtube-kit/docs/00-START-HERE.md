# 00 — Start Here

## What this channel is

@NikRayani publishes **insider-lens fundamental analysis**. The differentiator is
not the ticker and not the charts — it is *the thing nobody else found*: the
footnote, the segment bridge, the guidance midpoint, the tax line. A video that
restates the press release has no reason to exist, and the build pipeline
literally refuses to produce one (see Rule Zero in `04-DECK-PIPELINE.md`).

Audience: **beginner and intermediate investors.** Every slide carries one idea,
one visual, and a plain-English reason it matters.

## The two formats

| | **Sunday — stock episode** | **Wednesday — educational episode** |
|---|---|---|
| Skill | `/stock-analysis-presentation <TICKER>` | `/learn-stock "<topic>"` |
| Subject | One company, its filings | One concept (shorting, options, risk sizing) |
| Source of truth | SEC filings → `episodes/<SYM>.json` | The lesson itself — no episode JSON |
| Engine | `build_deck.py` + `decks/<SYM>.py` | Copy `assets/deck-engine.html`, swap `DEFS` + visuals |
| Length | 8–10 slides (condensed) or ~20–25 (full) | 8–19 slides |
| Ends with | Hands off to the Webull chart | Recap + hook for the next video |

Both are 1920×1080 HTML decks in the same design language, recorded the same way
(camera beside the deck, not over it).

## The weekly loop

```
        ┌─────────────────────────────────────────────────┐
        │  /find-stock                                    │
        │  → one ticker, with momentum numbers            │
        └────────────────────┬────────────────────────────┘
                             ↓
        ┌─────────────────────────────────────────────────┐
        │  /stock-analysis-presentation <TICKER>          │
        │  Phase 1: read the filings, find the story      │
        │  Phase 2: build + audit + validate the deck     │
        │  → output/<TICKER> <DATE>/ (HTML, SCRIPT, Notes)│
        └────────────────────┬────────────────────────────┘
                             ↓
        ┌─────────────────────────────────────────────────┐
        │  Publish deck as an artifact → open on iPad     │
        │  → record full-screen, cut to Webull for the TA │
        └────────────────────┬────────────────────────────┘
                             ↓
        ┌─────────────────────────────────────────────────┐
        │  Extract Audio shortcut → attach M4A in chat    │
        │  /post-video → chapters, titles, description    │
        └─────────────────────────────────────────────────┘
```

Wednesday is the same shape with `/learn-stock` in the middle and no episode JSON.

## What each skill actually hands you

**`/find-stock` — research, no files.**
A written verdict: one ticker, its Google-Trends-on-YouTube momentum numbers
(early-week vs last-2-days), why it passes all four tests, then 2–3 runner-ups
with why each lost, tickers to skip despite the buzz, the literal search phrases
to build the title around, and the honest caveats.

**`/stock-analysis-presentation` — files.**
`$DECK_OUT/<TICKER> <YYYY-MM-DD>/` containing:
- `<SYM>-<DATE>.html` — the 1920×1080 deck you record from
- `SCRIPT.md` — what you say, per slide
- `Notes/` — one `.txt` of talking-point bullets per slide + `00 TALKING-POINTS.txt`
- `SOURCES.md` — every SEC URL behind every number
- `data/<SYM>-<DATE>.json` — the frozen payload the deck rendered from

Plus, at the repo root: `episodes/<SYM>.json` (the filing-read facts) and
`decks/<SYM>.py` (the bespoke narrative module).

**`/learn-stock` — files.**
`output/educational/<TOPIC> <YYYY-MM-DD>/` with the deck HTML and
`TALKING-POINTS.md` (per slide: head, punch, long-form notes, target seconds).

**`/post-video` — text.**
Timestamped transcript, linked chapters, 2–3 title options, a paste-ready
description in one code block, and a quality report flagging any spoken number
that disagrees with the verified episode JSON.

## The four tests `/find-stock` applies, in order

1. **Rising into the most recent days** beats bigger-but-fading. A name that peaked
   midweek and is decaying is the trap. Weekend-adjust: finance searches dip
   Sat/Sun, so anything rising *into* a weekend is genuinely accelerating.
2. **The story has legs** — an unresolved conflict or a dated future catalyst that
   keeps generating searches after you upload. One-day pops die.
3. **Low saturation** — if 300K-view videos already cover it, you can't rank,
   however big the demand.
4. **The catalyst is verified** by a targeted search, not by an agent's summary.

## Non-negotiables

- **Stdlib-only Python.** No pip, no server, no localhost dependency.
- **Never type a figure.** Every number is interpolated from data.
- **The loop must pass** before a deck is done — build → audit → validate, then
  both again with `--prove`.
- **Commit and push** everything in a cloud session. The container is disposable.

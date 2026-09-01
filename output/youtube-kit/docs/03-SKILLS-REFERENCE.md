# 03 — Skills Reference

Every skill in the kit: what triggers it, what it takes, what it hands back, and
whether it runs in a cloud session.

Legend: ☁️ works in cloud · 💻 Mac only · ⚠️ works with a caveat

---

## The three core channel skills

### ☁️ `/find-stock` — pick the ticker

**Argument:** optional constraints, candidate tickers, or a time window.
**Triggers:** "find me a stock", "what's trending", "which ticker should I cover",
"what should this week's video be on".

**Does:** three parallel research agents (market data / social buzz / YouTube
demand), then Google Trends on the **YouTube Search property** (`gprop=youtube`,
`now 7-d`, geo US), then a momentum verdict.

**Bundled tool:**
```bash
python3 skills/find-stock/trends_http.py "NBIS stock" "nebius stock" "PLTR stock"
python3 skills/find-stock/trends_http.py --related "NBIS stock"
```
Stdlib only, no browser. Prints daily averages, a last-2-day momentum verdict per
keyword, and related queries. If Google 429s (datacenter IPs sometimes are), it
says so plainly.

**Hands back (text, no files):** one ticker + its momentum numbers · 2–3 runner-ups
with why each lost · tickers to skip despite buzz · the literal search phrases for
the title · caveats (Trends values are relative 0–100 *per comparison set*;
absolute volumes are unknown).

**Hard rules:** inject today's date into every agent prompt · YouTube property is
mandatory, web-only Trends doesn't answer the question · max 5 keywords per
comparison with a shared anchor · momentum beats magnitude, weekend-adjusted ·
never recommend a saturated ticker whatever its volume · verify every catalyst
with a targeted search · if Trends is blocked, say so — never fabricate numbers.

**Cloud caveat:** the browser fallback in `trends-api.md` (Claude-in-Chrome, then
Playwright) is Mac-only. In cloud, use `trends_http.py`; if it's blocked, fall
back to the agent's YouTube-autocomplete and view-velocity evidence.

---

### ☁️ `/stock-analysis-presentation <TICKER>` — the Sunday deck

**Triggers:** a ticker plus "deck", "presentation", "episode", "run the deck for
X", "do NVDA next", "make me the slides for TSLA".

**Does:** Phase 1 finds the story in the filings (most of the value). Phase 2
writes `episodes/<SYM>.json` + `decks/<SYM>.py`. Phase 3 runs the build/audit/
validate loop. Phase 4 you look at it.

**Hands back:**
```
output/<TICKER> <YYYY-MM-DD>/
├── <SYM>-<DATE>.html        the 1920×1080 deck
├── SCRIPT.md                what you say, per slide
├── SOURCES.md               every SEC URL behind every number
├── data/<SYM>-<DATE>.json   the frozen payload the deck rendered from
└── Notes/
    ├── 00 TALKING-POINTS.txt
    └── <NN> <slide>.txt     one-sentence bullets per slide
episodes/<SYM>.json          the filing-read facts
decks/<SYM>.py               the bespoke narrative module
```

**References inside the skill — read the one you need:**

| File | When |
|---|---|
| `references/new-ticker-runbook.md` | **Start here for a new ticker.** The whole job, in order, with the code. |
| `references/episode-contract.md` | Before writing `episodes/<SYM>.json` |
| `references/plain-english.md` | Before writing any "why it matters" band |
| `references/recording-setup.md` | When filming — the `?cam=` system and the measurement behind it |

Full detail in `04-DECK-PIPELINE.md`.

---

### ☁️ `/learn-stock "<topic>"` — the Wednesday deck

**Triggers:** "Wednesday video", "educational episode", "teach X", "lesson deck on
X", "learn deck", or asking for a deck that explains a concept rather than
analysing a ticker.

**Does:** copies the verified engine (`assets/deck-engine.html`, a snapshot of the
canonical SWING-9TO5 build) and replaces exactly two things — the `DEFS` array and
the per-slide `v*()` mount functions. **Never rebuild the engine from scratch.**

**Hands back:** `output/educational/<TOPIC> <YYYY-MM-DD>/` with the deck HTML and
`TALKING-POINTS.md` (per slide: head, punch, long-form notes, target seconds).

**Assets:**
- `assets/deck-engine.html` — the engine to copy
- `assets/visual-library.html` — 12 browsable extra visual patterns
- `format.md` — the engine contract, read before editing
- `visuals.md` — the catalogue of all 31 proven visual patterns

**Copy budgets:** head ≤ 9 words · punch ≤ 14 words · ~21 words on screen ·
2–3 carrying words of the punch wrapped in `<b>` · everything else into `notes`.

---

### ☁️ `/post-video` — YouTube metadata

**Argument:** path to the final export (Mac) or the extracted audio (cloud), plus
the ticker/topic if the filename doesn't say.
**Triggers:** "/post-video", "get this ready to post", "make the chapters", "title
and description for my video", or dropping a final export.

**Does:** transcribes, then builds chapters, titles and description **grounded in
what the video actually says** — never guessed.

```bash
which ffmpeg || apt-get install -y ffmpeg
# Mac (video in) — strip the audio:
ffmpeg -y -v error -i "$VIDEO" -vn -ac 1 -acodec libmp3lame -q:a 4 "$SP/final.mp3"
# Cloud (M4A in) — just transcode:
ffmpeg -y -v error -i "$AUDIO" -ac 1 -acodec libmp3lame -q:a 4 "$SP/final.mp3"
npx hyperframes transcribe "$SP/final.mp3" -d "$SP" --json --model small.en
```
First run in a fresh cloud session downloads the whisper model — allow a minute or
two. `transcript.json` is a flat word array `[{text,start,end}, …]`; words are
grouped into sentences at terminal punctuation and printed with `M:SS` stamps.

**Hands back:** chapters · 2–3 title options (best first) · a paste-ready
description in one code block · a quality report.

Full detail in `06-POSTING-CHECKLIST.md`.

---

## Supporting skills

### ☁️ `/design` — the visual vocabulary

**Load before touching any chart, layout or colour.** Governs how decks look;
`stock-analysis-presentation` governs the decks themselves.

23 chart forms, each mapped to the job it's for — `forecast`, `gauge`, `sankey`,
`bridge`, `dumbbell`, `slope`, `distribution`, `smallmult`, `indexed`, `track`,
`range`, `radar`, `stackedh`, `bars`, `line`, `hbars`, `peers`, `donut`,
`treemap`, `fvband`, `insider`, `grouped`. Non-chart slide types: `title`, `mega`,
`tiles`, `quote`, `findings`, `snapshot`, `twocol`, `verdict`, `reasons`.

**Four rules `audit_deck.py` enforces:**
1. `slide-variety` — no single chart form carries more than a third of a deck.
2. No `null` where a function is expected; formatters are named strings
   (`fmtKind`), never callables across the payload boundary.
3. `chart-entities` — **no HTML entity in any chart spec.** Chart labels are
   written with `textContent`, so `&times;` renders as seven literal characters
   and the extra width pushes a value label into the next column. Entities are for
   prose fields (`head`, `sub`, `why`) only; chart labels take the glyph.
4. `no-hardcoded-figures` — no typed figure in the template *or* in `decks/*.py`
   string literals. Docstrings are exempt; definitional label text must be
   declared in a module-level `LITERALS_OK` tuple, so every exception is a
   decision someone made.

Before any new colour pair, load the bundled `dataviz` skill and run its
`scripts/validate_palette.js`. Never eyeball it. `dataviz` ships inside Claude
Code, not this repo — if it's ever missing, `design`'s own reference records the
validated pairs; don't invent new chart colours without the validator.

### ☁️ `/design-craft` — high-craft HTML/CSS/JS

For new visual patterns when the catalogue has nothing that fits: animated motion
pieces, prototypes, data viz, print, 3D. 20 reference files (animation,
gradients-color-effects, layout-type-color, svg, three-d, accessibility,
performance, decks, …) and 8 worked examples.

### ☁️ `/fa <TICKER>` — full fundamental analysis

Buy-side analysis in eleven sections: revenue quality · profitability and
operating leverage · returns on capital · solvency · cash conversion · capital
allocation · valuation · accounting red flags · street expectations · verdict.

```bash
python3 skills/fa/analyze.py TICKER          # report
python3 skills/fa/analyze.py TICKER --json   # raw inputs beside outputs
```
Stdlib only. **Run the engine first — never hand-assemble numbers.** Every ratio
is arithmetic on a *named XBRL tag*, and `--json` prints the tag that fed each
figure. Read `reference.md` for interpretation thresholds, the tag map and the
reverse-DCF. Authority order: SEC XBRL companyfacts (authoritative) → vendor data
(cross-check only) → price bars.

Note: **leases are debt.** Excluding them understated DaVita by $7.7B.

### ⚠️ `/technical-analysis` — grade a swing trade

Grades a planned or open trade against the measured A-setup (a 50 SMA bounce in a
steep uptrend, in the right volatility band), scores it 1–10, sizes it, runs the
4%/8% math.

The finding that matters: **the edge is real but slow.** Winners take a median 9
bars (~4.5 trading days) to reach +8%. A 3-day habit turns the system from
profitable to pointless. But the line is **+4%, not the clock** — once price
touches +4% the stop moves to breakeven and the trade is free. Median winner
reaches +4% in 4 bars; losers hit the stop in 4 bars too.

Three evidence files, and they disagree: `reference/journal-evidence.md` (25 real
trades), `reference/backtest.md` (50 names × 14 months on Webull bars) and
**`reference/alpaca-remeasure.md` (the rebuild with a random-entry control — quote
this one).** The Alpaca run measures roughly half the expectancy `backtest.md`
claims and the two have not been reconciled; the Alpaca run is the conservative
pair and ships with its control.

**Cloud caveat:** `screener.py` and `backtest.py` need Alpaca credentials:
```bash
export APCA_API_KEY_ID=...  APCA_API_SECRET_KEY=...
export ALPACA_FEED=sip      # iex sees ~3% of the tape
```
Grading a chart screenshot needs no keys.

Also ships `playbook/4h-swing-playbook.pdf`.

---

## Higgsfield skills — 💻 Mac only

All four generate media through the **Higgsfield MCP**, which is not connected in
a cloud session. Never substitute local tools (ffmpeg, ImageMagick, yt-dlp).
Each one loads its MCP tools via ToolSearch before calling them.

### 💻 `/youtube-thumbnail-maker "<app A>" and "<app B>"`
Dark gradient background + bold white headline + two 3D iOS-style app icons
flanking a white "+" + a subtle green stock-chart line.
Flow: find high-res icons by search (brand press page → App Store → Wikipedia →
`cdn.simpleicons.org` last resort) → `media_upload` all three images in one
batched call → `curl --upload-file` to each `upload_url` → `media_confirm` →
`generate_image`. **Never invent the headline** — ask once; text is the most
visible element and a wrong guess wastes a generation.

### 💻 `/youtube-popup-graphic "<item name>" [style reference image]`
A single card popping into frame in the exact style of a supplied UI reference.
Pipeline: upload the reference → `generate_video` with `seedance_2_0`, the
reference passed as `role: "image"`, and a **short** prompt.
Defaults, don't re-ask: `seedance_2_0` · 16:9 · 8s · 1080p · genre auto · SFX-only
audio.
What it deliberately does *not* do any more: no `nano_banana_2` intermediate
image · no `start_image`/`end_image` interpolation (stiff PowerPoint A→B) · no
20-line over-specified prompt (diffusion models can't read that detail) · **no
multi-card layouts** — three text labels in one 8-second shot get garbled by every
video model. One card per popup; stitch in post. Multiple items → N parallel
generations.

### 💻 `/youtube-broll-maker <photo> "<action>"`
10-second B-roll of you doing an action, via Seedance 2.0. Needs a photo, an
action phrase, and one of 5 cinematography style presets chosen through
`AskUserQuestion` — **never pick the preset for the user.**

### 💻 `/youtube-clipper <youtube url>`
Short-form clips via the Higgsfield personal clipper (FNF Clipify).
Defaults: 10 clips (max 20) · `9:16` · "Inter" subtitle font. `urls` is an array
even for one video. Capture the returned `row_id`, poll `personal_clipper_status`
(first wake ~270s, then 600–1200s). Report the count that actually came back —
never claim 10 if fewer did.

---

## Not in this kit

- **`/race-dossier`** — F1 betting dossier, needs `~/Projects/f1-dossier` locally.
  Nothing to do with the channel; a copy is in the repo if you want it.
- **`dataviz`** — bundled inside Claude Code itself, not a repo file. Should exist
  in cloud sessions too.
- **Retired:** the `terminal` and `bull` skills are gone. Every data trap that
  mattered is now carried in `marketdata.py`'s comments.

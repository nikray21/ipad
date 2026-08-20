# Episode deck pipeline

Nikil's YouTube stock-analysis engine: pull SEC filings + market data, find the
story nobody else found, build a 1920×1080 HTML slide deck with presenter notes,
prove every number traces to a filing. The workflow lives in
`.claude/skills/stock-analysis-presentation` (deck episodes) and
`.claude/skills/find-stock` (ticker discovery) — invoke those, don't improvise.

## Environment

- **Local Mac:** nothing to configure. Output defaults to `~/Desktop/…` via
  `deckpath.py`.
- **Cloud session (iPad workflow):**
  - `export DECK_OUT=output` before building — write decks into the repo.
  - `source .env` before running **anything** that touches market data —
    `marketdata.py` (so decks, quotes, `history`), `liquidity_swings.py`,
    `trade_setup.py`. All of them need `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`
    now that Alpaca backs price/chart data repo-wide (see Market data below).
    A fresh shell has neither set — that's the first thing to check on any
    "not set" error, not a reason to fall back to Yahoo.
  - **Commit and push `output/` and any new `episodes/<SYM>.json` /
    `decks/<SYM>.py`** at the end of the session. The repo is the only
    persistence between cloud sessions; anything uncommitted is lost. This
    does **not** include `.env` — it's gitignored on purpose (see Market data)
    and won't survive to the next session; re-export the keys each time, or
    set them as the cloud environment's own persistent env vars if that's
    configured.
  - Network access must be set to **Full** (or a custom allowlist including
    `sec.gov`, `api.nasdaq.com`, `data.alpaca.markets`, `query1.finance.yahoo.com`,
    `api.stocktwits.com`, `trends.google.com`) — the default Trusted list
    blocks these upstreams. Yahoo stays on the list even though chart/quote
    moved off it: `build_fundamentals_yahoo` still uses it for foreign
    filers (NIO-style 20-F/6-K names with no SEC XBRL) — that's fundamentals,
    not chart/price data, and out of scope for the Alpaca rule below. If
    `source .env && python3 marketdata.py quote NVDA` fails, check network
    first, then whether `.env` actually has both Alpaca vars.
  - There is no localhost. To view a deck, **publish the HTML as an artifact**
    and open the private URL (append `?theme=cream&audit=1` for the built-in
    layout audit). This is also how Nikil opens the deck full-screen on the
    iPad to record.

## Market data

**Hard rule, repo-wide: chart and price data comes from Alpaca only, via
`alpaca_data.py`. Never Yahoo, Nasdaq, or Webull for chart/price data.**
Requires `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` — they live in the repo's
own gitignored `.env` (`source .env` before running anything below; see
`.env.example` for the variable names, free key at https://alpaca.markets).
Never commit real values — a leaked key in git history stays leaked even
after the line is deleted, so `.env` is the only place they belong.

This covers two things that used to be separate:

- **`liquidity_swings.py` / `trade_setup.py`** — the LuxAlgo Liquidity Swings
  port (CC BY-NC-SA, see the module docstring) plus the ATR/50-SMA playbook
  math. The `technical-analysis` skill runs them instead of reading a
  screenshot — the SWING CALL colour is the only input left that a human has
  to supply. A first pass on Yahoo's feed reproduced zone shape and rough
  price levels but not exact edges, closely enough to look right and far
  enough to place a stop wrong. Self-checks: `python3 test_liquidity_swings.py`,
  `python3 test_trade_setup.py`.
- **`marketdata.py`'s `history` and `quote` routes** — the deck's price
  chart and live quote, used by every `build_deck.py` run. `fundamentals` /
  `filings` (SEC XBRL) and `profile` / `street` / `estimates` (Nasdaq) are
  untouched — they're not chart/price data, so they're out of scope for this
  rule. `build_fundamentals_yahoo` (the foreign-filer fallback for names like
  NIO with no SEC XBRL) is also untouched for the same reason.

Zone volume labels out of `liquidity_swings.py` are not yet trustworthy off
any feed; a different indicator is the plan for that number, so grade zones
on price (`top`/`btm`/`level`), not `volume`.

## Invariants

- Stdlib-only Python. No pip installs, no server.
- Never type a figure into a deck — every number is interpolated from data.
- The loop must pass before a deck is done: `build_deck.py` →
  `audit_deck.py` → `validate_facts.py`, then both with `--prove`.
- `.cache_filings/` and `.cache_form4/` are disposable and gitignored.

## Skills in this repo

`.claude/skills/` carries the channel toolkit for cloud sessions. The two that
matter most: **stock-analysis-presentation** (Sunday ticker episode) and
**learn-stock** (Wednesday educational episode). Supporting: `design` (load
before touching any chart), `fa`, `find-stock`, `technical-analysis`.
`design-craft` (high-craft HTML/CSS/JS visual work — learn-stock leans on it
for new visual patterns).
Reference-only in cloud (they need local tools/MCPs the sandbox lacks):
`race-dossier` (local ~/Projects/f1-dossier), `youtube-thumbnail-maker`,
`youtube-popup-graphic`, `youtube-broll-maker`, `youtube-clipper` (Higgsfield
MCP — usually absent in cloud).

The `dataviz` skill both deck skills cite is bundled inside Claude Code
itself (not a repo file) and should exist in cloud sessions too. If it is
ever absent: the `design` skill already records the validated palette pairs —
do not invent new chart colors without the validator.

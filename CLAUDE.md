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
  - **Commit and push `output/` and any new `episodes/<SYM>.json` /
    `decks/<SYM>.py`** at the end of the session. The repo is the only
    persistence between cloud sessions; anything uncommitted is lost.
  - Network access must be set to **Full** (or a custom allowlist including
    `sec.gov`, `data.alpaca.markets`, `api.nasdaq.com`,
    `query1.finance.yahoo.com`, `api.stocktwits.com`, `trends.google.com`) —
    the default Trusted list
    blocks these upstreams. If `python3 marketdata.py quote NVDA` fails with
    connection errors, this is why.
  - There is no localhost. To view a deck, **publish the HTML as an artifact**
    and open the private URL (append `?theme=cream&audit=1` for the built-in
    layout audit). This is also how Nikil opens the deck full-screen on the
    iPad to record.

## Market data — Alpaca is the price source

Every price and every chart in this repo comes from **Alpaca**: `marketdata.py`
(deck charts and quotes), `.claude/skills/fa/analyze.py` (the price behind every
valuation multiple), and `.claude/skills/technical-analysis/alpaca.py` (the trade
grader). Yahoo and Nasdaq remain only as fallbacks for when no key is set, and
Nasdaq still supplies the things Alpaca does not carry — analyst ratings, targets,
estimates, sector/industry/market-cap metadata, and the earnings calendar. Every
payload names the source that answered it.

Needs `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in the environment. Set them as
**environment variables on the cloud environment**, not in a committed file — a key
in git is a key in every clone and fork of the repo. Without them the code falls
back to Yahoo/Nasdaq and says so rather than failing.

Feeds, in descending order of truth: `sip` (real-time full tape, paid plans),
`delayed_sip` (same tape, 15 min late), `iex` (real time but ~3% of the tape).
Historical bars come back on `sip` even on the free plan; only live quotes are
restricted. A late full-tape price beats a live sliver, so `delayed_sip` outranks
`iex` everywhere.

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

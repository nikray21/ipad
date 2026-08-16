# Running a new ticker, end to end

Two episodes have gone through this: DVA and PLTR. Budget most of the time for
Phase 1 — the research is the product, the deck is the packaging.

---

## 0. Preflight

```bash
cd "$(git rev-parse --show-toplevel)"   # repo root — everything runs from here
python3 marketdata.py quote <SYM>     # upstreams reachable? nothing to start
ls decks/ episodes/                   # what already exists
```

**Nothing to start.** `marketdata.py` fetches SEC XBRL, the Yahoo chart API and Nasdaq
directly. A failing route means connectivity or an upstream shape change, not a
service being down.

Tell him up front if this is a heavy run (it is — many filings, long outputs) and
offer to do it in chunks.

---

## 1. The tape, before any filing

```python
import sys, os, datetime
sys.path.insert(0, os.getcwd())   # run from the repo root
from marketdata import get
p = get("history", "<SYM>")["points"][-252:]
dt = lambda x: datetime.datetime.fromtimestamp(x["t"]/1000).strftime("%Y-%m-%d")
for i in range(len(p)-35, len(p)):
    ch = (p[i]["c"]/p[i-1]["c"] - 1) * 100
    print(f'{dt(p[i])}  {p[i]["c"]:8.2f}  {ch:+6.2f}%  vol {p[i]["v"]:>12,}')
```

Find the actual reaction day and its size. **It is usually not the day you assume.**
Then the in-order peak-to-trough — a high minus a low is not a drawdown if the high
came second (this is exactly PLTR's shape).

---

## 2. Every earnings 8-K for eight quarters

```python
import json, urllib.request
UA = {"User-Agent": "nikil.rayani@puriscorp.com research"}
sub = json.load(urllib.request.urlopen(urllib.request.Request(
    f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=UA)))
r = sub["filings"]["recent"]
for form, date, acc, items in zip(r["form"], r["filingDate"],
                                  r["accessionNumber"], r["items"]):
    if form == "8-K" and "2.02" in (items or ""):
        print(date, f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-','')}/")
```

Fetch each index, take the `ex99` href, flatten to text (recipe in
`episode-contract.md`). Build **one table across eight quarters**: EPS, revenue,
guidance low/high, segment operating income, debt, leverage, buybacks, per-unit
metrics.

Then line the guidance revisions up against the next session's move. For DVA that
table *was* the episode: the stock rose on one thing only, a higher midpoint.

---

## 3. The 10-Q and 10-K

- **10-Q** — MD&A, revenue-recognition note, segment note, subsequent events.
  The footnote lives here. Read the notes the release does not quote.
- **10-K** — Item 1 for unit economics and customer/payor concentration, Item 1A
  for the risk that is actually live (not the boilerplate list).

Ask of every beat: **did the profit come from the core business?** Bridge it by
segment. If a small or lumpy segment carried it, that is a finding.

---

## 4. Form 4s — only if insiders have been active

```python
# submissions JSON → every Form 4 → the XML document in each accession
# Cache to .cache_form4/<SYM>/ so the audit can recompute from source.
```

**Transaction codes are the whole game.** Only these are decisions to buy or sell
at the market price:

| Code | Meaning | Counts? |
|---|---|---|
| `S` | open-market sale | **yes** |
| `P` | open-market purchase | **yes** |
| `M` | option exercise | no |
| `C` | conversion | no |
| `A` | grant / award | no |
| `F` | shares withheld for tax | no |
| `G` | gift | no |

Counting M/C/A/F inflates the total and makes the slide wrong.

**Always state the 10b5-1 share.** 45 of PLTR's 57 filings cited a pre-set plan, so
"most of this was scheduled months ahead" is the fair reading — say it on the slide.
Check `aff10b5One` and fall back to searching the blob for "10b5-1".

These aggregates cannot be text-matched to any one filing, so mark the block
`_derived` and add an audit that re-parses the cached XML and recomputes every
figure. That is the verification.

---

## 5. Peers — fetched live, never typed

Pick 5 comparables and put only their **tickers and display names** in the episode
file. Multiples are computed at build time from `/api/profile` and
`/api/fundamentals` per peer (see `_peer()` in `decks/PLTR.py`). A typed peer
multiple is stale the next morning.

Always show **growth beside the multiple** — "expensive" and "expensive for its
growth" are different claims and the slide must show both.

---

## 6. Write the episode file

`references/episode-contract.md` is the full contract. Every numeric fact carries a
`src`. Declare `findings` (≥3, each naming a note/page/table), `proseLiteralsOK`
for structural figures written out in verdict prose, and the `fairValue` cases.

---

## 7. Write `decks/<SYM>.py`

```python
import re
from . import fmt

LITERALS_OK = ()          # definitional label text only, e.g. "Deals over $1M"

def derive(snap, ep, fund, qrows, die, fact):
    """Company-specific metrics. die() on anything that does not reconcile."""
    return {...}

def slides(snap, ep, fact, fund_quarters=None):
    m = b_ = fmt.usd              # millions in, unit chosen for you
    d2 = dm = fmt.dollars
    pc = fmt.pct
    fv = lambda *k: fact(ep["filings"], *k)      # every fact, sourced
    ...
    return S
```

`decks/fmt.py` is the only place money is formatted:

| Call | Gives |
|---|---|
| `fmt.usd(1800)` `fmt.usd(730)` `fmt.usd(0.208)` | `$1.8B` `$730M` `$208K` |
| `fmt.num(6893343)` | `6.9M` — a bare count |
| `fmt.dollars(172.01)` | `$172.01` — a share price, always 2dp |
| `fmt.pct(-48.2, 0)` | `−48%` (`signed=False` drops the `+`) |
| `fmt.mult(53, 0, plain=True)` | `53×` glyph for chart labels; without `plain` you get `&times;` for prose |

One decimal, dropped once the mantissa already has three significant figures —
`$442B`, not `$441.8B`.

**Reconciliation guards belong in `derive`**, not in a comment. Both shipped
episodes assert the cash bridge sums to reported operating cash flow and the
balance sheet balances, and `die()` if not.

---

## 8. Build, audit, prove

The build writes to `~/Desktop/<SYM> <DATE>/` unless `DECK_OUT` says otherwise.
Everything downstream resolves the folder through `deckpath.py`, which also
looks one level deeper — so a deck filed under `~/Desktop/Stock Analysis/` still
audits. Never re-pin these paths to a literal `~/Desktop/...`.

```bash
python3 build_deck.py <SYM>
python3 audit_deck.py <SYM>            # ALL DECK INVARIANTS PASS
python3 validate_facts.py <SYM>        # ALL EPISODE FACTS TRACE
python3 audit_deck.py <SYM> --prove    # must go red
python3 validate_facts.py <SYM> --prove
```

---

## 9. The layout audit — `?audit=1`

Source checks pass while a page renders wrong. The sweep is built into the deck, so
there is nothing to paste and nothing to forget:

```bash
cd "$(python3 -c 'import deckpath,sys; print(deckpath.read_dir(sys.argv[1], sys.argv[2]))' <SYM> <DATE>)" \
  && python3 -m http.server 4849 --bind 127.0.0.1 &
open "http://127.0.0.1:4849/<SYM>-<DATE>.html?theme=cream&audit=1"
# then again with &theme=dark
# Cloud session: no localhost — publish the deck as an artifact and open the
# private URL with the same query strings.
```

Read the console. It must say **`AUDIT CLEAN`** in both themes. What it catches:

| Check | The bug it exists for |
|---|---|
| dead chart | a treemap that recursed forever; three charts handed the wrong spec keys |
| content vs **viewBox** | `bridge` drew 2587px inside a 500px box. The old check measured the `<svg>` element box, which is in bounds by definition |
| overlap with the why band | the same bridges drew through the copy and the footer |
| text-on-text | `"$9.55"` running into `"average $5.60"` on a dumbbell |
| unknown / unfilled animation | `grow` on a horizontal bar; a missing `fill: both` |
| sub-15px on camera | 13 labels below the floor a phone can read |
| stage off-centre | a translate added for `?cam=` that fought the flex centring and cropped the deck |

Deliberate label/value stacks (a 110px numeral above its caption) touch at the
glyph box but not in ink — the audit skips pairs whose centres are within 24px.

`window.deckAudit()` returns the array directly if you want it in a variable.

**Audit both layouts.** A deck opens in the camera layout, so `?audit=1` covers
that by default — press `C` and re-run `window.deckAudit()` for the full-bleed one.
Both must be clean in cream and dark. Narrowing the charts for the camera column is
what surfaces label collisions; it has caught four.

**Then still step every slide and look.** The audit proves geometry. It cannot tell
you the chart fails to argue its own headline — which is how a segment slide shipped
showing only revenue under the words "only one of the three earns anything".

### The editorial pass, and how to make it fast

Screenshotting 21 slides is slow and you will still miss things. Dump each chart's
headline beside its own spec values and read the two against each other:

```js
DECK.slides.map((d,i) => d.chart && ({n:i+1, kind:d.chart.kind,
  head:(d.head||'').replace(/<[^>]+>/g,''), rows:d.chart.rows, series:d.chart.series}))
  .filter(Boolean)
```

That one dump caught four faults on an RKLB deck that had just passed 30 source
invariants and a CLEAN layout audit in both themes:

| What it looked like | What was wrong |
|---|---|
| head "23.8× what the defence companies cost" | the average included the acquisition target; primes-only is 35.2× |
| head "Costs grew +34% while revenue grew +62%" | chart showed only +25% and +50% — neither headline number was on it |
| row "guided 117–123 … $123M … inside the range" | the label rounded up into its own guidance top |
| an `fvband` at `band: 0.20` | the collar it drew is ±25%, so the shaded zone was not the collar |

**Do the arithmetic yourself on any ratio in a headline.** Every one of those was
found by dividing two numbers on the screen and not getting the third.

Then screenshot the handful you changed, and read the title slide — a broken key
prints the literal word "undefined" and it is the first thing on camera.

## 10. Read every why-band out loud

Run the readability measure in `references/plain-english.md`. Target: **average
reading grade under 7, zero jargon hits, no band over ~90 words.** Ten of PLTR's
23 failed the first pass and had to be rewritten.

---

## 11. Report honestly

- Both cuts, in minutes and seconds, and whether they clear the 5:00 budget.
- Every figure that could not be verified, named.
- Any Terminal bug found on the way, with the diagnosis, kept out of the deck.

Then kill the http server.

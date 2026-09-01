# 05 — Data Sources, Routes and Caches

`marketdata.py` owns the whole data layer. **Nothing in the pipeline talks to
`127.0.0.1`.** Upstreams are public and key-free.

---

## The seven routes

```bash
python3 marketdata.py <route> <SYMBOL>
```

| Route | Upstream | Memory TTL | Disk TTL |
|---|---|---|---|
| `quote` | Nasdaq (live price) | 8s / 20s / 120s by market state | — |
| `history` | Yahoo chart API | 60s / 300s / 1800s | — |
| `fundamentals` | SEC XBRL `companyfacts` | 6h | 7 days |
| `profile` | Nasdaq api | 6h | 7 days |
| `street` | Nasdaq api | 3h | 3 days |
| `estimates` | Nasdaq api | 6h | 7 days |
| `filings` | SEC `submissions` | 12h | 14 days |

The three-value TTLs (`ttl_for(a, b, c)`) are market-state dependent: open →
pre/post → closed.

From Python:
```python
import sys, os
sys.path.insert(0, os.getcwd())        # run from the repo root
from marketdata import get
snap = get("history", "NBIS")
```

An unknown route raises `KeyError` listing the valid ones.

---

## Why the builders are copied verbatim

Each builder in `marketdata.py` was lifted from the Terminal's `server.py`
deliberately: **each one encodes a data trap found the hard way** — deriving a
quarter from cumulative XBRL figures, the order to try revenue tags in, split
normalisation, the freshness ceilings. Reimplementing them would have meant
rediscovering all of it.

Proven two ways, and re-prove both after touching `marketdata.py`:

1. **Same numbers** — `fundamentals`, `estimates`, `filings`, `profile` and
   `street` matched the old HTTP route byte for byte on PLTR, SPCX and DVA.
2. **Genuinely independent** — the whole loop, both `--prove` suites included,
   runs with every localhost connection forcibly refused:

```python
# no_localhost.py — raises if anything reaches 127.0.0.1
_real = urllib.request.urlopen
def guard(req, *a, **kw):
    url = req if isinstance(req, str) else req.full_url
    if "127.0.0.1" in url or "localhost" in url:
        raise AssertionError(f"BLOCKED: pipeline tried to reach {url}")
    return _real(req, *a, **kw)
urllib.request.urlopen = guard
```

`TERMINAL_API` still switches back to HTTP, which is only useful for comparing
the two implementations.

---

## Caches

Live beside the code, all gitignored, all disposable:

| Dir | Holds |
|---|---|
| `.cache_market/` | route payloads (same TTL contract as the old server) |
| `.cache_filings/` | SEC documents |
| `.cache_form4/<SYM>/` | insider XML the audit recomputes from |

Delete any of them freely — they rebuild. **`.cache_form4/` matters more than it
looks:** rule 12 requires the insider aggregate be *recomputed* from the cached
XML by the audit, not text-matched from a filing.

---

## Going to SEC directly

Always send a User-Agent — SEC rejects requests without one.

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
`skills/stock-analysis-presentation/references/episode-contract.md`).

### Which forms, by issuer type

| Issuer | Earnings | Quarterly | Annual | Guidance often in |
|---|---|---|---|---|
| US domestic | 8-K Item 2.02 + EX-99.1 | 10-Q | 10-K | the 8-K's EX-99.1 |
| **Foreign private issuer** (e.g. NBIS) | **6-K** | — | **20-F** | **EX-99.2 shareholder letter** |

Shareholder letters filed as EX-99.2 are SEC-traceable sources for guidance.

**Restated comparatives** in year-later releases are the ONE consistent basis for
a quarterly series when a deconsolidation reclassified history.

---

## Two engine truths found on NBIS

- **Foreign private issuers** file 6-K/20-F, not 8-K/10-Q — handled above.
- **Pre-market reporters break the engine's next-session reaction assumption.**
  Derive the same-day move from the daily bars in the deck module and **never
  render the engine's `releases` moves.** The quote route's `asOf` now
  self-corrects against the last daily bar (Nasdaq's label can lag its own price
  by a session).

---

## The tape, day by day

```python
import sys, os, datetime
sys.path.insert(0, os.getcwd())
from marketdata import get
p = get("history", "<SYM>")["points"][-252:]
dt = lambda x: datetime.datetime.fromtimestamp(x["t"]/1000).strftime("%Y-%m-%d")
for i in range(len(p)-35, len(p)):
    ch = (p[i]["c"]/p[i-1]["c"] - 1) * 100
    print(f'{dt(p[i])}  {p[i]["c"]:8.2f}  {ch:+6.2f}%  vol {p[i]["v"]:>12,}')
```

Find the **actual** reaction day and its size — it is usually not the day you
assume. Then the in-order peak-to-trough: a high minus a low is not a drawdown if
the high came second (exactly PLTR's shape).

---

## Other upstreams used by the channel

| Skill | Upstream | Needs |
|---|---|---|
| `find-stock` | `trends.google.com` (YouTube Search property) | nothing — `trends_http.py` is stdlib |
| `find-stock` | `suggestqueries.google.com` (YouTube autocomplete) | nothing |
| `find-stock` agents | ApeWisdom, AltIndex, Tradestie, Stocktwits, Benzinga, stockanalysis.com | web access |
| `fa` | SEC XBRL companyfacts; vendor data as cross-check only | nothing |
| `technical-analysis` | Alpaca bars | `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `ALPACA_FEED=sip` |

Authority order, always: **SEC filing → computed from the filing → vendor
figure.** The codebase's entire defect history is one shape: *something other
than the source of truth became a source of truth, then drifted.*

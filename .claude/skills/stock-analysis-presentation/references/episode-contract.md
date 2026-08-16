# The episode file — `episodes/<SYM>.json`

Everything company-specific lives here. `build_deck.py` reads it, `audit_deck.py`
checks the arithmetic that comes out of it, and `validate_facts.py` downloads each
cited document and searches it for every number attributed to it.

**Every numeric fact needs a `src` naming a key in `sources`.** The build dies
otherwise. This is the single rule that makes the deck defensible on camera.

Three blocks are newer than the original contract and are documented at the bottom:
**`findings`** (rule zero), **prose tokens + `proseLiteralsOK`** (so verdict copy
cannot go stale), and the **`insider`** / **`peers`** blocks.

## Shape

```jsonc
{
  "symbol": "DVA", "company": "DaVita Inc.", "episodeDate": "2026-08-06",

  "sources": {                       // must be https://www.sec.gov/... URLs
    "8k-q2-26": { "label": "8-K EX-99.1 — Q2 2026 results, filed Aug 4 2026",
                  "url": "https://www.sec.gov/Archives/edgar/data/.../ex991.htm" },
    "10q-q2-26": { ... }, "10k-2025": { ... }
    // a directory URL ending in "/" works too — the validator pulls in every
    // exhibit the index lists, so a figure cited to "the 8-K" is found in its EX-99.1
  },

  "filings": {
    // Single facts: { v, src, unit?, note? }
    "operations":     { "treatmentsPerDay": { "v": 92649, "src": "8k-q2-26" } },
    "unitEconomics":  { "revPerTreatmentQ2": { "v": 415.87, "src": "8k-q2-26" } },
    "results":        { "epsQ2": { "v": 4.02, "src": "8k-q2-26" } },
    "balanceSheet":   { "netDebtQ2": { "v": 10179, "src": "8k-q2-26", "unit": "USD millions" } },
    "regulatory":     { "cms2027Proposed": { "v": 1.1, "src": "10q-q2-26", "unit": "%" } },

    // Prose facts: v is a string. Skipped by the number validator — verify by eye.
    "payorStructure": { "quote": { "v": "The payments we receive from commercial payors…",
                                   "src": "10k-2025", "note": "Item 1 Business" } },

    // A bare `src` on a container covers every numeric column beneath it
    "payorMixQ2": { "src": "10q-q2-26",
                    "y2026": { "commercial": 940228, "medicare": 1749289 },
                    "y2025": { "commercial": 947015, "medicare": 1659607 } },

    // Row tables: one src per row, all numeric columns validated
    "quarterly": { "rows": [
      { "q": "Q2'26", "end": "2026-06-30", "eps": 4.02, "debt": 10848,
        "netDebt": 10179, "lev": 3.37, "src": "8k-q2-26" }
    ]},
    "earningsHistory": { "releases": [
      { "date": "2026-08-04", "q": "Q2'26", "fy": "2026",
        "guideLow": 14.10, "guideHigh": 15.20, "src": "8k-q2-26" }
    ]},
    "buybacks": { "history": [
      { "period": "Q2 2026", "amount": 348, "shares": 2238, "avgPrice": 154.95, "src": "8k-q2-26" }
    ]},
    "segments": { "src": "10q-q2-26",
                  "q2_26": { "usDialysis": 538, "ancillary": 57, "corporate": -16, "total": 579 },
                  "q1_26": { ... } },
    "guidance": { "current": { "src": "8k-q2-26", "adjEpsLow": 14.10, "adjEpsHigh": 15.20, ... },
                  "prior":   { "src": "8k-q1-26", ... } }
  },

  "fairValue": {                     // seeds the live on-camera calculator
    "horizonYears": 5, "requiredReturn": 10.0,
    "cases": { "bear": { "revGrowth": 2.0, "opMargin": 14.5, "exitPE": 9.0, "shareChange": -4.0 },
               "base": { ... }, "bull": { ... } },
    "constants": { "netDebt": 10179, "interestRate": 5.43, "taxRate": 21.1,
                   "nciAnnualRunRate": 311, "startRevenueTTM": 14010 }
  },

  "findings": [                      // RULE ZERO — at least three, or the build fails
    { "claim": "They paid a 1.4% tax rate — $15M on $1,081M of pretax profit.",
      "where": "10-Q statement of operations, the tax line",   // note/page/table, never "the 10-Q"
      "src": "10q-q2-26" }
  ],

  "proseLiteralsOK": [               // structural figures written out in verdict prose
    "Operating margin went from 27% to 47%",
    "paid a 1.4% tax rate this half"
  ],

  "verdict": {
    "call": "WATCH", "callLine": "One line, his voice.",
    "tiles":  [{ "dim": "Margins", "rating": "strong", "fact": "…" }],   // 6 dimensions
    "scored": [{ "dim": "Margins", "score": 4, "tone": "", "fact": "…" }], // radar; tone "" | "warn" | "bad"
    "working": ["five things genuinely working"],
    "watch":   ["five things to watch"],
    "why":     ["3–5 paragraphs behind the call"]
  },

  "notes": { "<slideKey>": "The spoken script for that slide, in his voice." }
}
```

## Prose tokens — the fix for stale verdict copy

Verdict prose is written once and read on the last slide months later. Anything
**price-dependent** must be a token, resolved at build time by
`build_deck.resolve_prose()` against the live snapshot:

```jsonc
"why": ["At {price|$} you are paying about {val.evRevOnGuide|x0} the revenue the
         company itself guided to, and roughly {val.peTrailing|x0} what it earned
         over the last twelve months."]
```

| Format | Renders | For |
|---|---|---|
| `{path\|$}` | `$172.01` | a share price |
| `{path\|usd}` | `$9.4B` | money **in millions** |
| `{path\|usdB}` | `$2.1B` | money already **in billions** |
| `{path\|x0}` `{path\|x1}` | `53×` `12.6×` | a multiple |
| `{path\|%}` `{path\|%0}` | `11.1%` `13%` | a rate, unsigned |
| `{path\|%+}` | `+13%` | a change, signed |
| `{path\|%abs}` | `48%` | magnitude only — "fell 48%", not "fell −48%" |

Paths walk the snapshot and accept list indices: `{series.7.growth|%0}`,
`{peakToTrough.peak|$}`, `{backlog.rpoNext12|usdB}`, `{fwd.0.pe|x1}`.

**This was not optional.** The verdict slide shipped reading "At $169 … 49x … 145x"
while the snapshot said $172.01, 53× and 147×, and DVA's "12.3x next year's
earnings / 11.3% yield" had drifted to 12.6× and 11.1%.

Figures that are **structural** — read off a filing and fixed for the quarter — may
be written out, but the episode must list the phrase in `proseLiteralsOK` so each
exception is a decision. `audit_deck.py` strips those phrases, then fails on any
remaining `%`, `$` **or bare multiple**.

## The `insider` block

Aggregated from Form 4 XML, so no single filing states any of it. Mark it
`_derived`; `validate_facts.py` skips it and `audit_insider_aggregates` re-parses
`.cache_form4/<SYM>/*.xml` and recomputes every figure instead.

```jsonc
"insider": {
  "_derived": true, "src": "form4", "windowEnd": "2026-08-08",
  "totalSoldShares": 6893343, "totalSoldValue": 1011.3,   // $M
  "totalBought": 0, "distinctSellers": 9,
  "plan10b5Filings": 45, "totalFilings": 57,
  "buckets": [{ "label": "0–3 months", "people": 8, "sold": 1160270,
                "value": 156.7, "bought": 0 }],
  "topSellers": [{ "name": "Peter Thiel", "role": "Director",
                   "shares": 2000000, "value": 289.7 }]
}
```

Only transaction codes **S** and **P** count. See the runbook for the full table
and why M/C/A/F must be excluded.

## The `peers` block

Tickers and display names **only**. Every multiple is fetched live at build time —
a typed peer multiple is stale by morning.

```jsonc
"peers": { "tickers": ["SNOW", "DDOG", "MDB", "NOW", "CRM"],
           "names": { "SNOW": "Snowflake", "DDOG": "Datadog" } }
```

`ratings` map to tile colours: `strong` green · `weak`/`mixed` amber · `risk` red.
`scored` drives the radar and the pip rows — keep the two consistent, and remember
any summary sentence about them must be **counted**, not asserted.

## What to pull from where

| Fact | Document | Where in it |
|---|---|---|
| Revenue, EPS, op income, margins | 8-K EX-99.1 | the highlights table up top |
| Company-defined FCF and op cash flow | 8-K EX-99.1 | "Financial and operating metrics" |
| Full-year guidance, and the prior guide | 8-K EX-99.1 | "Outlook" / "Current … guidance" |
| Total debt, net debt, leverage, interest rate | 8-K EX-99.1 | "Debt and capital structure" |
| Buyback shares, dollars, average price | 8-K EX-99.1 | "Certain items impacting the quarter" |
| Post-quarter buybacks | 8-K EX-99.1 | "Subsequent to <quarter end> through …" |
| Per-unit economics | 8-K EX-99.1 | the operating-metrics table |
| Segment operating income | 10-Q | segment note + MD&A segment table |
| Revenue by customer/payor | 10-Q | revenue-recognition note |
| Prior-year revenue recognised now, contract assets | 10-Q | revenue-recognition note |
| Balance sheet: equity, assets, shares outstanding | 10-Q | condensed balance sheet |
| Buyback authorisation remaining, related-party deals | 10-Q | equity note |
| Subsequent events | 10-Q | last note |
| Regulatory rate changes | 10-Q MD&A / 10-K | the proposed/final rule paragraph |
| Unit economics, concentration, competitive position | 10-K | Item 1 Business |
| The live risk | 10-K | Item 1A Risk Factors |

## Extraction recipe

```python
# every quarterly earnings 8-K for the last 2 years
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

Then fetch each index, grab the `ex99` href, and flatten to text:

```python
import re, html
t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
t = re.sub(r"(?s)<[^>]+>", " ", t)
t = re.sub(r"[ \t\xa0]+", " ", html.unescape(t))
```

`validate_facts.py` caches every document it fetches under
`.cache_filings/` (gitignored), so re-runs are free and you can grep the
cached text directly to confirm anything the validator flags.

## When the validator flags a fact

**Confirm the value in the filing text first — do not loosen the validator until it
passes.** Every flag so far has been a form gap, not a bad number: two-digit
percentages needed a `%` suffix to be searchable, millions-stored values needed
their thousands form (`-765.096` → `"765,096"`), and small figures appear as prose
(`"$37 million"`, `"2.0 million shares"`). Verify by hand, then teach `forms()` the
representation it missed.

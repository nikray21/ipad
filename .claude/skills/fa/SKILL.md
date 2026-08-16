---
name: fa
description: Full fundamental analysis on a public company — revenue quality, margins and operating leverage, solvency, cash conversion, capital allocation, valuation, accounting red flags, street expectations and a verdict. Use when the user says "run a FA", "fundamental analysis", "analyse this stock", "is X a good buy", "look at the fundamentals", "should I buy X", or names a ticker and asks whether it is worth owning. Pairs with the `bull` skill for the trade decision and `terminal` for the dashboard.
argument-hint: [TICKER, e.g. DVA]
---

# Fundamental Analysis

You are a buy-side analyst. Your job is not to describe a company — it is to
decide whether the price is wrong, and to say plainly when you cannot tell.

**Run the engine first. Never hand-assemble numbers.**

```bash
python3 ~/.claude/skills/fa/analyze.py TICKER          # report
python3 ~/.claude/skills/fa/analyze.py TICKER --json   # raw inputs beside outputs
```

Read `~/.claude/skills/fa/reference.md` for the interpretation thresholds, the
XBRL tag map, and the reverse-DCF procedure.

## Sources, in order of authority

| Source | Gives | Trust |
|---|---|---|
| **SEC EDGAR XBRL companyfacts** | every income / balance / cash-flow line | authoritative — it *is* the filing |
| **yfinance** | street targets, estimates, market cap, beta | vendor-derived; use as the cross-check, never the primary |
| **Alpaca** | price and volume bars | authoritative for price |

No third-party ratio library. Every ratio here is arithmetic on a **named XBRL
tag**, and `--json` prints the tag that fed each figure. A library that computes
`operatingMargin` for you hides which revenue line it used, and this codebase's
entire defect history is one shape: *something other than the source of truth
became a source of truth, then drifted.*

## The eleven sections

1. **Revenue quality** — growth, and whether it is organic, recurring, concentrated.
2. **Profitability & operating leverage** — margin *trend*, and whether operating
   income grows faster than revenue. A single-period margin says nothing.
3. **Returns on capital** — ROIC vs an assumed cost of capital. ROE is meaningless
   when equity is negative or buyback-depleted; say so rather than printing 81%.
4. **Solvency** — net debt/EBITDA, interest coverage, maturity wall, Altman Z.
   **Leases are debt.** Excluding them understated DaVita by 7.7B.
5. **Cash conversion** — FCF/net income, accrual ratio, capex intensity, SBC.
   Earnings that don't become cash are the single most common way a story breaks.
6. **Capital allocation** — buybacks, dividends, M&A, debt paydown, as a share of
   FCF. Buying back stock above intrinsic value destroys capital; say it.
7. **Valuation** — multiples against the company's *own* history first, peers
   second. Always compute EV metrics alongside equity metrics: a cheap P/E on a
   levered balance sheet is leverage, not value.
8. **Accounting red flags** — receivable days vs revenue growth, inventory build,
   negative book value, share count trend, one-off gains inflating a quarter.
9. **Expectations** — what the price implies. Use the reverse DCF in
   `reference.md`. "Cheap" is a claim about expectations, not about a multiple.
10. **Risks / thesis-breakers** — the two or three things that would make you wrong.
11. **Verdict** — a rating per dimension, each with **the fact behind it**.

## HARD RULES

1. **Run `analyze.py` and read its `!!!!` lines before writing a word.** If the
   cross-check says `DO NOT USE`, that metric is excluded from the verdict — not
   quietly averaged, not silently preferred.
2. **Never present missing or unverified data as fact.** Absence renders as
   "unknown". A confident number the filings don't support is the worst output
   this skill can produce.
3. **Cross-check every headline figure against an independent source.** Internal
   consistency only proves our maths matches our extraction. `analyze.py` does
   this automatically; when it disagrees, investigate rather than choose.
4. **Derived quarters are the weak point.** No company files a standalone Q4, so
   Q4 = FY − 9M. The reconciliation block must say `ok` before any TTM figure is
   used. It caught a Q4 net income of 0.566B against a vendor's 0.234B — where
   *ours* turned out to be right.
5. **Never invent a catalyst.** If the numbers don't explain the price, say
   exactly that. Do not supply a sector narrative or a guidance rumour the
   filings don't contain. "The move is not in the financials" *is* the finding.
6. **Street targets are undated.** After any large move treat them as stale and
   label them so. A mean target above a stock that just fell 25% is almost
   certainly pre-collapse.
7. **Separate the business from the security.** A great company at the wrong
   price is a sell; a mediocre one cheap enough is a buy. State which you mean.
8. **Quote the period.** Every figure carries its fiscal period. "Revenue grew
   6%" is unusable without knowing over what.
9. **If asked whether to trade it, hand off to `bull`.** This skill sizes up the
   business. The entry, the stop and the position size belong to the strategy.

## What separates this from a stock-screener summary

- **Compare the reaction to the numbers.** Pull filing dates from
  `/submissions/CIK##########.json` and measure the 1-day and 3-day price move
  against that quarter's results. When good numbers get sold, the thesis is
  about expectations, not performance — and that is usually the whole story.
- **Trend beats level.** Five quarters of operating margin tells you more than
  one. The engine prints the trend for exactly this reason.
- **Follow the cash.** Net income is an opinion; cash flow is a fact. When they
  diverge, believe the cash and find out why they differ.
- **Ask what the price already assumes.** Then judge whether that is too
  pessimistic or too optimistic. That is the only question that pays.

## Worked example — why the guards exist

Running this on **DVA** on 2026-08-06 surfaced, in order:

- TTM revenue 13.77B → **14.01B** once the dropped Q4 was derived
- CFO 0.83B → **2.19B** once year-to-date cash-flow facts were differenced
- Total debt 5.74B → **13.41B** once lease liabilities were included, taking
  net debt/EBITDA from a benign-looking figure to **5.34x**
- Q2 beat Q1 on revenue, net income, growth *and* margin — and the stock went
  **+27% after Q1 and −23% after Q2**. The financials did not explain the move,
  so the honest verdict was "something is priced in that the filings don't show",
  not a fabricated catalyst.

Every one of those was caught by a check, not by inspection. Add a new check for
every data bug you find; that is why the same bug never ships twice.

## Final note

Use `$ARGUMENTS` as the ticker. If the user gives a company name, resolve it to a
ticker first and confirm the CIK the engine matched — `analyze.py` prints it, and
a wrong CIK produces a complete, plausible, entirely wrong analysis.

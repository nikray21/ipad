# Visual catalogue — every form worth stealing

Catalogued 2026-08-08 from a full Simply Wall St NVDA report (23 screens). These
are standard visualisation forms; we implement our own. Each entry records **what
it shows**, **the data it needs**, and **whether we have it**.

Status key: **BUILT** = implemented in `deck_template.html` · **TODO** = worth
building · **SKIP** = considered and rejected, with the reason.

---

## Valuation

### 1.1 Share Price vs Fair Value — horizontal verdict band · **BUILT** (`fvband`)
Three coloured zones (green *20% Undervalued* / amber *About Right* / red *20%
Overvalued*) with two labelled markers dropped on them: **Current Price $223.96**
and **Fair Value $234.27**, plus a big **4.4% Undervalued** callout above.
- *Needs:* current price, one fair-value estimate.
- *Why it is good:* converts a valuation argument into a single position on a
  ruler. A beginner reads it in a second without knowing what a DCF is.

### 1.3 P/E vs Peers — ranked bars + peer average + growth column · **BUILT** (`peers`)
Horizontal bars per peer (AMD 122×, Marvell 73×, Broadcom 69.4×, **NVIDIA 33.2×
highlighted**, Micron 19.7×), a **Peer Avg 71.0×** reference line, green zone left
of it and red right — and critically a right-hand **Earnings Growth** column
(38.33%, 26.44%, 33.69%, 22.80%, 33.56%).
- *Needs:* peer tickers with a multiple and a growth rate each.
- *Why it is good:* the growth column pre-empts the obvious objection. "Expensive"
  and "expensive **for its growth**" are different claims and this shows both.

### 1.5 P/E vs Industry — distribution histogram with "you are here" · **BUILT** (`distribution`, unused)
Histogram of the whole industry's P/E buckets, the company's bucket highlighted
blue, an **Industry Avg** marker line, green zone below it / red above, and a
drill-down table of the companies in the selected bucket.
- *Needs:* the population's distribution. **This is why ours is unused** — we
  cannot source industry buckets without inventing them.

### 1.6 P/E vs Fair Ratio — dual-marker gauge · **BUILT** (`gauge`, `compare` needle)
Semicircular gauge, **Current PE 34×** on a blue needle against **Fair PE 47.3×**
on a yellow marker, green band below the fair ratio and red above.
- *Why it is good:* "fair multiple given this growth and risk" is a more honest
  frame than a raw multiple, and the gauge shows the gap rather than asserting it.

### 1.7 Analyst Price Targets — forecast cone + **agreement quality** · **BUILT** (`track`)
Share price history continuing into a shaded 12-month forecast cone with the
average target line, split at *Past | 12m Forecast*. The tooltip carries the thing
we do not have: **Agreement: Low — "analysts agreement range is spread more than
15% from the average."**
- *Added.* `track` now prints a High/Moderate/Low agreement verdict plus the actual
  spread, derived from the lo/hi/mean already drawn. PLTR: "Low agreement — targets
  run 59% from the average at the widest."

### Fundamentals Summary — market-cap donut with revenue/earnings slivers · **BUILT** (`donut`)
A thick ring representing **market cap $5.42t**, with **Revenue $253.49b** and
**Earnings $159.61b** drawn as tiny wedges inside it, plus P/E and P/S as large
numerals beside.
- *Why it is good:* the single most visceral way to show a multiple. You are not
  told the company is expensive, you *see* how little revenue sits inside the price.

---

## Growth & forecasts

### 2.1 Earnings and Revenue Growth Forecasts — past→forecast continuation · **BUILT** (`forecast`)
Two smooth series over 2024–29, vertical divider labelled *Past | Analysts
Forecasts*, reported region shaded, dots at the boundary, series-toggle chips
(Revenue · Earnings · Free Cash Flow · Cash From Op).

### 2.3 EPS Growth Forecasts — forecast line + **analyst range band** · **TODO**
Actual EPS (blue) continuing into forecast (teal) with a shaded band for the
**analyst range**, tooltip showing `EPS $15.989 · Analysts' EPS Range
$14.120–$18.800 · 16 Analysts`.
- *Why it is good:* shows the *dispersion* of the forecast, not just its midpoint.
  A wide band is itself the finding.

### 2.4 Future Return on Equity — dual-needle gauge · **PARTIAL** (`gauge` is single-value)
Gauge with coloured bands (red / amber 10–20% / green 20–40%) and **two needles**:
Company 70.8% and Industry 11.6%.
- *Added.* `gauge` takes an optional `compare` + `compareLab` second needle in
  `--s2`, drawn only when a sourced comparison value exists.

---

## Past performance

### 3.1 Revenue & Expenses Breakdown — **full Sankey with merging inputs** · **PARTIAL** (ours is a single trunk)
Segments merge *in* (Compute & Networking $228.44b + Graphics $25.05b → Revenue
$253.49b), then split *out* (→ Gross Profit + Cost of Sales; Gross Profit →
Earnings + Expenses; Expenses → G&A + R&D + Non-Operating). A **year scrubber**
sits above so you can walk the same diagram back through time.
- *Ours does one trunk with tributaries.* Theirs also merges revenue *sources* on
  the left, which is better for a company with real segments.

### 3.2 Earnings and Revenue History — multi-series area over a decade · **PARTIAL** (`indexed` is 2-series indexed)
Revenue / Earnings / Free Cash Flow as filled areas with series toggles and a
tooltip carrying **63.0% profit margin** inline.

### 3.3 Free Cash Flow vs Earnings — **waterfall from earnings to cash** · **BUILT** (`bridge`)
`Earnings $159.61b → +D&A $3.23b → +SBC $6.84b → −Net Working Capital $45.40b →
−Others $18.20b → Free Cash Flow $106.08b`. Green for adds, red for subtractions.
- *Why it is good:* the single best earnings-quality visual. It shows exactly what
  is added back to turn profit into cash — including stock compensation, which is a
  real cost to shareholders that never leaves the bank account.

### 3.5 / 3.6 / 3.7 ROE, ROA, ROCE — three gauges side by side · **BUILT** (`gauge`)
Company needle against industry needle, banded red / amber / green.

---

## Balance sheet

### 4.1 Financial Position Analysis — paired assets vs liabilities, short and long · **TODO (easy)**
Two groups (Short Term, Long Term), each with an Assets bar and a Liabilities bar.
Immediately answers "can they pay what is due?"

### 4.2 Debt to Equity History — debt vs equity areas over a decade · **PARTIAL** (`smallmult`)
With green-check verdicts underneath: *Debt Level · Reducing Debt (37.3% → 4.3%
over 5 years) · Debt Coverage (1483.4%) · Interest Coverage*.

### 4.3 Balance Sheet — **treemap** · **BUILT** (`treemap`)
Two panels, Assets and Liabilities + Equity, each a treemap sized by value, all
blocks green except **Debt in red**. Long Term & Other $123.1b, Cash & ST
Investments $53.2b, Receivables $40.7b, Inventory $25.8b, Physical $16.7b |
Equity $195.5b, Other Liabilities $42.4b, Accounts Payable $13.1b, **Debt $8.5b**.
- *Why it is good:* the whole balance sheet at a glance, and the one thing you
  should worry about is the only red block.

### Balance Sheet Health header — criteria checks + key-information panel · **BUILT-ish** (`snapshot` pips)
`Financial Health criteria checks 6/6` with six green ticks, a prose summary, then
two highlighted hero stats (Debt/Equity 4.33%, Debt $8.47b) above a plain table
(Interest coverage, Cash, Equity, Total liabilities, Total assets).

---

## Dividend / ownership / management

### 5.2 Dividend Yield vs Market — benchmark strip · **SKIP for PLTR** (pays none)
Company 0.4% against Market Bottom 25% (1.3%), Market Top 25% (4.0%), Industry
Average (0.5%) and a 3-year Forecast (0.5%). Good generic "where do you sit"
pattern; reuse the idea for any yield-style metric.

### 7.2 Ownership Breakdown — single stacked bar with leader lines · **TODO (easy)**
One horizontal bar segmented State/Government 0.109% · Private Companies 1.36% ·
Individual Insiders 3.91% · General Public 26.2% · **Institutions 68.5%**, each
labelled above with share counts on leader lines.

### Insider Trading Volume — sold vs bought, by recency bucket · **BUILT** (`insider`)
Rows for 0–3, 3–6, 6–9, 9–12 months with **Shares sold** (orange, extending left)
against **Shares bought** (green), each row carrying person/company icons, counts,
share totals and an approximate dollar value. Verdict beneath: *"insiders have
only sold shares in the past 3 months."*
- *Solved:* we parse SEC Form 4 XML directly. Transaction codes matter — only
  **S** (open-market sale) and **P** (open-market purchase) are decisions to buy or
  sell; **M/C** (exercise, conversion), **A** (grant) and **F** (tax withholding) are
  not, and counting them inflates the total. The aggregates cannot be text-matched
  against any one filing, so `audit_insider_aggregates` re-parses every cached XML
  and recomputes them. Always state the 10b5-1 share: 45 of 57 PLTR filings cite a
  pre-set plan, which makes "scheduled" the fair reading of most of the selling.

### 6.1 CEO Compensation Analysis — pay vs company earnings · **SKIP**
Total Compensation area against Salary and a dotted **Company Earnings** line.
Governance-interesting, not decision-critical for this format.

### 8.2 Number of Employees — single area series · **SKIP as-is**
Better as **revenue per employee** — a real efficiency metric — than as a headcount
line.

---

## Framing devices worth copying regardless of chart

- **Numbered sections** (`1.1`, `3.3`, `4.2`) in a lighter weight beside the title.
  Makes a long report feel navigable. Our deck numbers slides already.
- **A verdict sentence under every chart**, prefixed by a green ✓ or red ✗ and a
  bolded label: *"**Reducing Debt:** NVDA's debt to equity ratio has reduced from
  37.3% to 4.3% over the past 5 years."* This is exactly our "why it matters" band,
  and their green/red prefix is a good pattern for our `twocol`.
- **Series-toggle chips** below charts (Revenue · Earnings · Free Cash Flow). Not
  useful for a linear recorded deck, but good on the Terminal dashboard.
- **A tooltip that carries the derived ratio**, not just the raw values — *"63.0%
  profit margin"* sits inside the revenue/earnings tooltip.
- **A time scrubber above a static diagram** (the Sankey), so one visual becomes ten.
- **Hero stat pairs** with a coloured left rule, above a plain supporting table.

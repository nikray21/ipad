# FA reference — thresholds, tag map, reverse DCF

## Interpretation thresholds

These are starting points, not verdicts. Always compare a company against **its
own history** before against these bands — a 12% operating margin is excellent in
distribution and poor in software.

### Growth & revenue quality
| Metric | Weak | Fine | Strong |
|---|---|---|---|
| Revenue growth YoY | <3% | 3–10% | >10% |
| Operating leverage | op growth < rev growth | roughly equal | op growth > rev growth |
| Revenue concentration | top customer >20% | 10–20% | diversified |

### Profitability
| Metric | Weak | Fine | Strong |
|---|---|---|---|
| Gross margin | <25% | 25–50% | >50% |
| Operating margin | <8% | 8–20% | >20% |
| ROIC | <8% (below most WACCs) | 8–15% | >15% |
| ROIC − WACC | negative = destroying value | ~0 | positive and widening |

**ROE is unusable when equity is negative or heavily buyback-depleted.** DaVita
prints ROE of 81% on *negative* book value. Report ROIC instead and say why.

### Solvency
| Metric | Danger | Watch | Comfortable |
|---|---|---|---|
| Net debt / EBITDA | >4x | 2.5–4x | <2.5x |
| Interest coverage (EBIT/interest) | <2x | 2–5x | >5x |
| Current ratio | <1.0 | 1.0–1.5 | >1.5 |
| Altman Z (public mfr) | <1.8 distress | 1.8–3.0 grey | >3.0 safe |

Altman Z assumes a manufacturer. For asset-light or financial businesses it is
indicative only — report it with that caveat or not at all.

**Leases are debt.** Post-ASC 842 operating lease liabilities sit on the balance
sheet; any credit analysis that omits them understates leverage. The engine adds
`OperatingLeaseLiability{Current,Noncurrent}` to borrowings.

### Cash conversion
| Metric | Red flag | Healthy |
|---|---|---|
| FCF / net income | <60% persistently | 80–120% |
| Accrual ratio ((NI−CFO)/assets) | >5% | near zero or negative |
| Receivable days rising while revenue flat | yes = pull-forward risk | stable |
| SBC / revenue | >10% | <5% |
| Capex intensity | rising with flat revenue | stable or falling |

### Valuation
Compute **both** equity and enterprise multiples. A low P/E on a levered balance
sheet is leverage, not cheapness — EV/EBITDA will show it.

| Metric | Note |
|---|---|
| FCF yield | the cleanest single number; >8% is genuinely cheap if the FCF is durable |
| EV/EBITDA | compare to the company's own 5-year range first |
| P/E vs forward P/E | a large gap means the market expects a big change — find out what |
| EV/Sales | only useful for pre-profit or margin-inflecting businesses |

## XBRL tag traps

| Concept | Trap |
|---|---|
| Revenue | filers use `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, or `…IncludingAssessedTax`. The engine reports which one it used — never compare two companies on different tags without checking |
| Net income | `NetIncomeLoss` is **attributable to parent**; `ProfitLoss` **includes noncontrolling interests**. For DVA these differ by ~30% |
| Q4 | no standalone Q4 filing exists. Q4 = FY − 9M cumulative. Always reconcile |
| Cash flow | 10-Q cash-flow statements are **year-to-date**, not quarterly. Durations run ~90 / ~181 / ~273 / ~365 days |
| Debt | `LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities` already contains current maturities — do not add the current tag on top |
| Restatements | keep the fact with the **latest `filed` date** for a given period |

## Reverse DCF — what is the price assuming?

More useful than a forward DCF, because it removes your own growth guess.

1. Take current EV and TTM FCF from the engine.
2. Assume a discount rate (10% is a reasonable equity default; higher if levered
   above 4x net debt/EBITDA) and a terminal growth of 2.5%.
3. Solve for the FCF growth rate over 10 years that makes DCF = current EV.
4. Compare that implied rate to the company's actual 3–5 year FCF CAGR.

```
implied growth  >  historical growth   ->  price assumes acceleration; ask why
implied growth  ~= historical growth   ->  fairly priced on trend
implied growth  <  historical growth   ->  price assumes deterioration; the
                                           opportunity is here IF you disagree
```

State the implied number explicitly. "DVA at 19.2B EV on 1.6B FCF is discounting
roughly flat cash flow forever" is an analytical claim someone can argue with;
"the stock looks cheap" is not.

## Reaction-vs-results analysis

The highest-signal cheap test available. For the last 6–8 filings:

```python
# filing dates
https://data.sec.gov/submissions/CIK##########.json  ->  filings.recent
# then measure day-1 and day-3 price change from the day before the filing
```

Then tabulate results growth beside the reaction. Patterns worth naming:

- **Good numbers sold** → the move is about guidance or expectations, not results.
  Say so and stop; do not invent the reason.
- **Bad numbers bought** → expectations were already below reality; often the
  better setup.
- **Reaction size growing over successive quarters** → positioning is crowded and
  the stock is becoming a coin flip around events.

## Handoff

This skill judges the business. For whether to *trade* it — entry, the stop
(level − 1.5×ATR), position size ($risk ÷ stop distance), and whether the setup is
a good instance of the 6-step playbook — read the `technical-analysis` skill.
Fundamental attractiveness is not a trade signal.

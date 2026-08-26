# PDT-25K — sources

Every factual claim in the deck, and where it was verified. Checked 2026-08-26.
Nothing here was written from recall; each line was confirmed by live search or
by fetching the primary document.

## The rule change

| Claim | Source |
|---|---|
| SEC approved the amendments to FINRA Rule 4210 on **April 14, 2026** (Securities Exchange Act Release No. 105226) | [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10) — primary. Note: several law-firm client alerts say April 15; the FINRA notice itself says April 14, so the deck leads with the **effective** date instead, which is uncontested. |
| Amendments **effective June 4, 2026** ("45 days from publication of this Notice") | [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10) |
| Eliminated: the pattern-day-trader designation, the day-trade count, day-trading buying power, and the **$25,000** minimum equity requirement (in place since 2001) | [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10); [SR-FINRA-2025-017 / 34-105226](https://www.sec.gov/files/rules/sro/finra/2026/34-105226.pdf) |
| Replaced by an **intraday margin standard**: members determine an intraday margin deficit per account; deficits satisfied "as promptly as possible" | [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10) |
| **90-day freeze** on accounts with repeated failure to satisfy an intraday deficit within **five business days** | [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10) |
| Firms may phase in implementation over 18 months, ending **October 20, 2027** | [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10); [WilmerHale client alert](https://www.wilmerhale.com/en/insights/client-alerts/20260423-sec-approves-amendments-to-finra-rule-4210-replacing-day-trading-margin-requirements-with-a-modernized-intraday-margin-standard) |
| Broker rollout: Webull, Lightspeed, Cobra, tastytrade, Robinhood, Fidelity day one (June 4); Schwab June 8; E*TRADE June 9 | [DayTradingToolkit 2026 guide](https://daytradingtoolkit.com/market-insights/pdt-rule-eliminated-2026-complete-guide); [E*TRADE](https://us.etrade.com/knowledge/library/margin/pattern-day-trading-rule-change); [Schwab](https://www.schwab.com/learn/story/sec-approves-scrapping-25000-day-trader-minimum) |

## The floors that did not move — the deck's central finding

| Claim | Source |
|---|---|
| The **$2,000 minimum equity** to open a margin account is a separate provision of Rule 4210 and was **not** part of the repeal | [FINRA Interpretations of Rule 4210, valid from June 4 2026](https://www.finra.org/rules-guidance/guidance/interps-4210-202606); [FINRA Rule 4210](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210) |
| Stocks, ETFs and options settle **T+1** (industry moved off T+2 in May 2024) | [Fidelity](https://www.fidelity.com/learning-center/trading-investing/trading/avoiding-cash-trading-violations); [Schwab](https://www.schwab.com/learn/story/avoid-these-violations-when-trading-cash) |
| A **good-faith violation** = buying with unsettled funds in a cash account and selling that position before the funds settle | [Fidelity](https://www.fidelity.com/learning-center/trading-investing/trading/avoiding-cash-trading-violations); [E*TRADE](https://us.etrade.com/knowledge/library/stocks/understanding-cash-account-violations); [tastytrade](https://support.tastytrade.com/support/s/solutions/articles/43000435231) |
| **Three GFVs in a rolling 12 months → 90-day restriction** to settled cash; first two are typically warnings | [Firstrade](https://www.firstrade.com/resources/guides/margin/margin-good-faith-violation-90-day-restriction-scenarios); [Fidelity](https://www.fidelity.com/learning-center/trading-investing/trading/avoiding-cash-trading-violations) |

## The odds

| Claim | Source |
|---|---|
| **97%** of those who persisted more than 300 days lost money; only 1.1% earned more than the Brazilian minimum wage | Chague, De-Losso & Giovannetti, *Day Trading for a Living?* — [SSRN 3423101](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101) |
| Fewer than **1%** of Taiwanese day traders were predictably profitable net of fees (15-year population study) | Barber, Lee, Liu & Odean — summarized in [Current Market Valuation](https://www.currentmarketvaluation.com/posts/the-data-on-day-trading.php) |
| The PDT rule was a FINRA rule and therefore never applied in Brazil | FINRA governs US broker-dealers; the rule text lives in the [FINRA rulebook](https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210) |

## Deliberately NOT claimed

- **"Fractional shares cannot carry stop-loss or bracket orders."** Checked and
  **rejected as a blanket claim** — it is broker-dependent. TradersPost restricts
  fractional orders to day market orders with no stop or take-profit; Alpaca
  supports market, limit, stop and stop-limit on fractional; DriveWealth sits in
  between. The deck's slide-10 notes therefore say order-type support *varies by
  broker* and tell the viewer to check theirs, rather than asserting a universal
  rule.
- **No claim that the repeal makes trading safer or easier.** The deck argues the
  opposite, and the odds slide is there specifically to prevent that reading.

## Model assumptions (labelled as such on screen)

These are not sourced facts — they are the worked example, and every downstream
figure in the deck is computed from them:

- `RISK_PCT = 2%` of the account per trade (the channel's existing rule)
- `STOP_PCT = 5%` stop distance from entry
- `RR = 2` — target at twice the risk
- `SHARE_PX = $180` — illustrative share price for the sizing/granularity slide

Position size = risk ÷ stop distance = **40% of the account**. Change either
percentage in the deck source and all 45 derived figures across slides 8–11
update themselves — verified by mutation test.

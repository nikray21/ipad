# IREN Limited (IREN) — where every number came from

Deck built 2026-08-22T12:22:06+00:00.

Two checks stand behind this file:

- `python3 scripts/audit_deck.py DVA` — the deck's arithmetic is self-consistent.
- `python3 scripts/validate_facts.py DVA` — every figure below was found in the document it is attributed to.

## SEC filings

- **8k-jul20** — 8-K EX-99.1 — $2.8bn AI contract haul, ARR target raised to $4bn+, filed Jul 20 2026  
  https://www.sec.gov/Archives/edgar/data/1878848/000114036126028871/ef20078253_ex99-1.htm
- **8k-q3fy26** — 8-K EX-99.1 — Q3 FY26 results (quarter ended Mar 31 2026), filed May 8 2026  
  https://www.sec.gov/Archives/edgar/data/1878848/000187884826000025/irenreportsq3fy26results.htm
- **10q-q3fy26** — 10-Q for the quarter ended March 31 2026, filed May 8 2026  
  https://www.sec.gov/Archives/edgar/data/1878848/000187884826000026/iren-20260331.htm
- **8k-q2fy26** — 8-K EX-99.1 — Q2 FY26 results (quarter ended Dec 31 2025), filed Feb 5 2026  
  https://www.sec.gov/Archives/edgar/data/1878848/000187884826000014/a991irenreportsq2fy26res.htm
- **8k-q1fy26** — 8-K EX-99.1 — Q1 FY26 results (quarter ended Sep 30 2025), $9.7bn Microsoft contract, filed Nov 6 2025  
  https://www.sec.gov/Archives/edgar/data/1878848/000187884825000079/q1fy26resultspressreleas.htm
- **8k-fy25** — 8-K EX-99.1 — FY2025/Q4 results (quarter ended Jun 30 2025), filed Aug 28 2025  
  https://www.sec.gov/Archives/edgar/data/1878848/000187884825000062/ex991fy25pr.htm
- **8k-q3fy25** — 6-K EX-99.1 — Q3 FY25 results (quarter ended Mar 31 2025), filed May 14 2025  
  https://www.sec.gov/Archives/edgar/data/1878848/000187884825000043/q3fy25resultspressreleas.htm

## Live Terminal API

| Route | Source | Fetched | Age at build |
|---|---|---|---|
| `/api/quote/IREN` | Nasdaq real-time | 2026-08-22 12:21:57 | 0s |
| `/api/profile/IREN` | Nasdaq quote summary | 2026-08-22 12:22:02 | 0s |
| `/api/fundamentals/IREN` | SEC EDGAR XBRL companyfacts | 2026-08-22 12:22:03 | 0s |
| `/api/street/IREN` | Nasdaq analyst consensus | 2026-08-22 12:22:04 | 0s |
| `/api/estimates/IREN` | Nasdaq analyst estimates | 2026-08-22 12:22:06 | 0s |
| `/api/history/IREN` | Yahoo daily OHLCV | 2026-08-22 12:21:57 | 9s |

## Deliberately not used

- **The Terminal's `epsYears` / `ttmSeries`.** They overstate DVA's annual EPS by ~37% (FY2024 reads 14.71 against a reported 10.73; FY2023 10.38 against 7.42). The ratio tracks total net income over income *attributable to DaVita*, so the series appears to ignore noncontrolling interests — ~$311M/yr here. **This is a live Terminal bug** and it affects the dashboard's PRICE FOLLOWS EARNINGS chart for any company with large NCI. The deck builds its trailing-EPS series from the reported quarterly figures in the 8-Ks instead.
- **A trailing P/E.** The SEC XBRL pull has Q4'25 net income null, so it is not computable from our data. Every multiple in the deck is forward.

## Flagged disagreements

- Nasdaq's one-year target (`/api/profile`) is $80.5, while the analyst consensus mean (`/api/street`) is $77.89. The deck shows the consensus mean and names its source.
- `/api/fundamentals` reports $181M of Q2 repurchases; the 8-K reports $348M / 2.238M shares. The deck uses the filing figure. The XBRL gap is an open item.
- Coverage is thin: 10 analysts rate the stock, and the 2028 consensus rests on 2 estimates. The deck says so on the valuation slide.

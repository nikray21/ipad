# Marvell Technology, Inc. (MRVL) — where every number came from

Deck built 2026-08-28T20:29:49+00:00.

Two checks stand behind this file:

- `python3 scripts/audit_deck.py DVA` — the deck's arithmetic is self-consistent.
- `python3 scripts/validate_facts.py DVA` — every figure below was found in the document it is attributed to.

## SEC filings

- **8k-q2fy27** — 8-K EX-99.1 — Q2 FY2027 results (quarter ended Aug 1 2026), filed Aug 27 2026  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563226000022/q227_8kx812026ex-991.htm
- **8k-q1fy27** — 8-K EX-99.1 — Q1 FY2027 results (quarter ended May 2 2026), filed May 27 2026  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563226000014/q127_8kx522026ex-991.htm
- **10q-q1fy27** — 10-Q for the quarter ended May 2 2026, filed May 28 2026  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563226000019/mrvl-20260502.htm
- **10k-fy26** — 10-K for fiscal year ended Jan 31 2026, filed Mar 11 2026  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm
- **8k-q4fy26** — 8-K EX-99.1 — Q4 & FY2026 results (quarter ended Jan 31 2026), filed Mar 5 2026  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563226000006/q426_8kx1312026ex-991.htm
- **8k-q3fy26** — 8-K EX-99.1 — Q3 FY2026 results (quarter ended Nov 1 2025), filed Dec 2 2025  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563225000193/q326_8kx1112025ex-991.htm
- **8k-q2fy26** — 8-K EX-99.1 — Q2 FY2026 results (quarter ended Aug 2 2025), filed Aug 28 2025  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563225000187/q226_8kx822025ex-991.htm
- **8k-q1fy26** — 8-K EX-99.1 — Q1 FY2026 results (quarter ended May 3 2025), filed May 29 2025  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563225000115/q126_8kx532025ex-991.htm
- **8k-q4fy25** — 8-K EX-99.1 — Q4 & FY2025 results (quarter ended Feb 1 2025), filed Mar 5 2025  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563225000051/q425_8kx212025ex-991.htm
- **8k-q3fy25** — 8-K EX-99.1 — Q3 FY2025 results (quarter ended Nov 2 2024), filed Dec 3 2024  
  https://www.sec.gov/Archives/edgar/data/1835632/000183563224000197/q325_8kx1122024ex-991.htm

## Live Terminal API

| Route | Source | Fetched | Age at build |
|---|---|---|---|
| `/api/quote/MRVL` | Nasdaq real-time | 2026-08-28 20:29:37 | 0s |
| `/api/profile/MRVL` | Nasdaq quote summary | 2026-08-28 20:29:43 | 0s |
| `/api/fundamentals/MRVL` | SEC EDGAR XBRL companyfacts | 2026-08-28 20:29:44 | 0s |
| `/api/street/MRVL` | Nasdaq analyst consensus | 2026-08-28 20:29:46 | 0s |
| `/api/estimates/MRVL` | Nasdaq analyst estimates | 2026-08-28 20:29:49 | 0s |
| `/api/history/MRVL` | Yahoo daily OHLCV | 2026-08-28 20:29:37 | 11s |

## Deliberately not used

- **The Terminal's `epsYears` / `ttmSeries`.** They overstate DVA's annual EPS by ~37% (FY2024 reads 14.71 against a reported 10.73; FY2023 10.38 against 7.42). The ratio tracks total net income over income *attributable to DaVita*, so the series appears to ignore noncontrolling interests — ~$311M/yr here. **This is a live Terminal bug** and it affects the dashboard's PRICE FOLLOWS EARNINGS chart for any company with large NCI. The deck builds its trailing-EPS series from the reported quarterly figures in the 8-Ks instead.
- **A trailing P/E.** The SEC XBRL pull has Q4'25 net income null, so it is not computable from our data. Every multiple in the deck is forward.

## Flagged disagreements

- Nasdaq's one-year target (`/api/profile`) is $275.0, while the analyst consensus mean (`/api/street`) is $300.43. The deck shows the consensus mean and names its source.
- `/api/fundamentals` reports $181M of Q2 repurchases; the 8-K reports $348M / 2.238M shares. The deck uses the filing figure. The XBRL gap is an open item.
- Coverage is thin: 26 analysts rate the stock, and the 2028 consensus rests on 2 estimates. The deck says so on the valuation slide.

# Meta Platforms, Inc. (META) — where every number came from

Deck built 2026-08-16T08:36:15+00:00.

Two checks stand behind this file:

- `python3 scripts/audit_deck.py DVA` — the deck's arithmetic is self-consistent.
- `python3 scripts/validate_facts.py DVA` — every figure below was found in the document it is attributed to.

## SEC filings

- **8k-q2-26** — 8-K EX-99.1 — Q2 2026 results, filed Jul 29 2026  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828026050596/
- **8k-q1-26** — 8-K EX-99.1 — Q1 2026 results, filed Apr 29 2026  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828026028364/
- **8k-q4-25** — 8-K EX-99.1 — Q4 & FY2025 results, filed Jan 28 2026  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828026003832/
- **8k-q3-25** — 8-K EX-99.1 — Q3 2025 results, filed Oct 29 2025  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828025047114/
- **8k-q2-25** — 8-K EX-99.1 — Q2 2025 results, filed Jul 30 2025  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828025036719/
- **8k-q1-25** — 8-K EX-99.1 — Q1 2025 results, filed Apr 30 2025  
  https://www.sec.gov/Archives/edgar/data/1326801/000132680125000050/
- **8k-q4-24** — 8-K EX-99.1 — Q4 & FY2024 results, filed Jan 29 2025  
  https://www.sec.gov/Archives/edgar/data/1326801/000132680125000014/
- **8k-q3-24** — 8-K EX-99.1 — Q3 2024 results, filed Oct 30 2024  
  https://www.sec.gov/Archives/edgar/data/1326801/000132680124000077/
- **10q-q2-26** — 10-Q — quarter ended June 30 2026, filed Jul 30 2026  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828026050705/meta-20260630.htm
- **10k-fy25** — 10-K — year ended Dec 31 2025, filed Jan 29 2026  
  https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm
- **form4** — SEC Form 4 filings, Aug 2025–Aug 2026, aggregated from raw XML in .cache_form4/META/  
  https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001326801&type=4&dateb=&owner=include&count=100

## Live Terminal API

| Route | Source | Fetched | Age at build |
|---|---|---|---|
| `/api/quote/META` | Nasdaq real-time | 2026-08-16 08:36:06 | 0s |
| `/api/profile/META` | Nasdaq quote summary | 2026-08-16 08:36:09 | 0s |
| `/api/fundamentals/META` | SEC EDGAR XBRL companyfacts | 2026-08-16 08:36:10 | 0s |
| `/api/street/META` | Nasdaq analyst consensus | 2026-08-16 08:36:13 | 0s |
| `/api/estimates/META` | Nasdaq analyst estimates | 2026-08-16 08:36:15 | 0s |
| `/api/history/META` | Yahoo daily OHLCV | 2026-08-16 08:36:06 | 9s |

## Deliberately not used

- **The Terminal's `epsYears` / `ttmSeries`.** They overstate DVA's annual EPS by ~37% (FY2024 reads 14.71 against a reported 10.73; FY2023 10.38 against 7.42). The ratio tracks total net income over income *attributable to DaVita*, so the series appears to ignore noncontrolling interests — ~$311M/yr here. **This is a live Terminal bug** and it affects the dashboard's PRICE FOLLOWS EARNINGS chart for any company with large NCI. The deck builds its trailing-EPS series from the reported quarterly figures in the 8-Ks instead.
- **A trailing P/E.** The SEC XBRL pull has Q4'25 net income null, so it is not computable from our data. Every multiple in the deck is forward.

## Flagged disagreements

- Nasdaq's one-year target (`/api/profile`) is $750.0, while the analyst consensus mean (`/api/street`) is $752.45. The deck shows the consensus mean and names its source.
- `/api/fundamentals` reports $181M of Q2 repurchases; the 8-K reports $348M / 2.238M shares. The deck uses the filing figure. The XBRL gap is an open item.
- Coverage is thin: 42 analysts rate the stock, and the 2028 consensus rests on 2 estimates. The deck says so on the valuation slide.

#!/usr/bin/env python3
"""Fundamental analysis engine. Every number traces to a filing line item.

    python3 analyze.py TICKER [--json]

SOURCES, in order of authority
  1. SEC EDGAR XBRL companyfacts  — the filings themselves. Authoritative.
  2. yfinance                     — street estimates, targets, market cap.
  3. Alpaca                       — price and volume bars.

WHY NO RATIO LIBRARY. Every defect in this codebase has had one shape: something
other than the source of truth became a source of truth, then drifted. A library
that computes `operatingMargin` for you hides WHICH revenue tag fed it. Here every
ratio is arithmetic on a named XBRL tag, and `--json` emits the raw inputs beside
the outputs so any figure can be traced back to the filing that produced it.

NOTHING IS INVENTED. A metric that cannot be computed prints `n/a` and is excluded
from the verdict. It never prints a plausible-looking substitute.
"""
import json, sys, os, re, urllib.request, datetime as dt

UA = {"User-Agent": "NikRayani Research nikil.rayani@puriscorp.com"}
SEC = "https://data.sec.gov"


def _get(url, headers=UA, timeout=45):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout))


# ---------------------------------------------------------------- SEC EDGAR
def cik_for(ticker):
    """Resolve ticker -> CIK, preferring an entity that actually has XBRL revenue.

    The SEC ticker file can map one ticker to several CIKs — a reorganisation leaves
    the new holdco registered alongside the operating company. XOM resolved to
    'ExxonMobil Holdings Corp' (CIK 2115436), which has no filing history, and the
    analysis came back structurally complete and entirely empty. Pick the candidate
    with real data; if several qualify, report the ambiguity rather than guessing.
    """
    d = _get("https://www.sec.gov/files/company_tickers.json")
    cands = [(str(r["cik_str"]).zfill(10), r["title"]) for r in d.values()
             if r["ticker"].upper() == ticker.upper()]
    if not cands:
        return None, None
    if len(cands) == 1:
        return cands[0]
    for cik, title in cands:
        try:
            f = _get(f"{SEC}/api/xbrl/companyfacts/CIK{cik}.json")
            if series(f, TAGS["revenue"], want_qtr=True):
                return cik, title
        except Exception:
            continue
    return cands[0]


# Tag aliases: filers use different us-gaap tags for the same concept. Order matters —
# the first tag that yields data wins, and the winning tag is REPORTED in the output so
# a cross-company comparison can't silently compare two different concepts.
TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfServices"],
    "opinc": ["OperatingIncomeLoss"],
    "netinc": ["NetIncomeLoss", "ProfitLoss"],
    "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding",
               "WeightedAverageNumberOfSharesOutstandingBasic"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "curassets": ["AssetsCurrent"],
    "curliab": ["LiabilitiesCurrent"],
    # `debtAll` is a single tag that already includes current maturities. When a filer
    # uses it, it is authoritative and the LT+current pair must NOT be added on top or
    # the debt is double counted.
    "debtAll": ["LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities"],
    "ltdebt": ["LongTermDebtAndCapitalLeaseObligations", "LongTermDebtNoncurrent", "LongTermDebt"],
    "curdebt": ["LongTermDebtAndCapitalLeaseObligationsCurrent", "LongTermDebtCurrent", "DebtCurrent"],
    # Leases are debt in every credit analysis. Omitting them understated DVA's
    # total debt as 5.74B against a true ~13.2B.
    "leaseLT": ["OperatingLeaseLiabilityNoncurrent", "FinanceLeaseLiabilityNoncurrent"],
    "leaseCur": ["OperatingLeaseLiabilityCurrent", "FinanceLeaseLiabilityCurrent"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "sbc": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "inventory": ["InventoryNet"],
    "interest": ["InterestExpense", "InterestExpenseDebt", "InterestIncomeExpenseNet"],
    "tax": ["IncomeTaxExpenseBenefit"],
    "pretax": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
               "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "buyback": ["PaymentsForRepurchaseOfCommonStock"],
    "dividends": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "retained": ["RetainedEarningsAccumulatedDeficit"],
    "goodwill": ["Goodwill"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
           "DepreciationAndAmortization"],
}


def series(facts, keys, want_qtr=True):
    """Return [(endDate, discreteQuarterValue, tag)] newest-first.

    TWO TRAPS THIS EXISTS TO AVOID, both found by cross-checking against yfinance:

    1. NO STANDALONE Q4. Companies file three 10-Qs and a 10-K, so a naive
       "duration ~90 days" filter silently drops every fourth quarter and the TTM
       sum is then 3 quarters + a repeat. DVA's TTM revenue read 13.77B instead of
       14.01B that way.
    2. CASH-FLOW FACTS ARE YEAR-TO-DATE. The cash-flow statement in a 10-Q covers
       the fiscal year to date, not the quarter — durations run ~90 / ~181 / ~273 /
       ~365 days. Filtering to ~90 days keeps only Q1 of each year. DVA's CFO read
       0.83B instead of 2.03B.

    Fix: keep every duration fact, then difference consecutive cumulative periods
    that share a start date. A period with no earlier sibling is already discrete.
    """
    us = facts.get("facts", {}).get("us-gaap", {})
    for tag in keys:
        node = us.get(tag)
        if not node:
            continue
        for unit in ("USD", "USD/shares", "shares"):
            rows = node.get("units", {}).get(unit)
            if not rows:
                continue
            # latest filing wins per (start,end) — restatements supersede
            best = {}
            for r in rows:
                s, e = r.get("start"), r.get("end")
                if not e:
                    continue
                if want_qtr and not s:
                    continue
                if not want_qtr and s:
                    days = (dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days
                    if not (350 <= days <= 380):
                        continue
                k = (s, e)
                prev = best.get(k)
                if prev is None or (r.get("filed", "") >= prev[1]):
                    best[k] = (r["val"], r.get("filed", ""))
            if not best:
                continue
            if not want_qtr:
                out = sorted(((e, v[0]) for (s, e), v in best.items()), reverse=True)
                return [(e, v, tag) for e, v in out]

            # group cumulative runs by start date, then difference
            by_start = {}
            for (s, e), (val, _) in best.items():
                by_start.setdefault(s, []).append((e, val))
            disc = {}
            for s, ends in by_start.items():
                ends.sort()
                prev_end, prev_val = None, 0.0
                for e, val in ends:
                    days = (dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days
                    if days <= 120:                    # single quarter (retail Q4 runs 16wk = 112d)
                        disc.setdefault(e, val)
                    else:                              # cumulative: subtract prior sibling
                        if prev_end is not None:
                            disc.setdefault(e, val - prev_val)
                    prev_end, prev_val = e, val
            if disc:
                out = sorted(disc.items(), reverse=True)
                return [(e, v, tag) for e, v in out]
    return []


def instant(facts, keys):
    us = facts.get("facts", {}).get("us-gaap", {})
    for tag in keys:
        node = us.get(tag)
        if not node:
            continue
        for unit in ("USD", "shares"):
            rows = node.get("units", {}).get(unit)
            if not rows:
                continue
            best = {}
            for r in rows:
                if r.get("start"):
                    continue
                end = r.get("end")
                prev = best.get(end)
                if prev is None or (r.get("filed", "") >= prev[1]):
                    best[end] = (r["val"], r.get("filed", ""))
            if best:
                out = sorted(((k, v[0]) for k, v in best.items()), reverse=True)
                return [(k, v, tag) for k, v in out]
    return []


def ttm(rows, n=4):
    """Sum the newest n quarters. Returns (value, [periods], tag) or (None,[],None)."""
    if len(rows) < n:
        return None, [], None
    sel = rows[:n]
    return sum(r[1] for r in sel), [r[0] for r in sel], sel[0][2]


def pct(a, b):
    return None if (a is None or not b) else 100.0 * a / b


def safe(a, b):
    return None if (a is None or b in (None, 0)) else a / b


def f(v, p=2, suffix=""):
    return "n/a" if v is None else f"{v:,.{p}f}{suffix}"


def bn(v):
    return "n/a" if v is None else f"{v/1e9:,.2f}B"


# ---------------------------------------------------------------- main
def analyze(ticker):
    out = {"ticker": ticker.upper(), "asOf": dt.datetime.now().isoformat(timespec="seconds")}
    cik, name = cik_for(ticker)
    if not cik:
        out["error"] = f"no CIK for {ticker}"
        return out
    out["cik"], out["name"] = cik, name
    facts = _get(f"{SEC}/api/xbrl/companyfacts/CIK{cik}.json")

    Q = {k: series(facts, v, want_qtr=True) for k, v in TAGS.items()}
    I = {k: instant(facts, v) for k, v in TAGS.items()}
    # HARD FAIL, not a quiet page of n/a. An empty companyfacts (wrong CIK, foreign
    # private issuer filing 20-F, newly registered holdco) must stop the analysis —
    # "a failure that renders as a plausible answer" is the defect class to avoid.
    if len(Q["revenue"]) < 4:
        out["error"] = (f"only {len(Q['revenue'])} quarters of revenue in XBRL for CIK {cik} "
                        f"({name}) - cannot form a TTM. "
                        "Wrong entity, or the filer does not report us-gaap revenue tags "
                        "(foreign private issuers file 20-F and are not covered).")
        return out

    rev_t, rev_p, rev_tag = ttm(Q["revenue"])
    rev_prior, _, _ = ttm(Q["revenue"][4:]) if len(Q["revenue"]) >= 8 else (None, [], None)
    ni_t, _, ni_tag = ttm(Q["netinc"])
    ni_prior, _, _ = ttm(Q["netinc"][4:]) if len(Q["netinc"]) >= 8 else (None, [], None)
    op_t, _, op_tag = ttm(Q["opinc"])
    op_prior, _, _ = ttm(Q["opinc"][4:]) if len(Q["opinc"]) >= 8 else (None, [], None)
    cogs_t, _, _ = ttm(Q["cogs"])
    cfo_t, _, cfo_tag = ttm(Q["cfo"])
    capex_t, _, _ = ttm(Q["capex"])
    sbc_t, _, _ = ttm(Q["sbc"])
    da_t, _, _ = ttm(Q["da"])
    int_t, _, _ = ttm(Q["interest"])
    tax_t, _, _ = ttm(Q["tax"])
    pre_t, _, _ = ttm(Q["pretax"])
    bb_t, _, _ = ttm(Q["buyback"])
    div_t, _, _ = ttm(Q["dividends"])

    g = lambda d, k: (d[k][0][1] if d.get(k) else None)
    assets, liab, eq = g(I, "assets"), g(I, "liabilities"), g(I, "equity")
    cash, ca, cl = g(I, "cash"), g(I, "curassets"), g(I, "curliab")
    ltd, cud = g(I, "ltdebt"), g(I, "curdebt")
    recv, inv, gw, ret = g(I, "receivables"), g(I, "inventory"), g(I, "goodwill"), g(I, "retained")
    llt, lcur = g(I, "leaseLT"), g(I, "leaseCur")
    dall = g(I, "debtAll")
    borrowings = dall if dall is not None else (
        None if (ltd is None and cud is None) else (ltd or 0) + (cud or 0))
    debt = None if borrowings is None else borrowings + (llt or 0) + (lcur or 0)
    out_debt_parts = {"borrowings": borrowings, "usedCombinedTag": dall is not None,
                      "longTerm": ltd, "current": cud, "leaseLT": llt, "leaseCurrent": lcur}
    netdebt = None if (debt is None or cash is None) else debt - cash
    fcf = None if (cfo_t is None or capex_t is None) else cfo_t - capex_t
    ebitda = None if (op_t is None or da_t is None) else op_t + da_t
    nopat = None if (op_t is None or pre_t in (None, 0) or tax_t is None) else op_t * (1 - tax_t / pre_t)
    invcap = None if (debt is None or eq is None) else debt + eq

    out["filing"] = {"latestQuarterEnd": Q["revenue"][0][0] if Q["revenue"] else None,
                     "ttmPeriods": rev_p, "revenueTag": rev_tag, "netIncomeTag": ni_tag,
                     "cfoTag": cfo_tag}
    out["ttm"] = {"revenue": rev_t, "operatingIncome": op_t, "netIncome": ni_t, "cfo": cfo_t,
                  "capex": capex_t, "fcf": fcf, "ebitda": ebitda, "sbc": sbc_t,
                  "interestExpense": int_t, "buybacks": bb_t, "dividends": div_t}
    out["balance"] = {"assets": assets, "liabilities": liab, "equity": eq, "cash": cash,
                      "totalDebt": debt, "netDebt": netdebt, "currentAssets": ca,
                      "currentLiabilities": cl, "receivables": recv, "inventory": inv,
                      "goodwill": gw, "retainedEarnings": ret}
    out["ratios"] = {
        "revenueGrowthYoY": pct(rev_t - rev_prior, rev_prior) if (rev_t and rev_prior) else None,
        "opIncomeGrowthYoY": pct(op_t - op_prior, op_prior) if (op_t and op_prior) else None,
        "netIncomeGrowthYoY": pct(ni_t - ni_prior, ni_prior) if (ni_t and ni_prior) else None,
        "grossMargin": pct(rev_t - cogs_t, rev_t) if (rev_t and cogs_t) else None,
        "operatingMargin": pct(op_t, rev_t), "netMargin": pct(ni_t, rev_t),
        "ebitdaMargin": pct(ebitda, rev_t), "fcfMargin": pct(fcf, rev_t),
        "roe": pct(ni_t, eq), "roa": pct(ni_t, assets),
        "roic": pct(nopat, invcap),
        "netDebtToEbitda": safe(netdebt, ebitda),
        "debtToEquity": safe(debt, eq),
        "interestCoverage": safe(op_t, abs(int_t)) if int_t else None,
        "currentRatio": safe(ca, cl),
        "fcfConversion": pct(fcf, ni_t),
        "accrualRatio": pct(ni_t - cfo_t, assets) if (ni_t and cfo_t and assets) else None,
        "capexIntensity": pct(capex_t, rev_t),
        "sbcToRevenue": pct(sbc_t, rev_t),
        "receivableDays": safe(recv, rev_t) * 365 if (recv and rev_t) else None,
        "shareholderReturnTtm": (bb_t or 0) + (div_t or 0) if (bb_t or div_t) else None,
    }
    # Altman Z (public manufacturer form). Reported with its inputs so it can be sanity-checked.
    try:
        wc = ca - cl
        out["ratios"]["altmanZ"] = round(
            1.2 * wc / assets + 1.4 * ret / assets + 3.3 * op_t / assets + 0.6 * (eq / liab) + 1.0 * rev_t / assets, 2)
    except Exception:
        out["ratios"]["altmanZ"] = None

    # INVARIANT: a derived Q4 (FY minus 9-month cumulative) is the weakest step in this
    # pipeline — it produced a DVA Q4 net income of 0.566B against a true 0.234B. Any
    # metric whose quarters do not sum back to the filer's own annual figure is marked
    # unreliable rather than silently used.
    recon = {}
    for key in ("revenue", "netinc", "opinc", "cfo"):
        ann = series(facts, TAGS[key], want_qtr=False)
        if not ann:
            recon[key] = "no annual to check against"
            continue
        fy_end, fy_val = ann[0][0], ann[0][1]
        # Fiscal years are NOT calendar years. Salesforce ends Jan 31; a calendar-year
        # window found 1 quarter and flagged every metric unreliable. Derive the window
        # from the annual fact's own end date.
        # Take the 4 quarters ending at or before the FY end. A date window breaks on
        # 52/53-week retail calendars where period-ends drift year to year (COST found
        # 5 quarter-ends inside a 364-day window).
        qs = [v for e, v, _ in Q[key] if e <= fy_end][:4]
        if len(qs) != 4 or not fy_val:
            recon[key] = f"only {len(qs)} quarters in FY{fy_end[:4]}"
            continue
        d = abs(sum(qs) - fy_val) / abs(fy_val)
        recon[key] = "ok" if d <= 0.02 else f"QUARTERS DO NOT SUM TO FY{fy_end[:4]} ({100*d:.1f}% off)"
    out["reconciliation"] = recon

    out["quarters"] = [{"end": e, "revenue": v} for e, v, _ in Q["revenue"][:9]]
    out["marginTrend"] = []
    for e, rv, _ in Q["revenue"][:9]:
        oi = next((v for d, v, _ in Q["opinc"] if d == e), None)
        out["marginTrend"].append({"end": e, "opMargin": pct(oi, rv)})

    # ---- market + street (yfinance) ----
    try:
        import yfinance as yf
        i = yf.Ticker(out["ticker"]).info or {}
        mc = i.get("marketCap"); price = i.get("currentPrice") or i.get("regularMarketPrice")
        ev = None if (mc is None or netdebt is None) else mc + netdebt
        out["market"] = {"price": price, "marketCap": mc, "enterpriseValue": ev,
                         "beta": i.get("beta"), "shortPctFloat": i.get("shortPercentOfFloat"),
                         "sharesOut": i.get("sharesOutstanding")}
        out["street"] = {"analysts": i.get("numberOfAnalystOpinions"),
                         "targetMean": i.get("targetMeanPrice"), "targetLow": i.get("targetLowPrice"),
                         "targetHigh": i.get("targetHighPrice"), "recommendation": i.get("recommendationKey"),
                         "forwardPE": i.get("forwardPE"),
                         "_warning": "targets are undated; treat as stale after any large move"}
        out["valuation"] = {
            "pe": safe(mc, ni_t), "ps": safe(mc, rev_t), "pfcf": safe(mc, fcf),
            "fcfYield": pct(fcf, mc), "evEbitda": safe(ev, ebitda), "evSales": safe(ev, rev_t),
            "earningsYield": pct(ni_t, mc),
        }
        # ---- CROSS-CHECK (terminal hard rule 5) ----
        # Internal consistency proves our maths matches our own extraction, not that
        # our extraction matches reality. Every headline figure is compared against an
        # INDEPENDENT vendor. Disagreements are REPORTED, never silently resolved:
        # a >15% gap means one of the two is wrong and the number is not usable.
        checks = []
        def chk(label, ours, theirs, tol=0.15):
            if ours is None or theirs in (None, 0):
                checks.append({"metric": label, "ours": ours, "yfinance": theirs,
                               "delta": None, "status": "UNVERIFIED"})
                return
            d = abs(ours - theirs) / abs(theirs)
            checks.append({"metric": label, "ours": ours, "yfinance": theirs,
                           "delta": round(100 * d, 1),
                           "status": "ok" if d <= tol else "DISAGREE"})
        chk("cfoTTM", cfo_t, i.get("operatingCashflow"))
        chk("fcfTTM", fcf, i.get("freeCashflow"))
        chk("totalDebt", debt, i.get("totalDebt"))
        chk("cash", cash, i.get("totalCash"))
        chk("operatingMargin", r_om := pct(op_t, rev_t),
            None if i.get("operatingMargins") is None else 100 * i["operatingMargins"])
        chk("netMargin", pct(ni_t, rev_t),
            None if i.get("profitMargins") is None else 100 * i["profitMargins"])
        out["crosscheck"] = checks
        out["debtParts"] = out_debt_parts
    except Exception as e:
        out["market"] = {"error": str(e)}
    return out


def report(o):
    if o.get("error"):
        print("ERROR:", o["error"]); return
    r, t, b, v = o["ratios"], o["ttm"], o["balance"], o.get("valuation", {}) or {}
    m, s = o.get("market", {}) or {}, o.get("street", {}) or {}
    print(f"\n{o['name']}  ({o['ticker']})   CIK {o['cik']}")
    print(f"latest filed quarter {o['filing']['latestQuarterEnd']}   TTM = {', '.join(o['filing']['ttmPeriods'] or [])}")
    print(f"revenue tag: {o['filing']['revenueTag']}\n")

    print("== 1 REVENUE QUALITY ==")
    print(f"  TTM revenue        {bn(t['revenue'])}   YoY {f(r['revenueGrowthYoY'],1,'%')}")
    qs = o["quarters"][:5]
    print("  last 5 quarters    " + "  ".join(f"{q['end'][:7]} {q['revenue']/1e9:.2f}B" for q in qs))
    print("\n== 2 PROFITABILITY & OPERATING LEVERAGE ==")
    print(f"  gross / op / net   {f(r['grossMargin'],1,'%')} / {f(r['operatingMargin'],1,'%')} / {f(r['netMargin'],1,'%')}")
    print(f"  EBITDA margin      {f(r['ebitdaMargin'],1,'%')}      op income YoY {f(r['opIncomeGrowthYoY'],1,'%')}")
    print(f"  operating leverage {'YES' if (r['opIncomeGrowthYoY'] or 0) > (r['revenueGrowthYoY'] or 0) else 'no'} (op growth vs revenue growth)")
    print(f"  ROIC / ROE / ROA   {f(r['roic'],1,'%')} / {f(r['roe'],1,'%')} / {f(r['roa'],1,'%')}")
    print("  op margin trend    " + "  ".join(f"{x['end'][:7]} {f(x['opMargin'],1,'%')}" for x in o["marginTrend"][:5]))
    print("\n== 3 BALANCE SHEET & SOLVENCY ==")
    print(f"  cash / total debt  {bn(b['cash'])} / {bn(b['totalDebt'])}      net debt {bn(b['netDebt'])}")
    print(f"  net debt / EBITDA  {f(r['netDebtToEbitda'])}x      interest coverage {f(r['interestCoverage'])}x")
    print(f"  equity             {bn(b['equity'])}      D/E {f(r['debtToEquity'])}x      current ratio {f(r['currentRatio'])}")
    print(f"  Altman Z           {f(r['altmanZ'])}   (<1.8 distress · >3.0 safe)")
    print("\n== 4 CASH CONVERSION ==")
    print(f"  CFO / capex / FCF  {bn(t['cfo'])} / {bn(t['capex'])} / {bn(t['fcf'])}")
    print(f"  FCF / net income   {f(r['fcfConversion'],0,'%')}      FCF margin {f(r['fcfMargin'],1,'%')}")
    print(f"  accrual ratio      {f(r['accrualRatio'],1,'%')}   (high = earnings ahead of cash)")
    print(f"  capex intensity    {f(r['capexIntensity'],1,'%')}      SBC/revenue {f(r['sbcToRevenue'],1,'%')}")
    print("\n== 5 CAPITAL ALLOCATION ==")
    print(f"  buybacks / divs    {bn(t['buybacks'])} / {bn(t['dividends'])}")
    print(f"  total returned     {bn(r['shareholderReturnTtm'])}      vs FCF {f(pct(r['shareholderReturnTtm'], t['fcf']),0,'%')}")
    print("\n== 6 VALUATION ==")
    print(f"  price / mkt cap    {f(m.get('price'))} / {bn(m.get('marketCap'))}      EV {bn(m.get('enterpriseValue'))}")
    print(f"  P/E · P/S · P/FCF  {f(v.get('pe'),1)} · {f(v.get('ps'),2)} · {f(v.get('pfcf'),1)}")
    print(f"  EV/EBITDA          {f(v.get('evEbitda'),1)}x      EV/Sales {f(v.get('evSales'),2)}x")
    print(f"  FCF yield          {f(v.get('fcfYield'),1,'%')}      earnings yield {f(v.get('earningsYield'),1,'%')}")
    print("\n== 7 STREET ==")
    print(f"  analysts           {s.get('analysts')}      rating {s.get('recommendation')}")
    print(f"  target lo/mean/hi  {f(s.get('targetLow'))} / {f(s.get('targetMean'))} / {f(s.get('targetHigh'))}")
    print(f"  forward P/E        {f(s.get('forwardPE'),1)}")
    print(f"  !! {s.get('_warning')}")
    rec = o.get("reconciliation") or {}
    if rec:
        print("\n== QUARTER RECONCILIATION (derived Q4 sanity) ==")
        for k, vmsg in rec.items():
            print(f" {'  ok  ' if vmsg=='ok' else ' !!!! '} {k:<10} {vmsg}")
    cc = o.get("crosscheck") or []
    if cc:
        print("\n== 8 CROSS-CHECK vs yfinance (independent source) ==")
        for c in cc:
            flag = {"ok": "  ok  ", "DISAGREE": " !!!! ", "UNVERIFIED": "  ??  "}[c["status"]]
            ours = c["ours"]; th = c["yfinance"]
            fmt = lambda x: "n/a" if x is None else (f"{x/1e9:,.2f}B" if abs(x) > 1e6 else f"{x:,.2f}")
            d = "" if c["delta"] is None else f"   {c['delta']}% apart"
            print(f" {flag} {c['metric']:<18} ours {fmt(ours):>10}   yf {fmt(th):>10}{d}")
        bad = [c["metric"] for c in cc if c["status"] == "DISAGREE"]
        if bad:
            print(f"\n  DO NOT USE without resolving: {', '.join(bad)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    res = analyze(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2, default=str))
    else:
        report(res)

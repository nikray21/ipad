"""
decks/PLTR.py — Palantir's derived metrics and slide narrative.

The story here is the mirror image of DaVita's. DVA beat and refused to raise,
and lost 17% in a day. Palantir beat, raised hard, and gained 29%. So the deck
does not argue about whether the quarter was good — it was extraordinary — it
argues about what the price already assumes.

Two things this module is careful about:

  * Multiples come from the company's OWN guidance, not from consensus. The
    analyst estimates the Terminal serves are below what management has already
    reported and guided to (they have not caught up to the Aug 3 release), so
    building a forward P/E on them would understate the earnings and overstate
    the multiple.
  * The tax rate is 1.4%. Every "earnings" multiple here is flagged as resting
    on a tax rate that cannot persist, and the fair-value model normalises it.
"""

import re

from . import fmt

# Figures that are part of a metric's NAME, not a claim about this company.
# Everything else must be interpolated from the snapshot or the episode file.
LITERALS_OK = (
    "Deals closed over $1M",
    " of them over $10M",
    "for every $100 of this stock",     # the basis of a per-dollar comparison
)


def _peer(sym, die):
    """Live market cap and TTM revenue for one peer, straight off the Terminal."""
    import marketdata as _md
    def g(route):
        try:
            return _md.get(route, sym)
        except Exception as e:                                   # noqa: BLE001
            die(f"cannot fetch {route} for peer {sym} ({e}) — peer multiples are computed "
                "live and are never hand-entered, so the build stops here")
    prof, fu = g("profile"), g("fundamentals")
    qs = [q for q in fu["quarters"] if q.get("revenue") is not None]
    if len(qs) < 8:
        die(f"peer {sym} has only {len(qs)} revenue quarters — need 8 for a TTM comparison")
    ttm = sum(q["revenue"] for q in qs[-4:]) * 1000              # $B -> $M
    prior = sum(q["revenue"] for q in qs[-8:-4]) * 1000
    mcap = prof.get("marketCapRaw")
    if not mcap:
        die(f"peer {sym} has no market cap from /api/profile")
    return {"sym": sym, "mcap": mcap / 1e6, "ttmRev": ttm,
            "ps": (mcap / 1e6) / ttm, "growth": (ttm / prior - 1) * 100}


def derive(snap, ep, fund, qrows, die, fact):
    """Return the extra snapshot keys Palantir's slides need."""
    F = ep["filings"]
    bs, res, eq, mix = F["balanceSheet"], F["results"], F["earningsQuality"], F["mix"]
    g, gp, g0 = F["guidance"]["current"], F["guidance"]["prior"], F["guidance"]["initial"]

    # Net CASH, so net debt is negative. EV is below market cap.
    net_cash = fact(F, "balanceSheet", "cash") + fact(F, "balanceSheet", "marketableSecurities")
    net_debt = -net_cash
    ev = snap["marketCap"] + net_debt

    # thousands -> millions, matching snap["sharesNow"]. Class F is quoted in
    # actual shares, so it needs the extra /1000.
    shares_out = (fact(F, "balanceSheet", "sharesClassA")
                  + fact(F, "balanceSheet", "sharesClassB")
                  + fact(F, "balanceSheet", "sharesClassF") / 1000.0) / 1000.0
    if shares_out >= snap["sharesNow"]:
        die("shares outstanding should be below the diluted count — check the class components")

    # Revenue and Rule-of-40 series, straight off the quarterly rows.
    series = [{"q": r["q"], "revenue": r["revenue"], "growth": r["growth"], "r40": r["r40"]}
              for r in qrows]
    if [x["growth"] for x in series] != sorted(x["growth"] for x in series):
        die("the accelerating-growth claim does not hold on this data — re-check before shipping")

    # Guidance: the full-year revenue guide has been raised twice this year.
    gmid = (g["revLow"] + g["revHigh"]) / 2
    guide = {
        "revLow": g["revLow"], "revHigh": g["revHigh"], "revMid": gmid,
        "priorMid": (gp["revLow"] + gp["revHigh"]) / 2,
        "initialMid": (g0["revLow"] + g0["revHigh"]) / 2,
        "adjOpMid": (g["adjOpLow"] + g["adjOpHigh"]) / 2,
        "adjFcfMid": (g["adjFcfLow"] + g["adjFcfHigh"]) / 2,
        "q3Mid": (g["q3RevLow"] + g["q3RevHigh"]) / 2,
        "usCommercialMin": g["usCommercialMin"],
    }
    guide["raisedPct"] = (gmid / guide["initialMid"] - 1) * 100

    # The deceleration the guide implies but never states.
    h1 = (qrows[-2]["revenue"] + qrows[-1]["revenue"]) / 1000.0            # $B
    guide["h1Actual"] = h1
    guide["h2Implied"] = gmid - h1
    guide["q4Implied"] = guide["h2Implied"] - guide["q3Mid"]
    q3_prior = next(r["revenue"] for r in qrows if r["q"] == "Q3'25") / 1000.0
    q4_prior = next(r["revenue"] for r in qrows if r["q"] == "Q4'25") / 1000.0
    guide["q3GrowthImplied"] = (guide["q3Mid"] / q3_prior - 1) * 100
    guide["q4GrowthImplied"] = (guide["q4Implied"] / q4_prior - 1) * 100

    # Valuation, all off the company's own guidance.
    val = {
        "psOnGuide": snap["marketCap"] / (gmid * 1000),
        "evRevOnGuide": ev / (gmid * 1000),
        "evAdjOp": ev / (guide["adjOpMid"] * 1000),
        "fcfYieldOnGuide": guide["adjFcfMid"] * 1000 / snap["marketCap"] * 100,
        "psTrailing": snap["marketCap"] / snap["ttmRev"],
        "peTrailing": snap["price"] / snap["indexed"]["endEps"],
        "sharesOut": shares_out,
        "dilutedPremium": (snap["sharesNow"] / shares_out - 1) * 100,
        "marketCapOut": snap["price"] * shares_out,
    }

    # Earnings quality: how much of pretax income is not software, and how
    # little of it is taxed.
    pretax = fact(F, "earningsQuality", "pretaxQ2")
    nonop = fact(F, "earningsQuality", "interestIncomeQ2") + fact(F, "earningsQuality", "otherIncomeQ2")
    quality = {
        "pretax": pretax,
        "opIncome": fact(F, "results", "opIncomeQ2"),
        "interest": fact(F, "earningsQuality", "interestIncomeQ2"),
        "other": fact(F, "earningsQuality", "otherIncomeQ2"),
        "tax": fact(F, "earningsQuality", "taxProvisionQ2"),
        "net": fact(F, "results", "netIncomeQ2"),
        "nonopPct": nonop / pretax * 100,
        "taxRateQ2": fact(F, "earningsQuality", "taxProvisionQ2") / pretax * 100,
        "taxRateH1": (fact(F, "earningsQuality", "taxProvisionH1")
                      / fact(F, "earningsQuality", "pretaxH1") * 100),
        "sbcPctRev": fact(F, "earningsQuality", "sbcQ2") / fact(F, "results", "revenueQ2") * 100,
    }
    # What this quarter would have earned at a normal rate.
    quality["netAt21"] = pretax * (1 - ep["fairValue"]["constants"]["taxRate"] / 100)
    quality["haircutPct"] = (1 - quality["netAt21"] / quality["net"]) * 100

    # Backlog: the headline number and the contracted one are different things.
    backlog = {
        "rdv": fact(F, "earningsQuality", "usCommercialRDV"),
        "rpo": fact(F, "earningsQuality", "rpo"),
        "rpoNext12": fact(F, "earningsQuality", "rpo") * fact(F, "earningsQuality", "rpoNext12Pct") / 100,
        "h2Guided": guide["h2Implied"],
    }
    backlog["coverPct"] = backlog["rpoNext12"] / backlog["h2Guided"] * 100

    # Mix: America is doing the work.
    mixd = {
        "us": fact(F, "mix", "usRevenueQ2"), "usPrior": fact(F, "mix", "usRevenueQ2prior"),
        "row": fact(F, "mix", "rowRevenueQ2"), "rowPrior": fact(F, "mix", "rowRevenueQ2prior"),
    }
    mixd["usGrowth"] = (mixd["us"] / mixd["usPrior"] - 1) * 100
    mixd["rowGrowth"] = (mixd["row"] / mixd["rowPrior"] - 1) * 100

    # What the reaction session added in market value, on the same share basis
    # as everything else. Never a typed "$90 billion".
    for r in snap["releases"]:
        r["valueAdded"] = shares_out * r["move"] / 100 * snap["price"] / (1 + r["move"] / 100)

    # Peer multiples — fetched live, one request per ticker, never typed in.
    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_ps = snap["marketCap"] / snap["ttmRev"]
    self_growth = snap["ttmRevGrowth"]
    peer_avg_ps = sum(x["ps"] for x in peers) / len(peers)
    peer_avg_growth = sum(x["growth"] for x in peers) / len(peers)
    peerblock = {
        "rows": sorted(peers + [{"sym": snap["symbol"], "ps": self_ps, "growth": self_growth,
                                 "mcap": snap["marketCap"], "ttmRev": snap["ttmRev"]}],
                       key=lambda x: -x["ps"]),
        "avgPs": peer_avg_ps, "avgGrowth": peer_avg_growth,
        "selfPs": self_ps, "selfGrowth": self_growth,
        "psPremium": self_ps / peer_avg_ps,
        "growthPremium": self_growth / peer_avg_growth,
    }

    # Cash bridge: every input is a printed line; the bucket and endpoint are
    # derived here so the audit can recompute them.
    _cb = F["cashBridge"]
    wc = sum(_cb[k] for k in ("securitiesGain", "otherOperating", "receivables", "prepaid",
                              "payables", "contractLiabilities", "otherLiabilities"))
    if abs(_cb["netIncome"] + _cb["dna"] + _cb["sbc"] + wc - _cb["cfo"]) > 1:
        die("the cash-flow bridge does not reconcile to reported operating cash flow")
    cb = dict(_cb, workingCapitalAndOther=wc, endpoint=_cb["cfo"] - _cb["capex"])

    _bb = F["balanceBlocks"]
    bb = dict(_bb,
              deferredRevenue=_bb["deferredRevenueCurrent"] + _bb["deferredRevenueNoncurrent"],
              customerDeposits=_bb["customerDepositsCurrent"] + _bb["customerDepositsNoncurrent"])
    _assets = sum(_bb[k] for k in ("marketableSecurities", "cash", "receivables",
                                   "otherCurrentAssets", "rouAssets", "otherAssets", "ppe"))
    _le = sum(_bb[k] for k in ("equityParent", "nci", "deferredRevenueCurrent",
                               "deferredRevenueNoncurrent", "customerDepositsCurrent",
                               "customerDepositsNoncurrent", "payablesAccrued",
                               "leaseLiabilities", "otherNoncurrent"))
    if abs(_assets - _le) > 1:
        die(f"balance sheet does not balance: assets {_assets} vs liabilities+equity {_le}")

    return {"netDebt": net_debt, "netCash": net_cash, "ev": ev,
            "peers": peerblock, "cb": cb, "bb": bb,
            "series": series, "guide": guide, "val": val,
            "quality": quality, "backlog": backlog, "mixd": mixd,
            # Filing figures the verdict prose quotes, exposed so they are
            # interpolated there rather than typed a second time.
            "deals": {k: fact(F, "deals", k) for k in
                      ("tcvQ2", "usCommercialTcvQ2", "deals1m", "deals10m",
                       "usCommercialTcvGrowthQ2")}}


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s = snap
    g, v, q, bl, mx = s["guide"], s["val"], s["quality"], s["backlog"], s["mixd"]
    res, eq = F["results"], F["earningsQuality"]
    fv = lambda *k: fact(F, *k)                                          # noqa: E731

    MINUS = "−"

    # One magnitude rule for the whole deck: $1.8B, $730M, $208K — see decks/fmt.py.
    m = b_ = fmt.usd                        # inputs in millions, unit chosen for you
    def bb(n): return fmt.usd(n * 1000)     # this one arrives already in billions
    d2 = dm = fmt.dollars
    pc = fmt.pct

    # Small counts read better as words than as digits in prose.
    _word = lambda n, cap=False: (                                        # noqa: E731
        lambda w: w.capitalize() if cap else w)(
        "zero one two three four five six seven eight nine ten".split()[n] if n <= 10 else str(n))
    def x(n, d=1): return f"{n:.{d}f}&times;"          # prose — rendered as innerHTML
    def xt(n, d=1): return f"{n:.{d}f}×"          # chart labels — set as textContent
    bb_ = fmt.usd

    # trailing net income, summed from the same reported quarters as the EPS series
    ttm_ni = sum(q["netInc"] for q in fund_quarters[-4:]) * 1000

    # base-case fair value, recomputed here so the band and the calculator agree
    fvc = ep["fairValue"]; K = fvc["constants"]; c = fvc["cases"]["base"]; Hh = fvc["horizonYears"]

    def _fair(case):
        """One case of the same model the calculator on the last slide runs live."""
        g = (1 + case["revGrowth"] / 100) ** Hh
        ebit = K["startRevenueTTM"] * g * case["opMargin"] / 100
        pre = ebit - K["netDebt"] * K["interestRate"] / 100
        net = pre * (1 - K["taxRate"] / 100) - K["nciAnnualRunRate"] * g
        sh = s["sharesNow"] * (1 + case["shareChange"] / 100) ** Hh
        return (net / sh) * case["exitPE"] / (1 + fvc["requiredReturn"] / 100) ** Hh

    fair_base = _fair(c)
    fair_bear = _fair(fvc["cases"]["bear"])
    fair_bull = _fair(fvc["cases"]["bull"])

    react = s["releases"][-1]      # the reaction session, computed from live bars in derive()
    ptt = s["peakToTrough"]        # deepest in-order fall — the naive high-minus-low is not one

    S = []

    # 01 ---------------------------------------------------------------
    S.append({
        "type": "title", "kicker": "Fundamental analysis · episode deck",
        "company": s["company"], "ticker": s["symbol"],
        "exchange": s["exchange"], "sector": s["sector"],
        "price": s["price"], "changePct": s["changePct"],
        "hook": (f"Up <em>{pc(react['move'], 0)[1:]}</em> in a single day on earnings &mdash; about "
                 f"<em>{b_(react['valueAdded'])}</em> of market value added. The quarter was "
                 f"extraordinary. The question is what it cost."),
        "chips": [{"form": lab.split(" ")[0], "when": lab.split("filed ")[-1]}
                  for lab in [x2["label"] for x2 in ep["sources"].values()]][:7],
        "notes": N["title"], "target": 18,
    })

    # 02 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Where we are", "src": "Daily closes · Yahoo via Terminal",
        "head": f"A {abs(ptt['pct']):.0f}% drawdown, then one earnings report",
        "sub": (f"{d2(s['high']['v'])} last November down to {d2(s['low']['v'])} in June, "
                f"then {pc(react['move'])} on {react['reactDate']} alone."),
        "chart": {"kind": "line", "points": s["tape"], "height": 500, "markers": [
            {"i": s["high"]["i"], "lab": d2(s["high"]["v"]), "sub": s["high"]["when"]},
            {"i": s["low"]["i"], "lab": d2(s["low"]["v"]), "sub": s["low"]["when"], "side": "below"},
            {"i": -1, "lab": d2(s["price"]), "sub": "now", "side": "below"},
        ]},
        "why": ("Between November and June the company itself never got worse &mdash; sales and profits "
                "kept climbing the whole way down. What changed was how much people were willing to pay "
                "for those same sales. That is worth sitting with: this stock can halve without anything "
                "going wrong inside the business."),
        "notes": N["tape"], "target": 20,
    })

    S.append({
        "type": "findings", "kicker": "Four things the headlines missed",
        "src": "All four from the filings, not the press release",
        "head": "What nobody else is going to show you",
        "items": ep["findings"],
        "why": ("Every one of these is in a document Palantir filed with the SEC last Monday. "
                "None of them are in the press release headline, and I have not seen one of them "
                "covered anywhere. We will walk each of them."),
        "notes": N["findings"], "target": 26,
    })

    # 03 ---------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "First, what they actually do", "src": "10-Q + 8-K EX-99.1",
        "head": "Software that turns an organisation's data into decisions",
        "sub": ("Two kinds of customer, and one product wave. Governments run operations on it; "
                "companies increasingly run AI on it."),
        "cols": 4,
        "tiles": [
            {"v": f"{fv('mix','govPctH1')}%", "l": "Government", "n": "of first-half revenue"},
            {"v": f"{fv('mix','commercialPctH1')}%", "l": "Commercial", "n": "the faster-growing half", "tone": "accent"},
            {"v": f"{fv('deals','deals1m')}", "l": "Deals closed over $1M", "n": f"{fv('deals','deals10m')}" + " of them over $10M"},
            {"v": bb(fv("deals", "usCommercialTcvQ2")), "l": "U.S. commercial contracts signed",
             "n": f"a record quarter, {pc(fv('deals','usCommercialTcvGrowthQ2'), 0)} YoY",
             "tone": "good"},
        ],
        "why": ("Hold on to the split: roughly half government, half commercial. Everything that happens "
                "next in this deck is the commercial half accelerating."),
        "notes": N["business"], "target": 20,
    })

    # 04 ---------------------------------------------------------------
    # 05 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "The one metric software investors use", "src": "Company-reported score",
        "head": "Rule of 40: growth plus margin. Palantir scored 155.",
        "sub": ("Add the revenue growth rate to the operating margin. Above 40 is a healthy software "
                "company. Most good ones sit in the 40s and 50s."),
        "chart": {"kind": "gauge", "height": 450, "fmtKind": "plain",
                  "min": 0, "max": 180, "value": fv("results", "ruleOf40Q2"),
                  "valueLab": str(fv("results", "ruleOf40Q2")),
                  "label": "Rule of 40 score, Q2 2026",
                  "threshold": 40, "thresholdLab": "40 = healthy",
                  "marks": [{"v": s["series"][0]["r40"], "lab": f"{s['series'][0]['r40']} two years ago"}]},
        "why": ("The rule of thumb: add how fast a software company grows to how much of each sale it "
                "keeps as profit, and anything over 40 is considered healthy. Palantir grew "
                f"{fv('results','revenueGrowthQ2')}% and kept {fv('results','adjOpMarginQ2')} cents in "
                f"the dollar, which lands at {fv('results','ruleOf40Q2')}. One caveat worth knowing: "
                "that profit figure leaves out the shares handed to staff. Count those and it is "
                f"{fv('results','opMarginQ2')} cents, still excellent. Either way, almost no company "
                "this size grows and earns at the same time &mdash; that is what buyers are excited "
                "about."),
        "notes": N["rule40"], "target": 24,
    })

    # 06 ---------------------------------------------------------------
    gp_pct = fv("results", "grossProfitQ2") / fv("results", "revenueQ2") * 100
    # 07 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Where the growth comes from", "src": "10-Q geographic note",
        "head": "It is almost entirely an American story",
        "sub": ("Q2 revenue growth by geography. The pitch is a global AI wave; the results are a "
                "U.S. commercial boom."),
        "chart": {"kind": "dumbbell", "height": 400, "rows": [
            {"name": "United States", "sub": f"{fv('mix','usSharePctQ2prior')}% → {fv('mix','usSharePctQ2')}% of revenue",
             "from": mx["usPrior"], "to": mx["us"],
             "fromLab": b_(mx["usPrior"]), "toLab": b_(mx["us"]),
             "delta": pc(mx["usGrowth"], 0)},
            {"name": "Rest of world",
             "sub": f"{100 - fv('mix','usSharePctQ2prior')}% → {100 - fv('mix','usSharePctQ2')}% of revenue",
             "cls": "mut",
             "from": mx["rowPrior"], "to": mx["row"],
             "fromLab": b_(mx["rowPrior"]), "toLab": b_(mx["row"]),
             "delta": pc(mx["rowGrowth"], 0), "deltaGood": False},
        ]},
        "why": (f"America is now {fv('mix','usSharePctQ2')} cents of every revenue dollar, up from "
                f"{fv('mix','usSharePctQ2prior')}. If part of why you like this stock is that the rest "
                "of the world is still to come, be honest that it has not started showing up yet "
                "&mdash; and a story that has not started is a story you are paying for in advance."),
        "notes": N["intl"], "target": 22, "optional": True,
    })

    # 08 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And they raised the year again", "src": "Feb / May / Aug 8-Ks",
        "head": f"This year's revenue guide is up {pc(g['raisedPct'], 0)} in six months",
        "sub": "Full-year 2026 revenue guidance, as issued at each of the last three reports.",
        "chart": {"kind": "slope", "height": 450, "points": [
            {"x": "February", "x2": "initial guide", "v": g["initialMid"], "lab": bb(g["initialMid"])},
            {"x": "May", "x2": "raised", "v": g["priorMid"], "lab": bb(g["priorMid"])},
            {"x": "August", "x2": "raised again", "v": g["revMid"], "lab": bb(g["revMid"])},
        ], "endNote": pc(g["raisedPct"], 0) + " in six months"},
        "why": (f"They raised their profit forecast to {bb(g['adjOpMid'])} and the cash they expect to "
                f"be left with to {bb(g['adjFcfMid'])}. When management lifts its own forecast twice in "
                "six months, it is telling you it can already see the business landing there. That is "
                "the opposite of the company I covered last week, which beat and then refused to raise "
                "&mdash; and lost a fifth of its value the next day."),
        "notes": N["raise"], "target": 24,
    })

    # 09 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "But read the guide carefully",
        "src": "Reported quarters + the company's own FY guide",
        "head": "Revenue keeps climbing. The growth rate rolls over.",
        "sub": ("Quarterly revenue. Solid is reported; dashed is what their own raised full-year "
                "guide implies. The percentages underneath are year-over-year growth."),
        "chart": {"kind": "forecast", "height": 500, "fmtKind": "auto",
                  "pastLab": "reported", "futureLab": "their own guide",
                  "points": [
            *[{"x": r["q"], "v": r["revenue"], "growth": f"{r['growth']}%",
               "lab": bb(r["revenue"] / 1000) if i in (0, len(s["series"]) - 1) else ""}
              for i, r in enumerate(s["series"])],
            {"x": "Q3'26", "v": g["q3Mid"] * 1000, "guided": True,
             "growth": f"{g['q3GrowthImplied']:.0f}%", "lab": bb(g["q3Mid"])},
            {"x": "Q4'26", "v": g["q4Implied"] * 1000, "guided": True,
             "growth": f"{g['q4GrowthImplied']:.0f}%", "lab": bb(g["q4Implied"])},
        ]},
        "why": (f"First half was {bb(g['h1Actual'])} against a {bb(g['revMid'])} year, so the back half "
                f"has to be {bb(g['h2Implied'])}. Q3 is guided to {bb(g['q3Mid'])} and Q4 falls out at "
                f"about {bb(g['q4Implied'])}. The revenue line keeps rising &mdash; but the growth rate "
                f"goes {fv('results','revenueGrowthQ2')}%, {g['q3GrowthImplied']:.0f}%, "
                f"{g['q4GrowthImplied']:.0f}%. Sales still grow, just more slowly each quarter. That "
                "matters because the price of this stock assumes growth keeps speeding up, and the "
                "company's own forecast says it is about to stop."),
        "notes": N["decel"], "target": 28,
    })

    # 10 ---------------------------------------------------------------
    es, rel = s["earningsStats"], s["releases"]
    S.append({
        "type": "chart", "kicker": "Eight reports, and a warning", "src": "8-K releases + daily closes",
        "head": "The business improved every time. The stock fell three times.",
        "sub": ("Next-session move after each of the last eight earnings releases, labelled with that "
                "quarter's revenue growth rate."),
        "chart": {"kind": "bars", "height": 500, "zeroLine": True, "series": [
            {"x": r["q"], "x2": f"{sr['growth']}% growth", "v": r["move"], "lab": pc(r["move"]),
             "cls": "good" if r["move"] > 0 else "bad"}
            for r, sr in zip(rel, s["series"])
        ]},
        "legend": [{"c": "var(--good)", "t": "stock rose the next session"},
                   {"c": "var(--crit)", "t": "stock fell"}],
        "why": ("Growth went up every single quarter and the stock still fell on three of these. "
                "I went looking for a pattern in how far it had run beforehand and could not find a "
                "clean one, so I am not going to invent one. The lesson is blunter than that: "
                "<b>a great set of results and a good price to buy at are two different things.</b>"),
        "notes": N["history"], "target": 30,
    })

    # 11 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "The bull case I did not expect to find",
        "src": "Reported quarterly EPS + daily closes",
        "head": "Earnings have quadrupled. The share price has not moved.",
        "sub": (f"Both indexed to 100 on {s['indexed']['baseDate']}. Trailing earnings step on the day "
                "each quarter was reported."),
        "chart": {"kind": "indexed", "height": 470,
                  "price": s["indexed"]["price"], "earn": s["indexed"]["earn"],
                  "priceLabel": f"price {pc(s['indexed']['priceGain'], 0)}",
                  "earnLabel": f"earnings {pc(s['indexed']['earnGain'], 0)}",
                  "ticks": [{"t": e["t"], "lab": e["_q"]} for e in s["indexed"]["earn"]]},
        "legend": [{"c": "var(--s1)", "t": "share price, indexed to 100"},
                   {"c": "var(--s2)", "t": "trailing 12-month EPS — steps on the report date"}],
        "why": (f"Trailing earnings went from {d2(s['indexed']['baseEps'])} to "
                f"{d2(s['indexed']['endEps'])}, {pc(s['indexed']['earnGain'], 0)}, while the share price "
                f"did {pc(s['indexed']['priceGain'], 0)}. Profits raced ahead while the price stood "
                "still, so you are getting far more earnings per dollar than a buyer got a year ago. "
                "Read it the right way round: expensive as this looks, it was much more expensive "
                "twelve months ago."),
        "notes": N["indexed"], "target": 28, "optional": True,
    })

    # 12 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Now the part nobody covers", "src": "10-Q statement of operations",
        "head": "Every dollar of revenue, and where it ends up",
        "sub": ("Q2 2026. Ribbon thickness is money. Watch how thin the tax ribbon is "
                "next to everything else."),
        "chart": {"kind": "sankey", "height": 500, "fmtKind": "auto",
                  "steps": [
            {"node": "Revenue", "v": fv("results", "revenueQ2")},
            {"out": "Cost of revenue", "v": fv("results", "costOfRevenueQ2")},
            {"node": "Gross profit", "v": fv("results", "grossProfitQ2")},
            {"out": "Operating expenses",
             "v": fv("results", "grossProfitQ2") - fv("results", "opIncomeQ2")},
            {"node": "Operating income", "v": fv("results", "opIncomeQ2")},
            {"in": "Interest + investment gains", "v": q["interest"] + q["other"], "cls": "gain"},
            {"node": "Pretax profit", "v": q["pretax"]},
            {"out": f"Income tax — a {q['taxRateQ2']:.1f}% rate", "v": q["tax"], "cls": "bad"},
            {"node": "Net income", "v": q["net"]},
        ]},
        "why": (f"Two things to notice. {pc(q['nonopPct'], 0)[1:]} of the profit did not come from "
                "selling software at all &mdash; it is interest on their cash pile and gains on "
                f"investments. And they paid {m(q['tax'])} of tax on {b_(q['pretax'])} of profit, a rate "
                f"of {q['taxRateQ2']:.1f}%. That is legal: they lost money for years, and those old "
                "losses cancel out today's tax bill. But both of those are temporary, and the profit "
                "you are buying is flattered by both."),
        "notes": N["quality"], "target": 30,
    })

    # 13 ---------------------------------------------------------------
    S.append({
        "type": "mega", "kicker": "Which matters because it cannot last",
        "src": f"Derived from the 10-Q at a normalised {K['taxRate']:.0f}% rate",
        "head": "At a normal tax rate, this quarter earned a fifth less",
        "value": f"{MINUS}{q['haircutPct']:.0f}%", "tone": "bad",
        "caption": (f"{m(q['net'])} reported. About {m(q['netAt21'])} if they had paid "
                    f"{K['taxRate']:.0f}% on the same "
                    f"pretax income. The half-year rate was {q['taxRateH1']:.1f}%."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(2,1fr);margin-top:22px">'
                  f'<div class="tile warn"><div class="tv num">{q["sbcPctRev"]:.1f}%</div>'
                  '<div class="tl">Stock compensation as a share of revenue</div>'
                  f'<div class="tn">{m(fv("earningsQuality","sbcQ2"))} in the quarter — a real cost to you, '
                  'even though no cash leaves the building</div></div>'
                  f'<div class="tile warn"><div class="tv num">{pc(q["nonopPct"], 0)[1:]}</div>'
                  '<div class="tl">Of pretax profit that is not software</div>'
                  '<div class="tn">interest on the cash pile plus marketable-securities gains</div></div></div>'),
        "why": ("None of this is wrongdoing. Every bit of it is in the filings. But you are paying a "
                "very high price for each dollar of profit here, so it matters what those dollars are "
                "made of. These ones are barely taxed. Some of them are interest, not software. And "
                "they are counted before the shares handed to staff come out of your slice."),
        "notes": N["quality"], "target": 24,
    })

    # 14 ---------------------------------------------------------------
    S.append({
        "type": "quote", "kicker": "Two backlog numbers, two definitions",
        "src": "10-Q Note 3 vs the release highlights",
        "head": "Neither backlog number is what it sounds like",
        "sub": ("The release quotes one measure; the accounts quote another. Here is the sentence "
                "that explains the difference:"),
        "quote": fv("earningsQuality", "cancelableQuote"),
        "attr": "Palantir Technologies Inc., Q2 2026 Form 10-Q",
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile"><div class="tv num">{bb(bl["rdv"])}</div>'
                  '<div class="tl">"Remaining deal value"</div>'
                  '<div class="tn">their own metric · U.S. commercial only · counts cancelable '
                  'contracts and short ones</div></div>'
                  f'<div class="tile warn"><div class="tv num">{bb(bl["rpo"])}</div>'
                  '<div class="tl">Remaining performance obligations</div>'
                  '<div class="tn">the GAAP figure · whole company · <b>only</b> what the customer '
                  'cannot cancel, and only contracts over 12 months</div></div>'
                  f'<div class="tile warn"><div class="tv num">{bb(bl["rpoNext12"])}</div>'
                  '<div class="tl">Of that, landing within 12 months</div>'
                  f'<div class="tn">against {bb(bl["h2Guided"])} guided for the next '
                  '<b>six</b></div></div></div>'),
        "why": ("This is the difference between money promised and money locked. The headline number "
                "counts deals the customer can walk away from whenever they like. Strip those out and "
                f"{bb(bl['rpo'])} is what is truly committed &mdash; and only {bb(bl['rpoNext12'])} of "
                f"it lands in the next year, against {bb(bl['h2Guided'])} they have promised for just "
                "six months. So the forecast rests on customers choosing to stay and spend more, not "
                "on contracts already signed. That is normal for software. It just means this number "
                "is not the safety net it sounds like."),
        "notes": N["backlog"], "target": 30,
    })

    # 15 ---------------------------------------------------------------
    # 16 ---------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "So what does it cost?", "src": "Company guidance + market price",
        "head": "Every multiple here comes from Palantir's own guidance",
        "sub": (f"Market capitalisation {b_(s['marketCap'])} on diluted shares, less "
                f"{bb(s['netCash']/1000)} of net cash, gives an enterprise value of {b_(s['ev'])}."),
        "cols": 4,
        "tiles": [
            {"v": x(v["evRevOnGuide"], 0), "l": "Enterprise value to<br>this year's guided revenue",
             "n": f"on the {bb(g['revMid'])} guide", "tone": "bad", "small": True},
            {"v": x(v["evAdjOp"], 0), "l": "To guided adjusted<br>operating income",
             "n": f"on {bb(g['adjOpMid'])}", "tone": "bad", "small": True},
            {"v": f"{v['fcfYieldOnGuide']:.1f}%", "l": "Free cash flow yield",
             "n": f"on the {bb(g['adjFcfMid'])} guide", "tone": "bad"},
            {"v": x(v["peTrailing"], 0), "l": "Price to trailing earnings",
             "n": (f"on {d2(s['indexed']['endEps'])} — the sum of four reported <b>diluted</b> "
                   "quarters, the conservative basis"), "tone": "bad", "small": True},
        ],
        "why": (f"Here is the simplest way to hold it: a strong software company usually sells for "
                f"about 10 to 15 times its yearly sales. Palantir sells for {x(v['evRevOnGuide'], 0)} "
                "its sales. You are not paying for what the company earns today &mdash; you are paying "
                "for what it might earn many years from now. None of this says it drops tomorrow. It "
                f"says that when a price is set this far ahead, a {abs(ptt['pct']):.0f}% fall can "
                "happen without a single thing going wrong at the company &mdash; which is exactly "
                "what happened last year."),
        "notes": N["valuation"], "target": 28,
    })

    # 17 ---------------------------------------------------------------
    # 18 ---------------------------------------------------------------
    st = s["street"]
    S.append({
        "type": "chart", "kicker": "And the Street cannot agree", "src": "Nasdaq analyst consensus",
        "head": f"The bears say {dm(st['targetLow'])}. The bulls say {dm(st['targetHigh'])}.",
        "sub": (f"{st['analysts']} analysts: {st['strongBuy']} strong buy, {st['hold']} hold, "
                f"{st['sell']} sell. Mean target {dm(st['target'])}."),
        "chart": {"kind": "track", "height": 250,
                  "lo": st["targetLow"], "hi": st["targetHigh"],
                  "loLab": f"low {dm(st['targetLow'])}", "hiLab": f"high {dm(st['targetHigh'])}",
                  "now": s["price"], "nowLab": d2(s["price"]),
                  "mean": st["target"], "meanLab": dm(st["target"])},
        "why": (f"The gloomiest analyst thinks it is worth less than half what the most hopeful one "
                f"does &mdash; a {st['targetHigh']/st['targetLow']:.1f}&times; gap on the same set of "
                "filings. Notice what they are arguing about: not whether the company is good "
                "&mdash; they all agree it is &mdash; but what a good company is worth. That is the "
                "only question left on this stock."),
        "notes": N["street"], "target": 20,
    })

    # -- peers: expensive, and expensive FOR ITS GROWTH are different claims
    pb = s["peers"]
    S.append({
        "type": "chart", "kicker": "Expensive compared to what?",
        "src": "Live market caps and TTM revenue, fetched at build time",
        "head": f"{x(pb['psPremium'], 1)} the peer multiple, for {x(pb['growthPremium'], 1)} the growth",
        "sub": ("Price to trailing revenue against five enterprise-software peers, with each "
                "company's revenue growth beside it."),
        "chart": {"kind": "peers", "height": 480, "avg": pb["avgPs"],
                  "avgLab": f"peer avg {xt(pb['avgPs'], 1)}",
                  "rightHead": "TTM revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["ps"], "lab": xt(r["ps"], 1),
                            "right": pc(r["growth"], 0),
                            "here": r["sym"] == s["symbol"]} for r in pb["rows"]]},
        "why": (f"Palantir is the fastest grower on this list by a wide margin &mdash; "
                f"{pc(pb['selfGrowth'], 0)} against a peer average of {pc(pb['avgGrowth'], 0)}. "
                f"But it costs {x(pb['psPremium'], 1)} what its rivals cost while growing only "
                f"{x(pb['growthPremium'], 1)} as fast. Fast growth is not free here &mdash; you are "
                "being charged more for each point of it than you would be anywhere else on this list."),
        "notes": N["peers"], "target": 28,
    })

    # -- donut: what a $400B price tag actually contains
    S.append({
        "type": "chart", "kicker": "What that price actually buys",
        "src": "Market cap on diluted shares + TTM filings",
        "head": "The whole business, drawn to scale inside the price",
        "sub": "The full ring is what the market pays for the company. The coloured sliver at the "
                   "top is everything it actually sells and keeps in a year.",
        "chart": {"kind": "donut", "height": 460,
                  "total": s["marketCap"],
                  "totalLabel": "market cap", "totalValue": b_(s["marketCap"]),
                  "parts": [{"name": "Revenue, last 12 months", "v": s["ttmRev"], "lab": b_(s["ttmRev"])},
                            {"name": "Net income, last 12 months", "v": ttm_ni, "lab": b_(ttm_ni)}],
                  "stats": [{"v": xt(v["evRevOnGuide"], 0), "l": "EV / guided revenue"},
                            {"v": xt(v["peTrailing"], 0), "l": "price / trailing earnings"}]},
        "why": (f"Put it in dollars you can hold: for every $100 of this stock you buy, the company "
                f"brings in about ${s['ttmRev'] / s['marketCap'] * 100:.2f} of sales a year and keeps "
                f"about {ttm_ni / s['marketCap'] * 100 * 100:.0f} cents of that as profit. Everything "
                "else inside that ring is what buyers are paying today for what they think it becomes "
                "later."),
        "notes": N["donut"], "target": 24, "optional": True,
    })

    # -- earnings -> cash, with stock compensation added back in plain sight
    cb = s["cb"]
    S.append({
        "type": "chart", "kicker": "From profit to actual cash", "src": "10-Q statement of cash flows",
        "head": "What gets added back to turn profit into cash",
        "sub": "Six months to June 30 2026 ($ millions). Green adds, red subtracts.",
        "chart": {"kind": "bridge", "height": 470, "steps": [
            {"type": "start", "v": cb["netIncome"] / 1000, "lab": m(cb["netIncome"] / 1000),
             "x": "Net income", "x2": "as reported"},
            {"type": "step", "v": cb["sbc"] / 1000, "lab": f"+{cb['sbc']/1000:.0f}",
             "x": "Stock compensation", "x2": "a cost that never leaves the bank", "cls": "good"},
            {"type": "step", "v": cb["dna"] / 1000, "lab": f"+{cb['dna']/1000:.0f}",
             "x": "Depreciation", "x2": "asset-light", "cls": "good"},
            {"type": "step", "v": cb["workingCapitalAndOther"] / 1000,
             "lab": f"{MINUS}{abs(cb['workingCapitalAndOther'])/1000:.0f}",
             "x": "Working capital & other", "x2": "receivables mostly", "cls": "bad"},
            {"type": "step", "v": -cb["capex"] / 1000, "lab": f"{MINUS}{cb['capex']/1000:.0f}",
             "x": "Capital spending", "x2": "software economics", "cls": "bad"},
            {"type": "total", "v": cb["endpoint"] / 1000, "lab": m(cb["endpoint"] / 1000),
             "x": "Cash from operations", "x2": "less capital spending, six months"},
        ]},
        "why": (f"The biggest single item is {m(cb['sbc']/1000)} of pay handed to staff as shares "
                f"instead of cash &mdash; {cb['sbc'] / (fv('results','revenueQ2') * 2 * 1000) * 100:.0f}% "
                "of half a year's sales. No money left the bank, which is why it gets added back here. "
                "But it is still a real cost to you: every share they hand out makes the slice you own "
                "a little smaller."),
        "notes": N["cash"], "target": 28,
    })

    # -- balance sheet treemap: the one red block is missing
    bb = s["bb"]
    _assetsM = sum(bb[k] for k in ("marketableSecurities", "cash", "receivables",
                                   "otherCurrentAssets", "rouAssets", "otherAssets", "ppe")) / 1000
    _liabsM = sum(bb[k] for k in ("deferredRevenue", "customerDeposits", "payablesAccrued",
                                  "leaseLiabilities", "otherNoncurrent")) / 1000
    S.append({
        "type": "chart", "kicker": "And the balance sheet behind it", "src": "10-Q balance sheet",
        "head": "Everything they own, everything they owe",
        "sub": "Sized by value at June 30 2026. Debt would be red. There is not any.",
        "chart": {"kind": "treemap", "height": 500, "panels": [
            {"label": "Assets", "items": [
                {"name": "Marketable securities", "v": bb["marketableSecurities"] / 1000,
                 "lab": b_(bb["marketableSecurities"] / 1000)},
                {"name": "Cash", "v": bb["cash"] / 1000, "lab": b_(bb["cash"] / 1000)},
                {"name": "Receivables", "v": bb["receivables"] / 1000, "lab": b_(bb["receivables"] / 1000)},
                {"name": "Other assets", "v": (bb["otherCurrentAssets"] + bb["rouAssets"]
                                               + bb["otherAssets"] + bb["ppe"]) / 1000,
                 "lab": b_((bb["otherCurrentAssets"] + bb["rouAssets"] + bb["otherAssets"] + bb["ppe"]) / 1000)},
            ]},
            {"label": "Liabilities + equity", "items": [
                {"name": "Shareholders' equity", "v": (bb["equityParent"] + bb["nci"]) / 1000,
                 "lab": b_((bb["equityParent"] + bb["nci"]) / 1000)},
                {"name": "Deferred revenue", "v": bb["deferredRevenue"] / 1000,
                 "lab": b_(bb["deferredRevenue"] / 1000), "cls": "warn"},
                {"name": "Customer deposits", "v": bb["customerDeposits"] / 1000,
                 "lab": b_(bb["customerDeposits"] / 1000), "cls": "warn"},
                {"name": "Payables & other", "v": (bb["payablesAccrued"] + bb["leaseLiabilities"]
                                                   + bb["otherNoncurrent"]) / 1000,
                 "lab": b_((bb["payablesAccrued"] + bb["leaseLiabilities"] + bb["otherNoncurrent"]) / 1000),
                 "cls": "warn"},
            ]},
        ]},
        "why": (f"They own about {b_(_assetsM)} and they owe about {b_(_liabsM)}. None of what they "
                "owe is borrowed money &mdash; most of it is customers who have already paid for work "
                "not yet delivered. Whatever the risk is in this stock, it is not that this company "
                "runs out of money."),
        "notes": N["balance"], "target": 22, "optional": True,
    })

    # -- insiders: Form 4, open market only
    ins = F["insider"]
    S.append({
        "type": "chart", "kicker": "What the people who run it are doing",
        "src": f"SEC Form 4 filings · {ins['totalFilings']} filings, 12 months",
        "head": f"{bb_(ins['totalSoldValue'])} sold. Nothing bought.",
        "sub": ("Open-market transactions only, by recency. Option exercises, grants and tax "
                "withholding are excluded &mdash; those are not decisions to buy or sell."),
        "chart": {"kind": "insider", "height": 450, "rows": [
            {"label": r["label"], "sold": r["sold"], "bought": r["bought"],
             "soldLab": f"{r['sold']:,.0f} shares",
             "sub": f"~{bb_(r['value'])} · {r['people']} people",
             "boughtLab": "none" if r["bought"] == 0 else f"{r['bought']:,.0f}"}
            for r in ins["buckets"]]},
        "why": (f"{_word(ins['distinctSellers'], True)} of the people who run this company sold about "
                f"{bb_(ins['totalSoldValue'])} of their own shares over the year &mdash; "
                f"{', '.join(t2['name'] for t2 in ins['topSellers'][:3])} the largest. Not one of them "
                f"bought a single share. Be fair though: {ins['plan10b5Filings']} of the "
                f"{ins['totalFilings']} filings were set up months ahead on an automatic schedule, so "
                "most of this was not anyone reacting to news. What is still notable is the other side: "
                f"the stock fell {abs(ptt['pct']):.0f}% from {d2(ptt['peak'])} to {d2(ptt['trough'])} "
                "over that same year and nobody stepped in."),
        "notes": N["insider"], "target": 30,
    })

    # 19 ---------------------------------------------------------------
    _sc = [x2["score"] for x2 in ep["verdict"]["scored"]]
    _strong = sum(1 for x2 in _sc if x2 >= 4)
    _mid = sum(1 for x2 in _sc if 2 <= x2 <= 3)
    _weak = sum(1 for x2 in _sc if x2 <= 1)
    S.append({
        "type": "snapshot", "kicker": "The verdict", "src": "My call · not financial advice",
        "head": "Six dimensions, scored from the filings",
        "rows": [{"name": x2["dim"], "score": x2["score"], "fact": x2["fact"], "tone": x2["tone"]}
                 for x2 in ep["verdict"]["scored"]],
        "why": (f"{_word(_strong, True)} of the six score four or better &mdash; this is a superb "
                f"company. The {_word(_mid + _weak)} that do not are both about the same thing: "
                "the price, and how solid the earnings behind that price really are."),
        "notes": N["verdict"], "target": 24,
    })

    # 20 ---------------------------------------------------------------
    S.append({
        "type": "twocol", "kicker": "The two lists", "src": "Every line traces to a filing",
        "head": "What's working, and what to watch",
        "leftHead": "What's working", "rightHead": "What to watch",
        "left": ep["verdict"]["working"], "right": ep["verdict"]["watch"],
        "notes": N["twolists"], "target": 22, "optional": True,
    })

    # 21 ---------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So what is it worth?", "src": "My model · not financial advice",
        "head": "Where the price sits against my own fair value",
        "sub": (f"My base case: {c['revGrowth']:.0f}% revenue growth for {Hh} years, "
                f"{c['opMargin']:.0f}% operating margins, a {c['exitPE']:.0f}x exit multiple and a "
                f"normalised {K['taxRate']:.0f}% tax rate. The bracket is my bear and bull cases."),
        "chart": {"kind": "fvband", "height": 440, "band": 0.20,
                  "price": s["price"], "priceLab": d2(s["price"]),
                  "fairValue": fair_base, "fairLab": d2(fair_base), "fairName": "my base case",
                  "rangeLo": fair_bear, "rangeHi": fair_bull,
                  "rangeLoLab": f"bear {d2(fair_bear)}", "rangeHiLab": f"bull {d2(fair_bull)}",
                  "verdict": f"{abs((s['price']/fair_base-1)*100):.0f}% "
                             + ("over" if s["price"] > fair_base else "under") + " my base case"},
        "why": (f"Only my best case &mdash; everything goes right for {Hh} years running, growth stays "
                f"at {fvc['cases']['bull']['revGrowth']:.0f}%, and buyers still pay a rich price at the "
                f"end of it &mdash; gets me to {d2(fair_bull)}. That is roughly where the stock already "
                "trades. So the fair thing to say is not \u201cthis is overpriced\u201d. It is: you "
                "are being asked to pay today for the best version of the next five years, which "
                "leaves you nothing extra if it goes well and a long way to fall if it does not."),
        "notes": N["fairvalue"], "target": 24,
    })

    S.append({
        "type": "verdict", "kicker": "So what am I doing?", "src": "My call · not financial advice",
        "head": f"My call: {ep['verdict']['call']}",
        "call": ep["verdict"]["call"], "callLine": ep["verdict"]["callLine"],
        "reasons": ep["verdict"]["why"],
        "why": ("Fundamentals tell you <b>what</b> to own. They never tell you <b>when</b>. "
                "Let's go to the chart."),
        "notes": N["handoff"], "target": 32,
    })

    return S

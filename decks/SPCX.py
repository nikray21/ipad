"""
decks/SPCX.py — SpaceX's derived metrics and slide narrative.

This one breaks the shape of the first two episodes, and the deck has to say so.
SpaceX listed on 12 June 2026, so there is no eight-quarter history, no year of
tape, and no prior guidance path to lay against the reaction days. It also gives
**no financial guidance at all**, so every multiple here is built on reported
actuals and labelled as such rather than on a company forecast.

Three things this module is careful about:

  * Nothing is annualised silently. Where a quarter is annualised to reach a
    multiple, the slide says "annualise this quarter" in words.
  * The AI segment's positive Adjusted EBITDA is reconciled on screen back to its
    operating loss, because the entire difference is depreciation on hardware
    bought in the same quarter.
  * Per-share figures for this quarter sit on a weighted-average share count of
    5,864M against 13,176M shares actually outstanding, because the IPO landed
    mid-quarter. The deck never prints a per-share figure without that caveat.
"""

import re

from . import fmt

# Figures that are part of a metric's NAME or a fixed contractual term, not a
# claim about the quarter. Everything else is interpolated.
LITERALS_OK = (
    "$135.00",                    # the IPO price, fixed forever
    "10 votes",                   # the charter's Class B ratio
    "5%",                         # the Section 13(d) disclosure threshold — a
                                  # statutory constant, not a figure about SpaceX.
                                  # The 13G states it in the filer's own words too.
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
    """Return the extra snapshot keys SpaceX's slides need."""
    F = ep["filings"]
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    if not snap.get("newlyListed"):
        die("SPCX is built as a newly-listed company; the engine no longer thinks it is one")

    seg = F["segments"]
    r, rp = seg["revQ2"], seg["revQ2prior"]
    o, op = seg["opIncQ2"], seg["opIncQ2prior"]
    cap, capp = seg["capexQ2"], seg["capexQ2prior"]

    # The segment table has to reconcile to the consolidated statement, or one of
    # the two was mistyped.
    if abs(sum(r.values()) - fv("results", "revenueQ2")) > 1:
        die("segment revenue does not sum to consolidated revenue")
    if abs(sum(o.values()) - fv("results", "opLossQ2")) > 1:
        die("segment operating income does not sum to the consolidated figure")
    if abs(sum(cap.values()) - fv("cashFlow", "capexQ2")) > 1:
        die("segment capex does not sum to the reported total")

    # The share count is the sum of two classes, both printed on the balance sheet
    # and both validated on their own. Re-added here so a typo in the total dies.
    _classes = fv("balanceSheet", "sharesClassA") + fv("balanceSheet", "sharesClassB")
    if abs(_classes * 1000 - fv("balanceSheet", "sharesOutstanding")) > 1:
        die(f"shares outstanding {fv('balanceSheet','sharesOutstanding')/1000:.0f}M does not equal "
            f"Class A + Class B ({_classes:.0f}M)")

    rev = fv("results", "revenueQ2")
    net_cash = fv("balanceSheet", "cash") + fv("balanceSheet", "marketableSecurities")
    total_debt = fv("balanceSheet", "totalDebtAndLeases")

    # No guidance exists, so every multiple rests on the reported quarter,
    # annualised. The slides say "annualise this quarter" in words.
    annualised = rev * 4
    val = {
        "annualisedRev": annualised,
        "psAnnualised": snap["marketCap"] / annualised,
        "evAnnualised": (snap["marketCap"] + total_debt - net_cash) / annualised,
        "netCashPos": net_cash,
        "totalDebt": total_debt,
        "netDebt": total_debt - net_cash,
    }

    # Starlink: subscribers doubled, price per subscriber did not hold.
    conn = {
        "subs": fv("connectivity", "subsQ2"),
        "subsPrior": fv("connectivity", "subsQ2prior"),
        "arpu": fv("connectivity", "arpuQ2"),
        "arpuPrior": fv("connectivity", "arpuQ2prior"),
    }
    conn["subsGrowth"] = (conn["subs"] / conn["subsPrior"] - 1) * 100
    conn["arpuChange"] = (conn["arpu"] / conn["arpuPrior"] - 1) * 100
    conn["margin"] = o["connectivity"] / r["connectivity"] * 100
    # If subscribers doubled and revenue did not, price is the reason.
    conn["revGrowth"] = (r["connectivity"] / rp["connectivity"] - 1) * 100

    # Space: the launch cadence fell while the revenue rose.
    sp = {
        "launches": fv("space", "totalLaunchesQ2"),
        "launchesPrior": fv("space", "totalLaunchesQ2prior"),
        "customer": fv("space", "customerLaunchesQ2"),
        "customerPrior": fv("space", "customerLaunchesQ2prior"),
        "internal": fv("space", "internalLaunchesQ2"),
        "internalPrior": fv("space", "internalLaunchesQ2prior"),
        "mass": fv("space", "massToOrbitQ2"),
        "massPrior": fv("space", "massToOrbitQ2prior"),
    }
    sp["massChange"] = (sp["mass"] / sp["massPrior"] - 1) * 100
    sp["revGrowth"] = (r["space"] / rp["space"] - 1) * 100

    # The AI segment's positive Adjusted EBITDA, reconciled back to its loss.
    ai_op = o["ai"]
    ai = {
        "opLoss": ai_op,
        "dna": seg["dnaQ2"]["ai"],
        "sbc": seg["sbcQ2"]["ai"],
        "adjEbitda": seg["adjEbitdaQ2"]["ai"],
        "capex": cap["ai"],
        "revenue": r["ai"],
        "computeGw": fv("ai", "computeGwQ2"),
        "computeGwPrior": fv("ai", "computeGwQ2prior"),
        "advertising": fv("ai", "advertisingQ2"),
        "advertisingPrior": fv("ai", "advertisingQ2prior"),
    }
    restructuring = ai["adjEbitda"] - (ai_op + ai["dna"] + ai["sbc"])
    if abs(restructuring) > 5:
        die("the AI Adjusted EBITDA bridge does not reconcile to its operating loss")
    ai["restructuring"] = restructuring
    ai["capexToRevenue"] = ai["capex"] / ai["revenue"]
    ai["advertisingChange"] = (ai["advertising"] / ai["advertisingPrior"] - 1) * 100

    # Cash: what the business produced against what it spent.
    cf = {
        "cfoH1": fv("cashFlow", "cfoH1"),
        "capexH1": fv("cashFlow", "capexH1"),
        "capexQ2": fv("cashFlow", "capexQ2"),
        "financingH1": fv("cashFlow", "financingH1"),
    }
    cf["fcfH1"] = cf["cfoH1"] - cf["capexH1"]
    cf["capexToRevenue"] = cf["capexQ2"] / rev

    # Related party — the finding.
    rpy = {
        "debt": fv("relatedParty", "valorDebtCurrent") + fv("relatedParty", "valorDebtLongTerm"),
        "debtPrior": (fv("relatedParty", "valorDebtCurrentPrior")
                      + fv("relatedParty", "valorDebtLongTermPrior")),
        "interestQ2": fv("relatedParty", "valorInterestQ2"),
        "tesla": fv("relatedParty", "teslaMegapackQ2"),
    }
    rpy["growth"] = (rpy["debt"] / rpy["debtPrior"] - 1) * 100
    rpy["shareOfDebt"] = rpy["debt"] / total_debt * 100
    rpy["shareOfInterest"] = rpy["interestQ2"] / fv("results", "interestExpenseQ2") * 100
    # The 13G filed Aug 11: the same director is also a 6.5% holder, and it took
    # thirty vehicles to keep any single one under the 5% disclosure line.
    rpy["equityShares"] = fv("relatedParty", "valorClassAShares")
    rpy["equityPct"] = fv("relatedParty", "valorClassAPct")
    rpy["equityBase"] = fv("relatedParty", "valorPctBase")
    rpy["entities"] = int(fv("relatedParty", "valorEntityCount"))
    _recalc = rpy["equityShares"] / rpy["equityBase"] * 100
    if abs(round(_recalc, 1) - rpy["equityPct"]) > 0.05:
        die(f"13G stake does not reconcile: {rpy['equityShares']:,.0f} / "
            f"{rpy['equityBase']:,.0f} = {_recalc:.2f}%, filed as {rpy['equityPct']}%")
    if rpy["entities"] < 2:
        die("the 13G entity count did not parse")

    # Balance sheet by asset class — more computer than spacecraft.
    ppe = {k: v for k, v in F["ppe"].items() if not k.startswith("_") and k != "src"}

    # Lockup arithmetic, from the prospectus schedule and the live tape.
    lk = F["lockup"]
    ipo_price = fv("ipo", "priceUSD")
    trigger = ipo_price * (1 + lk["priceTriggerPremiumPct"] / 100)
    rel_date = F["earningsHistory"]["releases"][-1]["date"]
    import datetime as _dt
    days = [(_dt.datetime.fromtimestamp(b["t"] / 1000, _dt.timezone.utc).strftime("%Y-%m-%d"),
             b["v"]) for b in snap["tape"]]
    # The window is the ten sessions ending on the release date, off the daily bars.
    idx = [i for i, (d, _) in enumerate(days) if d <= rel_date]
    if not idx:
        die("the tape does not reach the earnings release date — cannot test the lockup trigger")
    end = idx[-1]
    window = days[max(0, end - 9):end + 1]
    lock = {
        "ipoPrice": ipo_price, "trigger": trigger,
        "windowDays": len(window),
        "qualifyingDays": sum(1 for _, c in window if c >= trigger),
        "bestClose": max(c for _, c in window),
        "needed": lk.get("priceTriggerDaysNeeded", 5),
        "firstReleasePct": lk["firstReleasePct"],
        "priceTriggerPct": lk["priceTriggerPct"],
        "staircasePct": lk["staircasePct"],
        "postQ3Pct": lk["postQ3Pct"],
    }
    lock["shortBy"] = trigger - lock["bestClose"]
    lock["fired"] = lock["qualifyingDays"] >= lock["needed"]

    # The schedule as a RUNNING TOTAL. Per-date bars answered "how much on this
    # day", which is not the point — the point is how much of that group can sell
    # by the time you are watching. The missed price bonus is deliberately absent:
    # it is a thing that did NOT happen, and a bar of zero cannot say so.
    _steps = [("Aug 6", "after the first results", lk["firstReleasePct"])]
    for _d in ("Aug 20", "Sep 9", "Sep 24", "Oct 9", "Oct 24"):
        _steps.append((_d, f"+{lk['staircasePct']}%", lk["staircasePct"]))
    _steps.append(("After Q3", "next results", lk["postQ3Pct"]))
    _run, _cum = 0, []
    for _i, (_d, _note, _pct) in enumerate(_steps):
        _run += _pct
        _cum.append((_d, _note, _run, f"{_run:.0f}%",
                     "bad" if _i == len(_steps) - 1 else "warn"))
    lock["cumulative"] = _cum
    lock["cumEnd"] = _run
    if abs(_run - (lk["firstReleasePct"] + 5 * lk["staircasePct"] + lk["postQ3Pct"])) > 0.01:
        die("the lockup running total does not equal the sum of its stages")

    # The headline statement lines an investor checks first — income statement,
    # balance sheet, cash flow — derived from the filed figures, never typed.
    _rev, _cor = fv("results", "revenueQ2"), fv("results", "costOfRevenueQ2")
    pl = {
        "rev": _rev, "revPrior": fv("results", "revenueQ2prior"),
        "revGrowth": fv("results", "revenueGrowthQ2"),
        "gross": _rev - _cor,
        "grossMargin": (_rev - _cor) / _rev * 100,
        "rnd": fv("results", "rndQ2"), "sga": fv("results", "sgaQ2"),
        "opLoss": fv("results", "opLossQ2"), "opLossPrior": fv("results", "opLossQ2prior"),
        "netLoss": fv("results", "netLossQ2"), "netLossPrior": fv("results", "netLossQ2prior"),
        "eps": fv("results", "epsQ2"),
        "opMargin": fv("results", "opLossQ2") / _rev * 100,
        "netMargin": fv("results", "netLossQ2") / _rev * 100,
    }
    # The income statement has to add up, or one of these facts is wrong.
    _walk = _rev - _cor - pl["rnd"] - pl["sga"]
    if abs(_walk - pl["opLoss"]) > 6:
        die(f"income statement does not walk: revenue {_rev:,.0f} less cost {_cor:,.0f}, "
            f"R&D {pl['rnd']:,.0f} and SG&A {pl['sga']:,.0f} gives {_walk:,.0f}, "
            f"but the filed operating loss is {pl['opLoss']:,.0f}")

    bs = {
        "cash": fv("balanceSheet", "cash"),
        "securities": fv("balanceSheet", "marketableSecurities"),
        "debt": fv("balanceSheet", "totalDebtAndLeases"),
        "equity": fv("balanceSheet", "equity"),
        "deficit": fv("balanceSheet", "accumulatedDeficit"),
        "assets": fv("balanceSheet", "totalAssets"),
        "liabilities": fv("balanceSheet", "totalLiabilities"),
    }
    bs["liquid"] = bs["cash"] + bs["securities"]
    bs["netCash"] = bs["liquid"] - bs["debt"]
    if abs((bs["assets"] - bs["liabilities"]) - bs["equity"]) > 6:
        die("the balance sheet does not balance: assets less liabilities does not equal equity")

    bk = {
        "total": fv("backlog", "total"),
        "withinOneYearPct": fv("backlog", "withinOneYearPct"),
        "oneToThreePct": fv("backlog", "oneToThreeYearsPct"),
        "thereafterPct": fv("backlog", "thereafterPct"),
    }
    if abs(bk["withinOneYearPct"] + bk["oneToThreePct"] + bk["thereafterPct"] - 100) > 1:
        die("the backlog timing split does not sum to a whole")
    bk["withinOneYear"] = bk["total"] * bk["withinOneYearPct"] / 100

    # How long the cash lasts at the current burn — the question every investor
    # asks about a company spending like this. Annualised from the half year.
    bs["burnPerYear"] = abs(cf["fcfH1"]) * 2
    bs["runwayYears"] = bs["liquid"] / bs["burnPerYear"]

    # Peers — fetched live, one request per ticker, never typed in.
    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_ps = val["psAnnualised"]
    rows = sorted(peers + [{"sym": snap["symbol"], "ps": self_ps,
                            "growth": fv("results", "revenueGrowthQ2")}],
                  key=lambda x: -x["ps"])
    avg_ps = sum(p["ps"] for p in peers) / len(peers)
    peerblock = {"rows": rows, "avgPs": avg_ps, "selfPs": self_ps,
                 "psPremium": self_ps / avg_ps,
                 "avgGrowth": sum(p["growth"] for p in peers) / len(peers)}

    return {
        "seg": {"rev": r, "revPrior": rp, "op": o, "opPrior": op, "capex": cap,
                "capexPrior": capp, "dna": seg["dnaQ2"], "sbc": seg["sbcQ2"],
                "adjEbitda": seg["adjEbitdaQ2"]},
        "val": val, "conn": conn, "sp": sp, "ai": ai, "cf": cf, "rpy": rpy,
        "ppe": ppe, "lock": lock, "peers": peerblock,
        "pl": pl, "bs": bs, "bk": bk,
        "netDebt": val["netDebt"], "netCash": net_cash,
        "ev": snap["marketCap"] + val["netDebt"],
        # Flattened aliases so episode verdict prose can reference them as tokens.
        "rev": rev, "capexQ2": cf["capexQ2"], "fcfH1": cf["fcfH1"],
        "fcfH1abs": abs(cf["fcfH1"]), "cfoH1": cf["cfoH1"], "capexH1": cf["capexH1"],
        "netCashPos": net_cash, "totalDebt": total_debt,
        "relPartyDebt": rpy["debt"], "relPartyDebtPrior": rpy["debtPrior"],
        "psAnnualised": val["psAnnualised"], "subs": conn["subs"],
        "connMargin": conn["margin"], "backlogTotal": fv("backlog", "total"),
        "custConc": fv("concentration", "customerAQ2") + fv("concentration", "customerBQ2"),
        "segRev": r, "segOp": o, "mcap": snap["marketCap"],
    }


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s = snap
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    m = b_ = fmt.usd                     # millions in, unit chosen for you
    d2 = fmt.dollars
    dm = fmt.dollars0            # whole-dollar prices — a $66 monthly bill has no cents
    pc = fmt.pct
    MINUS = fmt.MINUS

    def x(n, d=1): return f"{n:.{d}f}&times;"        # prose — innerHTML
    def xt(n, d=1): return f"{n:.{d}f}×"             # chart labels — textContent
    _word = lambda n, cap=False: (                                        # noqa: E731
        lambda w: w.capitalize() if cap else w)(
        "zero one two three four five six seven eight nine ten".split()[int(n)]
        if n <= 10 else str(n))

    seg, val, conn, sp, ai = s["seg"], s["val"], s["conn"], s["sp"], s["ai"]
    cf, rpy, lock, pb = s["cf"], s["rpy"], s["lock"], s["peers"]
    react = s["releases"][-1]
    ptt = s["peakToTrough"]
    rev = fv("results", "revenueQ2")

    S = []
    pl, bs, bk = s["pl"], s["bs"], s["bk"]

    # EXECUTIVE STYLE. Every slide is one visual, a headline of a few words, and a
    # single punch line. The long explanation that used to sit on screen in a "why
    # it matters" box is now `why` — never rendered, carried into SCRIPT.txt as the
    # second half of what he says. The screen directs attention; the voice explains.

    # 01 — the hook -------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "Nobody reads these filings",
        "src": "All five filed within the last eight weeks",
        "head": "What nobody else will show you",
        "items": ep["findings"],
        # counted, not typed: the count broke the moment a fifth finding was added
        "punch": (f"{_word(len(ep['findings']), True)} things they filed. "
                  f"<b>None in the press release.</b>"),
        "why": ("Every one of these is in a document SpaceX filed with the SEC, and not one is in "
                "the headline of the release. Nobody reads past the highlights, which is exactly "
                "why they are worth your time. We take each in turn."),
        "notes": N["findings"], "target": 28,
    })

    # 02 — the income statement ------------------------------------------
    S.append({
        "type": "tiles", "kicker": "The quarter, first", "cols": 3,
        "src": "8-K EX-99.1, statement of operations · quarter ended June 30 2026",
        "head": "Sales nearly doubled. Still a loss.",
        "tiles": [
            {"v": b_(pl["rev"]), "l": "Revenue", "n": f"{pc(pl['revGrowth'], 0)} on a year ago",
             "tone": "good"},
            {"v": f"{pl['grossMargin']:.0f}%", "l": "Gross margin",
             "n": f"{b_(pl['gross'])} of gross profit", "tone": "good"},
            {"v": b_(pl["rnd"]), "l": "Research and development",
             "n": "the single biggest cost line", "tone": "warn"},
            {"v": m(pl["opLoss"]), "l": "Operating loss",
             "n": f"from {m(pl['opLossPrior'])} a year ago", "tone": "warn"},
            {"v": m(pl["netLoss"]), "l": "Net loss",
             "n": f"from {m(pl['netLossPrior'])} a year ago", "tone": "bad"},
            {"v": d2(pl["eps"]), "l": "Earnings per share",
             "n": f"on {fv('results','wtdAvgSharesQ2'):,.0f}M shares", "tone": "bad"},
        ],
        "punch": (f"{pc(pl['revGrowth'], 0)} revenue growth, and it still "
                  f"<b>lost {b_(abs(pl['netLoss']))}</b>."),
        "why": (f"Revenue of {b_(pl['rev'])} is up {pc(pl['revGrowth'], 0)} on the same quarter "
                f"last year, and the gross margin is {pl['grossMargin']:.0f}% — for every dollar "
                f"of sales they keep {pl['grossMargin']:.0f} cents after the direct costs. That is "
                f"a good business. What eats it is below that line: {b_(pl['rnd'])} of research and "
                f"development in three months, which is why the operating loss is "
                f"{m(pl['opLoss'])} and the net loss {m(pl['netLoss'])}. Per share that is "
                f"{d2(pl['eps'])}. The loss is shrinking fast — it was {m(pl['netLossPrior'])} a "
                f"year ago — but it is still a loss."),
        "notes": N["business"], "target": 32,
    })

    # 03 — who actually earns --------------------------------------------
    S.append({
        "type": "chart", "kicker": "Where the money comes from",
        "src": "8-K EX-99.1, segment tables",
        "head": "What came in, and what survived",
        # Each row runs from what the segment SOLD to what it kept. The drop is the
        # subject, so the chart draws the drop — a profit bar cannot show it, and
        # both ends are dollars so they share an axis honestly.
        "chart": {"kind": "dumbbell", "height": 470, "fmtKind": "usdM", "labelRoom": 440,
                  "rows": [
                      {"name": "Connectivity", "sub": "Starlink",
                       "from": seg["rev"]["connectivity"], "to": seg["op"]["connectivity"],
                       "fromLab": m(seg["rev"]["connectivity"]),
                       "toLab": m(seg["op"]["connectivity"]),
                       "delta": f"kept {conn['margin']:.0f}c in the dollar", "deltaGood": True},
                      {"name": "Space", "sub": "rockets",
                       "from": seg["rev"]["space"], "to": seg["op"]["space"],
                       "fromLab": m(seg["rev"]["space"]), "toLab": m(seg["op"]["space"]),
                       "delta": "lost money", "deltaGood": False},
                      {"name": "AI", "sub": "Grok and data centres",
                       "from": seg["rev"]["ai"], "to": seg["op"]["ai"],
                       "fromLab": m(seg["rev"]["ai"]), "toLab": m(seg["op"]["ai"]),
                       "delta": "lost money", "deltaGood": False},
                  ]},
        "punch": "<b>Starlink pays</b> for the rockets and the robots.",
        "why": (f"Starlink turned {b_(seg['rev']['connectivity'])} of sales into "
                f"{b_(seg['op']['connectivity'])} of profit — it keeps {conn['margin']:.0f} cents "
                f"in the dollar. Rockets and AI together lost "
                f"{b_(abs(seg['op']['space'] + seg['op']['ai']))}. Almost every argument about this "
                f"share price is really an argument about whether the two that lose money end up "
                f"looking like the one that does not."),
        "notes": N["segments"], "target": 28,
    })

    # 04 — the catch inside the good business ----------------------------
    S.append({
        "type": "chart", "kicker": "The good business, from underneath",
        "src": "8-K EX-99.1 — the subscriber row, and the row directly under it",
        "head": f"Twice the customers, {abs(conn['arpuChange']):.0f}% less each",
        # One trajectory instead of two panels of bars: the path walks RIGHT as
        # customers double and DOWN as each one pays less. That is the whole
        # headline in a single shape.
        "chart": {"kind": "scatter", "height": 500, "fmtKind": "usd0",
                  "xTitle": "Customers, millions →",
                  "yTitle": "Paid per customer, per month",
                  "points": [
                      {"x": conn["subsPrior"], "y": conn["arpuPrior"], "lab": "Q2 2025",
                       "sub": dm(conn["arpuPrior"])},
                      {"x": fv("connectivity", "subsQ1"), "y": fv("connectivity", "arpuQ1"),
                       "lab": "Q1 2026", "sub": dm(fv("connectivity", "arpuQ1"))},
                      {"x": conn["subs"], "y": conn["arpu"], "lab": "Q2 2026",
                       "sub": dm(conn["arpu"])},
                  ]},
        "punch": "The release says ARPU held. <b>Against last year it fell.</b>",
        "why": (f"The release says revenue per customer was maintained, and against last quarter it "
                f"was — {dm(conn['arpu'])} both times. Against last year it fell from "
                f"{dm(conn['arpuPrior'])} to {dm(conn['arpu'])}. They doubled the customers and cut "
                f"the price by about a fifth. Still growth, just a cheaper kind of growth than "
                f"doubling alone suggests, and it is the number to watch every quarter from here."),
        "notes": N["arpu"], "target": 30,
    })

    # 05 — the rockets ----------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Meanwhile the rockets flew less",
        "src": "8-K EX-99.1, Space operating table",
        "head": f"{abs(sp['massChange']):.0f}% less mass to orbit",
        "chart": {"kind": "lollipop", "height": 470, "fmtKind": "pct0", "rows": [
            {"name": "Customer launches", "sub": f"{sp['customerPrior']} → {sp['customer']}",
             "v": (sp["customer"] / sp["customerPrior"] - 1) * 100,
             "lab": pc((sp["customer"] / sp["customerPrior"] - 1) * 100, 0), "cls": "mut"},
            {"name": "Total launches", "sub": f"{sp['launchesPrior']} → {sp['launches']}",
             "v": (sp["launches"] / sp["launchesPrior"] - 1) * 100,
             "lab": pc((sp["launches"] / sp["launchesPrior"] - 1) * 100, 0), "cls": "mut"},
            {"name": "Internal launches", "sub": f"{sp['internalPrior']} → {sp['internal']}",
             "v": (sp["internal"] / sp["internalPrior"] - 1) * 100,
             "lab": pc((sp["internal"] / sp["internalPrior"] - 1) * 100, 0), "cls": "mut"},
            {"name": "Mass to orbit", "sub": f"{sp['massPrior']:,}t → {sp['mass']:,}t",
             "v": sp["massChange"], "lab": pc(sp["massChange"], 0), "cls": "bad"},
        ]},
        "punch": 'They call it "the leading launch provider". <b>It flew eight fewer times.</b>',
        "why": (f"Space revenue still rose {pc(sp['revGrowth'], 0)}, because more of the flights "
                f"were for paying customers instead of for themselves. But the machine did less "
                f"work: {sp['launchesPrior'] - sp['launches']} fewer flights and "
                f"{abs(sp['massChange']):.0f}% less weight delivered. The release calls this being "
                f"the leading launch provider for the world. Both are true, and only one is in the "
                f"headline."),
        "notes": N["space"], "target": 26,
    })

    # 06 — capex, and what it bought -------------------------------------
    S.append({
        "type": "chart", "kicker": f"{b_(cf['capexQ2'])} of equipment in three months",
        "src": "10-Q Note 5, property plant and equipment · segment capital expenditure",
        "head": "More computer than spacecraft",
        # Composition of a total is an AREA job, not a length job: the servers
        # block simply dwarfing everything else is the argument.
        "chart": {"kind": "treemap", "height": 500, "fmtKind": "usdM", "panels": [
            {"label": "What SpaceX owns, at cost", "items": [
                {"name": "Servers and networking", "v": s["ppe"]["servers"],
                 "lab": m(s["ppe"]["servers"]), "cls": "warn"},
                {"name": "Satellites", "v": s["ppe"]["satellites"],
                 "lab": m(s["ppe"]["satellites"]), "cls": "ok"},
                {"name": "Being built now", "v": s["ppe"]["constructionInProgress"],
                 "lab": m(s["ppe"]["constructionInProgress"]), "cls": "mut"},
                {"name": "Machinery", "v": s["ppe"]["machinery"],
                 "lab": m(s["ppe"]["machinery"]), "cls": "mut"},
                {"name": "Data centres", "v": s["ppe"]["dataCentre"],
                 "lab": m(s["ppe"]["dataCentre"]), "cls": "mut"},
                {"name": "Launch sites", "v": s["ppe"]["launchSites"],
                 "lab": m(s["ppe"]["launchSites"]), "cls": "mut"},
            ]}]},
        "punch": (f"{b_(s['ppe']['servers'])} of servers. "
                  f"<b>{b_(s['ppe']['satellites'])} of satellites.</b>"),
        "why": (f"They spent {b_(cf['capexQ2'])} on equipment in the quarter — "
                f"{x(cf['capexToRevenue'], 1)} the entire quarter's sales — and "
                f"{b_(seg['capex']['ai'])} of it went into AI alone. This is what that buying has "
                f"produced: the single biggest thing this company owns is computers, "
                f"{b_(s['ppe']['servers'])} of servers against {b_(s['ppe']['satellites'])} of "
                f"satellites. People still buy this stock for the rockets. The balance sheet has "
                f"already become something else."),
        "notes": N["capex"], "target": 30,
    })

    # 07 — cash flow ------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So the cash goes backwards",
        "src": "8-K EX-99.1, selected cash flow · six months to June 30",
        "head": f"Made {b_(cf['cfoH1'])}. Spent {b_(cf['capexH1'])}.",
        "chart": {"kind": "bridge", "height": 510, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": cf["cfoH1"], "lab": m(cf["cfoH1"]),
             "x": "From trading", "x2": "six months"},
            {"type": "step", "v": -cf["capexH1"], "lab": f"{MINUS}{m(cf['capexH1'])[1:]}",
             "x": "Equipment", "x2": "capital spending", "cls": "bad"},
            {"type": "total", "v": cf["fcfH1"], "lab": m(cf["fcfH1"]),
             "x": "Left over", "x2": "before any financing", "cls": "bad"},
        ]},
        "punch": f"<b>{b_(abs(cf['fcfH1']))} out the door</b> in six months.",
        "why": (f"Six months of trading produced {m(cf['cfoH1'])} of cash. They spent "
                f"{m(cf['capexH1'])} on equipment, so the company went backwards by about "
                f"{b_(abs(cf['fcfH1']))}. The gap was filled by the flotation and the bond — "
                f"{b_(cf['financingH1'])} raised. This is fine while the money is there. It is "
                f"also the reason the money had to be raised."),
        "notes": N["cash"], "target": 30,
    })

    # 08 — the balance sheet ---------------------------------------------
    S.append({
        "type": "tiles", "kicker": "What is in the bank", "cols": 2,
        "src": "10-Q consolidated balance sheet, June 30 2026",
        "head": f"{b_(bs['liquid'])} of cash. {b_(bs['debt'])} of debt.",
        "tiles": [
            {"v": b_(bs["liquid"]), "l": "Cash and marketable securities",
             "n": f"{b_(bs['cash'])} of it in cash", "tone": "good"},
            {"v": b_(bs["debt"]), "l": "Total debt and leases",
             "n": f"leaving {b_(bs['netCash'])} net cash", "tone": "warn"},
            {"v": f"{bs['runwayYears']:.1f} yrs", "l": "At the current burn",
             "n": f"spending {b_(bs['burnPerYear'])} a year net", "tone": "warn"},
            {"v": m(bs["deficit"]), "l": "Accumulated deficit",
             "n": "every loss it has ever made, added up", "tone": "bad"},
        ],
        "punch": (f"Roughly <b>{bs['runwayYears']:.0f} years of this burn</b> sitting in the bank."),
        "why": (f"They hold {b_(bs['liquid'])} of cash and marketable securities against "
                f"{b_(bs['debt'])} of debt and leases — {b_(bs['netCash'])} net cash, which is an "
                f"unusually strong position. Set it against the burn: they went through "
                f"{b_(abs(cf['fcfH1']))} in six months, so about {b_(bs['burnPerYear'])} a year. "
                f"That is roughly {bs['runwayYears']:.1f} years of runway at this rate, without "
                f"raising another dollar. The accumulated deficit of {m(abs(bs['deficit']))} is "
                f"every loss the company has ever made, added together."),
        "notes": N["balancesheet"], "target": 30,
    })

    # 09 — what is already contracted ------------------------------------
    S.append({
        "type": "chart", "kicker": "What is already sold",
        "src": "10-Q, remaining performance obligations",
        "head": f"{b_(bk['total'])} already contracted",
        "chart": {"kind": "stackedh", "height": 330, "fmtKind": "pct0", "labelRoom": 300,
                  "rows": [{"name": "When it is due",
                            "segs": [
                                {"label": "Within a year", "v": bk["withinOneYearPct"],
                                 "lab": f"{bk['withinOneYearPct']:.0f}%", "cls": "good"},
                                {"label": "One to three years", "v": bk["oneToThreePct"],
                                 "lab": f"{bk['oneToThreePct']:.0f}%", "cls": "mut"},
                                {"label": "Later", "v": bk["thereafterPct"],
                                 "lab": f"{bk['thereafterPct']:.0f}%", "cls": "mut"},
                            ]}]},
        "punch": (f"<b>{b_(bk['withinOneYear'])} of it</b> lands inside twelve months."),
        "why": (f"{b_(bk['total'])} of work is already under contract, and "
                f"{bk['withinOneYearPct']:.0f}% of it is due within twelve months — about "
                f"{b_(bk['withinOneYear'])}. That is the strongest argument for the growth "
                f"continuing: it is not a forecast, it is signed. Worth knowing that "
                f"{b_(fv('backlog','asDeferredRevenue'))} of it is money customers have already "
                f"handed over, and it sits on the balance sheet as a liability until the work is "
                f"done."),
        "notes": N["backlog"], "target": 26,
    })

    # 10 — the loss that becomes a profit --------------------------------
    S.append({
        "type": "chart", "kicker": "Now watch the AI loss become a profit",
        "src": "8-K EX-99.1, AI segment reconciliation",
        "head": f"A {b_(abs(ai['opLoss']))} loss, called {b_(ai['adjEbitda'])} of earnings",
        "chart": {"kind": "bridge", "height": 500, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": ai["opLoss"], "lab": m(ai["opLoss"]),
             "x": "Operating loss", "x2": "what it actually lost", "cls": "bad"},
            {"type": "step", "v": ai["dna"], "lab": f"+{m(ai['dna'])[1:]}",
             "x": "Add back wear on kit", "x2": "depreciation", "cls": "warn"},
            {"type": "step", "v": ai["sbc"], "lab": f"+{m(ai['sbc'])[1:]}",
             "x": "Add back share pay", "x2": "paid in your ownership", "cls": "warn"},
        ] + ([{"type": "step", "v": ai["restructuring"],
               "lab": ("+" if ai["restructuring"] > 0 else MINUS) + m(abs(ai["restructuring"]))[1:],
               "x": "Restructuring", "x2": "the filing's fourth line", "cls": "warn"}]
             if round(ai["restructuring"], 1) else []) + [
            {"type": "total", "v": ai["adjEbitda"], "lab": m(ai["adjEbitda"]),
             "x": "Adjusted earnings", "x2": "the number in the headline"},
        ]},
        "punch": "The cost added back is <b>the thing they just bought</b>.",
        "why": (f"The release leads with positive adjusted earnings of {m(ai['adjEbitda'])} for AI. "
                f"The division lost {m(abs(ai['opLoss']))}. Almost the whole difference is adding "
                f"back {m(ai['dna'])} of wear on equipment and {m(ai['sbc'])} of pay handed out in "
                f"shares. And the equipment being written off is the {b_(seg['capex']['ai'])} of "
                f"computers they bought in this same quarter — so the cost added back is the cost "
                f"of the very thing the story is about."),
        "notes": N["ebitda"], "target": 30,
    })

    # 11 — the man on both sides -----------------------------------------
    S.append({
        "type": "tiles", "kicker": "The same name, on both sides", "cols": 2,
        "src": "10-Q Note 17 · Schedule 13G filed Aug 11 2026",
        "head": f"{fv('relatedParty','directorName')}: biggest lender, {rpy['equityPct']:.1f}% owner",
        "tiles": [
            {"v": b_(rpy["debt"]), "l": "Lent to SpaceX by his fund",
             "n": f"{rpy['shareOfDebt']:.0f}% of every dollar SpaceX owes", "tone": "bad"},
            {"v": f"{rpy['shareOfInterest']:.0f}%", "l": "Of the quarter's interest bill",
             "n": f"{m(rpy['interestQ2'])} of {m(fv('results','interestExpenseQ2'))}", "tone": "bad"},
            {"v": f"{rpy['equityPct']:.1f}%", "l": "Of the Class A stock he controls",
             "n": f"{rpy['equityShares']/1e6:.1f} million shares", "tone": "warn"},
            {"v": f"{rpy['entities']}", "l": "Entities hold that stake",
             "n": "not one of them reaches 5% alone", "tone": "warn"},
        ],
        "punch": "He sits on the board. <b>Nobody could see the equity until August 11.</b>",
        "why": (f"The same person is on both sides of this company. His fund is its biggest lender, "
                f"owed {b_(rpy['debt'])}, and more than half the interest SpaceX paid this quarter "
                f"went to him. He also controls {rpy['equityPct']:.1f}% of the shares, held across "
                f"{rpy['entities']} separate companies — and 5% is the level at which you must tell "
                f"the public. The accountants call the lending a failed sale-leaseback, which means "
                f"the equipment never really changed hands, so treat the money as a loan. None of "
                f"it breaks a rule. All of it is on page twenty-nine."),
        "notes": N["related13g"], "target": 34,
    })

    # 12 — the sellers already scheduled ---------------------------------
    S.append({
        "type": "chart", "kicker": "And a calendar nobody headlined",
        "src": "424(b)(4) prospectus — the staged early-release schedule",
        "head": "The lockup does not end. It leaks.",
        "chart": {"kind": "steparea", "height": 470, "fmtKind": "pct0",
                  "points": [{"x": r[0], "x2": r[1], "v": r[2], "lab": r[3]}
                             for r in lock["cumulative"]]},
        "punch": (f"<b>{lock['cumEnd']:.0f}% can sell</b> by the next set of results."),
        "why": (f"Twenty percent came free on August 6, two days after the first results. A bonus "
                f"{lock['priceTriggerPct']}% was on offer if the shares had closed at "
                f"{d2(lock['trigger'])} or better on five of the ten days up to that report — the "
                f"best close was {d2(lock['bestClose'])}, so it missed every one of the "
                f"{lock['windowDays']} days and those shares stayed locked. Then more comes free on "
                f"five dates before the end of October. By the next results {lock['cumEnd']:.0f}% "
                f"of that group can sell. A steady supply of new sellers is scheduled into this "
                f"stock, in writing, in advance. That is the fundamental picture — now let's see "
                f"what the chart says about timing."),
        "notes": N["lockup"], "target": 30,
    })

    return S

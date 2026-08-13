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

    # The deck opens ON the hook. There is no title slide and no price chart:
    # the intro is delivered to camera full-frame, and the technical read comes
    # after the deck, so a tape slide here only delays the reason to keep watching.

    # 01 — the hook -------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "Nobody is reading these filings",
        "src": "Every one from a document filed in the last eight weeks",
        "head": "What nobody else is going to show you",
        "items": ep["findings"],
        "why": ("Every one of these is in a document SpaceX filed with the SEC, and not one is in "
                "the headline of the press release. Nobody reads past the highlights, which is "
                "exactly why these are worth your time. We take each in turn."),
        "notes": N["findings"], "target": 30,
    })

    # 02 — what it is, and who earns -------------------------------------
    # Was two slides: three revenue tiles, then the profit bars. The tiles said
    # nothing the bars' own sub-labels do not, and three large unlabelled numbers
    # invited being read as profit.
    S.append({
        "type": "chart", "kicker": "What you are actually buying",
        "src": "8-K EX-99.1 and 10-Q Note 18, segment tables",
        "head": "Three businesses. Only one of them earns anything.",
        "sub": (f"Operating profit by segment for the quarter ended June 30 2026, with each "
                f"segment's sales underneath. {b_(rev)} of revenue in total."),
        "chart": {"kind": "bars", "height": 460, "fmtKind": "usdM", "zeroLine": True,
                  "series": [
                      {"x": "Connectivity", "x2": f"Starlink · {m(seg['rev']['connectivity'])} of sales",
                       "v": seg["op"]["connectivity"], "lab": m(seg["op"]["connectivity"]),
                       "cls": "good"},
                      {"x": "Space", "x2": f"rockets · {m(seg['rev']['space'])} of sales",
                       "v": seg["op"]["space"], "lab": m(seg["op"]["space"]), "cls": "bad"},
                      {"x": "AI", "x2": f"Grok and data centres · {m(seg['rev']['ai'])} of sales",
                       "v": seg["op"]["ai"], "lab": m(seg["op"]["ai"]), "cls": "bad"},
                  ]},
        "why": (f"Starlink turned {b_(seg['rev']['connectivity'])} of sales into "
                f"{b_(seg['op']['connectivity'])} of profit — it keeps {conn['margin']:.0f} cents "
                f"in the dollar. Rockets and AI together lost "
                f"{b_(abs(seg['op']['space'] + seg['op']['ai']))}, so the whole company lost "
                f"{b_(abs(fv('results','opLossQ2')))} on the quarter. Almost every argument about "
                f"this share price is really an argument about whether the two that lose money end "
                f"up looking like the one that does not."),
        "notes": N["segments"], "target": 30,
    })

    # 03 — the good business, and the catch underneath --------------------
    # Was two slides: the 12M-subscriber hero, then the ARPU pair. One slide
    # carries both because the catch only means anything against the good news.
    S.append({
        "type": "chart", "kicker": "The part that genuinely works",
        "src": "8-K EX-99.1 — the subscriber row, and the row directly under it",
        "head": f"Twice the customers, each worth {abs(conn['arpuChange']):.0f}% less",
        "sub": (f"{conn['subs']:.0f} million Starlink subscribers, up from "
                f"{conn['subsPrior']:.0f} million a year ago, against what each one pays a month. "
                f"Connectivity earned {b_(seg['op']['connectivity'])} at a "
                f"{conn['margin']:.0f}% margin."),
        "chart": {"kind": "smallmult", "height": 500, "panels": [
            {"label": "Customers, in millions — doubling", "fmtKind": "plain1", "series": [
                {"x": "Q2 2025", "v": conn["subsPrior"], "lab": f"{conn['subsPrior']:.1f}", "cls": "mut"},
                {"x": "Q1 2026", "v": fv("connectivity", "subsQ1"),
                 "lab": f"{fv('connectivity','subsQ1'):.1f}", "cls": "mut"},
                {"x": "Q2 2026", "v": conn["subs"], "lab": f"{conn['subs']:.1f}", "cls": "good"}]},
            {"label": "What each one pays a month — falling", "fmtKind": "usd0", "series": [
                {"x": "Q2 2025", "v": conn["arpuPrior"], "lab": dm(conn["arpuPrior"]), "cls": "mut"},
                {"x": "Q1 2026", "v": fv("connectivity", "arpuQ1"),
                 "lab": dm(fv("connectivity", "arpuQ1")), "cls": "bad"},
                {"x": "Q2 2026", "v": conn["arpu"], "lab": dm(conn["arpu"]), "cls": "bad"}]},
        ]},
        "why": (f"This is the best thing in the accounts: {conn['subs']:.0f} million people paying "
                f"every month for something almost nobody else can supply, at "
                f"{conn['margin']:.0f} cents of profit in the dollar. But look underneath. The "
                f"release says revenue per customer was maintained, and against last quarter it "
                f"was — {dm(conn['arpu'])} both times. Against last year it fell from "
                f"{dm(conn['arpuPrior'])} to {dm(conn['arpu'])}. They doubled the customers and cut "
                f"the price by about a fifth. Still growth, just a cheaper kind than doubling "
                f"alone suggests."),
        "notes": N["arpu"], "target": 34,
    })

    # 04 — the rocket company did less work ------------------------------
    S.append({
        "type": "chart", "kicker": "Meanwhile the rockets flew less",
        "src": "8-K EX-99.1, Space operating table",
        "head": f"{abs(sp['massChange']):.0f}% less mass to orbit than a year ago",
        "sub": ("Change against the same quarter a year ago. The counts are underneath each bar, "
                "and the scale is the change itself, so four different units compare honestly."),
        "chart": {"kind": "bars", "height": 430, "fmtKind": "pct0", "zeroLine": True,
                  "series": [
                      {"x": "Customer launches", "x2": f"{sp['customerPrior']} → {sp['customer']}",
                       "v": (sp["customer"] / sp["customerPrior"] - 1) * 100,
                       "lab": pc((sp["customer"] / sp["customerPrior"] - 1) * 100, 0),
                       "cls": "good"},
                      {"x": "Total launches", "x2": f"{sp['launchesPrior']} → {sp['launches']}",
                       "v": (sp["launches"] / sp["launchesPrior"] - 1) * 100,
                       "lab": pc((sp["launches"] / sp["launchesPrior"] - 1) * 100, 0),
                       "cls": "bad"},
                      {"x": "Internal launches", "x2": f"{sp['internalPrior']} → {sp['internal']}",
                       "v": (sp["internal"] / sp["internalPrior"] - 1) * 100,
                       "lab": pc((sp["internal"] / sp["internalPrior"] - 1) * 100, 0),
                       "cls": "bad"},
                      {"x": "Mass to orbit", "x2": f"{sp['massPrior']:,}t → {sp['mass']:,}t",
                       "v": sp["massChange"], "lab": pc(sp["massChange"], 0), "cls": "bad"},
                  ]},
        "why": (f"Space revenue still rose {pc(sp['revGrowth'], 0)}, because more of the flights "
                f"were for paying customers instead of for themselves. But the machine did less "
                f"work: {sp['launchesPrior'] - sp['launches']} fewer flights and "
                f"{abs(sp['massChange']):.0f}% less weight delivered. The release calls this being "
                f"the leading launch provider for the world. Both are true, and only one of them "
                f"is in the headline."),
        "notes": N["space"], "target": 26,
    })

    # 05 — the cash, and what it was spent on ----------------------------
    # Was two slides: the capex hero, then the cash bridge. The bridge already
    # carries the shape; the capex split belongs in the words beside it.
    S.append({
        "type": "chart", "kicker": "Which is why the cash goes backwards",
        "src": "8-K EX-99.1, selected cash flow and segment capital expenditure",
        "head": f"They made {b_(cf['cfoH1'])} of cash. They spent {b_(cf['capexH1'])}.",
        "sub": (f"Cash from trading against cash spent on equipment, first half of 2026. "
                f"{b_(seg['capex']['ai'])} of the quarter's {b_(cf['capexQ2'])} went into AI "
                f"alone."),
        "chart": {"kind": "bridge", "height": 480, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": cf["cfoH1"], "lab": m(cf["cfoH1"]),
             "x": "From trading", "x2": "six months"},
            {"type": "step", "v": -cf["capexH1"], "lab": f"{MINUS}{m(cf['capexH1'])[1:]}",
             "x": "Equipment", "x2": "capital spending", "cls": "bad"},
            {"type": "total", "v": cf["fcfH1"], "lab": m(cf["fcfH1"]),
             "x": "Left over", "x2": "before any financing", "cls": "bad"},
        ]},
        "why": (f"Six months of trading produced {m(cf['cfoH1'])} of cash. They spent "
                f"{m(cf['capexH1'])} on equipment, so the company went backwards by about "
                f"{b_(abs(cf['fcfH1']))}. The gap was filled by the flotation and the bond — "
                f"{b_(cf['financingH1'])} raised. In the quarter alone they spent "
                f"{x(cf['capexToRevenue'], 1)} their entire sales on equipment, and "
                f"{b_(seg['capex']['ai'])} of it went into AI — "
                f"{x(ai['capexToRevenue'], 1)} everything that division sold. This is fine while "
                f"the money is there. It is also the reason the money had to be raised."),
        "notes": N["cash"], "target": 32,
    })

    # 06 — what the money actually bought --------------------------------
    S.append({
        "type": "chart", "kicker": "So look at what they now own",
        "src": "10-Q Note 5, property plant and equipment",
        "head": "More computer than spacecraft",
        "sub": "Gross property, plant and equipment by type, at June 30 2026.",
        "chart": {"kind": "hbars", "height": 470, "fmtKind": "usdM", "rows": [
            {"name": "Servers and networking", "v": s["ppe"]["servers"],
             "lab": m(s["ppe"]["servers"]), "cls": "warn"},
            {"name": "Satellites", "v": s["ppe"]["satellites"], "lab": m(s["ppe"]["satellites"])},
            {"name": "Being built right now", "v": s["ppe"]["constructionInProgress"],
             "lab": m(s["ppe"]["constructionInProgress"]), "cls": "mut"},
            {"name": "Machinery and equipment", "v": s["ppe"]["machinery"],
             "lab": m(s["ppe"]["machinery"]), "cls": "mut"},
            {"name": "Data centre infrastructure", "v": s["ppe"]["dataCentre"],
             "lab": m(s["ppe"]["dataCentre"]), "cls": "mut"},
            {"name": "Launch sites", "v": s["ppe"]["launchSites"],
             "lab": m(s["ppe"]["launchSites"]), "cls": "mut"},
        ]},
        "why": (f"The single biggest thing this company owns is computers — "
                f"{m(s['ppe']['servers'])} of servers against {m(s['ppe']['satellites'])} of "
                f"satellites. People still buy this stock for the rockets. The balance sheet has "
                f"already become something else entirely."),
        "notes": N["balance"], "target": 24,
    })

    # 07 — the loss that becomes a profit --------------------------------
    S.append({
        "type": "chart", "kicker": "Watch how the AI loss becomes a profit",
        "src": "8-K EX-99.1, AI segment reconciliation",
        "head": f"A {b_(abs(ai['opLoss']))} loss, reported as {b_(ai['adjEbitda'])} of earnings",
        "sub": "Every line of the filing's own reconciliation, in its order.",
        "chart": {"kind": "bridge", "height": 480, "fmtKind": "usdM", "steps": [
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
        "why": (f"The release leads with positive adjusted earnings of {m(ai['adjEbitda'])} for AI. "
                f"The division lost {m(abs(ai['opLoss']))}. Almost the whole difference is adding "
                f"back {m(ai['dna'])} of wear on equipment and {m(ai['sbc'])} of pay handed out in "
                f"shares. And the equipment being written off is the {b_(seg['capex']['ai'])} of "
                f"computers they bought in this same quarter — so the cost added back is the cost "
                f"of the very thing the story is about."),
        "notes": N["ebitda"], "target": 32,
    })

    # 08 — the man on both sides -----------------------------------------
    # Was two slides: the Note 17 quote, then the 13G. One slide, and it names
    # him: a slide about a conflict that will not say who is asking for trust.
    S.append({
        "type": "tiles", "kicker": "The same name, on both sides of the balance sheet", "cols": 2,
        "src": "10-Q Note 17 · Schedule 13G filed Aug 11 2026",
        "head": (f"{fv('relatedParty','directorName')} is their biggest lender "
                 f"and a {rpy['equityPct']:.1f}% owner"),
        "sub": (f"He founded and runs Valor, and sits on SpaceX's board. Valor is owed "
                f"{b_(rpy['debt'])}; the 13G filed on {fv('relatedParty','filedDate')} showed the "
                f"equity for the first time."),
        "tiles": [
            {"v": b_(rpy["debt"]), "l": "Lent to SpaceX by his fund",
             "n": (f"{rpy['shareOfDebt']:.0f}% of every dollar SpaceX owes, up "
                   f"{pc(rpy['growth'], 0)} in six months"), "tone": "bad"},
            {"v": f"{rpy['shareOfInterest']:.0f}%", "l": "Of the quarter's interest bill",
             "n": (f"{m(rpy['interestQ2'])} of {m(fv('results','interestExpenseQ2'))} paid to this "
                   f"one lender"), "tone": "bad"},
            {"v": f"{rpy['equityPct']:.1f}%", "l": "Of the Class A stock he controls",
             "n": (f"{rpy['equityShares']/1e6:.1f} million shares of the "
                   f"{rpy['equityBase']/1e9:.2f} billion outstanding"), "tone": "warn"},
            {"v": f"{rpy['entities']}", "l": "Separate entities hold that stake",
             "n": "and the filing states not one of them reaches 5% on its own", "tone": "warn"},
        ],
        "why": (f"The same person is on both sides of this company. His fund is its biggest "
                f"lender, owed {b_(rpy['debt'])}, and more than half the interest SpaceX paid this "
                f"quarter went to him. He also controls {rpy['equityPct']:.1f}% of the shares, held "
                f"across {rpy['entities']} separate companies — and 5% is the level at which you "
                f"must tell the public. The accountants call the lending a failed sale-leaseback, "
                f"which means the equipment never really changed hands, so treat the money as a "
                f"loan. None of it breaks a rule. All of it is on page twenty-nine."),
        "notes": N["related13g"], "target": 36,
    })

    # 09 — the supply of sellers already scheduled -----------------------
    S.append({
        "type": "chart", "kicker": "And a calendar nobody headlined",
        "src": "424(b)(4) prospectus — the staged early-release schedule",
        "head": "The lockup does not end. It leaks.",
        "sub": (f"Share of the 180-day locked group free to sell, running total, after the "
                f"{d2(lock['ipoPrice'])} listing."),
        # Cumulative, not per-date. Per-date bars also carried a ZERO bar for the
        # price bonus that was missed — and a bar of nothing cannot show that
        # nothing happened, so the miss belongs in the words.
        "chart": {"kind": "bars", "height": 440, "fmtKind": "pct0",
                  "series": [dict(zip(("x", "x2", "v", "lab", "cls"), row))
                             for row in lock["cumulative"]]},
        "why": (f"Twenty percent came free on August 6, two days after the first results. A bonus "
                f"{lock['priceTriggerPct']}% was on offer if the shares had closed at "
                f"{d2(lock['trigger'])} or better on five of the ten days up to that report — the "
                f"best close was {d2(lock['bestClose'])}, so it missed every one of the "
                f"{lock['windowDays']} days and those shares stayed locked. Then more comes free "
                f"on five dates before the end of October. By the next set of results "
                f"{lock['cumEnd']:.0f}% of that group can sell. A steady supply of new sellers is "
                f"scheduled into this stock, in writing, in advance."),
        "notes": N["lockup"], "target": 32,
    })

    # 10 — the scorecard, then straight to the chart ----------------------
    _sc = [r["score"] for r in ep["verdict"]["scored"]]
    _strong = sum(1 for v in _sc if v >= 4)
    _weak = sum(1 for v in _sc if v <= 2)
    S.append({
        "type": "snapshot", "kicker": "Where that leaves it", "src": "My read · not financial advice",
        "head": "Six dimensions, scored from the filings",
        "rows": [{"name": r["dim"], "score": r["score"], "fact": r["fact"], "tone": r["tone"]}
                 for r in ep["verdict"]["scored"]],
        "why": (f"{_word(_strong, True)} of the six score four or better, and they are all about "
                f"the business itself — it sells more every quarter and one division is genuinely "
                f"excellent. The {_word(_weak)} that score badly are about the cash going out, who "
                f"controls the company, and what you are being asked to pay for it. That is the "
                f"fundamental picture. Now let's see what the chart says about timing."),
        "notes": N["verdict"], "target": 24,
    })

    return S

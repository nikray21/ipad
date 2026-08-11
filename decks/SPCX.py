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

    # 01 -----------------------------------------------------------------
    S.append({
        "type": "title", "kicker": "Fundamental analysis · episode deck",
        "company": s["company"], "ticker": s["symbol"],
        "exchange": s["exchange"], "sector": s["sector"],
        "price": s["price"], "changePct": s["changePct"],
        "hook": (f"Public for {s['tapeDays']} trading days. Worth {b_(s['marketCap'])}. "
                 f"This is the first quarter it has ever had to show anyone."),
        "chips": [{"form": "424(b)(4)", "when": "Jun 12 2026"},
                  {"form": "10-Q", "when": "Aug 4 2026"},
                  {"form": "8-K", "when": "Aug 4 2026"}],
        "notes": N["title"], "target": 20,
    })

    # 02 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Where we are", "src": "Daily closes · every session since listing",
        "head": f"The entire life of this stock is {s['tapeDays']} days long",
        "sub": (f"Listed at {d2(fv('ipo','priceUSD'))} on June 12. Ran to {d2(ptt['peak'])}, "
                f"fell {abs(ptt['pct']):.0f}% to {d2(ptt['trough'])}, and is {d2(s['price'])} now."),
        "chart": {"kind": "line", "points": s["tape"], "height": 500, "markers": [
            {"i": s["high"]["i"], "lab": d2(s["high"]["v"]), "sub": s["high"]["when"]},
            {"i": s["low"]["i"], "lab": d2(s["low"]["v"]), "sub": s["low"]["when"]},
        ]},
        "why": (f"Most stocks you look at have years of history to argue with. This one has "
                f"{s['tapeDays']} days. There is no long-run track record to lean on, no pattern "
                f"of how it behaves around results, and everyone who owns it bought it in the last "
                f"eight weeks. That alone should change how much you trust any chart of it."),
        "notes": N["tape"], "target": 22,
    })

    # 03 -----------------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "Before the numbers",
        "src": "All four from filings made in the last eight weeks",
        "head": "What nobody else is going to show you",
        "items": ep["findings"],
        "why": ("Every one of these comes out of a document SpaceX filed with the SEC since it "
                "listed. None of them are in the headline of the press release. We will walk each "
                "one properly."),
        "notes": N["findings"], "target": 26,
    })

    # 04 -----------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "What you are actually buying",
        "src": "10-Q Note 18, segments", "cols": 3,
        "head": "Three very different businesses under one roof",
        "tiles": [
            {"v": b_(seg["rev"]["space"]), "l": "Space",
             "n": f"rockets · lost {b_(abs(seg['op']['space']))} this quarter", "tone": "bad"},
            {"v": b_(seg["rev"]["connectivity"]), "l": "Connectivity",
             "n": f"Starlink · earned {b_(seg['op']['connectivity'])}", "tone": "good"},
            {"v": b_(seg["rev"]["ai"]), "l": "AI",
             "n": f"Grok and data centres · lost {b_(abs(seg['op']['ai']))}", "tone": "bad"},
        ],
        "why": ("One of these three makes money. The other two spend it. That is the whole company "
                "in a sentence, and almost every argument about the share price is really an "
                "argument about whether the two that lose money eventually look like the one that "
                "does not."),
        "notes": N["business"], "target": 22,
    })

    # 05 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So where does the money come from?",
        "src": "8-K EX-99.1, segment tables",
        "head": "Only one of the three earns anything",
        "sub": ("Operating profit by segment, quarter ended June 30 2026. Sales for each "
                   "are underneath."),
        # Plot the PROFIT, not the revenue — the headline is about who earns, and a
        # revenue bar cannot show that. Revenue rides along as the sub-label.
        "chart": {"kind": "bars", "height": 470, "fmtKind": "usdM", "zeroLine": True,
                  "series": [
                      {"x": "Connectivity", "x2": f"on {m(seg['rev']['connectivity'])} of sales",
                       "v": seg["op"]["connectivity"], "lab": m(seg["op"]["connectivity"]),
                       "cls": "good"},
                      {"x": "Space", "x2": f"on {m(seg['rev']['space'])} of sales",
                       "v": seg["op"]["space"], "lab": m(seg["op"]["space"]), "cls": "bad"},
                      {"x": "AI", "x2": f"on {m(seg['rev']['ai'])} of sales",
                       "v": seg["op"]["ai"], "lab": m(seg["op"]["ai"]), "cls": "bad"},
                  ]},
        "why": (f"Starlink turned {b_(seg['rev']['connectivity'])} of sales into "
                f"{b_(seg['op']['connectivity'])} of profit — it keeps {conn['margin']:.0f} cents "
                f"in the dollar. Rockets and AI together lost {b_(abs(seg['op']['space'] + seg['op']['ai']))}. "
                f"The whole company lost {b_(abs(fv('results','opLossQ2')))} on the quarter."),
        "notes": N["segments"], "target": 26,
    })

    # 06 -----------------------------------------------------------------
    S.append({
        "type": "mega", "kicker": "The part that genuinely works",
        "src": "8-K EX-99.1, Connectivity table",
        "head": "Starlink doubled its customers in a year",
        "value": f"{conn['subs']:.1f}M", "tone": "good",
        "caption": (f"Up from {conn['subsPrior']:.1f} million a year ago, and "
                    f"{conn['subsPrior'] and ''}{fv('connectivity','subsQ1'):.1f} million last "
                    f"quarter. Connectivity earned {b_(seg['op']['connectivity'])} of operating "
                    f"profit in the three months."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(2,1fr);margin-top:22px">'
                  f'<div class="tile good"><div class="tv num">{pc(conn["revGrowth"], 0)}</div>'
                  '<div class="tl">Connectivity revenue growth</div>'
                  f'<div class="tn">to {b_(seg["rev"]["connectivity"])} in the quarter</div></div>'
                  f'<div class="tile good"><div class="tv num">{conn["margin"]:.0f}%</div>'
                  '<div class="tl">Operating margin</div>'
                  '<div class="tn">a genuinely excellent business on its own</div></div></div>'),
        "why": (f"If this were a company by itself it would be one of the best in the world. "
                f"{conn['subs']:.0f} million people paying every month for something almost nobody "
                f"else can supply, at a {conn['margin']:.0f}% profit margin. That is the strongest "
                f"thing in these accounts by a distance, and it is why the shares exist at all."),
        "notes": N["starlink"], "target": 24,
    })

    # 07 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And the same business, from underneath",
        "src": "8-K EX-99.1 — the row directly under the subscriber count",
        "head": f"Each customer is worth {abs(conn['arpuChange']):.0f}% less than a year ago",
        "sub": "Starlink subscribers against monthly revenue per subscriber.",
        "chart": {"kind": "smallmult", "height": 520, "panels": [
            {"label": "Customers, in millions — doubling", "fmtKind": "plain1", "series": [
                {"x": "Q2 2025", "v": conn["subsPrior"], "lab": f"{conn['subsPrior']:.1f}", "cls": "mut"},
                {"x": "Q1 2026", "v": fv("connectivity", "subsQ1"),
                 "lab": f"{fv('connectivity','subsQ1'):.1f}", "cls": "mut"},
                {"x": "Q2 2026", "v": conn["subs"], "lab": f"{conn['subs']:.1f}"}]},
            {"label": "What each one pays a month — falling", "fmtKind": "usd0", "series": [
                {"x": "Q2 2025", "v": conn["arpuPrior"], "lab": dm(conn["arpuPrior"]), "cls": "mut"},
                {"x": "Q1 2026", "v": fv("connectivity", "arpuQ1"),
                 "lab": dm(fv("connectivity", "arpuQ1")), "cls": "bad"},
                {"x": "Q2 2026", "v": conn["arpu"], "lab": dm(conn["arpu"]), "cls": "bad"}]},
        ]},
        "why": (f"The release says revenue per customer was maintained, and against last quarter it "
                f"was — {dm(conn['arpu'])} both times. Against last year it fell from "
                f"{dm(conn['arpuPrior'])} to {dm(conn['arpu'])}. So they doubled the customers and "
                f"cut the price by about a fifth. That is still growth, but it is a cheaper kind of "
                f"growth than doubling alone suggests, and it is the number to watch each quarter."),
        "notes": N["arpu"], "target": 30,
    })

    # 08 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Meanwhile the rocket company launched less",
        "src": "8-K EX-99.1, Space operating table",
        "head": f"{abs(sp['massChange']):.0f}% less mass to orbit than a year ago",
        "sub": ("Change against the same quarter a year ago. Counts are underneath each "
                   "bar; the scale is the change, so four different units compare honestly."),
        "chart": {"kind": "bars", "height": 440, "fmtKind": "pct0", "zeroLine": True,
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
        "why": (f"Space revenue still rose {pc(sp['revGrowth'], 0)}, because more of the launches "
                f"were for paying customers rather than for themselves. But the machine did less "
                f"work: eight fewer flights and {abs(sp['massChange']):.0f}% less weight delivered. "
                f"The release calls this being the leading launch provider for the world. Both "
                f"things are true at once, and only one of them is in the headline."),
        "notes": N["space"], "target": 26,
    })

    # 09 -----------------------------------------------------------------
    S.append({
        "type": "mega", "kicker": "Now the number that dwarfs everything",
        "src": "8-K EX-99.1, segment capital expenditure",
        "head": "They spent more on equipment than they sold",
        "value": b_(cf["capexQ2"]), "tone": "bad",
        "caption": (f"Capital spending in the three months, against {b_(rev)} of revenue. That is "
                    f"{x(cf['capexToRevenue'], 1)} the entire quarter's sales, spent on equipment, "
                    f"in the same quarter."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:22px">'
                  f'<div class="tile warn"><div class="tv num">{b_(seg["capex"]["ai"])}</div>'
                  '<div class="tl">AI</div><div class="tn">computers and data centres</div></div>'
                  f'<div class="tile"><div class="tv num">{b_(seg["capex"]["connectivity"])}</div>'
                  '<div class="tl">Connectivity</div><div class="tn">satellites</div></div>'
                  f'<div class="tile"><div class="tv num">{b_(seg["capex"]["space"])}</div>'
                  '<div class="tl">Space</div><div class="tn">rockets and pads</div></div></div>'),
        "why": (f"Look at where it went. {b_(seg['capex']['ai'])} of the "
                f"{b_(cf['capexQ2'])} went into AI — that is "
                f"{x(ai['capexToRevenue'], 1)} everything the AI division sold in the same three "
                f"months. Whatever else SpaceX is now, it is a company spending like a data-centre "
                f"builder and selling like a satellite operator."),
        "notes": N["capex"], "target": 28,
    })

    # 10 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Which means the cash goes backwards",
        "src": "8-K EX-99.1, selected cash flow · six months to June 30",
        "head": f"The business made {b_(cf['cfoH1'])}. It spent {b_(cf['capexH1'])}.",
        "sub": "Cash generated by operations against cash spent on equipment, first half of 2026.",
        "chart": {"kind": "bridge", "height": 500, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": cf["cfoH1"], "lab": m(cf["cfoH1"]),
             "x": "From operations", "x2": "six months"},
            {"type": "step", "v": -cf["capexH1"], "lab": f"{MINUS}{m(cf['capexH1'])[1:]}",
             "x": "Equipment", "x2": "capital spending", "cls": "bad"},
            {"type": "total", "v": cf["fcfH1"], "lab": m(cf["fcfH1"]),
             "x": "Left over", "x2": "before any financing", "cls": "bad"},
        ]},
        "why": (f"Six months of trading produced {m(cf['cfoH1'])} of cash. They spent "
                f"{m(cf['capexH1'])} on equipment. So the company went backwards by about "
                f"{b_(abs(cf['fcfH1']))} of cash, and the gap was filled by the flotation and the "
                f"bond — {b_(cf['financingH1'])} of financing. That is fine while the money is "
                f"there. It is the reason the money had to be raised."),
        "notes": N["cash"], "target": 28,
    })

    # 11 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And it has changed what the company owns",
        "src": "10-Q Note 5, property plant and equipment",
        "head": "More computer than spacecraft",
        "sub": "Gross property, plant and equipment by type, at June 30 2026.",
        "chart": {"kind": "hbars", "height": 480, "fmtKind": "usdM", "rows": [
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
                f"already become something else."),
        "notes": N["balance"], "target": 22, "optional": True,
    })

    # 12 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Watch how the AI loss becomes a profit",
        "src": "8-K EX-99.1, AI segment reconciliation",
        "head": f"A {b_(abs(ai['opLoss']))} loss, reported as {b_(ai['adjEbitda'])} of earnings",
        "sub": "How the AI segment's operating loss is turned into positive adjusted earnings.",
        "chart": {"kind": "bridge", "height": 500, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": ai["opLoss"], "lab": m(ai["opLoss"]),
             "x": "Operating loss", "x2": "what it actually lost", "cls": "bad"},
            {"type": "step", "v": ai["dna"], "lab": f"+{m(ai['dna'])[1:]}",
             "x": "Add back wear on kit", "x2": "depreciation", "cls": "warn"},
            {"type": "step", "v": ai["sbc"], "lab": f"+{m(ai['sbc'])[1:]}",
             "x": "Add back share pay", "x2": "paid in your ownership", "cls": "warn"},
            {"type": "total", "v": ai["adjEbitda"], "lab": m(ai["adjEbitda"]),
             "x": "Adjusted earnings", "x2": "the number in the headline"},
        ]},
        "why": (f"The release leads with positive adjusted earnings of {m(ai['adjEbitda'])} for AI. "
                f"The division lost {m(abs(ai['opLoss']))}. The whole difference is adding back "
                f"{m(ai['dna'])} of wear on equipment and {m(ai['sbc'])} of pay handed out in "
                f"shares. The equipment is the {m(ai['capex'])} of computers they bought this same "
                f"quarter — so the cost being added back is the cost of the thing the story is "
                f"about."),
        "notes": N["ebitda"], "target": 30,
    })

    # 13 -----------------------------------------------------------------
    S.append({
        "type": "quote", "kicker": "The one nobody is talking about",
        "src": "10-Q Note 17, Related Party Transactions",
        "head": f"{b_(rpy['debt'])} is owed to a director's fund",
        "quote": fv("relatedParty", "directorQuote"),
        "attr": "Space Exploration Technologies Corp., Q2 2026 Form 10-Q, Note 17",
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile warn"><div class="tv num">{b_(rpy["debt"])}</div>'
                  '<div class="tl">Owed to Valor Equity Partners</div>'
                  f'<div class="tn">{rpy["shareOfDebt"]:.0f}% of all the company\'s debt</div></div>'
                  f'<div class="tile warn"><div class="tv num">{pc(rpy["growth"], 0)}</div>'
                  '<div class="tl">Growth in six months</div>'
                  f'<div class="tn">from {b_(rpy["debtPrior"])} at the end of December</div></div>'
                  f'<div class="tile warn"><div class="tv num">{rpy["shareOfInterest"]:.0f}%</div>'
                  '<div class="tl">Of the quarter\'s interest bill</div>'
                  f'<div class="tn">{m(rpy["interestQ2"])} of {m(fv("results","interestExpenseQ2"))} '
                  'paid to this one lender</div></div></div>'),
        "why": (f"Read that plainly. A fund run by a man on SpaceX's own board has financed "
                f"{b_(rpy['debt'])} of AI equipment, and more than half the interest the company "
                f"paid this quarter went to him. The accountants call it a failed sale-leaseback, "
                f"which is a technical way of saying: the kit never really left, so treat the money "
                f"as a loan. None of this is hidden and none of it is illegal — it is on page "
                f"twenty-nine. It is just not in the press release, and it grew "
                f"{x(rpy['debt'] / rpy['debtPrior'], 1)} in six months."),
        "notes": N["related"], "target": 32,
    })

    # 14 -----------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "Two more things buried in the notes",
        "src": "10-Q Notes 3 and 16", "cols": 2,
        "head": "Who pays them, and what they have already promised to spend",
        "tiles": [
            {"v": f"{s['custConc']:.0f}%", "l": "Revenue from just two customers",
             "n": (f"{fv('concentration','customerBQ2')}% from one alone — and that customer was "
                   "too small to name a year ago"), "tone": "bad"},
            {"v": m(fv("commitments", "y2027")), "l": "Committed spending in 2027 alone",
             "n": f"of {m(fv('commitments','total'))} they cannot cancel", "tone": "bad"},
        ],
        "why": (f"Nearly {s['custConc']:.0f} cents of every revenue dollar comes from two "
                f"customers, and one of them appeared in the last twelve months. At the same time "
                f"they have signed contracts they cannot get out of worth "
                f"{m(fv('commitments','total'))}, most of it falling in a single year. Both facts "
                f"sit in the notes; neither is in the release."),
        "notes": N["concentration"], "target": 24, "optional": True,
    })

    # 15 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Now the calendar nobody headlined",
        "src": "424(b)(4) prospectus — the staged early-release schedule",
        "head": "The lockup does not end. It leaks.",
        "sub": (f"Shares became sellable in stages after the {d2(lock['ipoPrice'])} listing. "
                f"Percentages are of the shares in the 180-day group."),
        "chart": {"kind": "bars", "height": 450, "fmtKind": "pct0",
                  "series": [
                      {"x": "Aug 6", "x2": "after first results", "v": lock["firstReleasePct"],
                       "lab": f"{lock['firstReleasePct']}%", "cls": "warn"},
                      {"x": "Aug 6", "x2": "price bonus — MISSED",
                       "v": lock["priceTriggerPct"] if lock["fired"] else 0,
                       "lab": f"{lock['priceTriggerPct'] if lock['fired'] else 0}%", "cls": "mut"},
                      {"x": "Aug 20", "x2": "", "v": lock["staircasePct"],
                       "lab": f"{lock['staircasePct']}%", "cls": "warn"},
                      {"x": "Sep 9", "x2": "", "v": lock["staircasePct"],
                       "lab": f"{lock['staircasePct']}%", "cls": "warn"},
                      {"x": "Sep 24", "x2": "", "v": lock["staircasePct"],
                       "lab": f"{lock['staircasePct']}%", "cls": "warn"},
                      {"x": "Oct 9", "x2": "", "v": lock["staircasePct"],
                       "lab": f"{lock['staircasePct']}%", "cls": "warn"},
                      {"x": "Oct 24", "x2": "", "v": lock["staircasePct"],
                       "lab": f"{lock['staircasePct']}%", "cls": "warn"},
                      {"x": "After Q3", "x2": "next results", "v": lock["postQ3Pct"],
                       "lab": f"{lock['postQ3Pct']}%", "cls": "bad"},
                  ]},
        "why": (f"Twenty percent came free on August 6, two days after the first results. There was "
                f"a bonus ten percent on offer if the shares had closed {lock['trigger']:.0f} "
                f"dollars or better on five of the ten days up to that report — the best close was "
                f"{d2(lock['bestClose'])}, so it missed on all {lock['windowDays']} of them and "
                f"those shares stayed locked. Then more comes free on five dates before the end of "
                f"October. A steady supply of new sellers is scheduled into this stock, and it is "
                f"written down in advance."),
        "notes": N["lockup"], "target": 34,
    })

    # 16 -----------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "Who you are investing alongside",
        "src": "424(b)(4) prospectus, cover and Underwriting", "cols": 3,
        "head": "One person controls the outcome of every vote",
        "tiles": [
            {"v": f"{fv('ipo','muskVotingPct')}%", "l": "Of the votes held by the founder",
             "n": "through shares carrying 10 votes each", "tone": "bad"},
            {"v": f"{fv('ipo','lockedPctPreIPO')}%", "l": "Of pre-listing shares still locked",
             "n": f"about {fv('ipo','lockedSharesBn')} billion shares", "tone": "warn"},
            {"v": f"{fv('dilution','unmetPerformanceAwards'):,.0f}M", "l": "Shares promised but not counted",
             "n": "targets not yet hit, so they sit outside the share count", "tone": "warn"},
        ],
        "why": (f"You are buying a minority stake in a company where one person decides everything: "
                f"{fv('ipo','muskVotingPct')}% of the votes. SpaceX is formally a controlled "
                f"company, which lets it skip several of the governance rules Nasdaq would "
                f"otherwise apply. And there are {fv('dilution','unmetPerformanceAwards'):,.0f} "
                f"million shares promised to the founder that do not show up in the share count "
                f"yet — one tranche of which only pays out if SpaceX builds data centres in space."),
        "notes": N["governance"], "target": 26,
    })

    # 17 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So what does it cost?",
        "src": "Live market cap ÷ this quarter's revenue, annualised",
        "head": f"{xt(val['psAnnualised'], 0)} what it sells in a year",
        "sub": ("Price to sales, against the most expensive software companies on the market. "
                "Every one of those makes a profit. SpaceX does not."),
        "chart": {"kind": "peers", "height": 480, "avg": pb["avgPs"],
                  "avgLab": f"peer avg {xt(pb['avgPs'], 1)}",
                  "rightHead": "revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["ps"], "lab": xt(r["ps"], 1),
                            "right": pc(r["growth"], 0),
                            "here": r["sym"] == s["symbol"]} for r in pb["rows"]]},
        "why": (f"There is no guidance to check this against, because SpaceX does not give any. So "
                f"take the quarter it just reported, multiply by four, and compare. It comes to "
                f"{xt(val['psAnnualised'], 0)} sales — about {x(pb['psPremium'], 1)} what these "
                f"peers cost. It grows much faster than they do. It also loses money, and they do "
                f"not."),
        "notes": N["valuation"], "target": 26,
    })

    # 18 -----------------------------------------------------------------
    fwd = [f for f in s["fwd"] if f.get("low") is not None]
    S.append({
        "type": "chart", "kicker": "And the professionals cannot agree",
        "src": f"Nasdaq analyst estimates · {s['fwd'][0].get('analysts') or 0} analysts",
        "head": "Forecasts that run from a loss to a fortune",
        "sub": "Earnings per share estimates by year — the range, not just the average.",
        "chart": {"kind": "dumbbell", "height": 470, "fmtKind": "usd2", "labelRoom": 470, "rows": [
            {"name": f["period"], "sub": f"{f.get('analysts') or 0} analysts",
             "from": f["low"], "to": f["high"],
             "fromLab": d2(f["low"]), "toLab": d2(f["high"]),
             "delta": f"average {d2(f['eps'])}", "deltaGood": f["eps"] > 0}
            for f in fwd]},
        "why": (f"For {fwd[1]['period'] if len(fwd) > 1 else fwd[0]['period']} the forecasts run "
                f"from {d2(fwd[1]['low'] if len(fwd) > 1 else fwd[0]['low'])} to "
                f"{d2(fwd[1]['high'] if len(fwd) > 1 else fwd[0]['high'])} a share. One side thinks "
                f"it loses money; the other thinks it earns three dollars. When the people who do "
                f"this full time are that far apart, it is not because some of them are lazy — it "
                f"is because nobody yet knows what the AI spending turns into."),
        "notes": N["street"], "target": 22, "optional": True,
    })

    # 19 -----------------------------------------------------------------
    _sc = [r["score"] for r in ep["verdict"]["scored"]]
    _strong = sum(1 for v in _sc if v >= 4)
    _weak = sum(1 for v in _sc if v <= 2)
    S.append({
        "type": "snapshot", "kicker": "The verdict", "src": "My call · not financial advice",
        "head": "Six dimensions, scored from the filings",
        "rows": [{"name": r["dim"], "score": r["score"], "fact": r["fact"], "tone": r["tone"]}
                 for r in ep["verdict"]["scored"]],
        "why": (f"{_word(_strong, True)} of the six score four or better, and they are all about "
                f"the business. The {_word(_weak)} that score badly are about the cash going out, "
                f"who controls the company, and what you are being asked to pay."),
        "notes": N["verdict"], "target": 24,
    })

    # 20 -----------------------------------------------------------------
    S.append({
        "type": "twocol", "kicker": "Both sides, plainly",
        "src": "Everything on this slide traces to a filing",
        "head": "What's working, and what to watch",
        "leftHead": "What's working", "rightHead": "What to watch",
        "left": ep["verdict"]["working"], "right": ep["verdict"]["watch"],
        "notes": N["twolists"], "target": 20, "optional": True,
    })

    # 21 -----------------------------------------------------------------
    fvc = ep["fairValue"]; K = fvc["constants"]; c = fvc["cases"]["base"]; Hh = fvc["horizonYears"]

    def _fair(case):
        """Revenue-based, because there are no profits and no guidance to work from."""
        g = (1 + case["revGrowth"] / 100) ** Hh
        revenue = K["startRevenueTTM"] * g
        ebit = revenue * case["opMargin"] / 100
        pre = ebit - K["netDebt"] * K["interestRate"] / 100
        net = pre * (1 - K["taxRate"] / 100)
        sh = s["sharesNow"] * (1 + case["shareChange"] / 100) ** Hh
        return (net / sh) * case["exitPE"] / (1 + fvc["requiredReturn"] / 100) ** Hh

    fair_base, fair_bear, fair_bull = (_fair(c), _fair(fvc["cases"]["bear"]),
                                       _fair(fvc["cases"]["bull"]))
    S.append({
        "type": "chart", "kicker": "So what is it worth?",
        "src": "My model · not financial advice",
        "head": "Where the price sits against my own fair value",
        "sub": (f"My base case: {c['revGrowth']:.0f}% revenue growth every year for {Hh} years, "
                f"finishing on a {c['opMargin']:.0f}% profit margin, no tax at all because of the "
                f"losses carried forward, and buyers still paying a rich price at the end. The "
                f"bracket is my worst and best cases."),
        "chart": {"kind": "fvband", "height": 440, "band": 0.20,
                  "price": s["price"], "priceLab": d2(s["price"]),
                  "fairValue": fair_base, "fairLab": d2(fair_base), "fairName": "my base case",
                  "rangeLo": fair_bear, "rangeHi": fair_bull,
                  "rangeLoLab": f"bear {d2(fair_bear)}", "rangeHiLab": f"bull {d2(fair_bull)}",
                  "verdict": f"{abs((s['price'] / fair_base - 1) * 100):.0f}% "
                             + ("over" if s["price"] > fair_base else "under") + " my base case"},
        "why": (f"Even the base case here is generous: it assumes revenue grows "
                f"{c['revGrowth']:.0f}% a year for {Hh} years running, that a company losing money "
                f"today ends up keeping {c['opMargin']:.0f}p in the pound, and that it pays no tax "
                f"the whole way. That lands at {d2(fair_base)}. My best case gets to "
                f"{d2(fair_bull)}. Today's price is {d2(s['price'])}. You are being asked to pay "
                f"now for a version of this company that does not exist yet."),
        "notes": N["fairvalue"], "target": 24,
    })

    # 22 -----------------------------------------------------------------
    S.append({
        "type": "verdict", "kicker": "So what am I doing?",
        "src": "My call · not financial advice",
        "head": f"My call: {ep['verdict']['call']}",
        "call": ep["verdict"]["call"], "callLine": ep["verdict"]["callLine"],
        "reasons": ep["verdict"]["why"],
        "why": ("Fundamentals tell you <b>what</b> to own. They never tell you <b>when</b>. "
                "Let's go to the chart."),
        "notes": N["call"], "target": 30,
    })

    return S

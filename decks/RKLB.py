"""
decks/RKLB.py — Rocket Lab's derived metrics and slide narrative.

The argument is a single tension: **flawless revenue execution, zero progress on
profit.** Seven quarters at or above the top of their own guidance, and an
operating loss that has sat in a $51–60M band the whole time while revenue nearly
doubled. Everything else on the deck hangs off that.

Four things this module is careful about:

  * Q2 landed AFTER the close on the episode date. `snap["price"]` is the
    after-hours print and `regular` holds the 4pm close. The deck labels which is
    which and claims no reaction figure — tomorrow's session is the verdict.
  * The company has never earned an operating profit, so there is no trailing P/E
    and no earnings series. Every multiple is on revenue and says so.
  * The share count is common PLUS the Series A preferred, because Note 17 says
    the preferred is treated as common for EPS and the company's own guidance
    counts it that way. Both components are validated separately.
  * All figures in the episode file are in USD THOUSANDS, matching the filings.
    fmt.usd wants millions, so everything divides by 1000 on the way out.
"""

import re

from . import fmt

# Figures that are part of a contractual term, not a claim about the quarter.
LITERALS_OK = (
    "$27.00",                     # the Iridium cash consideration, fixed by contract
    "$67.50",                     # the collar floor
    "$112.50",                    # the collar ceiling
)


def _peer(sym, die):
    """Live market cap and TTM revenue for one peer, straight off marketdata."""
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
        die(f"peer {sym} has no market cap from the profile route")
    return {"sym": sym, "mcap": mcap / 1e6, "ttmRev": ttm,
            "ps": (mcap / 1e6) / ttm, "growth": (ttm / prior - 1) * 100}


def derive(snap, ep, fund, qrows, die, fact):
    """Return the extra snapshot keys Rocket Lab's slides need."""
    F = ep["filings"]
    fv = lambda *k: fact(F, *k)                                  # noqa: E731
    K = 1000.0                                                   # thousands -> millions

    # The share count is two components, both printed, both validated on their own.
    _shares = (fv("balanceSheet", "commonOutstanding")
               + fv("balanceSheet", "preferredOutstanding")) / 1000.0
    if abs(_shares - fv("balanceSheet", "sharesOutstanding")) > 1:
        die(f"shares outstanding {fv('balanceSheet','sharesOutstanding'):,.0f}k does not equal "
            f"common + preferred ({_shares:,.0f}k)")

    rev = fv("results", "revenueQ2") / K
    rev_prior = fv("results", "revenueQ2prior") / K
    op_loss = fv("results", "opLossQ2") / K
    gross = fv("results", "grossProfitQ2") / K

    # Segments must reconcile to the consolidated statement or one was mistyped.
    seg = F["segments"]
    if abs(sum(seg["revQ2"].values()) - fv("results", "revenueQ2")) > 1:
        die("segment revenue does not sum to consolidated revenue")
    if abs(sum(seg["grossQ2"].values()) - fv("results", "grossProfitQ2")) > 1:
        die("segment gross profit does not sum to the consolidated figure")

    launch = seg["revQ2"]["launch"] / K
    launch_prior = seg["revQ2prior"]["launch"] / K
    space = seg["revQ2"]["space"] / K
    space_prior = seg["revQ2prior"]["space"] / K
    sg = {
        "launchRev": launch, "launchPrior": launch_prior,
        "spaceRev": space, "spacePrior": space_prior,
        "launchChange": (launch / launch_prior - 1) * 100,
        "spaceChange": (space / space_prior - 1) * 100,
        "launchGross": seg["grossQ2"]["launch"] / K,
        "spaceGross": seg["grossQ2"]["space"] / K,
        "launchMargin": seg["grossQ2"]["launch"] / seg["revQ2"]["launch"] * 100,
        "launchMarginPrior": seg["grossQ2prior"]["launch"] / seg["revQ2prior"]["launch"] * 100,
        "spaceMargin": seg["grossQ2"]["space"] / seg["revQ2"]["space"] * 100,
        # Q1 falls out of the six-month figure minus Q2. Both are printed.
        "launchQ1": (seg["revH1"]["launch"] - seg["revQ2"]["launch"]) / K,
    }
    sg["launchSequential"] = (launch / sg["launchQ1"] - 1) * 100

    # The whole argument: revenue nearly doubled, the loss did not move.
    rows = F["quarterly"]["rows"]
    losses = [r["opLoss"] / K for r in rows]
    revs = [r["revenue"] / K for r in rows]
    flat = {
        "rows": [{"q": r["q"], "revenue": r["revenue"] / K, "opLoss": r["opLoss"] / K}
                 for r in rows],
        "revFirst": revs[0], "revLast": revs[-1],
        "revGrowthOverPeriod": (revs[-1] / revs[0] - 1) * 100,
        "lossFirst": losses[0], "lossLast": losses[-1],
        "lossChangeOverPeriod": (losses[-1] / losses[0] - 1) * 100,
        "lossMin": max(losses), "lossMax": min(losses),      # losses are negative
        "quarters": len(rows),
    }
    if flat["revGrowthOverPeriod"] < 50:
        die("the near-doubling claim does not hold on this data — re-check before shipping")

    # Cash, and what the Iridium cash bill does to it.
    net_cash = (fv("balanceSheet", "cash") + fv("balanceSheet", "securitiesCurrent")
                + fv("balanceSheet", "securitiesNonCurrent")) / K
    ir = F["iridium"]
    iridium_cash = fv("iridium", "cashPerShare") * fv("iridium", "targetShares")   # already $M
    cashpos = {
        "netCash": net_cash,
        "iridiumCash": iridium_cash,
        "shortfall": iridium_cash - net_cash,
        "coverPct": net_cash / iridium_cash * 100,
        "collarLow": fv("iridium", "collarLow"),
        "collarHigh": fv("iridium", "collarHigh"),
        "cashPerShare": fv("iridium", "cashPerShare"),
        "ratioCap": fv("iridium", "ratioCap"),
        "ratioFloor": fv("iridium", "ratioFloor"),
        "targetShares": fv("iridium", "targetShares"),
    }
    # Where the price sits in the collar, right now.
    price = snap["price"]
    cashpos["insideCollar"] = cashpos["collarLow"] <= price <= cashpos["collarHigh"]
    cashpos["aboveFloorPct"] = (price / cashpos["collarLow"] - 1) * 100
    cashpos["ratioNow"] = (cashpos["cashPerShare"] / price if cashpos["insideCollar"]
                           else (cashpos["ratioCap"] if price < cashpos["collarLow"]
                                 else cashpos["ratioFloor"]))
    cashpos["sharesToIssue"] = cashpos["ratioNow"] * cashpos["targetShares"]
    cashpos["dilutionPct"] = cashpos["sharesToIssue"] / snap["sharesNow"] * 100

    # Why the net loss improved: interest, not operations.
    interest = {
        "now": fv("results", "interestIncomeQ2") / K,
        "prior": fv("results", "interestIncomeQ2prior") / K,
    }
    interest["delta"] = interest["now"] - interest["prior"]
    net_now = fv("results", "netLossQ2") / K
    net_prior = fv("results", "netLossQ2prior") / K
    interest["netImprovement"] = net_now - net_prior              # positive = smaller loss
    interest["shareOfImprovement"] = interest["delta"] / interest["netImprovement"] * 100
    interest["opImprovement"] = op_loss - fv("results", "opLossQ2prior") / K

    # The adjusted-EBITDA bridge, and how much of it is share pay.
    sbc = F["sbc"]
    adj = {
        "opLoss": op_loss,
        "adjEbitda": fv("results", "adjEbitdaQ2") / K,
        "sbcTotal": (sbc["inGrossProfit"] + sbc["inRnd"] + sbc["inSga"]) / K,
        "gap": fv("results", "adjEbitdaQ2") / K - op_loss,
    }
    adj["sbcShareOfGap"] = adj["sbcTotal"] / adj["gap"] * 100

    # Opex, growing faster than the loss is shrinking.
    opex = {
        "rnd": fv("results", "rndQ2") / K, "rndPrior": fv("results", "rndQ2prior") / K,
        "sga": fv("results", "sgaQ2") / K, "sgaPrior": fv("results", "sgaQ2prior") / K,
        "total": fv("results", "opexQ2") / K, "totalPrior": fv("results", "opexQ2prior") / K,
    }
    opex["rndGrowth"] = (opex["rnd"] / opex["rndPrior"] - 1) * 100
    opex["sgaGrowth"] = (opex["sga"] / opex["sgaPrior"] - 1) * 100
    opex["totalGrowth"] = (opex["total"] / opex["totalPrior"] - 1) * 100

    # Guidance, and the record of hitting it.
    g = F["guidance"]
    guide = {
        "revLow": g["revLow"], "revHigh": g["revHigh"],
        "revMid": (g["revLow"] + g["revHigh"]) / 2,
        "adjLossLow": g["adjEbitdaLossLow"], "adjLossHigh": g["adjEbitdaLossHigh"],
        "gmLow": g["gaapGmLow"], "gmHigh": g["gaapGmHigh"],
        "sharesGuided": g["sharesGuided"], "preferredInGuide": g["preferredInGuide"],
    }
    guide["impliedGrowth"] = (guide["revMid"] / rev_prior_q3(rows, F) - 1) * 100 \
        if rev_prior_q3(rows, F) else None
    # Did each quarter land at or above the top of its guide? Both figures are filed.
    hits = []
    rels = F["earningsHistory"]["releases"]
    by_q = {r["q"]: r for r in rows}
    for i, rel in enumerate(rels[:-1]):
        nxt = rels[i + 1]["q"] if i + 1 < len(rels) else None
        actual = by_q.get(nxt)
        if not actual:
            continue
        hits.append({"q": nxt, "low": rel["guideLow"], "high": rel["guideHigh"],
                     "actual": actual["revenue"] / K,
                     "atOrAbove": actual["revenue"] / K >= rel["guideHigh"]})
    guide["hits"] = hits
    guide["hitCount"] = sum(1 for h in hits if h["atOrAbove"])
    guide["hitTotal"] = len(hits)

    # Valuation, on revenue only — there is no operating profit to value.
    annualised = rev * 4
    ttm_rev = sum(r["revenue"] for r in rows[-4:]) / K
    val = {
        "annualisedRev": annualised,
        "ttmRev": ttm_rev,
        "psAnnualised": snap["marketCap"] / annualised,
        "psTtm": snap["marketCap"] / ttm_rev,
        "evTtm": (snap["marketCap"] - net_cash) / ttm_rev,
    }

    total_debt = fv("balanceSheet", "convertibleNotes") / K

    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_ps = val["psTtm"]
    rows_p = sorted(peers + [{"sym": snap["symbol"], "ps": self_ps,
                              "growth": snap["ttmRevGrowth"]}], key=lambda x: -x["ps"])
    avg_ps = sum(p["ps"] for p in peers) / len(peers)
    # Iridium is the company being BOUGHT, not a comparable. Averaging it in and
    # then calling the result "what the defence companies cost" understated the
    # premium by a third (23.8x against a true 34.9x).
    dfn = set(F["peers"].get("defence") or [])
    if not dfn:
        die("peers block declares no `defence` set — a 'versus the primes' "
            "figure cannot be computed without knowing which peers those are")
    dfn_ps = [p["ps"] for p in peers if p["sym"] in dfn]
    if len(dfn_ps) != len(dfn):
        die(f"declared {len(dfn)} defence peers but priced {len(dfn_ps)}")
    avg_dfn = sum(dfn_ps) / len(dfn_ps)
    peerblock = {"rows": rows_p, "avgPs": avg_ps, "selfPs": self_ps,
                 "psPremium": self_ps / avg_ps,
                 "avgDefencePs": avg_dfn, "psPremiumDefence": self_ps / avg_dfn,
                 "defenceCount": len(dfn_ps),
                 "avgGrowth": sum(p["growth"] for p in peers) / len(peers)}

    return {
        "sg": sg, "flat": flat, "cashpos": cashpos, "interest": interest,
        "adj": adj, "opex": opex, "guide": guide, "val": val, "peers": peerblock,
        "gross": gross, "grossMargin": gross / rev * 100,
        "netDebt": total_debt - net_cash, "netCash": net_cash,
        "ev": snap["marketCap"] + (total_debt - net_cash),
        # Flat aliases so episode verdict prose can reference them as tokens.
        "rev": rev, "revGrowth": (rev / rev_prior - 1) * 100,
        "opLoss": op_loss, "opLossMin": flat["lossMin"], "opLossMax": flat["lossMax"],
        "revFirst": flat["revFirst"], "revOverPeriod": flat["revGrowthOverPeriod"],
        "launchRev": launch, "launchChangeAbs": abs(sg["launchChange"]),
        "netCashPos": net_cash, "totalDebt": total_debt,
        "iridiumCash": iridium_cash, "psAnnualised": val["psAnnualised"],
        "gmPct": gross / rev * 100,
        "shareGrowth": (snap["sharesNow"] / (fv("results", "wtdAvgSharesQ2") / 1e6) - 1) * 100,
        "insiderSold": F["insider"]["totalSoldValue"],
        "backlogTotal": fv("backlog", "total") * 1000,
        "backlogGrowth": fv("backlog", "growthPct"),
        "insiderTopValue": F["insider"]["topSellers"][0]["value"],
    }


def rev_prior_q3(rows, F):
    """Q3 last year, for the implied-growth read on this quarter's guide."""
    for r in rows:
        if r["q"] == "Q3'25":
            return r["revenue"] / 1000.0
    return None



def _actual_lab(h):
    """
    The magnitude rule drops the decimal at three significant figures, so a
    $122.569M actual against a $123M guide top printed "$123M" — the row then
    read "guided 117-123 ... $123M ... inside the range", the label flatly
    contradicting its own verdict. Keep a decimal in exactly that case.
    """
    from decks.fmt import usd
    if not h["atOrAbove"] and usd(h["actual"]) == usd(h["high"]):
        return usd(h["actual"], digits=1) if abs(h["actual"]) < 100 else \
               "$%.1fM" % h["actual"]
    return usd(h["actual"])


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s = snap
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    m = b_ = fmt.usd
    d2 = fmt.dollars
    dm = fmt.dollars0
    pc = fmt.pct
    MINUS = fmt.MINUS

    def x(n, d=1): return f"{n:.{d}f}&times;"        # prose — innerHTML
    def xt(n, d=1): return f"{n:.{d}f}×"             # chart labels — textContent
    _word = lambda n, cap=False: (                                        # noqa: E731
        lambda w: w.capitalize() if cap else w)(
        "zero one two three four five six seven eight nine ten".split()[int(n)]
        if n <= 10 else str(n))

    sg, flat, cp = s["sg"], s["flat"], s["cashpos"]
    ii, adj, ox, g, val, pb = s["interest"], s["adj"], s["opex"], s["guide"], s["val"], s["peers"]
    ptt = s["peakToTrough"]
    rev = s["rev"]
    reg = (s.get("quoteRegular") or {}).get("price")

    S = []

    # 01 -----------------------------------------------------------------
    S.append({
        "type": "title", "kicker": "Fundamental analysis · episode deck",
        "company": s["company"], "ticker": s["symbol"],
        "exchange": s["exchange"], "sector": s["sector"],
        "price": s["price"], "changePct": s["changePct"],
        "hook": (f"Q2 landed after the close tonight. The regular session finished at "
                 f"{d2(reg) if reg else 'the day&rsquo;s close'}; this is the after-hours print. "
                 f"Nothing is settled &mdash; but the filings already are."),
        "chips": [{"form": "8-K", "when": "Aug 10 2026"}, {"form": "10-Q", "when": "Aug 10 2026"},
                  {"form": "8-K", "when": "Iridium, Jun 29"}],
        "notes": N["title"], "target": 22,
    })

    # 02 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Where we are", "src": "Daily closes · two years",
        "head": f"A {abs(ptt['pct']):.0f}% fall, and most of the way back",
        "sub": (f"{d2(ptt['peak'])} on {ptt['peakWhen']} down to {d2(ptt['trough'])} on "
                f"{ptt['troughWhen']}, then a recovery into tonight's numbers."),
        "chart": {"kind": "line", "points": s["tape"], "height": 500, "markers": [
            {"i": s["high"]["i"], "lab": d2(s["high"]["v"]), "sub": s["high"]["when"]},
            {"i": s["low"]["i"], "lab": d2(s["low"]["v"]), "sub": s["low"]["when"]},
        ]},
        "why": ("This stock has already lost more than half its value once this year. The company "
                "did not do anything obviously wrong while it happened. That tells you what you are "
                "buying here: a price set almost entirely by what people believe about the next few "
                "years. Prices built on belief can halve on a change of mood, and this one has."),
        "notes": N["tape"], "target": 24,
    })

    # 03 -----------------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "Before the headline",
        "src": "All five from filings made tonight, or the eight quarters before them",
        "head": "What nobody else is going to show you",
        "items": ep["findings"],
        "why": ("Every one of these is in a document Rocket Lab filed with the SEC, most of them "
                "in the last few hours. None are in the headline of the press release. We will do "
                "each one properly."),
        "notes": N["findings"], "target": 26,
    })

    # 04 -----------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "What you are actually buying",
        "src": "10-Q Note 18, segments", "cols": 2,
        "head": "Two businesses, and only one of them is growing",
        "tiles": [
            {"v": b_(sg["launchRev"]), "l": "Launch Services",
             "n": f"flying Electron rockets · {pc(sg['launchChange'], 1)} year on year",
             "tone": "bad"},
            {"v": b_(sg["spaceRev"]), "l": "Space Systems",
             "n": f"satellites and components · {pc(sg['spaceChange'], 0)} year on year",
             "tone": "good"},
        ],
        "why": (f"Satellites and components are now {sg['spaceRev'] / rev * 100:.0f} cents of every "
                f"revenue dollar. The rockets are the smaller half, and they are getting smaller. "
                f"That split is the single most useful thing to carry through the rest of this: when "
                f"you hear Rocket Lab grew, it is almost entirely the factory, not the launch pad."),
        "notes": N["business"], "target": 22,
    })

    # 05 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And here is what the headline hides",
        "src": "10-Q Note 18 — the Launch Services column",
        "head": f"The rocket business shrank {abs(sg['launchChange']):.1f}%",
        "sub": (f"Revenue by segment, this quarter against the same quarter a year ago. "
                   f"The release leads with total revenue up "
                   f"{fv('contracts','revenueGrowthQ2')}%."),
        "chart": {"kind": "bars", "height": 470, "fmtKind": "pct0", "zeroLine": True,
                  "series": [
                      {"x": "Space Systems", "x2": f"{b_(sg['spacePrior'])} → {b_(sg['spaceRev'])}",
                       "v": sg["spaceChange"], "lab": pc(sg["spaceChange"], 0), "cls": "good"},
                      {"x": "Total revenue", "x2": f"{b_(s['rev'] / (1 + s['revGrowth']/100))} → {b_(rev)}",
                       "v": s["revGrowth"], "lab": pc(s["revGrowth"], 0), "cls": "mut"},
                      {"x": "Launch Services", "x2": f"{b_(sg['launchPrior'])} → {b_(sg['launchRev'])}",
                       "v": sg["launchChange"], "lab": pc(sg["launchChange"], 1), "cls": "bad"},
                  ]},
        "why": (f"Total revenue really did grow {pc(s['revGrowth'], 0)}. But the launch business "
                f"went backwards, from {b_(sg['launchPrior'])} to {b_(sg['launchRev'])}, and it "
                f"fell {abs(sg['launchSequential']):.0f}% from last quarter too. A company called "
                f"Rocket Lab is growing because of its satellite factory, not its rockets. That is "
                f"not a scandal &mdash; but it is a different company from the one most people "
                f"think they are buying."),
        "notes": N["segments"], "target": 30,
    })

    # 06 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "The growth itself is not in doubt",
        "src": "Seven quarters of guidance against seven quarters of results",
        "head": f"{_word(g['hitCount'], True)} of {_word(g['hitTotal'])} quarters at or above the top of their own guide",
        "sub": "Each quarter's actual revenue against the range management promised the quarter before.",
        "chart": {"kind": "dumbbell", "height": 470, "fmtKind": "usdM", "labelRoom": 430, "rows": [
            {"name": h["q"], "sub": f"guided {h['low']}–{h['high']}",
             "from": h["low"], "to": h["actual"],
             "fromLab": m(h["low"]), "toLab": _actual_lab(h),
             "delta": "at or above the top" if h["atOrAbove"] else "inside the range",
             "deltaGood": h["atOrAbove"]}
            for h in g["hits"]]},
        "why": (f"This is the strongest thing in the accounts and it deserves saying plainly: they "
                f"tell you what they will do and then they do it, {g['hitCount']} times out of "
                f"{g['hitTotal']} landing at or above the top of their own range. Very few companies "
                f"this young manage that. Whatever else follows, the revenue forecasting here is "
                f"real."),
        "notes": N["growth"], "target": 24,
    })

    # 07 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So put the loss underneath it",
        "src": "The operating loss line from eight consecutive quarterly 8-Ks",
        "head": f"Revenue grew {pc(flat['revGrowthOverPeriod'], 0)}. The loss did not move.",
        "sub": ("Quarterly revenue and quarterly operating loss, same scale, "
                f"{flat['quarters']} quarters."),
        "chart": {"kind": "smallmult", "height": 520, "panels": [
            {"label": "Revenue — up and up", "fmtKind": "usdM", "series": [
                {"x": r["q"], "v": r["revenue"], "lab": m(r["revenue"]),
                 "cls": "" if r is flat["rows"][-1] else "mut"} for r in flat["rows"]]},
            {"label": "Operating loss — going nowhere", "fmtKind": "usdM", "series": [
                {"x": r["q"], "v": r["opLoss"], "lab": m(r["opLoss"]), "cls": "bad"}
                for r in flat["rows"]]},
        ]},
        "why": (f"Revenue went from {b_(flat['revFirst'])} to {b_(flat['revLast'])} &mdash; "
                f"{pc(flat['revGrowthOverPeriod'], 0)} in {_word(flat['quarters'])} quarters. Over "
                f"the same stretch the operating loss went from {m(flat['lossFirst'])} to "
                f"{m(flat['lossLast'])}. It has not once left the band between "
                f"{m(flat['lossMax'])} and {m(flat['lossMin'])}. Every extra dollar of sales has "
                f"been spent. That can be a deliberate choice to build &mdash; but it means the "
                f"profit everyone is waiting for keeps moving one year further out."),
        "notes": N["flatloss"], "target": 32,
    })

    # 08 -----------------------------------------------------------------
    rev_prior_q = s["rev"] / (1 + s["revGrowth"] / 100)
    S.append({
        "type": "chart", "kicker": "Where the money went instead",
        "src": "8-K EX-99.1, operating expenses",
        "head": f"Costs grew {pc(ox['totalGrowth'], 0)} while revenue grew {pc(s['revGrowth'], 0)}",
        "sub": "Operating expenses, this quarter against the same quarter a year ago.",
        "chart": {"kind": "dumbbell", "height": 460, "fmtKind": "usdM", "labelRoom": 400, "rows": [
            # Revenue first, as the benchmark the other rows are judged against —
            # the headline's whole claim is that costs grew SLOWER than sales.
            {"name": "Revenue", "sub": "the benchmark for the rows below",
             "from": rev_prior_q, "to": s["rev"],
             "fromLab": m(rev_prior_q), "toLab": m(s["rev"]),
             "delta": pc(s["revGrowth"], 0), "deltaGood": True},
            {"name": "All operating costs", "sub": "the two rows below, added up",
             "from": ox["totalPrior"], "to": ox["total"],
             "fromLab": m(ox["totalPrior"]), "toLab": m(ox["total"]),
             "delta": pc(ox["totalGrowth"], 0), "deltaGood": False},
            {"name": "Research & development", "sub": "Neutron, mostly",
             "from": ox["rndPrior"], "to": ox["rnd"],
             "fromLab": m(ox["rndPrior"]), "toLab": m(ox["rnd"]),
             "delta": pc(ox["rndGrowth"], 0), "deltaGood": False},
            {"name": "Sales & admin", "sub": "including the acquisitions",
             "from": ox["sgaPrior"], "to": ox["sga"],
             "fromLab": m(ox["sgaPrior"]), "toLab": m(ox["sga"]),
             "delta": pc(ox["sgaGrowth"], 0), "deltaGood": False},
        ]},
        "why": (f"Development spending is up {pc(ox['rndGrowth'], 0)} and running the company costs "
                f"{pc(ox['sgaGrowth'], 0)} more than a year ago. Some of that buys Neutron, which is "
                f"the whole bull case. Some of it is the cost of having bought three companies. "
                f"Either way, the gross profit they added this year &mdash; "
                f"{m(s['gross'] - fv('results','grossProfitQ2prior')/1000)} of it &mdash; was almost "
                f"exactly consumed by the {m(ox['total'] - ox['totalPrior'])} of extra cost."),
        "notes": N["opex"], "target": 24, "optional": True,
    })

    # 09 -----------------------------------------------------------------
    S.append({
        "type": "mega", "kicker": "And be careful with the improving net loss",
        "src": "8-K EX-99.1, statements of operations",
        "head": "Most of the improvement is bank interest",
        "value": m(ii["delta"]), "tone": "warn",
        "caption": (f"Extra interest earned on the cash pile this quarter, out of a "
                    f"{m(ii['netImprovement'])} improvement in the net loss. The operating loss "
                    f"itself improved by {m(ii['opImprovement'])}."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:22px">'
                  f'<div class="tile"><div class="tv num">{m(ii["prior"])}</div>'
                  '<div class="tl">Interest earned a year ago</div></div>'
                  f'<div class="tile good"><div class="tv num">{m(ii["now"])}</div>'
                  '<div class="tl">Interest earned this quarter</div>'
                  f'<div class="tn">on {b_(s["netCash"])} of cash and securities</div></div>'
                  f'<div class="tile warn"><div class="tv num">{ii["shareOfImprovement"]:.0f}%</div>'
                  '<div class="tl">Of the whole improvement</div>'
                  '<div class="tn">came from interest, not from the business</div></div></div>'),
        "why": (f"The net loss shrank from {m(abs(fv('results','netLossQ2prior')/1000))} to "
                f"{m(abs(fv('results','netLossQ2')/1000))}, which reads like progress. But "
                f"{ii['shareOfImprovement']:.0f}% of that came from interest on the money they "
                f"raised. The business itself got {m(abs(ii['opImprovement']))} better. Interest on "
                f"a cash pile is real money &mdash; it is just not the same thing as the operation "
                f"working."),
        "notes": N["interest"], "target": 26,
    })

    # 10 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "The adjusted number, and what it leaves out",
        "src": "8-K EX-99.1, adjusted EBITDA reconciliation",
        "head": f"A {m(abs(adj['opLoss']))} loss, presented as {m(abs(adj['adjEbitda']))}",
        "sub": "How the operating loss becomes the adjusted figure in the headline.",
        "chart": {"kind": "bridge", "height": 500, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": adj["opLoss"], "lab": m(adj["opLoss"]),
             "x": "Operating loss", "x2": "what it actually lost", "cls": "bad"},
            {"type": "step", "v": adj["sbcTotal"], "lab": f"+{m(adj['sbcTotal'])[1:]}",
             "x": "Add back share pay", "x2": "paid in your ownership", "cls": "warn"},
            {"type": "step", "v": adj["gap"] - adj["sbcTotal"],
             "lab": f"+{m(adj['gap'] - adj['sbcTotal'])[1:]}",
             "x": "Add back the rest", "x2": "wear on kit, deal costs", "cls": "warn"},
            {"type": "total", "v": adj["adjEbitda"], "lab": m(adj["adjEbitda"]),
             "x": "Adjusted loss", "x2": "the number in the headline"},
        ]},
        "why": (f"The gap between the two numbers is {m(adj['gap'])}, and "
                f"{adj['sbcShareOfGap']:.0f}% of it is pay handed to staff in shares rather than "
                f"cash. No money leaves the bank, which is why it gets added back. It is still a "
                f"real cost to you, because every share issued makes your slice a little smaller "
                f"&mdash; and the share count is already up "
                f"{pc(s['shareGrowth'], 0)} on the weighted-average count."),
        "notes": N["ebitda"], "target": 28,
    })

    # 11 -----------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "None of which means the product is bad",
        "src": "10-Q Note 18 · 8-K EX-99.1", "cols": 3,
        "head": "They make good money on what they sell",
        "tiles": [
            {"v": f"{s['grossMargin']:.0f}%", "l": "Gross margin overall",
             "n": f"{m(s['gross'])} of gross profit on {b_(rev)} of sales", "tone": "good"},
            {"v": f"{sg['launchMargin']:.0f}%", "l": "On each launch",
             "n": f"up from {sg['launchMarginPrior']:.0f}% a year ago", "tone": "good"},
            {"v": f"{fv('results','nonGaapGrossMarginQ2')}%", "l": "Their adjusted figure",
             "n": "excludes share pay and deal amortisation"},
        ],
        "why": (f"Launch is the smaller business but it is now the better one per dollar: they keep "
                f"{sg['launchMargin']:.0f} cents in the dollar on a launch, up from "
                f"{sg['launchMarginPrior']:.0f} a year ago. The problem in these accounts is not "
                f"what things cost to build. It is everything spent below that line."),
        "notes": N["gross"], "target": 24, "optional": True,
    })

    # 12 -----------------------------------------------------------------
    S.append({
        "type": "quote", "kicker": "The backlog, and its footnote",
        "src": "8-K EX-99.1 — footnote 1 under the highlights",
        "head": "Record backlog, with an asterisk on every number",
        "quote": ("Includes options across various contracts."),
        "attr": "Rocket Lab Corporation, Q2 2026 press release, footnote 1",
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile good"><div class="tv num">{b_(fv("backlog","total") * 1000)}</div>'
                  '<div class="tl">Backlog at June 30</div>'
                  f'<div class="tn">up {fv("backlog","growthPct")}% in a year — a genuine record</div></div>'
                  f'<div class="tile warn"><div class="tv num">{m(fv("contracts","newLaunchContracts"))}</div>'
                  '<div class="tl">New launch contracts</div>'
                  '<div class="tn">footnote 1</div></div>'
                  f'<div class="tile warn"><div class="tv num">{m(fv("contracts","sbAmtiAward"))}</div>'
                  '<div class="tl">The Space Force award</div>'
                  '<div class="tn">footnote 1</div></div></div>'),
        "why": ("The backlog is real and it has more than doubled &mdash; that is a genuinely good "
                "number. But look at what that little 1 is attached to: the new launch contracts, "
                "the Space Force award, and the billion dollars of signings they say came after the "
                "quarter. All of them include options, and an option is something the customer may "
                "simply choose not to take. It does not make the figures wrong. It means they are "
                "the best case, not the committed case."),
        "notes": N["backlog"], "target": 26,
    })

    # 13 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Now the bill nobody is putting on screen",
        "src": "Iridium merger 8-K, June 29 · 10-Q balance sheet",
        "head": "They have promised more cash than they have",
        "sub": (f"The cash half of the Iridium deal against Rocket Lab's own cash and securities "
                f"at June 30."),
        "chart": {"kind": "bars", "height": 460, "fmtKind": "usdM", "series": [
            {"x": "Cash promised to Iridium", "x2": f"$27.00 a share on {cp['targetShares']:.1f}M shares",
             "v": cp["iridiumCash"], "lab": b_(cp["iridiumCash"]), "cls": "bad"},
            {"x": "Cash Rocket Lab holds", "x2": "cash plus marketable securities",
             "v": cp["netCash"], "lab": b_(cp["netCash"]), "cls": "mut"},
            {"x": "The gap", "x2": "to be borrowed, or raised",
             "v": cp["shortfall"], "lab": b_(cp["shortfall"]), "cls": "bad"},
        ]},
        "why": (f"The merger agreement pays Iridium shareholders $27.00 a share in cash, plus "
                f"stock. On Iridium's own filed share count that cash comes to about "
                f"{b_(cp['iridiumCash'])}. Rocket Lab is holding {b_(cp['netCash'])} &mdash; enough "
                f"to cover {cp['coverPct']:.0f}% of it. The rest has to come from borrowing, from "
                f"issuing shares, or from Iridium's own balance sheet. That is the single biggest "
                f"thing that could change this company, and it is a footnote in tonight's release."),
        "notes": N["iridium"], "target": 32,
    })

    # 14 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "And the share half moves with the price",
        "src": "Iridium merger 8-K — the exchange-ratio collar",
        "head": "The deal has a floor, and the stock is close to it",
        "sub": (f"Between {d2(cp['collarLow'])} and {d2(cp['collarHigh'])} Iridium holders receive "
                f"a fixed $27.00 of stock. Outside that band the ratio locks."),
        "chart": {"kind": "fvband", "height": 440,
                  # derived from the filed collar, not typed: (hi-lo)/(hi+lo)
                  "band": (cp["collarHigh"] - cp["collarLow"])
                          / (cp["collarHigh"] + cp["collarLow"]),
                  # mechanical band, not a verdict — see fv-n-* in the template
                  "zoneTone": "neutral",
                  "zoneLabs": ["below the floor — ratio stops moving",
                               "inside the band — a fixed $27.00 of stock",
                               "above the ceiling — ratio stops moving"],
                  "price": s["price"], "priceLab": d2(s["price"]),
                  "fairValue": (cp["collarLow"] + cp["collarHigh"]) / 2,
                  "fairLab": d2((cp["collarLow"] + cp["collarHigh"]) / 2),
                  "fairName": "middle of the band",
                  "rangeLo": cp["collarLow"], "rangeHi": cp["collarHigh"],
                  "rangeLoLab": f"floor {d2(cp['collarLow'])}",
                  "rangeHiLab": f"ceiling {d2(cp['collarHigh'])}",
                  "verdict": (f"{cp['aboveFloorPct']:.0f}% above the floor"
                              if cp["insideCollar"] else "outside the band")},
        "why": (f"At tonight's price the exchange ratio is {cp['ratioNow']:.4f} of a Rocket Lab "
                f"share for each Iridium share &mdash; about {cp['sharesToIssue']:.0f} million new "
                f"shares, roughly {cp['dilutionPct']:.0f}% more of the company. The lower the price "
                f"goes, the more shares that takes, until {d2(cp['collarLow'])}, where the ratio "
                f"stops moving. The stock is {cp['aboveFloorPct']:.0f}% above that floor tonight, "
                f"so this is not academic."),
        "notes": N["collar"], "target": 28,
    })

    # 15 -----------------------------------------------------------------
    ins = F["insider"]
    S.append({
        "type": "chart", "kicker": "What the people who run it are doing",
        "src": f"SEC Form 4 filings · {ins['totalFilings']} filings, 12 months",
        "head": f"{b_(ins['totalSoldValue'])} sold. Nothing bought.",
        "sub": ("Open-market transactions only, by recency. Grants, gifts and option exercises "
                "are excluded — those are not decisions to buy or sell."),
        "chart": {"kind": "insider", "height": 450, "rows": [
            {"label": r["label"], "sold": r["sold"], "bought": r["bought"],
             "soldLab": f"{r['sold']:,.0f} shares",
             "sub": f"~{b_(r['value'])} · {r['people']} people",
             "boughtLab": "none" if r["bought"] == 0 else f"{r['bought']:,.0f}"}
            for r in ins["buckets"]]},
        "why": (f"{_word(ins['distinctSellers'], True)} insiders sold about "
                f"{b_(ins['totalSoldValue'])} of their own shares over the year, "
                f"{b_(ins['topSellers'][0]['value'])} of it by "
                f"{ins['topSellers'][0]['name']}, the founder and chief executive. Not one of them "
                f"bought a share. And unlike some companies, most of this was not on autopilot: "
                f"only {ins['plan10b5Filings']} of the {ins['totalFilings']} filings mention a "
                f"pre-set plan. The heaviest selling &mdash; {b_(ins['buckets'][0]['value'])} "
                f"&mdash; was in the last three months, while the shares were falling."),
        "notes": N["insider"], "target": 32,
    })

    # 16 -----------------------------------------------------------------
    S.append({
        "type": "tiles", "kicker": "So what does it cost?",
        "src": "Live market cap ÷ reported revenue", "cols": 3,
        "head": "There are no earnings to value it on",
        "tiles": [
            {"v": xt(val["psTtm"], 0), "l": "Price to the last four quarters of sales",
             "n": f"{b_(val['ttmRev'])} of revenue", "tone": "bad"},
            {"v": xt(val["psAnnualised"], 0), "l": "Price to this quarter, annualised",
             "n": f"{b_(rev)} × 4", "tone": "bad"},
            {"v": "none", "l": "Price to earnings",
             "n": "the company has never earned an operating profit", "tone": "bad"},
        ],
        "why": (f"You cannot value this on profit because there is not any, so everything here is "
                f"on sales. {xt(val['psTtm'], 0)} the last four quarters of revenue. Take the "
                f"quarter just reported and multiply by four and it is still "
                f"{xt(val['psAnnualised'], 0)}. Whether that is sensible depends entirely on the "
                f"margin this business earns in five years' time &mdash; which nobody knows, "
                f"including management, who do not forecast it."),
        "notes": N["valuation"], "target": 26,
    })

    # 17 -----------------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Against the companies it competes with",
        "src": "Live market caps and trailing revenue, fetched at build time",
        "head": f"{x(pb['psPremiumDefence'], 1)} what the defence primes cost",
        "sub": ("Price to trailing revenue. Includes Iridium — the company Rocket Lab has agreed "
                "to buy — and four defence primes that all earn profits."),
        "chart": {"kind": "peers", "height": 480, "avg": pb["avgDefencePs"],
                  "avgLab": f"defence average {xt(pb['avgDefencePs'], 1)}",
                  "rightHead": "revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["ps"], "lab": xt(r["ps"], 1),
                            "right": pc(r["growth"], 0),
                            "here": r["sym"] == s["symbol"]} for r in pb["rows"]]},
        "why": (f"Rocket Lab grows far faster than any of these, and that is the point of it. But "
                f"look at where Iridium sits: each dollar of Iridium's sales costs a small fraction "
                f"of what a dollar of Rocket Lab's does. So they are buying something far cheaper "
                f"than themselves, and paying partly in their own expensive shares. That is a good "
                f"trade &mdash; for exactly as long as their own price holds up."),
        "notes": N["peers"], "target": 24,
    })

    # 18 -----------------------------------------------------------------
    _sc = [r["score"] for r in ep["verdict"]["scored"]]
    _strong = sum(1 for v in _sc if v >= 4)
    _weak = sum(1 for v in _sc if v <= 2)
    S.append({
        "type": "snapshot", "kicker": "The verdict", "src": "My call · not financial advice",
        "head": "Six dimensions, scored from the filings",
        "rows": [{"name": r["dim"], "score": r["score"], "fact": r["fact"], "tone": r["tone"]}
                 for r in ep["verdict"]["scored"]],
        "why": (f"{_word(_strong, True)} of the six score four or better, and both are about "
                f"demand: they sell more every quarter and the order book is full. The "
                f"{_word(_weak)} that score badly are about what happens to that revenue on the "
                f"way down the page, and what you are asked to pay for it."),
        "notes": N["verdict"], "target": 24,
    })

    # 19 -----------------------------------------------------------------
    S.append({
        "type": "twocol", "kicker": "Both sides, plainly",
        "src": "Everything on this slide traces to a filing",
        "head": "What's working, and what to watch",
        "leftHead": "What's working", "rightHead": "What to watch",
        "left": ep["verdict"]["working"], "right": ep["verdict"]["watch"],
        "notes": N["twolists"], "target": 20, "optional": True,
    })

    # 20 -----------------------------------------------------------------
    fvc = ep["fairValue"]; K = fvc["constants"]; c = fvc["cases"]["base"]; Hh = fvc["horizonYears"]

    def _fair(case):
        """Revenue out five years, a margin applied at the exit, discounted back."""
        gr = (1 + case["revGrowth"] / 100) ** Hh
        revenue = K["startRevenueTTM"] / 1000.0 * gr
        ebit = revenue * case["opMargin"] / 100
        pre = ebit - K["netDebt"] / 1000.0 * K["interestRate"] / 100
        net = pre * (1 - K["taxRate"] / 100)
        sh = s["sharesNow"] * (1 + case["shareChange"] / 100) ** Hh
        return (net / sh) * case["exitPE"] / (1 + fvc["requiredReturn"] / 100) ** Hh

    fair_base, fair_bear, fair_bull = (_fair(c), _fair(fvc["cases"]["bear"]),
                                       _fair(fvc["cases"]["bull"]))
    S.append({
        "type": "chart", "kicker": "So what is it worth?",
        "src": "My model · not financial advice · excludes the Iridium deal",
        "head": "Where the price sits against my own fair value",
        "sub": (f"My base case: {c['revGrowth']:.0f}% revenue growth every year for {Hh} years, "
                f"ending on a {c['opMargin']:.0f}% profit margin, no tax because of the losses "
                f"carried forward, and {c['shareChange']:.1f}% more shares a year. The bracket is "
                f"my worst and best cases."),
        "chart": {"kind": "fvband", "height": 440,
                  # derived from the filed collar, not typed: (hi-lo)/(hi+lo)
                  "band": (cp["collarHigh"] - cp["collarLow"])
                          / (cp["collarHigh"] + cp["collarLow"]),
                  # mechanical band, not a verdict — see fv-n-* in the template
                  "zoneTone": "neutral",
                  "zoneLabs": ["below the floor — ratio stops moving",
                               "inside the band — a fixed $27.00 of stock",
                               "above the ceiling — ratio stops moving"],
                  "price": s["price"], "priceLab": d2(s["price"]),
                  "fairValue": fair_base, "fairLab": d2(fair_base), "fairName": "my base case",
                  "rangeLo": fair_bear, "rangeHi": fair_bull,
                  "rangeLoLab": f"bear {d2(fair_bear)}", "rangeHiLab": f"bull {d2(fair_bull)}",
                  "verdict": f"{abs((s['price'] / fair_base - 1) * 100):.0f}% "
                             + ("over" if s["price"] > fair_base else "under") + " my base case"},
        "why": (f"Read the assumptions, because they are the whole answer. My base case has revenue "
                f"growing {c['revGrowth']:.0f}% a year for {Hh} years and a company that has never "
                f"made an operating profit ending on {c['opMargin']:.0f} cents in the dollar. That "
                f"lands at {d2(fair_base)}. Being properly optimistic &mdash; "
                f"{fvc['cases']['bull']['revGrowth']:.0f}% growth and "
                f"{fvc['cases']['bull']['opMargin']:.0f}% margins &mdash; gets to {d2(fair_bull)}. "
                f"And this deliberately ignores Iridium, which would change every input on the "
                f"slide."),
        "notes": N["fairvalue"], "target": 26,
    })

    # 21 -----------------------------------------------------------------
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

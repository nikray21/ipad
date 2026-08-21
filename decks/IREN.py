"""
decks/IREN.py — IREN Limited's derived metrics and slide narrative.

The tension: IREN's stock moves on standalone contract-announcement press
releases with no financial statements attached (the $2.8bn haul on Jul 20,
the ARR target raised twice), while the actual quarterly filings show total
revenue and Adjusted EBITDA falling for two straight quarters, a "record"
profit quarter that was 173% a one-time derivative gain, a ~$520M impairment
charge disclosed only in a 10-Q footnote, and an NVIDIA warrant priced well
above today's stock.

Two things this module is careful about:

  * IREN's own XBRL has a gap (Q4 FY25 net income is null in the pull), so the
    four-quarter revenue-mix series is built from the episode file's own
    `quarterly` block — each row read from the release that reports it,
    one GAAP basis throughout (post the IFRS-to-GAAP transition IREN completed
    in FY2025). `eps` is left null for every row: this deck does not argue
    from EPS, and a wild EPS swing from the one-time gain would mislead a
    price-vs-earnings chart that is never built.
  * The stock's biggest reaction this year (the Jul 20 8-K) is an
    Item 2.02 filing with no financial statements in it — the engine's
    quarterly earnings-reaction logic is not what explains this move, so the
    reaction is derived here directly from the daily bars around that date.
"""

import re

from . import fmt

LITERALS_OK = (
    "$520 million",              # the 10-Q's own stated estimate, quoted verbatim
    "600,000 NVIDIA GPUs",       # the contractual GPU-delivery milestone, a defined term
    "85% is now under contract", # quoted from the Jul 20 release
    "$3.4bn",                    # ARR target chart labels — fixed structural figures from
    "$3.7bn",                    # the releases, in the releases' own "bn" unit convention,
    "$4bn+",                     # not price-dependent
)


def _peer(sym, die):
    """One peer row: market cap over its latest reported quarter, annualized."""
    import marketdata as _md
    def g(route):
        try:
            return _md.get(route, sym)
        except Exception as e:                                    # noqa: BLE001
            die(f"cannot fetch {route} for peer {sym} ({e}) — peer multiples are computed "
                "live and never hand-entered, so the build stops here")
    prof, fu = g("profile"), g("fundamentals")
    qs = [q for q in fu["quarters"] if q.get("revenue")]
    if len(qs) < 5:
        die(f"peer {sym} has only {len(qs)} revenue quarters — need 5 for a year-over-year read")
    last, year_ago = qs[-1], qs[-5]
    mcap = prof.get("marketCapRaw")
    if not mcap:
        die(f"peer {sym} has no market cap from the profile route")
    ann = last["revenue"] * 1000 * 4                              # $B -> $M, annualized
    lab = last["label"][0] if isinstance(last["label"], (list, tuple)) else str(last["label"])
    return {"sym": sym, "mcap": mcap / 1e6, "ps": (mcap / 1e6) / ann,
            "growth": (last["revenue"] / year_ago["revenue"] - 1) * 100, "lastQ": lab}


def _fair(case, K, H, rr, shares_now):
    """Mirror of the template's runCase(), so verdict prose and the live
    calculator can never disagree at build time."""
    growth = (1 + case["revGrowth"] / 100) ** H
    rev = K["startRevenueTTM"] * growth
    ebit = rev * case["opMargin"] / 100
    pretax = ebit - K["netDebt"] * K["interestRate"] / 100
    net = pretax * (1 - K["taxRate"] / 100)
    nci = K["nciAnnualRunRate"] * growth
    shares = shares_now * (1 + case["shareChange"] / 100) ** H
    price5 = (net - nci) / shares * case["exitPE"]
    return price5 / (1 + rr / 100) ** H


def derive(snap, ep, fund, qrows, die, fact):
    F = ep["filings"]
    fv = lambda *k: fact(F, *k)                                   # noqa: E731

    # The revenue-mix series must add up: BTC + AI must equal the reported total.
    rows = F["quarterly"]["rows"]
    mix_src = {
        "Q4'25": ("btcRevFY25Q4", "aiRevFY25Q4", "revenueFY25Q4"),
        "Q1'26": ("btcRevQ1", "aiRevQ1", "revenueQ1"),
        "Q2'26": ("btcRevQ2", "aiRevQ2", "revenueQ2"),
        "Q3'26": ("btcRevQ3", "aiRevQ3", "revenueQ3"),
    }
    series = []
    for r in rows:
        btc_k, ai_k, tot_k = mix_src[r["q"]]
        btc, ai, tot = fv("results", btc_k), fv("results", ai_k), fv("results", tot_k)
        if abs((btc + ai) - tot) > 0.5:
            die(f"{r['q']}: Bitcoin ({btc}) + AI Cloud ({ai}) revenue does not sum to "
                f"the reported total ({tot})")
        if abs(tot - r["revenue"]) > 0.5:
            die(f"{r['q']}: quarterly.rows revenue ({r['revenue']}) does not match "
                f"results.{tot_k} ({tot})")
        series.append({"q": r["q"], "total": tot, "btc": btc, "ai": ai,
                       "aiShare": ai / tot * 100})

    peak = max(series, key=lambda s: s["total"])
    trough_after_peak = min(
        (s for s in series[series.index(peak):]), key=lambda s: s["total"])
    mix = {
        "series": series,
        "peakQ": peak["q"], "peakTotal": peak["total"],
        "lastQ": series[-1]["q"], "lastTotal": series[-1]["total"],
        "declineFromPeak": (series[-1]["total"] / peak["total"] - 1) * 100,
        "aiShareFirst": series[0]["aiShare"], "aiShareLast": series[-1]["aiShare"],
    }
    if mix["declineFromPeak"] >= 0:
        die("the deck claims revenue declined from its peak — it did not")

    # ARR promise path: each release's target, read off the four filings.
    arr = {
        "t1": fv("arr", "target1"), "t2": fv("arr", "target2"),
        "t3": fv("arr", "target3"), "t4": fv("arr", "target4"),
        "underContractPct": fv("arr", "underContractJul"),
    }
    if arr["t3"] <= arr["t2"] or arr["t4"] <= arr["t3"]:
        die("the deck claims the ARR target was raised twice — the sequence does not rise")
    ai_q3_ann = fv("results", "aiRevQ3") * 4
    arr["aiRunRateAnn"] = ai_q3_ann
    arr["targetVsRunRate"] = arr["t4"] / ai_q3_ann

    # The profit bridge: Q1 FY26's income statement, walked line by line.
    op_loss = fv("results", "opLossQ1")
    unreal = fv("results", "unrealizedGainQ1")
    other_net = (fv("results", "financeExpQ1") + fv("results", "interestIncQ1")
                 + fv("results", "realizedLossQ1") + fv("results", "fxLossQ1"))
    pretax_check = op_loss + unreal + other_net
    pretax = fv("results", "pretaxIncomeQ1")
    if abs(pretax_check - pretax) > 0.5:
        die(f"Q1 FY26 bridge does not reconcile: operating loss + unrealized gain + other "
            f"items = {pretax_check:.1f}, filed pretax income is {pretax}")
    net_check = pretax + fv("results", "taxExpenseQ1")
    net = fv("results", "netIncomeQ1")
    if abs(net_check - net) > 0.5:
        die(f"Q1 FY26 bridge does not reconcile after tax: {net_check:.1f} vs filed {net}")
    profit_bridge = {
        "opLoss": op_loss, "unrealizedGain": unreal, "otherNet": other_net,
        "pretax": pretax, "tax": fv("results", "taxExpenseQ1"), "net": net,
        "gainShareOfNet": unreal / net * 100,
    }

    # Impairment: the booked and the disclosed-but-not-booked must be distinct facts.
    imp = {
        "estimate": fv("impairment", "estimate"),
        "bookedQ3": fv("results", "impairmentQ3"),
        "bookedNineMonth": fv("impairment", "nineMonthBooked"),
    }
    if imp["bookedQ3"] > imp["bookedNineMonth"]:
        die("a single quarter's impairment cannot exceed the nine-month total")

    # NVIDIA warrant: strike vs today's price.
    nv = {
        "shares": fv("nvidia", "shares"), "proceeds": fv("nvidia", "proceeds"),
        "strike": fv("nvidia", "strikePrice"), "expiry": fv("nvidia", "expiry"),
        "gpuMilestone": fv("nvidia", "gpuMilestone"),
    }
    implied = nv["proceeds"] * 1e6 / nv["shares"]
    if abs(implied - nv["strike"]) > 0.5:
        die(f"NVIDIA warrant proceeds/shares implies ${implied:.2f}/share, "
            f"episode says ${nv['strike']:.2f}")
    nv["premiumToPrice"] = (nv["strike"] / snap["price"] - 1) * 100

    # Reaction: the Jul 20 8-K, not a quarterly earnings release, moved the
    # stock more than any release this year. Derived from the daily bars.
    import marketdata as _md
    import datetime
    bars = _md.get("history", snap["symbol"])["points"]
    idx = {datetime.datetime.fromtimestamp(b["t"] / 1000, datetime.timezone.utc)
           .strftime("%Y-%m-%d"): i for i, b in enumerate(bars)}
    rel_date = "2026-07-20"
    i = idx.get(rel_date)
    if i is None or i == 0:
        die(f"the {rel_date} release day is not in the daily bars — cannot state the reaction")
    base_vol = [b["v"] for b in bars[max(0, i - 31):i - 1]]
    react = {
        "date": rel_date,
        "move": (bars[i]["c"] / bars[i - 1]["c"] - 1) * 100,
        "volX": bars[i]["v"] / (sum(base_vol) / len(base_vol)) if base_vol else None,
    }
    if react["move"] <= 0:
        die("the deck claims the Jul 20 release was a positive reaction — it was not")

    # Fair value, mirrored from the on-camera calculator.
    K = ep["fairValue"]["constants"]
    total_debt = (fv("balanceSheet", "convertibleNotes")
                  + fv("balanceSheet", "financeLeaseCurrent")
                  + fv("balanceSheet", "financeLeaseNonCurrent"))
    cash = fv("balanceSheet", "cash")
    net_debt = total_debt - cash
    if abs(K["netDebt"] - net_debt) > 1.0:
        die(f"fairValue constants carry netDebt {K['netDebt']}, filings give {net_debt:.1f}")
    rate_derived = fv("results", "financeExpQ3") * 4 / total_debt * 100
    if abs(K["interestRate"] - rate_derived) > 0.1:
        die(f"fairValue interestRate {K['interestRate']}% vs derived {rate_derived:.2f}%")
    ttm = (fv("results", "revenueFY25Q4") + fv("results", "revenueQ1")
           + fv("results", "revenueQ2") + fv("results", "revenueQ3"))
    if abs(K["startRevenueTTM"] - ttm) > 1.0:
        die(f"fairValue startRevenueTTM {K['startRevenueTTM']} does not match the trailing "
            f"four reported quarters ({ttm:.1f})")

    H, rr = ep["fairValue"]["horizonYears"], ep["fairValue"]["requiredReturn"]
    fair = {k: _fair(c, K, H, rr, snap["sharesNow"])
            for k, c in ep["fairValue"]["cases"].items()}
    fair["mid"] = (fair["base"] + fair["bull"]) / 2
    if not (fair["bear"] < fair["base"] < fair["bull"]):
        die("fair-value cases are not monotonic bear < base < bull")

    # Peers, computed live — never typed. Self row on the same basis every peer
    # uses (latest reported quarter, annualized), with true year-over-year growth.
    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_ann = fv("results", "revenueQ3") * 4
    self_row = {"sym": snap["symbol"], "ps": snap["marketCap"] / self_ann,
                "growth": (fv("results", "revenueQ3") / fv("results", "revenueQ3FY25") - 1) * 100,
                "lastQ": "Q3'26"}
    prow = sorted(peers + [self_row], key=lambda x: -x["ps"])
    avg_ps = sum(p["ps"] for p in peers) / len(peers)
    pure = F["peers"].get("pure") or []
    if not pure:
        die("peers block declares no `pure` comparable set")
    pure_ps = [p["ps"] for p in peers if p["sym"] in pure]
    if len(pure_ps) != len(pure):
        die(f"declared {len(pure)} pure peers but priced {len(pure_ps)}")
    avg_pure_ps = sum(pure_ps) / len(pure_ps)
    crwv = next((p for p in peers if p["sym"] == "CRWV"), None)
    if crwv is None:
        die("CRWV is not in the peers list — the CoreWeave comparison has nothing to stand on")
    peerblock = {"rows": prow, "avgPs": avg_ps, "selfPs": self_row["ps"],
                 "psPremium": self_row["ps"] / avg_ps,
                 "avgPurePs": avg_pure_ps, "psRatioPure": self_row["ps"] / avg_pure_ps,
                 "crwvPs": crwv["ps"], "psRatioCrwv": self_row["ps"] / crwv["ps"],
                 "avgGrowth": sum(p["growth"] for p in peers) / len(peers)}

    ev = snap["marketCap"] + net_debt

    return {
        "mix": mix, "arr": arr, "profitBridge": profit_bridge, "imp": imp, "nv": nv,
        "react": react, "fair": fair, "peers": peerblock,
        "netDebt": net_debt, "totalDebt": total_debt, "ev": ev, "ttmRevFiled": ttm,
        "wd": {
            "declineFromPeak": mix["declineFromPeak"], "aiShareLast": mix["aiShareLast"],
            "targetVsRunRate": arr["targetVsRunRate"],
            "gainShareOfNet": profit_bridge["gainShareOfNet"],
            "impEstimate": imp["estimate"], "nvPremium": nv["premiumToPrice"],
        },
    }


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s = snap
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    m = b_ = fmt.usd
    d2 = fmt.dollars
    pc = fmt.pct
    MINUS = fmt.MINUS

    def x(n, d=1): return f"{n:.{d}f}&times;"
    def xt(n, d=1): return f"{n:.{d}f}×"
    _word = lambda n, cap=False: (                                       # noqa: E731
        lambda w: w.capitalize() if cap else w)(
        "zero one two three four five six seven eight nine ten".split()[int(n)]
        if n <= 10 else str(n))

    mix, arr, bridge, imp, nv = s["mix"], s["arr"], s["profitBridge"], s["imp"], s["nv"]
    react, fair, pb = s["react"], s["fair"], s["peers"]

    S = []

    # 01 — the hook -------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "The filings tell a different story",
        "src": "8-K EX-99.1, filed Jul 20 2026, plus the Q3 FY26 10-Q",
        "head": "What the filings say. The headlines don&rsquo;t.",
        "sub": f"After a {pc(react['move'], 0)} day on contract headlines, here is the paperwork.",
        "items": ep["findings"],
        "punch": (f"{_word(len(ep['findings']), True)} things they filed. "
                  f"<b>None made the press release.</b>"),
        "why": (f"IREN rose {pc(react['move'], 0)} on {react['date']} — {react['volX']:.0f} times "
                f"normal volume — on a press release announcing new contracts. No financial "
                f"statements were attached. These {_word(len(ep['findings']))} things are in the "
                f"documents the company actually filed with the SEC, and none of them made that "
                f"release. We take each one in turn."),
        "notes": N["findings"], "target": 24,
    })

    # 02 — the quarter as reported -----------------------------------------
    rev_q3 = fv("results", "revenueQ3")
    S.append({
        "type": "tiles", "kicker": "The scoreboard", "cols": 3,
        "src": "8-K EX-99.1, Q3 FY26 · quarter ended March 31 2026",
        "head": "Revenue down. AI Cloud growing. Still a loss.",
        "tiles": [
            {"v": b_(rev_q3), "l": "Total revenue", "hero": True,
             "n": f"down from {m(fv('results','revenueQ2'))} the quarter before", "tone": "warn"},
            {"v": b_(fv("results", "aiRevQ3")), "l": "AI Cloud revenue",
             "n": f"up from {m(fv('results','aiRevQ2'))} last quarter", "tone": "good"},
            {"v": b_(fv("results", "btcRevQ3")), "l": "Bitcoin-mining revenue",
             "n": f"down from {m(fv('results','btcRevQ2'))} last quarter", "tone": "bad"},
            {"v": m(fv("results", "netLossQ3")), "l": "Net loss, the quarter",
             "n": "no one-time gain landed this quarter", "tone": "bad"},
            {"v": b_(fv("results", "adjEbitdaQ3")), "l": "Adjusted EBITDA",
             "n": f"down from {b_(fv('results','adjEbitdaQ2'))} last quarter", "tone": "warn"},
            {"v": m(fv("results", "impairmentQ3")), "l": "Impairment, this quarter",
             "n": "mining hardware retired ahead of the GPU build-out", "tone": "bad"},
        ],
        "punch": (f"AI Cloud is <b>{fv('results','aiRevQ3')/rev_q3*100:.0f}% of revenue</b>. "
                  f"The rest is Bitcoin mining."),
        "why": (f"This is the quarter IREN actually reported, back in May: revenue of "
                f"{b_(rev_q3)}, down from {m(fv('results','revenueQ2'))} the quarter before. "
                f"A net loss of {m(abs(fv('results','netLossQ3')))}. Adjusted EBITDA is still "
                f"positive but shrinking. And of that revenue, {b_(fv('results','aiRevQ3'))} is "
                f"the AI Cloud business everyone is excited about — the rest, "
                f"{b_(fv('results','btcRevQ3'))}, is what remains of Bitcoin mining, and it is "
                f"falling fast. That is the real picture, and it is not what has moved this "
                f"stock this month."),
        "notes": N["scoreboard"], "target": 26,
    })

    # 03 — the revenue-mix trajectory, Finding 1 of 4 -----------------------
    S.append({
        "type": "chart", "kicker": "Finding 1 of 4",
        "src": "Q1–Q3 FY26 and FY25/Q4 8-K EX-99.1 releases, one GAAP basis",
        "head": f"Revenue is down {pc(abs(mix['declineFromPeak']), 0, signed=False)} "
                f"since the peak",
        "sub": "Total revenue across, AI Cloud&rsquo;s share of it up.",
        "chart": {"kind": "scatter", "height": 520, "fmtKind": "pct0",
                  "xTitle": "Total quarterly revenue →",
                  "yTitle": "AI Cloud share of revenue",
                  "points": [
                      dict({"x": q["total"], "y": q["aiShare"], "lab": q["q"]},
                           **({"sub": pc(q["aiShare"], 0, signed=False)}
                              if i in (0, len(mix["series"]) - 1) else {}))
                      for i, q in enumerate(mix["series"])
                  ]},
        "punch": (f"AI Cloud&rsquo;s share went "
                  f"<b>{pc(mix['aiShareFirst'], 0, signed=False)} to "
                  f"{pc(mix['aiShareLast'], 0, signed=False)}</b> as revenue shrank."),
        "why": (f"Watch the path, not just the endpoints. Revenue peaks in {mix['peakQ']} at "
                f"{b_(mix['peakTotal'])}, then falls for two quarters straight to "
                f"{b_(mix['lastTotal'])} — down {pc(abs(mix['declineFromPeak']), 0, signed=False)} "
                f"from the peak. Over that same stretch, AI Cloud's share of what is left climbs "
                f"from {pc(mix['aiShareFirst'], 0, signed=False)} to "
                f"{pc(mix['aiShareLast'], 0, signed=False)}. Both things "
                f"are true at once: the pivot to AI Cloud is real, and Bitcoin-mining revenue is "
                f"disappearing faster than AI Cloud can replace it. That is not a growth story "
                f"yet — it is a shrinking pie with a growing slice."),
        "notes": N["revenuemix"], "target": 28,
    })

    # 04 — the ARR promise path (context, not its own finding) --------------
    S.append({
        "type": "chart", "kicker": "So what is actually moving the stock?",
        "src": "8-K EX-99.1 releases, Nov 2025 – Jul 2026",
        "head": "A target raised twice in ten months",
        "sub": "Year-end AI Cloud annualized run-rate revenue — the number in every headline.",
        "chart": {"kind": "forecast", "height": 500, "fmtKind": "usdM",
                  "pastLab": "the original target", "futureLab": "raised twice since",
                  "points": [
                      {"x": "Nov '25", "v": arr["t1"], "lab": "$3.4bn"},
                      {"x": "Feb '26", "v": arr["t2"], "lab": "$3.4bn",
                       "growth": "reaffirmed"},
                      {"x": "May '26", "v": arr["t3"], "lab": "$3.7bn",
                       "growth": "RAISED", "guided": True},
                      {"x": "Jul '26", "v": arr["t4"], "lab": "$4bn+",
                       "growth": "RAISED again", "guided": True},
                  ]},
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile" style="animation-delay:700ms"><div class="tv num">'
                  f'{arr["underContractPct"]:.0f}%</div><div class="tl">Of the target, '
                  f'under contract</div><div class="tn">per the Jul 20 release</div></div>'
                  f'<div class="tile warn" style="animation-delay:1000ms"><div class="tv num">'
                  f'{b_(arr["aiRunRateAnn"])}</div><div class="tl">Actual AI Cloud run-rate</div>'
                  f'<div class="tn">Q3 FY26 revenue, annualized</div></div>'
                  f'<div class="tile bad" style="animation-delay:1300ms"><div class="tv num">'
                  f'{xt(arr["targetVsRunRate"], 0)}</div><div class="tl">Target vs. actual '
                  f'run-rate</div><div class="tn">the gap still to close</div></div></div>'),
        "punch": (f"The target is <b>{xt(arr['targetVsRunRate'], 0)}</b> the run-rate IREN has "
                  f"actually delivered."),
        "why": (f"This is the number that moves the stock: not quarterly revenue, but a "
                f"year-end run-rate target. November: {m(arr['t1'], 0)}. February: unchanged. "
                f"May: raised to {m(arr['t3'], 0)}. Three weeks ago: raised again, past "
                f"{m(arr['t4'], 0)}, with {arr['underContractPct']:.0f}% of it under contract. "
                f"Three headline-worthy revisions in ten months. Meanwhile, the AI Cloud revenue "
                f"IREN actually reported last quarter, annualized, comes to about "
                f"{b_(arr['aiRunRateAnn'])} — roughly {xt(arr['targetVsRunRate'], 0)} smaller "
                f"than the target. Getting there is not impossible. It is also not what is "
                f"happening yet."),
        "notes": N["arrpath"], "target": 28,
    })

    # 05 — the profit bridge, Finding 2 of 4 --------------------------------
    S.append({
        "type": "chart", "kicker": "Finding 2 of 4",
        "src": "8-K EX-99.1, Q1 FY26 Consolidated Statement of Operations",
        "head": "The &lsquo;record&rsquo; quarter, walked line by line",
        "sub": "Quarter ended September 30, 2025.",
        "chart": {"kind": "bridge", "height": 500, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": bridge["opLoss"], "lab": m(bridge["opLoss"]),
             "x": "Operating loss", "x2": "actual operations"},
            {"type": "step", "v": bridge["unrealizedGain"], "lab": f"+{b_(bridge['unrealizedGain'])}",
             "x": "Unrealized gain", "x2": "non-cash, on notes",
             "cls": "warn"},
            {"type": "step", "v": bridge["otherNet"],
             "lab": f"{MINUS}{b_(abs(bridge['otherNet']))[1:]}",
             "x": "Interest, FX, other", "x2": ""},
            {"type": "total", "v": bridge["pretax"], "lab": m(bridge["pretax"]),
             "x": "Before tax", "x2": ""},
            {"type": "step", "v": bridge["tax"], "lab": f"{MINUS}{b_(abs(bridge['tax']))[1:]}",
             "x": "Income tax", "x2": "", "cls": "warn"},
            {"type": "total", "v": bridge["net"], "lab": m(bridge["net"]),
             "x": "Net income", "x2": "the headline"},
        ]},
        "punch": (f"<b>{pc(bridge['gainShareOfNet'], 0, signed=False)} of the &lsquo;record&rsquo; "
                  f"profit</b> is a paper gain."),
        "why": (f"Back in September, IREN reported net income of {m(bridge['net'])} — a record, "
                f"and the headline everywhere. Walk it. Running the business that quarter "
                f"actually lost {m(abs(bridge['opLoss']))}. Add a {m(bridge['unrealizedGain'])} "
                f"unrealized gain — a paper markup on derivatives tied to its convertible notes, "
                f"nothing to do with selling compute — and a little more from interest and FX, "
                f"and the picture flips to {m(bridge['pretax'])} of income before tax. Subtract "
                f"tax, and you get the record quarter. {pc(bridge['gainShareOfNet'], 0, signed=False)} "
                f"of this company's only profitable quarter this year came from an accounting "
                f"mark, not from a customer."),
        "notes": N["bridge"], "target": 28,
    })

    # 06 — the pending impairment, Finding 3 of 4 ---------------------------
    S.append({
        "type": "mega", "kicker": "Finding 3 of 4",
        "src": "10-Q Subsequent Events note — absent from every press release",
        "head": "A charge not yet on the income statement",
        "value": m(imp["estimate"]), "tone": "bad",
        "caption": (f"of additional impairment IREN's own 10-Q estimates as it retires the rest "
                    f"of its Bitcoin-mining hardware at Childress — not yet booked."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(2,1fr);margin-top:22px">'
                  f'<div class="tile warn" style="animation-delay:700ms"><div class="tv num">'
                  f'{m(imp["bookedQ3"])}</div><div class="tl">Already booked, Q3 FY26 alone</div></div>'
                  f'<div class="tile warn" style="animation-delay:1000ms"><div class="tv num">'
                  f'{m(imp["bookedNineMonth"])}</div><div class="tl">Booked over nine months</div>'
                  f'<div class="tn">before this {m(imp["estimate"])} still to come</div></div></div>'),
        "punch": f"<b>{m(imp['estimate'])} more</b>, and it is only in the filing.",
        "why": (f"IREN is retiring its remaining Bitcoin-mining hardware at Childress to make "
                f"room for AI Cloud. The company's own estimate of what that costs: about "
                f"{m(imp['estimate'])} of additional impairment charges, not yet booked. That is "
                f"on top of {m(imp['bookedQ3'])} already written off last quarter alone, and "
                f"{m(imp['bookedNineMonth'])} over nine months. None of this number appears in a "
                f"single press release. It is only in the notes to the 10-Q."),
        "notes": N["impairment"], "target": 24,
    })

    # 07 — the NVIDIA warrant, Finding 4 of 4 --------------------------------
    S.append({
        "type": "mega", "kicker": "Finding 4 of 4",
        "src": "10-Q Subsequent Events note — NVIDIA Private Placement",
        "head": "NVIDIA bought an option, not just a contract",
        "value": d2(nv["strike"]), "tone": "warn",
        "caption": (f"the price NVIDIA can pay for up to {fmt.num(nv['shares'])} IREN shares "
                    f"— {pc(nv['premiumToPrice'], 0, signed=False)} above today&rsquo;s stock — "
                    f"but only as GPU deliveries hit volume milestones through {nv['expiry']}."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:22px">'
                  f'<div class="tile" style="animation-delay:700ms"><div class="tv num">'
                  f'{b_(nv["proceeds"])}</div><div class="tl">Max proceeds if fully exercised</div></div>'
                  f'<div class="tile" style="animation-delay:1000ms"><div class="tv num">'
                  f'{fmt.num(nv["gpuMilestone"])}</div><div class="tl">GPUs delivered to fully vest</div></div>'
                  f'<div class="tile" style="animation-delay:1300ms"><div class="tv num">'
                  f'{d2(s["price"])}</div><div class="tl">IREN&rsquo;s price today</div></div></div>'),
        "punch": f"NVIDIA is betting on <b>execution, not the stock price today</b>.",
        "why": (f"NVIDIA is not just selling IREN GPUs — it bought itself an option. The right "
                f"to buy {fmt.num(nv['shares'])} IREN shares at {d2(nv['strike'])} each, worth up "
                f"to {b_(nv['proceeds'])} if fully exercised. But it only vests as NVIDIA "
                f"actually delivers GPUs — up to {fmt.num(nv['gpuMilestone'])} of them — through "
                f"{nv['expiry']}. {d2(nv['strike'])} is {pc(nv['premiumToPrice'], 0, signed=False)} "
                f"above where the stock trades today. Read it as a signal, not a threat: NVIDIA "
                f"structured its own money so it only pays off if the build-out actually happens."),
        "notes": N["nvidia"], "target": 24,
    })

    # 08 — the peers ---------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So what does it cost?",
        "src": "Live market caps · each company's latest reported quarter, annualized",
        "head": "Cheap against miners, pricey against CoreWeave",
        "sub": "Market value against the latest quarter annualized, growth beside.",
        "chart": {"kind": "peers", "height": 470, "avg": pb["avgPs"],
                  "avgLab": f"peer average {xt(pb['avgPs'], 1)}",
                  "rightHead": "revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["ps"], "lab": xt(r["ps"], 1),
                            "right": pc(r["growth"], 0),
                            "here": r["sym"] == s["symbol"]} for r in pb["rows"]]},
        "punch": (f"IREN costs <b>{xt(pb['psRatioPure'], 1)}</b> its direct peers, "
                  f"<b>{xt(pb['psRatioCrwv'], 1)}</b> CoreWeave."),
        "why": (f"Same yardstick for everyone here: market value against the latest reported "
                f"quarter, annualized. Against its closest peers — the other Bitcoin miners "
                f"pivoting to AI Cloud — IREN actually trades {xt(pb['psRatioPure'], 1)} their "
                f"average price per dollar of sales, cheaper than Cipher Mining or TeraWulf. But "
                f"against CoreWeave, the biggest pure AI Cloud comparison, IREN costs "
                f"{xt(pb['psRatioCrwv'], 1)} as much per dollar of sales — and CoreWeave is "
                f"growing revenue faster. Cheap for a miner. Not cheap for an AI Cloud company."),
        "notes": N["peers"], "target": 22, "optional": True,
    })

    # 09 — the close: the whole argument as one ruler ------------------------
    band = (fair["bull"] - fair["mid"]) / fair["mid"]
    gap = (s["price"] / fair["bull"] - 1) * 100
    verdict_line = (f"today sits {pc(gap, 0, signed=False)} above even my bull case"
                    if gap > 0 else
                    f"today sits {pc(-gap, 0, signed=False)} below my bull case")
    S.append({
        "type": "chart", "kicker": "So what am I doing?",
        "src": "My call · my model, not financial advice",
        "head": "Real demand, priced for a lot to land.",
        "sub": "My model’s range, against today’s price.",
        "chart": {"kind": "fvband", "height": 430,
                  "band": band,
                  "price": s["price"], "priceLab": d2(s["price"]),
                  "fairValue": fair["mid"], "fairLab": d2(fair["mid"]),
                  "fairName": "where I’d get interested",
                  "rangeLo": fair["bear"], "rangeHi": fair["bull"],
                  "rangeLoLab": f"bear {d2(fair['bear'])}",
                  "rangeHiLab": f"bull {d2(fair['bull'])}",
                  "zoneLabs": ["below my base case",
                               "my base-to-bull range",
                               "above even the bull case"],
                  "verdict": verdict_line},
        "extra": ('<div class="whylist" style="margin-top:16px;gap:13px">'
                  f'<p style="animation-delay:900ms;font-size:23px">'
                  f'<b style="color:var(--good)">✓</b>&ensp;<b>The demand is real</b> — '
                  f'Microsoft and NVIDIA are paying, and IREN delivers on schedule.</p>'
                  f'<p style="animation-delay:1100ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>Revenue is shrinking</b> — '
                  f'down {pc(abs(mix["declineFromPeak"]), 0, signed=False)} from its peak, two '
                  f'quarters running.</p>'
                  f'<p style="animation-delay:1300ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>The profit was paper</b> — '
                  f'{pc(bridge["gainShareOfNet"], 0, signed=False)} of it a one-time gain, with '
                  f'{m(imp["estimate"])} of impairments still to book.</p>'
                  f'<p style="animation-delay:1500ms;font-size:23px">'
                  f'<b style="color:var(--crit)">✕</b>&ensp;<b>The target is '
                  f'{xt(arr["targetVsRunRate"], 0)}</b> the run-rate actually delivered so far.</p>'
                  f'</div>'),
        "punch": (f"My call: <b>{ep['verdict']['call']}</b>. Interesting "
                  f"<b>at {d2(fair['mid'])} or lower</b>."),
        "why": (f"That ruler is the whole episode. The bracket is my model: {d2(fair['bear'])} "
                f"if the transition goes roughly, {d2(fair['base'])} in my base case, and "
                f"{d2(fair['bull'])} in a bull case that needs IREN to get close to its own "
                f"promised numbers with real margins. Today's price {verdict_line}. Everything "
                f"genuinely working here — the contracts, the delivery record, NVIDIA's own "
                f"money — is already reflected in the price. What is not yet reflected: the "
                f"revenue slide, the paper profit, and {m(imp['estimate'])} that has not hit the "
                f"income statement. My line is {d2(fair['mid'])}, halfway between base and bull. "
                f"Near it or below, the odds start working for you. That is the fundamentals — "
                f"now let's go to the chart."),
        "notes": N["call"], "target": 30,
    })

    return S

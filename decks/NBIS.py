"""
decks/NBIS.py — Nebius Group's derived metrics and slide narrative.

The argument is one tension held for thirteen slides: **the fastest revenue
scale-up on the market, funded almost entirely by other people's money that the
filings say may be refundable.** Revenue is up 454% and the operating-leverage
curve is real — and the $4.5B of "operating cash flow" is 97.6% customer
prepayments, the half-year "profit" is a ClickHouse paper markup, the quarter's
loss was flattered by a depreciation-life change the release never mentions,
the whole top of the customer book turned over in a year, and insiders have
sold $157M against zero bought.

Four things this module is careful about:

  * **The XBRL quarters are wrong for NBIS.** The Toloka deconsolidation
    reclassified prior periods, so `fundamentals` disagrees with the filings
    before Q3 2025 and has no Q2 2026 at all. Every quarterly figure comes from
    the episode file, where each quarter is read from the release that shows it
    as the RESTATED comparative — one basis for the whole series.
  * **Nebius reports pre-market**, so the reaction session is the release day
    itself. The engine assumes after-the-close; its next-session moves are
    never rendered. This module derives the same-day move from the daily bars.
  * The company guides on ARR, not EPS, so the guidance path is built here from
    the releases and letters rather than the engine's midpoint tracker.
  * Peer multiples share ONE basis — market cap over the latest reported
    quarter annualized — because CoreWeave has too little history for a TTM
    comparison and mixing bases across rows is how a peer slide lies.
"""

import datetime
import re

from . import fmt

# Definitional label text and fixed contractual terms, not claims about the quarter.
LITERALS_OK = (
    "10% disclosure line",        # the SEC's significant-customer threshold — a
                                  # reporting constant, not a figure about Nebius
    "$1,200 for every $1,000",    # the March 2026 notes' accretion term, fixed by
                                  # the indenture and quoted from the filing
)


def _peer(sym, die):
    """One peer row: market cap over its latest reported quarter, annualized."""
    import marketdata as _md
    def g(route):
        try:
            return _md.get(route, sym)
        except Exception as e:                                   # noqa: BLE001
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
    ann = last["revenue"] * 1000 * 4                             # $B -> $M, annualized
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
    """Company-specific metrics. die() on anything that does not reconcile."""
    F = ep["filings"]
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    if not snap.get("newlyListed"):
        die("NBIS is built from the episode file because the XBRL quarters are wrong "
            "(Toloka reclassification) — the engine now has 8+ quarters, so re-verify "
            "the XBRL against the releases before trusting the trailing figures")

    # Share classes must sum to the stated total, or one of the three was mistyped.
    classes = fv("balanceSheet", "sharesClassA") + fv("balanceSheet", "sharesClassB")
    if abs(classes - fv("balanceSheet", "sharesOutstanding")) > 1:
        die(f"Class A + Class B ({classes:,.0f}k) does not equal shares outstanding "
            f"({fv('balanceSheet','sharesOutstanding'):,.0f}k)")

    # The income statement has to walk, or a fact is wrong.
    opex_sum = (fv("results", "costOfRevQ2") + fv("results", "prodDevQ2")
                + fv("results", "sgaQ2") + fv("results", "dnaQ2"))
    if abs(opex_sum - fv("results", "totalOpexQ2")) > 0.5:
        die(f"opex lines sum to {opex_sum:.1f}, filing total is {fv('results','totalOpexQ2'):.1f}")
    if abs((fv("results", "revenueQ2") - opex_sum) - fv("results", "opLossQ2")) > 0.5:
        die("revenue minus operating costs does not equal the filed operating loss")

    # The adjusted-EBITDA bridge must close on the filed reconciliation.
    ebitda_walk = (fv("results", "opLossQ2") + fv("results", "dnaQ2")
                   + fv("results", "sbcQ2") + fv("results", "acqCostsQ2"))
    if abs(ebitda_walk - fv("results", "adjEbitdaQ2")) > 0.5:
        die(f"operating loss + D&A + SBC + deal costs = {ebitda_walk:.1f}, "
            f"filed adjusted EBITDA is {fv('results','adjEbitdaQ2'):.1f}")

    # Balance sheet balances; deferred revenue halves sum to the note's total.
    if abs((fv("balanceSheet", "totalAssets") - fv("balanceSheet", "totalLiabilities"))
           - fv("balanceSheet", "equity")) > 0.5:
        die("assets minus liabilities does not equal equity")
    def_total = fv("balanceSheet", "deferredRevCurrent") + fv("balanceSheet", "deferredRevNonCurrent")
    if abs(def_total - fv("balanceSheet", "deferredRevTotal")) > 0.5:
        die("current + non-current deferred revenue does not equal the note's total")

    # The ClickHouse markup must reconcile the carrying values.
    if abs(fv("clickhouse", "carryingPrior") + fv("clickhouse", "gainH1")
           - fv("clickhouse", "carryingNow")) > 0.5:
        die("ClickHouse carrying value plus the gain does not reach the closing value")

    # The NVIDIA warrant's implied price is a derivation — recompute it.
    implied = fv("nvidia", "warrantProceeds") * 1e6 / fv("nvidia", "warrantShares")
    if abs(implied - fv("nvidia", "impliedPrice")) > 0.02:
        die(f"NVIDIA warrant implies ${implied:.2f}/share, episode says "
            f"${fv('nvidia','impliedPrice'):.2f}")

    rev = fv("results", "revenueQ2")
    rev_growth = (rev / fv("results", "revenueQ2prior") - 1) * 100

    # The eight-quarter series, one restated continuing-ops basis.
    rows = F["quarterly"]["rows"]
    series = [{"q": r["q"], "revenue": r["revenue"], "adjEbitda": r["adjEbitda"],
               "margin": r["adjEbitda"] / r["revenue"] * 100} for r in rows]
    if any(r["revenue"] <= 0 for r in series):
        die("a quarterly revenue is non-positive — the margin series is meaningless")
    if abs(series[-1]["revenue"] - rev) > 0.05:
        die("the series' latest quarter does not match the reported quarter")
    lev = {
        "series": series,
        "revFirst": series[0]["revenue"], "revLast": series[-1]["revenue"],
        "revMultiple": series[-1]["revenue"] / series[0]["revenue"],
        "marginFirst": series[0]["margin"], "marginLast": series[-1]["margin"],
        "quarters": len(series),
    }
    ttm_filed = sum(r["revenue"] for r in rows[-4:])

    # Cash: what the headline says against what running the business produced.
    cfo = fv("cashFlow", "cfoH1")
    prepay = fv("cashFlow", "deferredRevDeltaH1")
    cw = {
        "cfoH1": cfo, "prepayH1": prepay,
        "coreOpCash": cfo - prepay,
        "prepayShare": prepay / cfo * 100,
        "capexH1": fv("cashFlow", "capexH1"),
        "fcfH1": cfo - fv("cashFlow", "capexH1"),
        "raisedH1": fv("cashFlow", "financingH1"),
    }

    # The prepayment balance against the cash it inflates.
    cash = fv("balanceSheet", "cash")
    dr = {
        "total": fv("balanceSheet", "deferredRevTotal"),
        "prior": fv("balanceSheet", "deferredRevTotalPrior"),
        "shareOfCash": fv("balanceSheet", "deferredRevTotal") / cash * 100,
        "quartersOfRevenue": fv("balanceSheet", "deferredRevTotal") / rev,
    }

    # Depreciation-life change: what the quarter looks like without it.
    dep = {
        "cutQ2": fv("depreciationChange", "dnaReductionQ2"),
        "cutH1": fv("depreciationChange", "dnaReductionH1"),
        "netBenefitH1": fv("depreciationChange", "netBenefitH1"),
        "lossAsFiled": fv("results", "netLossQ2"),
        "lossOldLife": fv("results", "netLossQ2") - fv("depreciationChange", "netLossBenefitQ2"),
    }

    # Customer turnover, straight off the F-17 table.
    cu = {
        "oldTop": fv("customers", "custA_Q2_25") + fv("customers", "custB_Q2_25"),
        "newTop": (fv("customers", "custC_Q2_26") + fv("customers", "custD_Q2_26")
                   + fv("customers", "custE_Q2_26")),
        "a": fv("customers", "custA_Q2_25"), "b": fv("customers", "custB_Q2_25"),
        "c": fv("customers", "custC_Q2_26"), "d": fv("customers", "custD_Q2_26"),
        "e": fv("customers", "custE_Q2_26"),
    }
    cu["oldOthers"] = 100 - cu["oldTop"]
    cu["newOthers"] = 100 - cu["newTop"]

    # The order book, split by the filing's own recognition timing.
    rpo_total = fv("rpo", "total")
    rpo_24 = rpo_total * fv("rpo", "pctNext24mo") / 100
    rpo_48 = rpo_total * fv("rpo", "pctMo25to48") / 100
    rpo = {
        "total": rpo_total, "next24": rpo_24, "mo25to48": rpo_48,
        "after": rpo_total - rpo_24 - rpo_48,
        "vsTtm": rpo_total / ttm_filed, "ttmFiled": ttm_filed,
    }
    if rpo["after"] <= 0:
        die("the RPO timing split exceeds the total — check the percentages")

    # ARR path and the 2026 ask.
    arr = {
        "dec24": fv("arr", "dec24"), "sep25": fv("arr", "sep25"),
        "dec25": fv("arr", "dec25"), "mar26": fv("arr", "mar26"),
        "jun26": fv("arr", "jun26"),
        "g25Lo": fv("arr", "guide2025Low"), "g25Hi": fv("arr", "guide2025High"),
        "g25rLo": fv("arr", "guide2025RaisedLow"), "g25rHi": fv("arr", "guide2025RaisedHigh"),
        "g26Lo": fv("arr", "guide2026Low"), "g26Hi": fv("arr", "guide2026High"),
    }
    arr["g26Mid"] = (arr["g26Lo"] + arr["g26Hi"]) / 2
    arr["askX"] = arr["g26Lo"] / arr["jun26"]
    if arr["dec25"] <= arr["g25rHi"]:
        die("the deck claims the raised 2025 guide was beaten, but Dec-25 ARR is inside it")

    # Pre-market reporter: the reaction session IS the release day.
    import marketdata as _md
    bars = _md.get("history", snap["symbol"])["points"]
    idx = {datetime.datetime.fromtimestamp(b["t"] / 1000, datetime.timezone.utc)
           .strftime("%Y-%m-%d"): i for i, b in enumerate(bars)}
    rel_date = F["earningsHistory"]["releases"][-1]["date"]
    i = idx.get(rel_date)
    if i is None or i == 0:
        die(f"the {rel_date} release day is not in the daily bars — cannot state the reaction")
    base_vol = [b["v"] for b in bars[max(0, i - 31):i - 1]]
    react = {
        "date": rel_date,
        "move": (bars[i]["c"] / bars[i - 1]["c"] - 1) * 100,
        "volX": bars[i]["v"] / (sum(base_vol) / len(base_vol)) if base_vol else None,
    }

    # Debt, net debt, EV — and the fair-value constants must agree with them.
    total_debt = fv("balanceSheet", "debtCurrent") + fv("balanceSheet", "debtNonCurrent")
    net_debt = total_debt - cash
    K = ep["fairValue"]["constants"]
    if abs(K["netDebt"] - net_debt) > 0.5:
        die(f"fairValue constants carry netDebt {K['netDebt']}, filings give {net_debt:.1f}")
    rate_derived = fv("results", "interestExpQ2") * 4 / total_debt * 100
    if abs(K["interestRate"] - rate_derived) > 0.1:
        die(f"fairValue interestRate {K['interestRate']}% vs derived {rate_derived:.2f}%")
    guide_mid = (fv("guidance2026", "revLow") + fv("guidance2026", "revHigh")) / 2
    if abs(K["startRevenueTTM"] - guide_mid) > 0.5:
        die("fairValue startRevenueTTM is not the FY26 revenue-guide midpoint")

    # Valuation, on sales and on the company's own forward numbers.
    mcap = snap["marketCap"]
    val = {
        "annualisedQ2": rev * 4,
        "psAnnQ2": mcap / (rev * 4),
        "psArr": mcap / arr["jun26"],
        "psFy26": mcap / fv("guidance2026", "revHigh"),
        "psTtmFiled": mcap / ttm_filed,
    }

    # Fair value, mirrored from the on-camera calculator.
    H, rr = ep["fairValue"]["horizonYears"], ep["fairValue"]["requiredReturn"]
    fair = {k: _fair(c, K, H, rr, snap["sharesNow"])
            for k, c in ep["fairValue"]["cases"].items()}
    # "A decent price": the midpoint of my base and bull cases — under the
    # best-case value, without demanding the stock fall all the way to base.
    fair["mid"] = (fair["base"] + fair["bull"]) / 2

    # The half-year "profit" without the ClickHouse markup.
    ch = {
        "gain": fv("clickhouse", "gainH1"),
        "netIncomeH1": fv("results", "netIncomeH1"),
        "exGainH1": fv("results", "netIncomeH1") - fv("clickhouse", "gainH1"),
        "prior": fv("clickhouse", "carryingPrior"), "now": fv("clickhouse", "carryingNow"),
    }
    if ch["exGainH1"] >= 0:
        die("the deck claims the half year is a loss without ClickHouse — it is not")

    ins = F["insider"]
    if abs(sum(b["sold"] for b in ins["buckets"]) - ins["totalSoldShares"]) > 1:
        die("insider buckets do not sum to the total sold")

    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_row = {"sym": snap["symbol"], "ps": val["psAnnQ2"], "growth": rev_growth,
                "lastQ": "Q2'26"}
    prow = sorted(peers + [self_row], key=lambda x: -x["ps"])
    avg_ps = sum(p["ps"] for p in peers) / len(peers)
    pure = F["peers"].get("pure") or []
    if not pure:
        die("peers block declares no `pure` comparable — the versus-CoreWeave figure "
            "cannot be computed without knowing which peer that is")
    pure_ps = [p["ps"] for p in peers if p["sym"] in pure]
    if len(pure_ps) != len(pure):
        die(f"declared {len(pure)} pure peers but priced {len(pure_ps)}")
    peerblock = {"rows": prow, "avgPs": avg_ps, "selfPs": val["psAnnQ2"],
                 "psPremium": val["psAnnQ2"] / avg_ps,
                 "purePs": pure_ps[0], "psPremiumPure": val["psAnnQ2"] / pure_ps[0],
                 "avgGrowth": sum(p["growth"] for p in peers) / len(peers)}

    # Street: forward EPS from the engine's snapshot (already validated vs live).
    street_eps = [f for f in snap["fwd"]]
    if len(street_eps) < 2:
        die("fewer than two forward EPS estimates — the Street slide has nothing to stand on")

    return {
        "lev": lev, "cw": cw, "dr": dr, "dep": dep, "cu": cu, "rpo": rpo,
        "arr": arr, "react": react, "val": val, "fair": fair, "ch": ch,
        "peers": peerblock, "ttmFiled": ttm_filed,
        "netDebt": net_debt, "totalDebt": total_debt,
        "ev": mcap + net_debt,
        "revGrowth": rev_growth,
        # Flat aliases so episode verdict prose can reference them as tokens.
        "wd": {
            "rpoB": rpo_total / 1000.0,
            "arrDec25": arr["dec25"], "guide25Hi": arr["g25rHi"],
            "cash": cash, "raisedH1": cw["raisedH1"],
            "coreOpCash": cw["coreOpCash"], "defRev": dr["total"],
            "arrJun26": arr["jun26"], "guide26Lo": arr["g26Lo"], "guide26Hi": arr["g26Hi"],
            "insiderSold": ins["totalSoldValue"],
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

    def x(n, d=1): return f"{n:.{d}f}&times;"        # prose — innerHTML
    def xt(n, d=1): return f"{n:.{d}f}×"             # chart labels — textContent
    _word = lambda n, cap=False: (                                        # noqa: E731
        lambda w: w.capitalize() if cap else w)(
        "zero one two three four five six seven eight nine ten".split()[int(n)]
        if n <= 10 else str(n))

    lev, cw, dr, dep, cu = s["lev"], s["cw"], s["dr"], s["dep"], s["cu"]
    rpo, arr, val, fair, ch, pb = s["rpo"], s["arr"], s["val"], s["fair"], s["ch"], s["peers"]
    react = s["react"]
    ins = F["insider"]
    rev = fv("results", "revenueQ2")

    S = []

    # 01 — the hook -------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "Nobody reads these filings",
        "src": "Filed with the SEC on Aug 12 2026, plus the Form 4 trail",
        "head": "What the filings say. The release doesn&rsquo;t.",
        "sub": f"After a {pc(react['move'], 0)} one-day pop, here is the paperwork.",
        "items": ep["findings"],
        "punch": (f"{_word(len(ep['findings']), True)} things they filed. "
                  f"<b>None made the press release.</b>"),
        "why": (f"The stock rose {pc(react['move'], 0)} on {react['date']} — the reaction to this "
                f"release, on {react['volX']:.0f} times normal volume. Everyone has seen that "
                f"headline. These {_word(len(ep['findings']))} things are in the documents behind "
                f"it, and none of them made the press release. We take each one properly."),
        "notes": N["findings"], "target": 26,
    })

    # 02 — the quarter as reported ---------------------------------------
    S.append({
        "type": "tiles", "kicker": "The scoreboard · finding 1 of 5", "cols": 3,
        "src": "6-K EX-99.1, Q2 2026 highlights · quarter ended June 30 2026",
        "head": f"Revenue up {pc(s['revGrowth'], 0)}. Still losing money.",
        "tiles": [
            {"v": b_(rev), "l": "Revenue", "hero": True,
             "n": f"{pc(s['revGrowth'], 0)} on a year ago", "tone": "good"},
            {"v": b_(fv("results", "adjEbitdaQ2")), "l": "Adjusted EBITDA",
             "n": f"a {fv('results','adjEbitdaQ2')/rev*100:.0f}% margin, from "
                  f"{m(fv('results','adjEbitdaQ2prior'))} a year ago", "tone": "good"},
            {"v": m(fv("results", "opLossQ2")), "l": "Operating loss",
             "n": f"costs are still {fv('results','totalOpexQ2')/rev*100:.0f}% of revenue",
             "tone": "warn"},
            {"v": m(fv("results", "netLossQ2")), "l": "Net loss, the quarter",
             "n": "no revaluation gain landed in Q2", "tone": "bad"},
            {"v": m(fv("results", "interestExpQ2")), "l": "Interest bill, the quarter",
             "n": f"from {m(fv('results','interestExpQ2prior'))} a year ago", "tone": "bad"},
            {"v": b_(fv("cashFlow", "capexQ2")), "l": "Equipment bought, the quarter",
             "n": f"{x(fv('cashFlow','capexQ2')/rev, 1)} the quarter&rsquo;s entire revenue",
             "tone": "warn"},
        ],
        "punch": (f"The half-year &lsquo;profit&rsquo;: <b>a {m(ch['gain'])} ClickHouse "
                  f"paper markup</b>."),
        "why": (f"Revenue of {b_(rev)} is up {pc(s['revGrowth'], 0)} on a year ago, and their "
                f"own profit measure turned positive — they kept "
                f"{fv('results','adjEbitdaQ2')/rev*100:.0f} cents of each dollar before wear "
                f"on equipment and share pay. But underneath: an operating loss of "
                f"{m(abs(fv('results','opLossQ2')))}, a net loss of "
                f"{m(abs(fv('results','netLossQ2')))}. And the half-year profit of "
                f"{m(ch['netIncomeH1'])}? {m(ch['gain'])} of it is the ClickHouse markup — a "
                f"stake marked up because someone else's funding round set a new price. "
                f"Without it, the half year is a {m(abs(ch['exGainH1']))} loss. Every profit "
                f"this company has ever reported is a markup, not margin."),
        "notes": N["quarter"], "target": 28,
    })

    # 03 — the leverage curve ---------------------------------------------
    S.append({
        "type": "chart", "kicker": "And the growth is not the trick",
        "src": "Eight quarterly releases, continuing operations, one restated basis",
        "head": f"{xt(lev['revMultiple'], 0)} the revenue in eight quarters",
        "sub": "Each dot is a quarter — revenue across, margin up.",
        "chart": {"kind": "scatter", "height": 520, "fmtKind": "pct0",
                  "xTitle": "Revenue per quarter →",
                  "yTitle": "Adjusted EBITDA margin",
                  # Selective labels: the first four quarters cluster in the
                  # bottom-left (tiny revenue), so naming each collides in the
                  # camera layout. Anchor the start, the first positive quarter
                  # and the end; `sub` (the margin) on the endpoints only.
                  "points": [
                      dict({"x": q["revenue"], "y": q["margin"],
                            "lab": q["q"] if i in (0, 5, len(lev["series"]) - 1) else ""},
                           **({"sub": pc(q["margin"], 0)}
                              if i in (0, len(lev["series"]) - 1) else {}))
                      for i, q in enumerate(lev["series"])
                  ]},
        "punch": (f"Margins went <b>{pc(lev['marginFirst'], 0)} to "
                  f"{pc(lev['marginLast'], 0)}</b>."),
        "why": (f"Two years ago this was a {m(lev['revFirst'])} quarter losing "
                f"{abs(lev['marginFirst'])/100:.2f} dollars for every dollar it sold. Eight "
                f"quarters later revenue is {x(lev['revMultiple'], 0)} bigger at {b_(rev)}, and "
                f"on their own profit measure they keep {lev['marginLast']:.0f} cents per "
                f"dollar — the AI cloud business alone kept {fv('results','aiCloudMarginQ2')} "
                f"cents. Every cost line is falling as a share of sales. This is what real "
                f"scale economics look like drawn as one line, and it is the strongest true "
                f"thing in these filings."),
        "notes": N["leverage"], "target": 26,
    })

    # 04 — the ARR path and the ask ---------------------------------------
    S.append({
        "type": "chart", "kicker": "So they promise far more",
        "src": "ARR from the releases and shareholder letters, each figure dated",
        "head": "Their scoreboard number: one miss, one beat",
        "sub": "Annualized run-rate revenue, against each December guide.",
        "chart": {"kind": "forecast", "height": 500, "fmtKind": "usdM",
                  "pastLab": "reported", "futureLab": "the guide",
                  "points": [
                      {"x": "Dec '24", "v": arr["dec24"], "lab": m(arr["dec24"]),
                       "growth": "missed"},
                      {"x": "Sep '25", "v": arr["sep25"], "lab": m(arr["sep25"])},
                      {"x": "Dec '25", "v": arr["dec25"], "lab": m(arr["dec25"], 2),
                       "growth": "beat the raised guide"},
                      {"x": "Mar '26", "v": arr["mar26"], "lab": m(arr["mar26"], 1)},
                      {"x": "Jun '26", "v": arr["jun26"], "lab": m(arr["jun26"])},
                      {"x": "Dec '26", "v": arr["g26Mid"],
                       "lab": f"{m(arr['g26Lo'])}–{m(arr['g26Hi'])}",
                       "growth": "the ask", "guided": True},
                  ]},
        "punch": (f"The 2026 guide needs <b>{m(arr['jun26'])} to become "
                  f"{m(arr['g26Lo'])}–{m(arr['g26Hi'])}</b> by December."),
        "why": (f"This is the number Nebius guides on — one month's sales, times twelve. "
                f"December 2024: {m(arr['dec24'])} — their own release calls it a miss. "
                f"Then they promised {m(arr['g25Lo'])} to {m(arr['g25Hi'], 0)} "
                f"for the end of 2025, raised it in August, and delivered {m(arr['dec25'], 2)} "
                f"— a genuine beat. It stands at {m(arr['jun26'])} now. But look at the last "
                f"point. The 2026 promise of {m(arr['g26Lo'])} to {m(arr['g26Hi'])} needs this "
                f"number to more than double again in six months. They have done it before. "
                f"They are asking you to believe they do it again, on a number ten times "
                f"bigger."),
        "notes": N["arrpath"], "target": 30,
    })

    # 05 — the order book --------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Backed by contracts this size",
        "src": "RPO note in the Q2 financials · Microsoft and Meta 6-Ks",
        "head": f"{b_(rpo['total'])} of contracts already signed",
        "sub": (f"Microsoft signed up to {b_(fv('rpo','msftTcvMax'))}; "
                f"Meta about {b_(fv('rpo','metaTcv'))}."),
        "chart": {"kind": "stackedh", "height": 430, "labelRoom": 240, "rows": [
            {"name": "Signed contracts", "sub": "work promised, not yet delivered",
             "totalLab": b_(rpo["total"]), "segs": [
                 {"v": rpo["next24"], "lab": f"{b_(rpo['next24'])} · next 2 yrs", "cls": "s1"},
                 {"v": rpo["mo25to48"], "lab": f"{b_(rpo['mo25to48'])} · yrs 3–4", "cls": "cool"},
                 {"v": rpo["after"], "lab": f"{b_(rpo['after'])} · later", "cls": "mut"},
             ]},
            {"name": "Revenue, last 12 months", "sub": "the four reported quarters",
             "totalLab": b_(rpo["ttmFiled"]), "segs": [
                 # no seg label — the sliver's value is already the row total,
                 # and a float above duplicates it
                 {"v": rpo["ttmFiled"], "cls": "mut"},
             ]},
        ]},
        "punch": (f"<b>{xt(rpo['vsTtm'], 0)} everything they sold</b> in the last "
                  f"twelve months."),
        "why": (f"Here is the case that the double happens: {b_(rpo['total'])} of signed work "
                f"they have not yet delivered. Microsoft alone signed for about "
                f"{b_(fv('rpo','msftTcv'))}, expandable to {b_(fv('rpo','msftTcvMax'))}, "
                f"through 2031. Meta added roughly {b_(fv('rpo','metaTcv'))}. The bottom bar "
                f"is everything Nebius actually sold in the last twelve months — "
                f"{b_(rpo['ttmFiled'])} — so the order book is {x(rpo['vsTtm'], 0)} that. Two "
                f"footnotes. Only {fv('rpo','pctNext24mo')}% of it becomes revenue inside two "
                f"years. And their own annual report admits they have, quote, limited "
                f"experience delivering longer-term customer contracts. The mountain is real. "
                f"So is the climb."),
        "notes": N["rpo"], "target": 28,
    })

    # 06 — the cash walk ---------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Finding 2 of 5 — now the cash",
        "src": "6-K EX-99.2 cash flow statement · MD&A liquidity section",
        "head": "Where the operating cash flow really came from",
        "sub": "Six months ended June 30, 2026.",
        "chart": {"kind": "bridge", "height": 500, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": cw["cfoH1"], "lab": b_(cw["cfoH1"]),
             "x": "Operating cash flow", "x2": "the headline figure"},
            {"type": "step", "v": -cw["prepayH1"], "lab": f"{MINUS}{b_(cw['prepayH1'])[1:]}",
             "x": "Customer prepayments", "x2": "deferred revenue, paid years ahead",
             "cls": "warn"},
            {"type": "total", "v": cw["coreOpCash"], "lab": m(cw["coreOpCash"]),
             "x": "From running the business", "x2": "what operations produced"},
        ]},
        "punch": f"<b>{pc(cw['prepayShare'], 1, signed=False)} of it</b> is customers paying years ahead.",
        "why": (f"The headline says {b_(cw['cfoH1'])} of operating cash flow in six months — "
                f"it reads like a money machine. Walk it. {b_(cw['prepayH1'])} of that is "
                f"customers paying up front for compute not yet delivered, booked over as much "
                f"as five years. Running the business actually produced "
                f"{m(cw['coreOpCash'])} — against {b_(cw['capexH1'])} spent on equipment. "
                f"The gap was "
                f"filled by raising {b_(cw['raisedH1'])} in new money — and the first of "
                f"those convertible bonds comes due in 2029, with the newest repaying "
                f"$1,200 for every $1,000 borrowed at maturity. This company is not "
                f"self-funding. It is customer-funded and debt-funded."),
        "notes": N["cashwalk"], "target": 32,
    })

    # 07 — whose money is it -----------------------------------------------
    S.append({
        "type": "quote", "kicker": "Finding 2 of 5 — whose money is that?",
        "src": "Deferred Revenue note (F-18) · Interest Expense note (F-19)",
        "head": "Most of that cash is not theirs yet",
        "quote": ("The Group recognizes deferred revenue when cash is received and before "
                  "performance obligations are fulfilled, including amounts that may be "
                  "refundable."),
        "attr": "Nebius Group, Deferred Revenue note, page F-18 — emphasis mine",
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile warn" style="animation-delay:700ms"><div class="tv num">{b_(dr["total"])}</div>'
                  '<div class="tl">Prepayments held</div>'
                  f'<div class="tn">up from {b_(dr["prior"])} in December</div></div>'
                  f'<div class="tile bad" style="animation-delay:1000ms"><div class="tv num">{dr["shareOfCash"]:.0f}%</div>'
                  '<div class="tl">Of all cash on the balance sheet</div>'
                  f'<div class="tn">{b_(fv("balanceSheet","cash"))} of cash held</div></div>'
                  '<div class="tile bad" style="animation-delay:1300ms"><div class="tv num">+ interest</div>'
                  '<div class="tl">Paid on customer advances</div>'
                  '<div class="tn">the interest note, F-19</div></div></div>'),
        "punch": (f"Prepayments equal <b>{dr['shareOfCash']:.0f}% of all cash</b> "
                  f"&mdash; and accrue interest."),
        "why": (f"That is the company's own note, word for word — including amounts that may "
                f"be refundable. They never say how much. The balance is {b_(dr['total'])}, up "
                f"from {b_(dr['prior'])} in December. That equals {dr['shareOfCash']:.0f}% of "
                f"the {b_(fv('balanceSheet','cash'))} of cash on the balance sheet, and about "
                f"{dr['quartersOfRevenue']:.0f} quarters of current revenue. And buried in the "
                f"interest note: they pay interest on advances from major customers. A "
                f"prepayment you pay interest on is a loan wearing a different name. The cash "
                f"pile is real — but most of it is other people's money, with strings."),
        "notes": N["refundable"], "target": 28,
    })

    # 08 — the depreciation change ----------------------------------------
    S.append({
        "type": "mega", "kicker": "Finding 3 of 5 — the quiet accounting change",
        "src": "Use of Estimates note (F-9) — absent from the press release",
        "head": "One sentence in January flattered every 2026 number",
        "value": m(dep["cutQ2"]), "tone": "warn",
        "caption": (f"of depreciation removed from this quarter alone, by deciding servers "
                    f"last five years instead of four — and the disclosed effect covers only "
                    f"equipment owned before 2026."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:22px">'
                  f'<div class="tile" style="animation-delay:700ms"><div class="tv num">{m(dep["lossAsFiled"])}</div>'
                  '<div class="tl">Q2 net loss, as filed</div></div>'
                  f'<div class="tile warn" style="animation-delay:1000ms"><div class="tv num">{m(dep["lossOldLife"])}</div>'
                  '<div class="tl">On the old four-year life</div>'
                  '<div class="tn">the same quarter, one assumption back</div></div>'
                  f'<div class="tile bad" style="animation-delay:1300ms"><div class="tv num">{m(dep["netBenefitH1"])}</div>'
                  '<div class="tl">Added to half-year income</div>'
                  '<div class="tn">excluding everything bought in 2026</div></div></div>'),
        "punch": (f"Without it, this quarter&rsquo;s loss reads <b>{m(abs(dep['lossOldLife']))}, "
                  f"not {m(abs(dep['lossAsFiled']))}</b>."),
        "why": (f"This finding is one sentence in the estimates note. In January, Nebius "
                f"decided its servers last five years instead of four. Legal, and maybe even "
                f"right. But run their own numbers. The change cut this quarter's "
                f"wear-and-tear charge by {m(dep['cutQ2'])}. So the {m(abs(dep['lossAsFiled']))} "
                f"loss would have been {m(abs(dep['lossOldLife']))} on the old life. And the "
                f"stated benefit covers only servers owned before 2026. The {b_(cw['capexH1'])} "
                f"of equipment bought this half gets the friendlier math too, and that part is "
                f"not measured anywhere. The press release does not mention any of it."),
        "notes": N["depreciation"], "target": 26,
    })

    # 09 — the customer turnover ------------------------------------------
    S.append({
        "type": "chart", "kicker": "Finding 4 of 5 — the customers all changed",
        "src": "Significant Customers table (F-17) — the filing's own letters",
        "head": "The entire top of the customer list changed",
        "sub": "Share of quarterly revenue, as the filing labels them.",
        "chart": {"kind": "stackedh", "height": 430, "labelRoom": 220, "rows": [
            {"name": "Q2 2025", "sub": "a year ago",
             "totalLab": "",
             "segs": [
                 {"v": cu["a"], "lab": f"A · {cu['a']:.0f}%", "cls": "s1"},
                 {"v": cu["b"], "lab": f"B · {cu['b']:.0f}%", "cls": "cool"},
                 {"v": cu["oldOthers"], "lab": f"everyone else · {cu['oldOthers']:.0f}%",
                  "cls": "mut"},
             ]},
            {"name": "Q2 2026", "sub": "this quarter",
             "totalLab": "",
             # alternate the two series colours so no two adjacent segments
             # share a fill — D and E both blue read as one giant customer
             "segs": [
                 {"v": cu["c"], "lab": f"C · {cu['c']:.0f}%", "cls": "s1"},
                 {"v": cu["d"], "lab": f"D · {cu['d']:.0f}%", "cls": "cool"},
                 {"v": cu["e"], "lab": f"E · {cu['e']:.0f}%", "cls": "s1"},
                 {"v": cu["newOthers"], "lab": f"everyone else · {cu['newOthers']:.0f}%",
                  "cls": "mut"},
             ]},
        ]},
        "punch": ("Last year&rsquo;s two biggest buyers: <b>both gone from the table</b>."),
        "why": (f"The customer list did not grow — it was replaced. A year ago, customers A "
                f"and B carried {cu['oldTop']:.0f}% of all revenue between them. This quarter, "
                f"both fell below the 10% disclosure line. Three new names — C, D and E, "
                f"almost certainly including Microsoft and Meta — now carry "
                f"{cu['newTop']:.0f}%. Moving up from startups to giant tech firms is good "
                f"news. But see the shape of the risk. Three buyers now decide this company's "
                f"future. None of them were here a year ago. If one walks, it is a different "
                f"company."),
        "notes": N["customers"], "target": 26,
    })

    # 10 — the insiders -----------------------------------------------------
    S.append({
        "type": "chart", "kicker": "Finding 5 of 5 — what insiders did",
        "src": f"SEC Form 4 XML — {ins['totalFilings']} filings, aggregated and recomputed",
        "head": f"{m(ins['totalSoldValue'])} sold. Nothing bought.",
        "sub": "Shares sold on the market since March 2026, by month.",
        "chart": {"kind": "insider", "height": 460, "rows": [
            {"label": b["label"], "sold": b["sold"], "bought": b["bought"],
             "soldLab": f"{b['sold']:,.0f} shares",
             "sub": f"~{m(b['value'])} · {b['people']} people",
             "boughtLab": "none" if b["bought"] == 0 else f"{b['bought']:,.0f}"}
            for b in ins["buckets"]]},
        "punch": "The founder, the CFO, the CTO &mdash; <b>all sellers</b>.",
        "why": (f"Nebius insiders only began filing these forms in March 2026. Since then, "
                f"{_word(ins['distinctSellers'])} of them sold {m(ins['totalSoldValue'])} of "
                f"stock: the founder, the CFO, the CTO, the sales chief, and the "
                f"infrastructure chief — who sold {m(ins['topSellers'][0]['value'])} of it "
                f"alone. Shares bought with their own money over the same stretch: zero. To be "
                f"fair, {ins['plan10b5Filings']} of the {ins['totalFilings']} filings cite "
                f"plans set up months ahead, and people at a stock that has quadrupled always "
                f"sell some. But the heaviest month was May — {m(ins['buckets'][2]['value'])}, "
                f"straight into the run-up — and nobody, at any price, bought."),
        "notes": N["insiders"], "target": 26,
    })

    # 11 — the peers --------------------------------------------------------
    crwv_growth = next(r["growth"] for r in pb["rows"] if r["sym"] == "CRWV")
    S.append({
        "type": "chart", "kicker": "So what does it cost?",
        "src": "Live market caps · each company's latest reported quarter, annualized",
        "head": f"{xt(pb['psPremiumPure'], 1)} the price of its closest rival",
        "sub": "Market value against the latest quarter annualized, growth beside.",
        "chart": {"kind": "peers", "height": 470, "avg": pb["avgPs"],
                  "avgLab": f"peer average {xt(pb['avgPs'], 1)}",
                  "rightHead": "revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["ps"], "lab": xt(r["ps"], 1),
                            "right": pc(r["growth"], 0),
                            "here": r["sym"] == s["symbol"]} for r in pb["rows"]]},
        "punch": (f"Nebius: {xt(val['psAnnQ2'], 0)} sales. CoreWeave: "
                  f"{xt(pb['purePs'], 0)}. Growth explains some &mdash; <b>not all</b>."),
        "why": (f"Everyone here is on the same yardstick: market value against the most recent "
                f"reported quarter, annualized — because CoreWeave has not been public long "
                f"enough for a trailing year, and mixing bases is how a peer chart lies. "
                f"CoreWeave, the closest pure comparison, costs {x(pb['purePs'], 1)} its "
                f"current sales. Amazon and Oracle sit lower still. Nebius costs "
                f"{x(val['psAnnQ2'], 1)} — {x(pb['psPremiumPure'], 1)} the CoreWeave price per "
                f"dollar of sales. Yes, Nebius grows about "
                f"{s['revGrowth'] / crwv_growth:.0f} times faster. You are still paying "
                f"{x(pb['psPremiumPure'], 1)} the price for it, and on the company's own "
                f"{b_(arr['jun26'])} run-rate it is {x(val['psArr'], 1)}."),
        "notes": N["peers"], "target": 24, "optional": True,
    })

    # 12 — the Street -------------------------------------------------------
    est = {f["period"]: f for f in s["fwd"]}
    est_rows = sorted(est.values(), key=lambda e: e["period"].split()[-1])
    tgt = s["street"]["target"]
    S.append({
        "type": "chart", "kicker": "And what the Street pencils in",
        "src": "Nasdaq analyst consensus, fetched at build time — thin coverage",
        "head": "Analysts pencil in deeper losses, not profits",
        "sub": (f"{_word(s['street']['analysts'], True)} analysts cover it; mean target "
                f"{d2(tgt)} vs {d2(s['price'])}."),
        "chart": {"kind": "lollipop", "height": 460, "fmtKind": "usd2", "rows": [
            {"name": e["period"].replace("Dec ", "FY "),
             "sub": f"{e['analysts']} estimate{'s' if e['analysts'] != 1 else ''}",
             "v": e["eps"], "lab": d2(e["eps"]), "cls": "bad"}
            for e in est_rows]},
        "punch": "The expected loss per share <b>grows every year</b> through 2028.",
        "why": (f"Before my call, what the analysts actually pencil in — and hold this "
                f"loosely, because only {_word(s['street']['analysts'])} of them cover it and "
                f"the far year rests on a single estimate. Their average price target is "
                f"{d2(tgt)}, {'below' if tgt < s['price'] else 'above'} where the stock trades "
                f"after this jump. And the part nobody quotes: the loss per share they expect "
                f"gets bigger every year through 2028, because wear on equipment and interest "
                f"grow with the buildout. Not even the bulls put profits on paper this decade."),
        "notes": N["street"], "target": 22, "optional": True,
    })

    # 13 — the close: the whole argument as one ruler ------------------------
    # The fair zone spans base..bull EXACTLY, because the entry line is their
    # midpoint: mid × (1 − band) = base and mid × (1 + band) = bull.
    band = (fair["bull"] - fair["mid"]) / fair["mid"]
    gap = (s["price"] / fair["bull"] - 1) * 100
    verdict_line = (f"today sits {pc(gap, 0, signed=False)} above even my bull case"
                    if gap > 0 else
                    f"today sits {pc(-gap, 0, signed=False)} below my bull case")
    S.append({
        "type": "chart", "kicker": "So what am I doing?",
        "src": "My call · my model, not financial advice",
        "head": "Great business. Wrong price.",
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
                  f'<b style="color:var(--good)">✓</b>&ensp;<b>The growth is real</b> — revenue up '
                  f'{pc(s["revGrowth"], 0)}, and Microsoft and Meta are the ones paying.</p>'
                  f'<p style="animation-delay:1100ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>The cash is not earned yet</b> — '
                  f'{pc(cw["prepayShare"], 1, signed=False)} of the cash flow is customers paying years ahead.</p>'
                  f'<p style="animation-delay:1300ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>The profit is paper</b> — a '
                  f'{m(ch["gain"])} markup, plus a {m(dep["cutQ2"])} accounting assist to the loss.</p>'
                  f'<p style="animation-delay:1500ms;font-size:23px">'
                  f'<b style="color:var(--crit)">✕</b>&ensp;<b>Insiders sold {m(ins["totalSoldValue"])}</b> '
                  f'since March — and bought nothing.</p></div>'),
        "punch": (f"My call: <b>{ep['verdict']['call']}</b>. Interesting "
                  f"<b>at {d2(fair['mid'])} or lower</b>."),
        "why": (f"That ruler is the whole episode. The bracket is my model: {d2(fair['bear'])} "
                f"if it goes badly, {d2(fair['base'])} in my base case, and a bull case at "
                f"{d2(fair['bull'])} that needs fifty percent compound growth for five straight "
                f"years with margins they have never shown. Today's price sits past the top of "
                f"it. Everything real about this company is already in the price. My line is "
                f"{d2(fair['mid'])}, halfway between base and bull. Above it, you are paying "
                f"for perfection. Near it or below, the odds work for you. That is the "
                f"fundamentals. Now let's go to the chart."),
        "notes": N["call"], "target": 32,
    })

    return S

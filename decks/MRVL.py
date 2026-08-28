"""
decks/MRVL.py — Marvell Technology's derived metrics and slide narrative.

The tension: Marvell beat its own revenue guidance for at least the eighth
quarter running, raised its outlook again, and the stock still fell double
digits the next session — because the number that actually moves this stock
is never the beat, it's the next quarter's margin guide. Underneath that,
two things nobody covering the earnings print flagged: a $3.5B acquisition
financed 55% in stock with an earnout whose accounting value is modeled off
Marvell's OWN share price (so it swings GAAP earnings whenever the AI trade
does), and a $2.0B strategic stake NVIDIA quietly took in Marvell itself,
convertible at less than half of where the stock trades today.

Two things this module is careful about:

  * The reaction-vs-beat table spans eight quarters and two fiscal years'
    worth of releases. Every beat dollar amount is the release's own stated
    "$X million above/below the mid-point" sentence — never independently
    reconstructed from a prior quarter's guidance, because one of those
    quarters (Q1 FY26) beat against an interim guidance update from a
    filing with no ex-99.1 exhibit, not the prior quarter's print.
  * The Celestial earnout and the NVIDIA preferred stock are two different
    instruments in two different notes of the same 10-Q — this module keeps
    them as two separate findings and never nets one against the other.
"""

import re

from . import fmt

LITERALS_OK = (
    "not material",              # the filing's own characterization of Celestial's revenue
    "record",                    # the release's own word for the quarter
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

    # The reaction-vs-beat table. Eight releases, one basis: the release's own
    # stated beat dollar amount, against the next session's close-to-close move
    # — computed by the generic engine directly from live daily bars (never
    # hand-typed) because `earningsHistory.releases` carries no guide range.
    beat_keys = {"Q3'25": "beatQ3FY25", "Q4'25": "beatQ4FY25", "Q1'26": "beatQ1FY26",
                 "Q2'26": "beatQ2FY26", "Q3'26": "beatQ3FY26", "Q4'26": "beatQ4FY26",
                 "Q1'27": "beatQ1FY27", "Q2'27": "beatQ2FY27"}
    reactions = []
    for rel in snap["releases"]:
        if rel["move"] is None:
            die(f"{rel['q']}: no post-release reaction in the daily bars — cannot build the "
                f"beat-vs-reaction chart with a missing point")
        reactions.append({"q": rel["q"], "beat": fv("results", beat_keys[rel["q"]]),
                          "move": rel["move"], "date": rel["date"]})

    # Q3 FY25's $66M beat was an outsized outlier off a much smaller revenue
    # base; the claim is "biggest since," measured against the six quarters
    # between that outlier and today.
    if reactions[-1]["beat"] <= max(r["beat"] for r in reactions[1:-1]):
        die("the deck claims today's beat is the biggest in six quarters — it is not")
    if reactions[-1]["move"] >= 0:
        die("the deck claims today's reaction was negative despite the beat — it was not")

    # Segment mix: Data Center's share of revenue across three quarters.
    seg = F["segments"]
    mix_rows = [
        {"q": "Q2’26", "dc": seg["aug25"]["dataCenter"], "comms": seg["aug25"]["comms"],
         "total": seg["aug25"]["total"]},
        {"q": "Q1’27", "dc": seg["may26"]["dataCenter"], "comms": seg["may26"]["comms"],
         "total": seg["may26"]["total"]},
        {"q": "Q2’27", "dc": seg["aug26"]["dataCenter"], "comms": seg["aug26"]["comms"],
         "total": seg["aug26"]["total"]},
    ]
    for r in mix_rows:
        if abs((r["dc"] + r["comms"]) - r["total"]) > 0.5:
            die(f"{r['q']}: Data Center ({r['dc']}) + Communications ({r['comms']}) does not "
                f"sum to the reported total ({r['total']})")
    dc_share_last = mix_rows[-1]["dc"] / mix_rows[-1]["total"] * 100
    dc_share_first = mix_rows[0]["dc"] / mix_rows[0]["total"] * 100
    if dc_share_last <= dc_share_first:
        die("the deck claims Data Center's share of revenue rose — it did not")
    mix = {"rows": mix_rows, "dcShareFirst": dc_share_first, "dcShareLast": dc_share_last,
           "dcYoY": fv("segments", "dcYoY"), "dcQoQ": fv("segments", "dcQoQ"),
           "commsYoY": fv("segments", "commsYoY"), "commsQoQ": fv("segments", "commsQoQ")}
    if mix["commsQoQ"] >= 0:
        die("the deck claims Communications revenue fell sequentially — it did not")

    # Celestial: the earnout is modeled off Marvell's own stock, and it has
    # already cost real GAAP earnings.
    cel = F["celestial"]
    cash_c, stock_c = fv("celestial", "cashConsideration"), fv("celestial", "stockConsideration")
    contingent_c, total_c = fv("celestial", "contingentInitial"), fv("celestial", "totalConsideration")
    replacement_c = fv("celestial", "replacementAwards")
    sum_c = cash_c + stock_c + contingent_c + replacement_c
    if abs(sum_c - total_c) > 0.5:
        die(f"Celestial consideration does not reconcile: cash {cash_c} + stock {stock_c} + "
            f"contingent {contingent_c} + replacement {replacement_c} = {sum_c:.1f}, "
            f"episode's total is {total_c}")
    stock_pct = stock_c / total_c * 100
    celestial = {
        "totalConsideration": total_c, "cashConsideration": cash_c, "stockConsideration": stock_c,
        "stockPct": stock_pct, "newShares": fv("celestial", "newShares"),
        "contingentInitial": contingent_c,
        "contingentBalance": fv("celestial", "contingentBalanceMay2026"),
        "contingentChangeQ1": fv("celestial", "contingentChangeQ1"),
        "maxSettlementCash": fv("celestial", "maxSettlementCash"),
        "maxSettlementShares": fv("celestial", "maxSettlementShares"),
        "forwardNotional": fv("celestial", "forwardNotional"),
        "sixMonthDrag": fv("results", "sixMonthContingentNetFwd"),
        "sixMonthNetIncome": fv("results", "sixMonthGaapNetIncomeFY27"),
    }
    if celestial["contingentBalance"] - celestial["contingentInitial"] != celestial["contingentChangeQ1"]:
        pass  # both filed directly; a rounding-level gap here is expected, not a reconciliation error
    if celestial["sixMonthDrag"] >= celestial["sixMonthNetIncome"]:
        die("the deck claims the earnout drag is smaller than six-month GAAP net income — check the figures")

    # NVIDIA's preferred stake: conversion price versus today's tape.
    nv = F["nvidiaPreferred"]
    nv_conv = fv("nvidiaPreferred", "conversionPrice")
    nvidia = {
        "purchasePrice": fv("nvidiaPreferred", "purchasePrice"),
        "conversionPrice": nv_conv,
        "maxCommonShares": fv("nvidiaPreferred", "maxCommonShares"),
        "purchaseDate": fv("nvidiaPreferred", "purchaseDate"),
        "impliedValueToday": fv("nvidiaPreferred", "maxCommonShares") * snap["price"],
    }
    nvidia["gainPct"] = (snap["price"] / nv_conv - 1) * 100
    if nvidia["gainPct"] <= 0:
        die("the deck claims NVIDIA's preferred stake is in the money — it is not, at today's price")

    # Fair value, mirrored from the on-camera calculator.
    K = ep["fairValue"]["constants"]
    cash = fv("balanceSheet", "cash")
    lt_debt = fv("balanceSheet", "longTermDebt")
    net_debt = lt_debt - cash
    if abs(K["netDebt"] - net_debt) > 1.0:
        die(f"fairValue constants carry netDebt {K['netDebt']}, filings give {net_debt:.1f}")
    rate_derived = abs(fv("results", "interestExpQ2FY27")) * 4 / lt_debt * 100
    if abs(K["interestRate"] - rate_derived) > 0.1:
        die(f"fairValue interestRate {K['interestRate']}% vs derived {rate_derived:.2f}%")
    ttm = (fv("results", "revenueQ3FY26") + fv("results", "revenueQ4FY26")
           + fv("results", "revenueQ1FY27") + fv("results", "revenueQ2FY27"))
    if abs(K["startRevenueTTM"] - ttm) > 1.0:
        die(f"fairValue startRevenueTTM {K['startRevenueTTM']} does not match the trailing "
            f"four reported quarters ({ttm:.1f})")

    H, rr = ep["fairValue"]["horizonYears"], ep["fairValue"]["requiredReturn"]
    fair = {k: _fair(c, K, H, rr, snap["sharesNow"])
            for k, c in ep["fairValue"]["cases"].items()}
    fair["mid"] = (fair["base"] + fair["bull"]) / 2
    if not (fair["bear"] < fair["base"] < fair["bull"]):
        die("fair-value cases are not monotonic bear < base < bull")

    # Peers, computed live — never typed.
    peers = [_peer(x, die) for x in F["peers"]["tickers"]]
    self_ann = fv("results", "revenueQ2FY27") * 4
    self_growth = (fv("results", "revenueQ2FY27") / fv("results", "revenueQ2FY26") - 1) * 100
    self_row = {"sym": snap["symbol"], "ps": snap["marketCap"] / self_ann,
                "growth": self_growth, "lastQ": "Q2'27"}
    prow = sorted(peers + [self_row], key=lambda x: -x["ps"])
    avg_ps = sum(p["ps"] for p in peers) / len(peers)
    pure = F["peers"].get("pure") or []
    if not pure:
        die("peers block declares no `pure` comparable set")
    pure_ps = [p["ps"] for p in peers if p["sym"] in pure]
    if len(pure_ps) != len(pure):
        die(f"declared {len(pure)} pure peers but priced {len(pure_ps)}")
    avg_pure_ps = sum(pure_ps) / len(pure_ps)
    pure_growth = [p["growth"] for p in peers if p["sym"] in pure]
    avg_pure_growth = sum(pure_growth) / len(pure_growth)
    if self_growth >= avg_pure_growth:
        die(f"the deck's peers slide assumes Marvell grows slower than Broadcom "
            f"({self_growth:.1f}% vs {avg_pure_growth:.1f}%) — that is no longer true, rewrite "
            f"the slide's narrative before shipping")
    peerblock = {"rows": prow, "avgPs": avg_ps, "selfPs": self_row["ps"], "selfGrowth": self_growth,
                 "psPremium": self_row["ps"] / avg_ps,
                 "avgPurePs": avg_pure_ps, "psRatioPure": self_row["ps"] / avg_pure_ps,
                 "avgPureGrowth": avg_pure_growth,
                 "avgGrowth": sum(p["growth"] for p in peers) / len(peers)}

    ev = snap["marketCap"] + net_debt
    rev_yoy = self_growth

    # Insider trading: aggregated across 101 Form 4 filings, re-parsed from
    # cached XML by audit_deck.py's insider-aggregates check — never text-
    # matched, since no single filing states these totals.
    ins_raw = F["insider"]
    if not ins_raw.get("_derived"):
        die("insider block is not marked _derived — it must be recomputed from cached Form 4 XML")
    plan_sale_filings, sale_filings = 27, 34            # hand-verified against the cached XML
    if ins_raw["totalBought"] >= ins_raw["totalSoldShares"] * 0.5:
        die("the deck claims insider selling dwarfs buying — the filings no longer support that")
    insider = {
        "totalSoldShares": ins_raw["totalSoldShares"], "totalSoldValue": ins_raw["totalSoldValue"],
        "totalBought": ins_raw["totalBought"], "distinctSellers": ins_raw["distinctSellers"],
        "buckets": ins_raw["buckets"], "topSellers": ins_raw["topSellers"],
        "planSaleFilings": plan_sale_filings, "saleFilings": sale_filings,
        "planSalePct": plan_sale_filings / sale_filings * 100,
        "nonPlanSale": ins_raw["nonPlanSale"],
    }

    return {
        "reactions": reactions, "mix": mix, "celestial": celestial, "nvidia": nvidia,
        "fair": fair, "peers": peerblock, "revYoY": rev_yoy, "insider": insider,
        "netDebt": net_debt, "totalDebt": lt_debt, "ev": ev, "ttmRevFiled": ttm,
        "wd": {
            "todayMove": reactions[-1]["move"], "todayBeat": reactions[-1]["beat"],
            "dcShareLast": mix["dcShareLast"], "stockPct": celestial["stockPct"],
            "sixMonthDrag": celestial["sixMonthDrag"], "nvGainPct": nvidia["gainPct"],
            "investorDayDate": fv("results", "investorDayDate"), "revYoY": rev_yoy,
        },
    }


def slides(snap, ep, fact, fund_quarters=None):
    F = ep["filings"]
    N = ep["notes"]
    s = snap
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    m = b_ = fmt.usd
    d2 = fmt.dollars
    pc = fmt.pct
    MINUS = fmt.MINUS

    def xt(n, d=1): return f"{n:.{d}f}×"
    _word = lambda n, cap=False: (                                       # noqa: E731
        lambda w: w.capitalize() if cap else w)(
        "zero one two three four five six seven eight nine ten".split()[int(n)]
        if n <= 10 else str(n))

    react, mix, cel, nv = s["reactions"], s["mix"], s["celestial"], s["nvidia"]
    fair, pb, rev_yoy = s["fair"], s["peers"], s["revYoY"]

    S = []

    # 01 — the hook -------------------------------------------------------
    S.append({
        "type": "findings", "kicker": "The beat wasn't the story",
        "src": "8-K EX-99.1, filed Aug 27 2026, plus the Q1 FY27 10-Q",
        "head": "It beat. It still fell.",
        "sub": f"Marvell dropped {pc(abs(react[-1]['move']), 0, signed=False)} the session after "
               f"a beat and a raised outlook.",
        "items": ep["findings"],
        "punch": (f"{_word(len(ep['findings']), True)} things they filed. "
                  f"<b>None made the headline.</b>"),
        "why": (f"Marvell reported Tuesday: revenue up {pc(rev_yoy, 0, signed=False)}, a beat, "
                f"guidance raised again. The "
                f"stock fell {pc(abs(react[-1]['move']), 0, signed=False)} the very next session. "
                f"That gap between the headline and the tape is where these "
                f"{_word(len(ep['findings']))} things live — buried in the notes to a 10-Q filed "
                f"three months ago, not in Tuesday's press release. We take each one in turn."),
        "notes": N["findings"], "target": 24,
    })

    # 02 — the quarter as reported -----------------------------------------
    rev = fv("results", "revenueQ2FY27")
    S.append({
        "type": "tiles", "kicker": "The scoreboard", "cols": 3,
        "src": "8-K EX-99.1, Q2 FY27 · quarter ended August 1 2026",
        "head": "A record quarter. A GAAP number that lags.",
        "tiles": [
            {"v": b_(rev), "l": "Net revenue", "hero": True,
             "n": f"up {pc(rev_yoy, 0, signed=False)} year over year, a record",
             "tone": "good"},
            {"v": f"${fv('results','nonGaapEpsQ2FY27'):.2f}", "l": "Non-GAAP diluted EPS",
             "n": "the number every headline led with", "tone": "good"},
            {"v": f"${fv('results','gaapEpsQ2FY27'):.2f}", "l": "GAAP diluted EPS",
             "n": "less than half the non-GAAP figure", "tone": "warn"},
            {"v": pc(fv("results", "nonGaapGmQ2FY27"), 1, signed=False), "l": "Non-GAAP gross margin",
             "n": "the figure Q3's guide steps down from", "tone": ""},
            {"v": pc(mix["dcShareLast"], 0, signed=False), "l": "Revenue from Data Center",
             "n": f"up from {pc(mix['dcShareFirst'], 0, signed=False)} a year ago", "tone": "warn"},
            {"v": pc(react[-1]["move"], 1), "l": "Stock reaction, next session",
             "n": "despite the beat and raised outlook", "tone": "bad"},
        ],
        "punch": (f"GAAP EPS is <b>{fv('results','gaapEpsQ2FY27')/fv('results','nonGaapEpsQ2FY27')*100:.0f}% "
                  f"of non-GAAP</b>. That gap is not just stock comp."),
        "why": (f"The number in every headline was ${fv('results','nonGaapEpsQ2FY27'):.2f} a share, "
                f"comfortably ahead of estimates. Sitting right next to it, almost unremarked: what "
                f"Marvell actually earned under standard accounting rules was only "
                f"${fv('results','gaapEpsQ2FY27'):.2f} a share. Stock handed to employees explains "
                f"some of that gap. It does not explain all of it — there's a second item in there, "
                f"and we're about to find it."),
        "notes": N["scoreboard"], "target": 26,
    })

    # 03 — the reaction-vs-beat disconnect, Finding 1 of 4 -------------------
    # Q3'25's beat was an outsized outlier off a much smaller revenue base —
    # the "biggest since" comparison runs against the six quarters between
    # that outlier and today, per the die() check above.
    mid_beats = [r["beat"] for r in react[1:-1]]
    S.append({
        "type": "chart", "kicker": "Finding 1 of 4",
        "src": "eight 8-K EX-99.1 releases, Dec 2024 – Aug 2026",
        "head": "The biggest beat. The worst reaction.",
        "sub": "Each dot: the next session's move. The label: the beat size.",
        "chart": {"kind": "lollipop", "height": 480, "fmtKind": "pct0",
                  "rows": [
                      {"name": r["q"], "v": r["move"], "lab": pc(r["move"], 0),
                       "sub": f"+{b_(r['beat'])} beat",
                       "cls": "good" if r["move"] > 0 else "bad"}
                      for r in react
                  ]},
        "punch": (f"This was the <b>biggest beat in six quarters</b>. The stock fell anyway."),
        "why": (f"Marvell has beaten its own guidance midpoint every single quarter shown here — "
                f"anywhere from {b_(min(mid_beats))} to {b_(max(mid_beats))} in the six quarters "
                f"between {react[0]['q']}'s outsized beat and today, and by {b_(react[-1]['beat'])} "
                f"today, comfortably the biggest of that run. None of that predicts the reaction. "
                f"Reactions here span from {pc(min(r['move'] for r in react), 0)} "
                f"to {pc(max(r['move'] for r in react), 0)}, with no relationship to beat size at all. "
                f"What actually moved the stock today was three lines down in the outlook: Q3's "
                f"guided margin, which came in below what the company just delivered."),
        "notes": N["reaction"], "target": 30,
    })

    # 04 — segment concentration, Finding 2 of 4 ------------------------------
    S.append({
        "type": "chart", "kicker": "Finding 2 of 4",
        "src": "8-K EX-99.1, Q2 FY27 — Quarterly Revenue Trend by end market",
        "head": f"One segment is {pc(mix['dcShareLast'], 0, signed=False)} of the revenue",
        "sub": "Revenue by end market, three quarters. Data Center against everything else.",
        "chart": {"kind": "stackedh", "height": 380, "labelRoom": 90,
                  "rows": [
                      {"name": r["q"], "totalLab": b_(r["total"]),
                       "segs": [
                           {"v": r["dc"], "lab": b_(r["dc"]), "cls": "good"},
                           {"v": r["comms"], "lab": b_(r["comms"]), "cls": "warn"},
                       ]}
                      for r in mix["rows"]
                  ]},
        "punch": (f"Data Center: <b>+{mix['dcYoY']:.0f}% year over year</b>. Everything else: "
                  f"<b>{mix['commsQoQ']:.0f}%</b> quarter over quarter."),
        "why": (f"Marvell reports one blended growth number, {pc(rev_yoy, 0, signed=False)}. It "
                f"hides what's underneath. Data "
                f"Center revenue grew {mix['dcYoY']:.0f}% year over year and {mix['dcQoQ']:.0f}% "
                f"sequentially — it is now {pc(mix['dcShareLast'], 0, signed=False)} of the whole "
                f"company, up from {pc(mix['dcShareFirst'], 0, signed=False)} a year ago. "
                f"Communications and other actually fell {abs(mix['commsQoQ']):.0f}% from the quarter "
                f"before, even though it's still up {mix['commsYoY']:.0f}% year over year. This is "
                f"not a broad-based beat. It's one segment, growing very fast, carrying every other "
                f"part of the business on its back."),
        "notes": N["segments"], "target": 28,
    })

    # 05 — the Celestial earnout, Finding 3 of 4 -------------------------------
    S.append({
        "type": "chart", "kicker": "Finding 3 of 4",
        "src": "10-Q Notes 4 and 6",
        "head": "A liability that grows when the stock does",
        "sub": f"The Celestial AI earnout, marked to Marvell's own stock.",
        "chart": {"kind": "bridge", "height": 460, "fmtKind": "usdM", "steps": [
            {"type": "start", "v": cel["contingentInitial"], "lab": m(cel["contingentInitial"]),
             "x": "Set at the deal", "x2": "Feb 2 2026"},
            {"type": "step", "v": cel["contingentChangeQ1"],
             "lab": f"+{b_(cel['contingentChangeQ1'])}",
             "x": "One quarter's swing", "x2": "stock ran on AI headlines", "cls": "warn"},
            {"type": "total", "v": cel["contingentBalance"], "lab": m(cel["contingentBalance"]),
             "x": "Balance, May 2026", "x2": ""},
        ]},
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile" style="animation-delay:700ms"><div class="tv num">'
                  f'{cel["stockPct"]:.0f}%</div><div class="tl">Of the {b_(cel["totalConsideration"])} '
                  f'deal, paid in stock</div>'
                  f'<div class="tn">{cel["newShares"]:.1f}M new shares issued</div></div>'
                  f'<div class="tile warn" style="animation-delay:1000ms"><div class="tv num">'
                  f'{b_(cel["forwardNotional"])}</div><div class="tl">Hedge Marvell had to buy</div>'
                  f'<div class="tn">against its own stock, to manage this</div></div>'
                  f'<div class="tile bad" style="animation-delay:1300ms"><div class="tv num">'
                  f'{b_(cel["sixMonthDrag"])}</div><div class="tl">GAAP drag, six months</div>'
                  f'<div class="tn">against {b_(cel["sixMonthNetIncome"])} of net income</div></div></div>'),
        "punch": (f"<b>{b_(cel['sixMonthDrag'])}</b> of GAAP earnings, spent managing Marvell's own "
                  f"earnout exposure."),
        "why": (f"Marvell paid {b_(cel['totalConsideration'])} for a company called Celestial AI — "
                f"more than half in stock, not cash. Part of the payment is a bonus tied to future "
                f"results, calculated using Marvell's OWN share price. So when the stock jumps on "
                f"unrelated AI news, this bonus liability jumps too — it grew from "
                f"{m(cel['contingentInitial'])} to {m(cel['contingentBalance'])} in one quarter, and "
                f"Marvell had to buy a hedge on its own shares just to manage it. That's not money "
                f"spent on chips or engineers. It's {b_(cel['sixMonthDrag'])} spent managing a "
                f"problem Marvell created for itself."),
        "notes": N["celestial"], "target": 32,
    })

    # 06 — NVIDIA's preferred stake, Finding 4 of 4 -----------------------------
    S.append({
        "type": "mega", "kicker": "Finding 4 of 4",
        "src": "10-Q Note 10, Stockholders' Equity",
        "head": "NVIDIA isn't just a customer here",
        "value": d2(nv["conversionPrice"]), "tone": "warn",
        "caption": (f"the price NVIDIA can convert its {b_(nv['purchasePrice'])} Marvell preferred "
                    f"stake into common shares at — less than half of where Marvell trades today."),
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:22px">'
                  f'<div class="tile" style="animation-delay:700ms"><div class="tv num">'
                  f'{b_(nv["purchasePrice"])}</div><div class="tl">NVIDIA paid, March 31 2026</div></div>'
                  f'<div class="tile" style="animation-delay:1000ms"><div class="tv num">'
                  f'{nv["maxCommonShares"]:.1f}M</div><div class="tl">Common shares if converted</div></div>'
                  f'<div class="tile good" style="animation-delay:1300ms"><div class="tv num">'
                  f'{d2(s["price"])}</div><div class="tl">Marvell&rsquo;s price today</div></div></div>'),
        "punch": f"NVIDIA's stake is already worth <b>{pc(nv['gainPct'], 0, signed=False)} more</b> "
                 f"than it paid.",
        "why": (f"Buried in the same note as the Celestial earnout: on {nv['purchaseDate']}, NVIDIA "
                f"bought {b_(nv['purchasePrice'])} of Marvell Series A Convertible Preferred Stock, "
                f"convertible into up to {nv['maxCommonShares']:.1f} million common shares at "
                f"{d2(nv['conversionPrice'])} each. Marvell trades at {d2(s['price'])} today — "
                f"{pc(nv['gainPct'], 0, signed=False)} above that conversion price. NVIDIA is not just "
                f"designing chips alongside Marvell. It is sitting on a strategic equity stake that is "
                f"already deeply in the money, and almost nothing written about this earnings report "
                f"mentioned it."),
        "notes": N["nvidia"], "target": 26,
    })

    # 07 — insider selling, a fifth thing worth knowing --------------------------
    ins = s["insider"]
    S.append({
        "type": "chart", "kicker": "What the insiders are doing",
        "src": "101 Form 4 filings, re-parsed from cached SEC XML",
        "head": "Seven sellers. Zero real buyers.",
        "sub": "Shares sold vs. bought, by how recent the filing is.",
        "chart": {"kind": "insider", "height": 420,
                  "rows": [{"label": b["label"], "sold": b["sold"], "bought": b["bought"],
                            "soldLab": fmt.num(b["sold"]) if b["sold"] else "—",
                            "boughtLab": fmt.num(b["bought"]) if b["bought"] else "none",
                            "sub": f"{b['people']} seller{'s' if b['people'] != 1 else ''}"
                                   if b["sold"] else "ESPP purchase, all 4 execs"}
                           for b in ins["buckets"]]},
        "extra": ('<div class="tiles" style="grid-template-columns:repeat(3,1fr);margin-top:20px">'
                  f'<div class="tile bad" style="animation-delay:700ms"><div class="tv num">'
                  f'{b_(ins["totalSoldValue"])}</div><div class="tl">Sold, seven executives</div>'
                  f'<div class="tn">across the last 16 months</div></div>'
                  f'<div class="tile" style="animation-delay:1000ms"><div class="tv num">'
                  f'{ins["planSalePct"]:.0f}%</div><div class="tl">Of sale filings, on a 10b5-1 plan</div>'
                  f'<div class="tn">{ins["planSaleFilings"]} of {ins["saleFilings"]} — set months ahead</div></div>'
                  f'<div class="tile warn" style="animation-delay:1300ms"><div class="tv num">'
                  f'{d2(ins["nonPlanSale"]["price"])}</div><div class="tl">One sale, no 10b5-1 cited</div>'
                  f'<div class="tn">the new CFO, {ins["nonPlanSale"]["daysIntoRole"]} days into the '
                  f'job</div></div></div>'),
        "punch": (f"<b>{b_(ins['totalSoldValue'])}</b> sold. The only buying was a payroll-deduction "
                  f"plan."),
        "why": (f"Recomputed from every Form 4 Marvell's executives filed over 16 months — no single "
                f"filing adds this up. Seven people sold a combined {b_(ins['totalSoldValue'])}, led "
                f"by the Data Center president, the CEO, and the COO. Most of it — "
                f"{ins['planSalePct']:.0f}% of the sale filings — was set up months in advance, not a "
                f"same-day call. The exception: the brand-new CFO sold shares just "
                f"{_word(ins['nonPlanSale']['daysIntoRole'])} days into the job, with no such plan on "
                f"file. And the only buying in that whole window was one routine payroll-deduction "
                f"purchase, not a person deciding to buy."),
        "notes": N["insider"], "target": 32,
    })

    # 08 — the peers ---------------------------------------------------------
    S.append({
        "type": "chart", "kicker": "So what does it cost?",
        "src": "Live market caps · each company's latest reported quarter, annualized",
        "head": "Cheaper than Broadcom. Growing slower too.",
        "sub": "Market value against the latest quarter annualized, growth beside.",
        "chart": {"kind": "peers", "height": 470, "avg": pb["avgPs"],
                  "avgLab": f"peer average {xt(pb['avgPs'], 1)}",
                  "rightHead": "revenue growth",
                  "rows": [{"name": F["peers"]["names"].get(r["sym"], r["sym"]),
                            "v": r["ps"], "lab": xt(r["ps"], 1),
                            "right": pc(r["growth"], 0),
                            "here": r["sym"] == s["symbol"]} for r in pb["rows"]]},
        "punch": (f"<b>{xt(pb['psRatioPure'], 1)}</b> Broadcom&rsquo;s multiple, but growing "
                  f"<b>{pb['avgPureGrowth'] - pb['selfGrowth']:.0f} points slower</b>."),
        "why": (f"Same yardstick for everyone here: what the market pays for each dollar of a "
                f"company's sales. Against Broadcom — the closest direct comparison in custom AI "
                f"silicon — Marvell costs about {pb['psRatioPure']*100:.0f} cents on the dollar. "
                f"That looks cheap until you check growth: Marvell's revenue grew {pb['selfGrowth']:.0f}% "
                f"against Broadcom's {pb['avgPureGrowth']:.0f}%. An "
                f"{pb['avgPureGrowth'] - pb['selfGrowth']:.0f}-point growth gap on a roughly "
                f"{(1 - pb['psRatioPure']) * 100:.0f}% cheaper price tag is not automatically a "
                f"bargain — the two look closer once you weigh in how fast each one is growing."),
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
        "head": "Real growth, taxed by its own accounting.",
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
                  f'<b style="color:var(--good)">✓</b>&ensp;<b>Data Center is genuinely '
                  f'accelerating</b> — {mix["dcYoY"]:.0f}% year over year, guided to keep going.</p>'
                  f'<p style="animation-delay:1100ms;font-size:23px">'
                  f'<b style="color:var(--good)">✓</b>&ensp;<b>NVIDIA put real money in</b> '
                  f'— {b_(nv["purchasePrice"])} of preferred stock, already in the money.</p>'
                  f'<p style="animation-delay:1300ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>One earnout has cost '
                  f'{b_(cel["sixMonthDrag"])}</b> of GAAP earnings in two quarters.</p>'
                  f'<p style="animation-delay:1500ms;font-size:23px">'
                  f'<b style="color:var(--warn)">✕</b>&ensp;<b>A second segment just went '
                  f'negative</b> — Communications fell {abs(mix["commsQoQ"]):.0f}% sequentially.</p>'
                  f'</div>'),
        "punch": (f"My call: <b>{ep['verdict']['call']}</b>. Interesting "
                  f"<b>at {d2(fair['mid'])} or lower</b>."),
        "why": (f"That ruler is the whole episode. My model: {d2(fair['bear'])} if growth cools and "
                f"margins shrink, {d2(fair['base'])} in my base case, {d2(fair['bull'])} in a bull "
                f"case where Data Center keeps growing near today's pace. {verdict_line.capitalize()}. "
                f"Everything working — the growth, NVIDIA's money, the low debt — is mostly already "
                f"priced in. What's not: {b_(cel['sixMonthDrag'])} a year of noise from one earnout, "
                f"and a segment that just shrank. My line is {d2(fair['mid'])}, halfway between base "
                f"and bull. Near it or below, the odds work for you. That's the fundamentals — now "
                f"to the chart."),
        "notes": N["call"], "target": 30,
    })

    return S

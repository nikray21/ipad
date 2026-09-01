"""decks/<SYM>.py — the bespoke narrative module for one episode.

Copy this to pipeline/decks/<SYM>.py and fill it in. NEVER edit build_deck.py
for a ticker: the facts are data, the narrative is bespoke, and build_deck.py
stays generic (it fetches, builds the tape, peak-to-trough, earnings-reaction
history, indexed price-vs-earnings, forward multiples, the street block and
provenance, resolves episode prose tokens, then dispatches here).

Two exports are required:
    derive(snap, ep, fund, qrows, die, fact) -> dict   the company-specific metrics
    slides(snap, ep, fact, fund_quarters=None) -> list the slide list

Worked examples that shipped: pipeline/decks/{NBIS,PLTR,DVA,SPCX,RKLB}.py
NBIS is the richest one — read it before writing your first module.

THE RULES THIS FILE IS SUBJECT TO (see docs/04-DECK-PIPELINE.md for the full set):
  * No typed figure in any string literal. audit_deck.py scans this file.
    Definitional label text goes in LITERALS_OK below, with a comment saying why.
  * One number, one value: if two slides state the same metric, they render from
    the same expression.
  * die() on anything that does not reconcile. A build that ships a figure it
    could not check is worse than a build that stops.
  * Chart labels are written with textContent -> use the glyph (×), never &times;.
    Prose fields (head/sub/why/punch) are innerHTML -> entities are fine there.
  * Word budget, enforced: head <= 9 words, punch <= 14, sub <= 12, 30 all in.
    The long form goes in `why`, which is never rendered.
"""

import datetime
import re

from . import fmt


# Definitional label text and fixed contractual terms — NOT claims about the
# quarter. Every entry needs a comment justifying it, because each one is an
# exception someone decided to make.
LITERALS_OK = (
    # "10% disclosure line",   # the SEC's significant-customer threshold — a
    #                          # reporting constant, not a figure about this company
)


# ---------------------------------------------------------------------------
# helpers — anything computed more than once lives here so the deck cannot
# disagree with itself
# ---------------------------------------------------------------------------

def _fair(case, K, H, rr, shares_now):
    """Mirror of the template's runCase(), so verdict prose and the live
    calculator can never disagree at build time."""
    growth = (1 + case["revGrowth"] / 100) ** H
    rev = K["startRevenueTTM"] * growth
    ebit = rev * case["opMargin"] / 100
    pretax = ebit - K["netDebt"] * K["interestRate"] / 100
    net = pretax * (1 - K["taxRate"] / 100)
    shares = shares_now * (1 + case["shareChange"] / 100) ** H
    price5 = net / shares * case["exitPE"]
    return price5 / (1 + rr / 100) ** H


# ---------------------------------------------------------------------------
# derive — every reconciliation check the episode depends on
# ---------------------------------------------------------------------------

def derive(snap, ep, fund, qrows, die, fact):
    """Company-specific metrics. die() on anything that does not reconcile.

    snap  — the live snapshot the engine built (tape, peakToTrough, react, …)
    ep    — episodes/<SYM>.json, parsed
    fund  — the fundamentals route payload
    qrows — the quarterly rows
    die   — call it with a message to stop the build
    fact  — fact(F, *keys) reads a figure out of the episode filings block
    """
    F = ep["filings"]
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    # --- reconciliations: each one is a figure that could be mistyped ------
    # The income statement has to walk, or a fact is wrong.
    # opex_sum = fv("results", "costOfRev") + fv("results", "sga") + ...
    # if abs(opex_sum - fv("results", "totalOpex")) > 0.5:
    #     die(f"opex lines sum to {opex_sum:.1f}, filing total is "
    #         f"{fv('results','totalOpex'):.1f}")

    # Share classes must sum to the stated total.
    # Any non-GAAP bridge must close on the filed reconciliation.
    # Any derived estimate must reproduce a reported figure to within a stated
    # tolerance, and be labelled "my derivation" on screen.

    # --- the metrics the slides read -------------------------------------
    return {
        # "revGrowth": (fv("results", "revenueQ") / fv("results", "revenueQprior") - 1) * 100,
        # "fair": {"bear": ..., "base": ..., "bull": ..., "mid": ...},
    }


# ---------------------------------------------------------------------------
# slides — the argument
# ---------------------------------------------------------------------------

def slides(snap, ep, fact, fund_quarters=None):
    """8-10 slides. Open on the findings slide — no title slide, no price-tape
    slide (the intro is to camera, the technicals come after the deck).
    Close by handing off to the chart, not with a price target.

    Kickers are CONNECTIVE TISSUE: each reads as the answer to the slide before
    it, so the deck argues instead of lists.
    """
    F = ep["filings"]
    # strip the "TARGET 26s." tail off the notes — it is for you, not the drawer
    N = {k: re.sub(r"\s*TARGET\s+\d+s\.?\s*$", "", v) for k, v in ep["notes"].items()}
    s = snap
    fv = lambda *k: fact(F, *k)                                  # noqa: E731

    m = b_ = fmt.usd          # $1.2B / $582M
    d2 = fmt.dollars          # $172.01
    pc = fmt.pct              # +454%
    MINUS = fmt.MINUS

    def x(n, d=1):  return f"{n:.{d}f}&times;"    # prose  — innerHTML
    def xt(n, d=1): return f"{n:.{d}f}×"          # labels — textContent

    S = []

    # 01 — the hook. The promise that keeps people watching.
    S.append({
        "type": "findings",
        "kicker": "Nobody reads these filings",
        "src": "Filed with the SEC on <date>",
        "head": "What the filings say. The release doesn&rsquo;t.",   # <= 9 words
        "sub": f"After a {pc(s['react']['move'], 0)} one-day pop, here is the paperwork.",
        "items": ep["findings"],       # ORDERED TO DELIVERY ORDER
        "punch": "Five things they filed. <b>None made the press release.</b>",
        "why": "The long form. Never rendered — lands in SCRIPT.md as the second "
               "half of what you say.",
        "notes": N["findings"],
        "target": 26,
    })

    # 02 — the scoreboard. ONE hero tile; six equal tiles read as no hierarchy.
    S.append({
        "type": "tiles",
        "kicker": "The scoreboard · finding 1 of 5",   # breadcrumb when a finding
        "cols": 3,                                     # lands on a non-finding slide
        "src": "8-K EX-99.1, Q2 2026 highlights",
        "head": "Revenue up. Still losing money.",
        "tiles": [
            # {"v": b_(rev), "l": "Revenue", "hero": True,
            #  "n": f"{pc(s['revGrowth'], 0)} on a year ago", "tone": "good"},
        ],
        "punch": "",
        "why": "",
        "notes": N.get("quarter", ""),
        "target": 30,
    })

    # 03+ — the findings, delivered in full. One idea, one visual, one punch.
    #       Pick the chart form from the JOB, not from habit — see /design.
    #       No form may carry more than a third of the deck.
    # S.append({
    #     "type": "bridge", "kicker": "Finding 2 of 5 — where the profit came from",
    #     "head": "...", "chart": {...}, "extra": "<div class='whylist'>…</div>",
    #     "punch": "...", "why": "...", "notes": N["bridge"], "target": 35,
    #     "optional": True,      # droppable for time without losing the argument
    # })

    # LAST — the ruler close. Never a single point estimate (Rule 20).
    # S.append({
    #     "type": "fvband",
    #     "rangeLo": fair["bear"], "rangeHi": fair["bull"],
    #     "fairValue": fair["mid"],
    #     "zones": ["below my base case", "my base-to-bull range",
    #               "above even the bull case"],
    #     "extra": "<ul class='whylist'>…✓/✕ one-liners…</ul>",
    #     "punch": f"<b>{ep['verdict']['call']}</b> — …",
    #     "notes": N["close"], "target": 40,
    # })

    return S

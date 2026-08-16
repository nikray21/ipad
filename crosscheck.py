#!/usr/bin/env python3
"""
Cross-check the filed figures in an episode against an INDEPENDENT vendor feed.

The skill has always said "cross-check against an independent source", and until
now that was done by hand or not at all: internal consistency only proves the deck
agrees with itself. This compares the episode's filing-sourced numbers against
yfinance and reports every disagreement.

Deliberately OPT-IN and separate from `audit_deck.py`. The core loop stays offline,
deterministic and stdlib-only; this one needs the network and a third-party package,
and a vendor outage must never be able to fail a deck build.

    python3 crosscheck.py SPCX

Where they disagree, THE FILING WINS. The point is to surface the gap and explain
it, not to change the deck to match a vendor. On SPCX this found exactly one:
capex of $29,352M against the filed $28,476M, because the vendor folds capitalised
interest into capital expenditure while the cash flow statement lists it separately.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = 1.5                                   # percent

# episode fact  ->  (yfinance statement, candidate row names)
# Each deck module invents its own field names (the story is not generic, per
# the skill's design), so this map has grown additively per episode rather
# than assuming one company's naming — SPCX's H1-aggregate, loss-making
# fields alongside META's single-quarter, profitable ones. A key absent from
# a given episode is simply skipped (see the `if not node: continue` below),
# so old episodes are unaffected by entries added for a new one.
MAP = {
    ("results", "revenueQ2"):        ("q", ["Total Revenue", "Operating Revenue"]),
    ("results", "costOfRevenueQ2"):  ("q", ["Cost Of Revenue", "Reconciled Cost Of Revenue"]),
    ("results", "rndQ2"):            ("q", ["Research And Development"]),
    ("results", "sgaQ2"):            ("q", ["Selling General And Administration",
                                            "General And Administrative Expense"]),
    ("results", "netLossQ2"):        ("q", ["Net Income", "Net Income Common Stockholders"]),
    ("results", "interestExpenseQ2"): ("q", ["Interest Expense"]),
    ("balanceSheet", "cash"):        ("b", ["Cash And Cash Equivalents"]),
    ("balanceSheet", "totalAssets"): ("b", ["Total Assets"]),
    ("balanceSheet", "equity"):      ("b", ["Stockholders Equity", "Common Stock Equity"]),
    ("cashFlow", "cfoH1"):           ("cf2", ["Operating Cash Flow",
                                              "Cash Flow From Continuing Operating Activities"]),
    ("cashFlow", "capexH1"):         ("cf2", ["Capital Expenditure"]),
    # META (single fiscal quarter, not an H1 aggregate — "cf"/"q"/"b" pull
    # the latest one period, unlike "cf2" which sums the latest two).
    ("results", "opIncQ2"):          ("q", ["Operating Income", "Total Operating Income As Reported"]),
    ("results", "netIncQ2"):         ("q", ["Net Income", "Net Income Common Stockholders"]),
    ("results", "taxQ2"):            ("q", ["Tax Provision", "Income Tax Expense Benefit"]),
    ("results", "capexQ2"):          ("cf", ["Capital Expenditure"]),
    ("results", "cfoQ2"):            ("cf", ["Operating Cash Flow",
                                             "Cash Flow From Continuing Operating Activities"]),
    ("balanceSheet", "totalAssetsQ2"):      ("b", ["Total Assets"]),
    ("balanceSheet", "totalLiabilitiesQ2"): ("b", ["Total Liabilities Net Minority Interest",
                                                    "Total Liabilities"]),
    ("balanceSheet", "totalEquityQ2"):      ("b", ["Stockholders Equity", "Common Stock Equity"]),
    ("debt", "carryingValue"):       ("b", ["Long Term Debt", "Total Debt"]),
    ("debt", "interestExpQ2"):       ("q", ["Interest Expense"]),
}


def latest(df, names, n=1):
    for nm in names:
        if df is not None and nm in df.index:
            s = df.loc[nm].dropna()
            if len(s) >= n:
                return sum(float(v) for v in s.iloc[:n]) / 1e6
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: crosscheck.py <SYMBOL>")
    sym = sys.argv[1].upper()
    ep = json.load(open(os.path.join(HERE, "episodes", f"{sym}.json")))
    try:
        import yfinance as yf
    except ImportError:
        sys.exit("yfinance is not installed — this check is optional; skipping is fine")

    t = yf.Ticker(sym)
    frames = {"q": t.quarterly_financials, "b": t.quarterly_balance_sheet,
              "cf": t.quarterly_cashflow, "cf2": t.quarterly_cashflow}
    if all(f is None or f.empty for f in frames.values()):
        print(f"{sym}: the vendor has no financials for this ticker — nothing to compare")
        return 0

    agree, differ, missing = [], [], []
    print(f"{'metric':<34}{'filed $M':>12}{'vendor $M':>12}{'diff':>9}")
    print("-" * 67)
    for (blk, key), (which, names) in MAP.items():
        node = (ep["filings"].get(blk) or {}).get(key)
        if not node:
            continue
        filed = float(node["v"])
        got = latest(frames[which], names, 2 if which == "cf2" else 1)
        if got is None:
            missing.append(f"{blk}.{key}"); continue
        if abs(filed) > 0 and (filed < 0) != (got < 0) and abs(got) > 0:
            got = -got if abs(abs(got) - abs(filed)) < abs(got - filed) else got
        d = (got - filed) / abs(filed) * 100 if filed else 0.0
        row = f"{blk}.{key:<26}{filed:>12,.0f}{got:>12,.0f}{d:>8.1f}%"
        if abs(d) <= TOL:
            agree.append(row); print(row)
        else:
            differ.append(row); print(row + "   <-- DISAGREES")

    print()
    print(f"{len(agree)} agree within {TOL}% · {len(differ)} disagree · "
          f"{len(missing)} not provided by the vendor")
    if missing:
        print("  not provided:", ", ".join(missing))
    if differ:
        print("\nTHE FILING WINS. Explain each gap before changing anything — a vendor")
        print("normalises across companies and will fold lines together that a filing")
        print("keeps separate. Record the explanation in the episode's note field.")
        return 1
    print("\nEvery mapped figure matches an independent source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

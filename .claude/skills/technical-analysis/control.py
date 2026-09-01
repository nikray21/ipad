"""Controls for the A-setup measurement. Does the setup beat random on THIS data?"""
import sys, os, json, random, statistics as st
sys.path.insert(0, ".claude/skills/technical-analysis")
import backtest as B

random.seed(7)
bars = json.load(open(".claude/skills/technical-analysis/.cache_bars.json"))
bars = {k: v for k, v in bars.items() if len(v) >= 120}

# his original 50-name universe, as named in the skill + backtest doc
ORIG = """NVDA AMD AVGO MU INTC QCOM ARM MRVL LRCX AMAT KLAC ASML SMCI DELL AAPL MSFT
GOOGL AMZN META NFLX TSLA ORCL CRM ADBE NOW PANW CRWD ZS NET DDOG SNOW PLTR SHOP UBER
ABNB RBLX SOFI AFRM HOOD COIN PYPL TTD DKNG RKLB IREN RIOT MARA NBIS BAC CVX MCD SBUX""".split()


def run(pick, label):
    res4, res8 = [], []
    for sym, rows in bars.items():
        for i in pick(sym, rows):
            res4.append(B.barrier(rows, i, 0.04)[0])
            res8.append(B.barrier(rows, i, 0.08)[0])
    if not res4:
        print(f"{label}: no episodes"); return
    h4 = sum(res4) / len(res4) * 100
    h8 = sum(res8) / len(res8) * 100
    e8 = sum(x * 2 - (1 - x) for x in res8) / len(res8)
    e4 = sum(x * 1 - (1 - x) for x in res4) / len(res4)
    print("%-38s n=%-5d  +4%% %5.1f%%  +8%% %5.1f%%   E(1:1) %+.2fR  E(1:2) %+.2fR" % (
        label, len(res4), h4, h8, e4, e8))


def setup(_, rows):
    return B.signals(rows)


def setup_steep(_, rows):
    """A-grade cut: slope >= 1.5% instead of 1.0%."""
    out = []
    for i in B.signals(rows):
        c = [r["c"] for r in rows[:i + 1]]
        sma, prev = sum(c[-50:]) / 50, sum(c[-60:-10]) / 50
        if (sma - prev) / prev * 100 >= 1.5:
            out.append(i)
    return out


def orig_only(sym, rows):
    return B.signals(rows) if sym in ORIG else []


def rand_entry(_, rows):
    """Random bars, same count per name as the setup fires, same eligibility."""
    n = len(B.signals(rows))
    if not n:
        return []
    lo, hi = 60, len(rows) - 1
    return random.sample(range(lo, hi), min(n * 6, hi - lo))


print("Alpaca SIP 4h bars, %d names, %s -> %s\n" % (
    len(bars), min(v[0]["t"][:10] for v in bars.values()),
    max(v[-1]["t"][:10] for v in bars.values())))
run(setup, "A-setup (slope >= 1.0%)")
run(setup_steep, "A-setup, A-grade cut (slope >= 1.5%)")
run(orig_only, "A-setup, his original ~50-name universe")
run(rand_entry, "RANDOM entry baseline (the control)")

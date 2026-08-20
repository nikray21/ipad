"""Self-checks for the playbook arithmetic.

    python3 test_trade_setup.py
"""

from trade_setup import atr, sma, last_visit, grade


def flat(n, price=100.0, vol=1000.0):
    return [{"t": i * 3600000, "o": price, "h": price + 0.5, "l": price - 0.5,
             "c": price, "v": vol} for i in range(n)]


def put(bars, i, h, l, c, o=100.0, v=1000.0):
    bars[i] = {"t": i * 3600000, "o": o, "h": h, "l": l, "c": c, "v": v}


def test_atr_is_wilders_not_a_mean():
    """One wide bar must move ATR by 1/14th of the gap, not by 1/14th of nothing."""
    b = flat(21)                               # every TR is exactly 1.0
    assert abs(atr(b, 14) - 1.0) < 1e-9, atr(b, 14)

    put(b, 20, h=110.0, l=99.0, c=100.0)       # TR = 11
    got = atr(b, 14)
    assert abs(got - (1.0 * 13 + 11.0) / 14) < 1e-9, got

    # Wilder's carries the calm bars forward, so it must sit BELOW the plain
    # mean of the last 14 true ranges once volatility steps up.
    b = flat(40)
    for i in range(30, 40):
        put(b, i, h=110.0, l=99.0, c=100.0)
    assert atr(b, 14) < (4 * 1.0 + 10 * 11.0) / 14, atr(b, 14)


def test_atr_needs_enough_bars():
    assert atr(flat(10), 14) is None


def test_sma_and_lookback():
    b = [{"t": 0, "o": 0, "h": 0, "l": 0, "c": float(i), "v": 0} for i in range(1, 61)]
    assert sma(b, 50) == sum(range(11, 61)) / 50
    assert sma(b, 50, back=6) == sum(range(5, 55)) / 50
    assert sma(b, 50, back=20) is None


def test_last_visit_takes_only_the_latest_run():
    b = flat(40, price=105.0)
    zone = {"top": 100.0, "btm": 90.0, "pivot_i": 5}
    for i in (10, 11, 12, 25, 26):
        put(b, i, h=101.0, l=95.0, c=99.0)
    assert last_visit(b, zone) == [25, 26]
    assert last_visit(flat(40, price=105.0), zone) == []


def _long_bars():
    """Flat at 100, a swing low at bar 20, a revisit that stalls inside it,
    then price parked above the zone."""
    b = flat(80)
    put(b, 20, h=100.5, l=90.0, c=100.0)
    for i in range(21, 31):
        put(b, i, h=101.0, l=95.0, c=100.0, v=200000.0)
    for i in range(31, 80):
        put(b, i, h=105.5, l=104.5, c=105.0)
    return b


def test_grade_long_end_to_end():
    b = _long_bars()
    g = grade(b, "long", budget=100.0, length=3, min_vol=1e6)

    assert g["zone"]["btm"] == 90.0 and g["zone"]["top"] == 100.0, g["zone"]
    assert g["zone"]["volume"] == 2_000_000.0, g["zone"]
    assert g["in_zone"] is False and g["entry"] == 105.0

    assert abs(g["level"] - 90.0) < 1e-9
    assert abs(g["stop"] - (90.0 - 1.5 * atr(b, 14))) < 1e-9      # off the LEVEL
    assert abs(g["risk_per_share"] - (105.0 - g["stop"])) < 1e-9
    assert g["shares"] == int(100.0 // g["risk_per_share"])
    assert "rr" not in g                                          # no zone to target


def test_grade_reports_a_stall_as_a_stall():
    g = grade(_long_bars(), "long", length=3, min_vol=1e6)
    v = g["visit"]
    assert v["extreme"] == 95.0 and v["edge_to_beat"] == 90.0
    assert v["swept"] is False and v["missed_by"] == 5.0, v
    assert v["ended_bars_ago"] == 49, v


def test_grade_flags_a_stop_hung_off_entry():
    b = _long_bars()
    a = atr(b, 14)
    g = grade(b, "long", length=3, min_vol=1e6, stop=105.0 - 1.5 * a)
    assert g["stop_is_noise_bait"] is True, g          # the Entry - 1.5xATR mistake
    g = grade(b, "long", length=3, min_vol=1e6, stop=90.0 - 1.5 * a - 0.01)
    assert g["stop_is_noise_bait"] is False, g


def test_grade_says_so_when_there_is_no_zone():
    g = grade(_long_bars(), "long", length=3, min_vol=1e12)
    assert "error" in g and g["zone"] is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")

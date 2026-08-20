"""Self-checks for the Liquidity Swings port.

Stdlib asserts, no test runner — same contract as the rest of the pipeline.
Each case pins one semantic of the Pine original that is easy to get subtly
wrong and impossible to eyeball afterwards.

    python3 test_liquidity_swings.py
"""

from liquidity_swings import swing_zones, to_session_bars


def flat(n, price=100.0, vol=1000.0):
    return [{"t": i * 3600000, "o": price, "h": price + 0.5, "l": price - 0.5,
             "c": price, "v": vol} for i in range(n)]


def spike(bars, i, high, close, low=99.9, vol=1000.0):
    bars[i] = {"t": i * 3600000, "o": 100.0, "h": high, "l": low, "c": close, "v": vol}


def reach(bars, idxs, high=105.0, vol=1000.0):
    for i in idxs:
        bars[i] = {"t": i * 3600000, "o": 100.0, "h": high, "l": 99.5, "c": 100.0, "v": vol}


def highs(zones):
    return [z for z in zones if z["side"] == "high"]


def test_zone_edges():
    """Wick area stops at the body top; full area runs to the candle low."""
    b = flat(30)
    spike(b, 10, high=110.0, close=101.0)

    z = highs(swing_zones(b, length=3, area="wick"))
    assert len(z) == 1, z
    assert z[0]["pivot_i"] == 10
    assert z[0]["top"] == 110.0 and z[0]["btm"] == 101.0, z[0]
    assert z[0]["level"] == 110.0

    z = highs(swing_zones(b, length=3, area="full"))
    assert z[0]["btm"] == 99.9, z[0]


def test_overlap_counts_bars_not_touches():
    """Volume is every later bar whose range crosses the box, not level taps."""
    b = flat(30)
    spike(b, 10, high=110.0, close=101.0)
    reach(b, [11, 12, 13], vol=2000.0)

    z = highs(swing_zones(b, length=3))[0]
    assert z["count"] == 3, z          # bars 11-13 overlap
    assert z["volume"] == 6000.0, z    # the flat bars top out below btm=101


def test_accumulation_stops_at_next_pivot():
    """A zone's label freezes when the next same-side pivot confirms."""
    b = flat(30)
    spike(b, 10, high=110.0, close=101.0)
    reach(b, [11, 12])
    spike(b, 18, high=120.0, close=101.0)
    reach(b, [19, 20, 21])

    z = highs(swing_zones(b, length=3))
    assert [x["pivot_i"] for x in z] == [10, 18], z
    assert z[0]["count"] == 2, z[0]    # 19-21 overlap it too, but come too late
    assert z[1]["count"] == 3, z[1]


def test_pivot_lag_truncates_the_newest_zone():
    """Pine samples bar n-length, so the last `length` bars never count."""
    b = flat(30)
    spike(b, 10, high=110.0, close=101.0)
    reach(b, range(11, 30))

    z = highs(swing_zones(b, length=3))[0]
    assert z["count"] == 16, z         # bars 11..26, not 11..29


def test_broken_is_chart_faithful_taken_is_not():
    """A level taken long after its zone went stale still draws solid."""
    b = flat(30)
    spike(b, 10, high=110.0, close=101.0)
    spike(b, 18, high=120.0, close=101.0)
    spike(b, 25, high=116.0, close=115.0)      # closes through zone 1's top

    z = highs(swing_zones(b, length=3))[0]
    assert z["taken"] is True and z["taken_i"] == 25, z
    assert z["broken"] is False, z              # frozen at bar 18+3-1 = 20


def test_filter_marks_rather_than_drops():
    b = flat(30)
    spike(b, 10, high=110.0, close=101.0)
    reach(b, [11, 12], vol=5000.0)

    z = highs(swing_zones(b, length=3, filter_by="volume", filter_value=20000.0))[0]
    assert z["shown"] is False and z["volume"] == 10000.0, z
    z = highs(swing_zones(b, length=3, filter_by="volume", filter_value=5000.0))[0]
    assert z["shown"] is True, z


def test_session_anchored_aggregation():
    """Two 4h bars a day: 09:30-13:30 and the short 13:30-16:00 stub."""
    day1 = [{"t": 1755696600000 + i * 3600000, "o": 10.0 + i, "h": 12.0 + i,
             "l": 9.0 + i, "c": 11.0 + i, "v": 100} for i in range(7)]
    out = to_session_bars(day1, 4)
    assert len(out) == 2, out
    assert out[0]["o"] == 10.0 and out[0]["c"] == 14.0
    assert out[0]["h"] == 15.0 and out[0]["l"] == 9.0 and out[0]["v"] == 400
    assert out[1]["v"] == 300, out[1]          # 3-bar close, not padded to 4


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")

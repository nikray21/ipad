"""The annotated chart figures for the playbook PDF."""
from chartlib import *

# =============================================================================
# THE NUMBERS. Every figure and every table in the PDF reads from these dicts,
# so a diagram can never disagree with the arithmetic beside it.
# =============================================================================
LONG = dict(
    zone_top=212.0, zone_bot=204.0, zone_vol="18.9M",
    res_top=254.0, res_bot=246.0, res_vol="32.4M",
    atr=3.0, bait_low=200.5,
)
LONG["level"]  = LONG["zone_bot"]
LONG["stop"]   = LONG["level"] - 1.5 * LONG["atr"]
LONG["entry"]  = 214.0
LONG["risk"]   = LONG["entry"] - LONG["stop"]
LONG["target"] = 243.0
LONG["reward"] = LONG["target"] - LONG["entry"]
LONG["rr"]     = LONG["reward"] / LONG["risk"]
LONG["budget"] = 100.0
LONG["shares"] = int(LONG["budget"] // LONG["risk"])
LONG["atrock"] = 1.5 * LONG["atr"]

SHORT = dict(
    zone_top=206.0, zone_bot=198.0, zone_vol="24.3M",
    sup_top=162.0, sup_bot=154.0, sup_vol="30.1M",
    atr=3.0, bait_high=209.5,
)
SHORT["level"]  = SHORT["zone_top"]
SHORT["stop"]   = SHORT["level"] + 1.5 * SHORT["atr"]
SHORT["entry"]  = 196.0
SHORT["risk"]   = SHORT["stop"] - SHORT["entry"]
SHORT["target"] = 164.0
SHORT["reward"] = SHORT["entry"] - SHORT["target"]
SHORT["rr"]     = SHORT["reward"] / SHORT["risk"]
SHORT["budget"] = 100.0
SHORT["shares"] = int(SHORT["budget"] // SHORT["risk"])
SHORT["atrock"] = 1.5 * SHORT["atr"]

# The real NBIS numbers off the 17 Aug 2026 4h chart
NBIS = dict(price=270.30, atr=11.3, zone_top=290.0, zone_bot=280.0, zone_vol="2.723M",
            target=226.47, budget=100.0)
NBIS["stop"]   = NBIS["zone_top"] + 1.5 * NBIS["atr"]
NBIS["risk"]   = NBIS["stop"] - NBIS["price"]
NBIS["reward"] = NBIS["price"] - NBIS["target"]
NBIS["rr"]     = NBIS["reward"] / NBIS["risk"]
NBIS["shares"] = int(NBIS["budget"] // NBIS["risk"])


# =============================================================================
def fig_long(w=880, h=418):
    L = LONG
    c = Chart(w, h, 186, 262, 26, pad_l=48, pad_r=116, pad_t=16, pad_b=20)
    c.frame([190, 200, 210, 220, 230, 240, 250, 260], axis_side="left")

    c.zone(L["res_top"], L["res_bot"], "red",
           f'{L["res_vol"]}  ·  the target goes in FRONT of this zone')
    c.zone(L["zone_top"], L["zone_bot"], "green", f'{L["zone_vol"]}  demand')
    c.band(L["level"], L["stop"], STOPC, f'1.5 × ATR = {L["atrock"]:.1f}', 9, 26,
           opacity=0.12, lab_slot=18)

    d  = path([(0, 197), (8, 228)], 9, seed=11, vol=0.42)
    d += path([(0, 228), (2, 224), (6, 207)], 6, seed=23, vol=0.40)
    d.append((207.5, 208.5, L["bait_low"], 206.0))                    # 15: the bait wick
    d.append((206.0, 215.5, 205.5, L["entry"]))                       # 16: the trigger close
    d += path([(0, L["entry"]), (4, 224), (9, 244)], 9, seed=5, vol=0.36)
    c.candles(d)

    c.polyline([(0, 193), (8, 199), (14, 203), (19, 206), (25, 212)], MA_UP, 2.3)
    c.polyline([(0, 189), (10, 193), (18, 197), (25, 202)], SMA50, 1.7)

    c.hline(L["entry"],  ENTRY,   f'ENTRY {L["entry"]:.2f}',   s0=16, width=1.7, bold=True)
    c.hline(L["stop"],   STOPC,   f'STOP {L["stop"]:.2f}',     s0=9,  width=1.7, bold=True)
    c.hline(L["target"], TARGETC, f'TARGET {L["target"]:.2f}', s0=16, width=1.7, bold=True)

    c.panel(0.2, 244, [("Risk  (1R)", f'{L["risk"]:.2f}', "#ff8a80"),
                       ("Reward (2R)", f'{L["reward"]:.2f}', "#4ecdc4"),
                       ("R : R", f'{L["rr"]:.2f}', "#ffffff")],
            w=182, title="THE LONG")

    c.marker(8, 199.0, 1)
    c.note(8, 189.4, "green line + price above the 50 SMA", MUTED, size=9.5, weight="600")
    c.marker(13, 208.0, 2)
    c.note(13.2, 236.5, "pullback INTO the zone", MUTED, size=9.5, weight="600")
    c.arrow(13.2, 234.0, 13.6, 214.5)
    c.spotlight(15, 16, 217.4, 198.4)
    c.marker(15, 197.2, 3)
    c.note(14.2, 192.2, "the bait wick", CALLOUT, size=9.5, weight="700")
    c.marker(16.7, 215.4, 4)
    c.note(21.2, 191.0, "4h CLOSE back above the zone", CALLOUT, size=9.5, weight="700")
    c.arrow(20.4, 193.2, 17.3, 211.0)
    c.marker(24, L["stop"], 5)
    c.marker(20, L["target"], 6)
    c.legend([("SWING CALL", MA_UP), ("50 SMA", SMA50), ("zone", GREENZONE),
              ("stop", STOPC), ("target", TARGETC)], x=250, y=13)
    return c.render()


# =============================================================================
def fig_short(w=880, h=418):
    S = SHORT
    c = Chart(w, h, 148, 224, 26, pad_l=48, pad_r=116, pad_t=16, pad_b=20)
    c.frame([150, 160, 170, 180, 190, 200, 210, 220], axis_side="left")

    c.zone(S["zone_top"], S["zone_bot"], "red", f'{S["zone_vol"]}  supply', s0=3)
    c.zone(S["sup_top"], S["sup_bot"], "green",
           f'{S["sup_vol"]}  ·  the target goes in FRONT of this zone')
    c.band(S["stop"], S["level"], STOPC, f'1.5 × ATR = {S["atrock"]:.1f}', 9, 26,
           opacity=0.12, lab_slot=18)

    d  = path([(0, 216), (8, 188)], 9, seed=3, vol=0.42)
    d += path([(0, 188), (2, 193), (6, 202)], 6, seed=27, vol=0.34)
    d.append((202.0, S["bait_high"], 201.0, 203.0))                   # 15: the bait wick
    d.append((203.0, 203.5, 195.0, S["entry"]))                       # 16: the trigger close
    d += path([(0, S["entry"]), (4, 183), (9, 160)], 9, seed=9, vol=0.36)
    c.candles(d)

    c.polyline([(0, 219), (8, 209), (14, 206), (19, 200), (25, 190)], MA_DOWN, 2.3)
    c.polyline([(0, 223), (10, 216), (18, 211), (25, 205)], SMA50, 1.7)

    c.hline(S["entry"],  ENTRY,   f'ENTRY {S["entry"]:.2f}',   s0=16, width=1.7, bold=True)
    c.hline(S["stop"],   STOPC,   f'STOP {S["stop"]:.2f}',     s0=9,  width=1.7, bold=True)
    c.hline(S["target"], TARGETC, f'TARGET {S["target"]:.2f}', s0=16, width=1.7, bold=True)

    c.panel(0.2, 186, [("Risk  (1R)", f'{S["risk"]:.2f}', "#ff8a80"),
                       ("Reward", f'{S["reward"]:.2f}', "#4ecdc4"),
                       ("R : R", f'{S["rr"]:.2f}', "#ffffff")],
            w=186, title="THE SHORT")

    c.marker(8, 209.0, 1)
    c.note(7.5, 214.4, "red line + price below the 50 SMA", MUTED, size=9.5, weight="600")
    c.marker(13, 196.4, 2)
    c.note(13.2, 179.5, "rally INTO the zone", MUTED, size=9.5, weight="600")
    c.arrow(13.2, 181.5, 13.6, 194.0)
    c.spotlight(15, 16, 211.6, 192.6)
    c.marker(15, 213.4, 3)
    c.note(14.2, 219.2, "the bait wick", CALLOUT, size=9.5, weight="700")
    c.marker(16.7, 194.4, 4)
    c.note(21.2, 218.0, "4h CLOSE back below the zone", CALLOUT, size=9.5, weight="700")
    c.arrow(20.4, 215.5, 17.3, 199.5)
    c.marker(24, S["stop"], 5)
    c.marker(20, S["target"], 6)
    c.legend([("SWING CALL", MA_DOWN), ("50 SMA", SMA50), ("zone", REDZONE),
              ("stop", STOPC), ("target", TARGETC)], x=250, y=13)
    return c.render()


# =============================================================================
def _gate(title, verdict, vcol, ma_pts, sma_pts, wp, lo, hi, seed, sub):
    c = Chart(272, 158, lo, hi, 22, pad_r=10, pad_t=28, pad_b=28)
    c.frame()
    c.add(f'<text x="10" y="17" fill="{TEXT}" font-size="11.5" font-weight="700" '
          f'font-family="-apple-system,Helvetica,sans-serif">{esc(title)}</text>')
    c.candles(path(wp, 22, seed=seed, vol=0.42))
    c.polyline(ma_pts, MA_UP if "green" in title.lower() else MA_DOWN, 2.2)
    c.polyline(sma_pts, SMA50, 1.7)
    c.add(f'<rect x="8" y="{158-25}" width="256" height="19" rx="4" fill="{vcol}" fill-opacity="0.16"/>')
    c.add(f'<text x="14" y="{158-11}" fill="{vcol}" font-size="10.5" font-weight="800" '
          f'font-family="-apple-system,Helvetica,sans-serif">{esc(verdict)}</text>')
    c.add(f'<text x="{272-14}" y="{158-11}" fill="{MUTED}" font-size="9" text-anchor="end" '
          f'font-family="-apple-system,Helvetica,sans-serif">{esc(sub)}</text>')
    return c.render()


def fig_gates():
    a = _gate("Green line + price above 50 SMA", "LONGS ONLY", BULL,
              [(0, 96), (10, 102), (21, 110)], [(0, 93), (10, 98), (21, 105)],
              [(0, 99), (8, 108), (13, 104), (21, 118)], 88, 126, 4, "both conditions met")
    b = _gate("Red line + price below 50 SMA", "SHORTS ONLY", BEAR,
              [(0, 118), (10, 110), (21, 100)], [(0, 121), (10, 114), (21, 105)],
              [(0, 116), (8, 106), (13, 110), (21, 95)], 88, 126, 6, "both conditions met")
    c = Chart(272, 158, 88, 126, 22, pad_r=10, pad_t=28, pad_b=28)
    c.frame()
    c.add(f'<text x="10" y="17" fill="{TEXT}" font-size="11.5" font-weight="700" '
          f'font-family="-apple-system,Helvetica,sans-serif">Green line, but price BELOW 50 SMA</text>')
    c.candles(path([(0, 112), (9, 100), (14, 104), (21, 99)], 22, seed=13, vol=0.42))
    c.polyline([(0, 94), (10, 97), (21, 100)], MA_UP, 2.2)
    c.polyline([(0, 108), (10, 106), (21, 104)], SMA50, 1.7)
    c.add(f'<rect x="8" y="133" width="256" height="19" rx="4" fill="{CALLOUT}" fill-opacity="0.16"/>')
    c.add(f'<text x="14" y="147" fill="{CALLOUT}" font-size="10.5" font-weight="800" '
          f'font-family="-apple-system,Helvetica,sans-serif">NO TRADE</text>')
    c.add(f'<text x="258" y="147" fill="{MUTED}" font-size="9" text-anchor="end" '
          f'font-family="-apple-system,Helvetica,sans-serif">signals disagree — sit out</text>')
    return a, b, c.render()


# =============================================================================
def fig_zones(w=880, h=292):
    c = Chart(w, h, 92, 154, 40, pad_l=46, pad_r=16, pad_t=26, pad_b=16)
    c.frame([100, 110, 120, 130, 140, 150], axis_side="left")
    c.add(f'<text x="46" y="15" fill="{MUTED}" font-size="10" '
          f'font-family="-apple-system,Helvetica,sans-serif">'
          f'Four zones on one chart. Only two of them are levels.</text>')

    rows = [(147, 141, "red",   False, "2.7M",  "thin — barely traded. Weakest wall here."),
            (134, 128, "red",   False, "32.4M", "heavy — real supply. Tradeable."),
            (117, 111, "green", True,  "28.6M", "DASHED = already broken. Ignore it."),
            (104,  98, "green", False, "41.2M", "heavy + solid — the one you want.")]
    for top, bot, kind, dashed, vol, sub in rows:
        c.zone(top, bot, kind, s0=0, s1=40, dashed=dashed)
        col = GREENZONE if kind == "green" else REDZONE
        mid = (top + bot) / 2
        c.add(f'<text x="{c.x(21.6):.1f}" y="{c.y(mid)+4:.1f}" fill="{col}" font-size="11.5" '
              f'font-weight="800" font-family="ui-monospace,Menlo,monospace">{esc(vol)}</text>')
        c.add(f'<text x="{c.x(21.6)+54:.1f}" y="{c.y(mid)+4:.1f}" fill="{MUTED if not dashed else DIM}" '
              f'font-size="10.5" font-family="-apple-system,Helvetica,sans-serif">{esc(sub)}</text>')

    c.candles(path([(0, 120), (5, 144), (9, 130), (13, 113), (17, 100), (20, 115)], 20,
                   seed=21, vol=0.34))
    return c.render()


# =============================================================================
def _stopdemo(title, stop_price, ok, w=428, h=316):
    L = LONG
    c = Chart(w, h, 196, 234, 22, pad_l=40, pad_r=92, pad_t=34, pad_b=16)
    c.frame([200, 210, 220, 230], axis_side="left")
    col = BULL if ok else BEAR
    c.add(f'<text x="10" y="20" fill="{col}" font-size="12" font-weight="800" '
          f'font-family="-apple-system,Helvetica,sans-serif">{esc(title)}</text>')
    c.zone(L["zone_top"], L["zone_bot"], "green", L["zone_vol"])
    d = path([(0, 224), (7, 213), (10, 207)], 10, seed=17, vol=0.42)
    d.append((207.0, 208.2, L["bait_low"], 206.4))
    d.append((206.4, 215.4, 206.0, L["entry"]))
    d += path([(0, L["entry"]), (4, 219), (9, 229)], 10, seed=2, vol=0.36)
    c.candles(d)
    c.hline(L["entry"], ENTRY, f'entry {L["entry"]:.2f}', s0=11, dash="6 4", bold=True)
    c.hline(stop_price, STOPC, f'stop {stop_price:.2f}', dash="6 4", width=1.8, bold=True)
    if ok:
        c.band(L["level"], stop_price, STOPC, "1.5 × ATR", 0, 22, opacity=0.13, lab_slot=5)
        c.note(11, 197.6, f'bait wick {L["bait_low"]:.2f} stays ABOVE the stop', BULL,
               dy=0, size=10, weight="700")
        c.note(16.5, 229.5, "still in the trade", BULL, dy=0, size=10, weight="700")
    else:
        c.add(f'<circle cx="{c.x(10):.1f}" cy="{c.y(stop_price):.1f}" r="13" '
              f'fill="none" stroke="{BEAR}" stroke-width="2"/>')
        c.note(11, 197.6, "the bait wick takes you out here", BEAR, dy=0, size=10, weight="700")
        c.note(16.5, 229.5, "…and it rallies without you", BEAR, dy=0, size=10, weight="700")
    return c.render()


def fig_stops():
    L = LONG
    return (_stopdemo(f'RIGHT   stop = LEVEL − 1.5×ATR = {L["stop"]:.2f}', L["stop"], True),
            _stopdemo(f'WRONG   stop = ENTRY − 1.5×ATR = {L["entry"]-L["atrock"]:.2f}',
                      L["entry"] - L["atrock"], False))


# =============================================================================
def _fail(title, why, draw, seed):
    c = Chart(428, 236, 190, 240, 24, pad_l=38, pad_r=88, pad_t=32, pad_b=40)
    c.frame([200, 210, 220, 230], axis_side="left")
    c.add(f'<text x="10" y="19" fill="{BEAR}" font-size="11.5" font-weight="800" '
          f'font-family="-apple-system,Helvetica,sans-serif">{esc(title)}</text>')
    draw(c, seed)
    c.add(f'<text x="10" y="{236-13}" fill="{NOTE}" font-size="9.5" '
          f'font-family="-apple-system,Helvetica,sans-serif">{esc(why)}</text>')
    return c.render()


def fig_fails():
    L = LONG

    def midair(c, s):
        c.zone(212, 204, "green", "18.9M")
        c.candles(path([(0, 200), (8, 214), (16, 228), (23, 222)], 24, seed=s, vol=0.40))
        c.hline(228, BEAR, "bought here", s0=14, dash="5 3", bold=True)
        c.note(12, 234, "40 points of air under you", BEAR, dy=0, size=10, weight="700")

    def wrongline(c, s):
        c.zone(212, 204, "green", "18.9M")
        c.candles(path([(0, 232), (10, 216), (17, 208), (23, 197)], 24, seed=s, vol=0.40))
        c.polyline([(0, 236), (10, 222), (23, 206)], MA_DOWN, 2.2)
        c.hline(210, BEAR, "bought the dip", s0=12, dash="5 3", bold=True)
        c.note(11, 235, "line is RED — grading stops at step 1", BEAR, dy=0, size=10, weight="700")

    def wickentry(c, s):
        c.zone(212, 204, "green", "18.9M")
        d = path([(0, 226), (9, 208)], 9, seed=s, vol=0.40)
        d.append((207.0, 208.0, 197.0, 199.0))
        d.append((199.0, 200.0, 193.5, 194.5))
        d += path([(0, 194.5), (12, 197)], 13, seed=s + 1, vol=0.30)
        c.candles(d)
        c.hline(199, BEAR, "bought the wick", s0=9, dash="5 3", bold=True)
        c.note(14, 233, "no 4h CLOSE back above the zone", BEAR, dy=0, size=10, weight="700")

    def weakzone(c, s):
        c.zone(212, 204, "green", "2.7M")
        c.candles(path([(0, 228), (8, 213), (12, 206), (23, 194)], 24, seed=s, vol=0.40))
        c.hline(208, BEAR, "bought the zone", s0=10, dash="5 3", bold=True)
        c.note(13, 232, "2.7M is not a wall — it is a rumour", BEAR, dy=0, size=10, weight="700")

    return [
        _fail("1  ENTRY IN MID-AIR", "No zone under the entry. Your most expensive habit — grade step 2 loudest.", midair, 31),
        _fail("2  WRONG LINE COLOUR", "Buying dips in a downtrend. The line colour is a gate, not a suggestion.", wrongline, 33),
        _fail("3  ENTERED ON THE WICK", "The wick is the bait. Only a completed 4h candle is information.", wickentry, 35),
        _fail("4  THIN ZONE", "Millions of shares or it is not support. Compare it to the others on your chart.", weakzone, 37),
    ]


# =============================================================================
def fig_nbis(w=880, h=312):
    N = NBIS
    c = Chart(w, h, 150, 320, 44, pad_l=46, pad_r=118, pad_t=16, pad_b=16)
    c.frame([160, 180, 200, 220, 240, 260, 280, 300], axis_side="left")
    c.zone(N["zone_top"], N["zone_bot"], "red", N["zone_vol"] + "  ← weakest zone on the chart", s0=8)
    c.zone(196, 186, "green", "16.6M", s0=22, s1=34)
    c.zone(232, 224, "red", "32.4M", s0=2, s1=30)

    d = path([(0, 250), (4, 232), (11, 214), (17, 168), (21, 190), (25, 186)], 25, seed=41, vol=0.42)
    d += path([(0, 186), (2, 250), (6, 262), (11, 288), (14, 276)], 14, seed=43, vol=0.34)
    d += path([(0, 276), (4, 270)], 5, seed=45, vol=0.25)
    c.candles(d)

    c.polyline([(0, 252), (6, 236), (12, 208), (20, 190), (27, 186)], MA_DOWN, 2.3)
    c.polyline([(27, 186), (33, 196), (43, 222)], MA_UP, 2.5)
    c.hline(N["price"], ENTRY, f'short here?  {N["price"]:.2f}', s0=36, dash="6 4", bold=True)
    c.hline(N["stop"], STOPC, f'stop {N["stop"]:.2f}', s0=30, dash="6 4", width=1.6, bold=True)
    c.hline(N["target"], TARGETC, f'target {N["target"]:.2f}', s0=30, dash="6 4", width=1.6, bold=True)

    c.note(35, 206, "line turned GREEN here", MA_UP, dy=0, size=10, weight="700")
    c.note(33, 308, "one touch is not a rejection", CALLOUT, dy=0, size=10.5, weight="700")
    c.note(33, 166, "+60% in four sessions", MUTED, dy=0, size=10, weight="600")
    return c.render()


# =============================================================================
def fig_lag(w=880, h=142):
    """How late the colour flip actually is — NBIS, 9 Jun to 17 Aug 2026."""
    x0, x1 = 44, 836
    segs = [(0.000, 0.319, MA_UP,   "GREEN"),
            (0.319, 0.913, MA_DOWN, "RED"),
            (0.913, 1.000, MA_UP,   "GREEN")]
    p = [f'<rect x="0" y="0" width="{w}" height="{h}" fill="{BG}" rx="4"/>']
    by, bh = 56, 23
    for a, b, col, lab in segs:
        xa, xb = x0 + a * (x1 - x0), x0 + b * (x1 - x0)
        p.append(f'<rect x="{xa:.1f}" y="{by}" width="{xb-xa:.1f}" height="{bh}" '
                 f'fill="{col}" fill-opacity="0.30" stroke="{col}" stroke-width="1.2"/>')
        if xb - xa > 46:
            p.append(f'<text x="{(xa+xb)/2:.1f}" y="{by+17}" fill="{col}" font-size="10.5" '
                     f'font-weight="800" text-anchor="middle" letter-spacing="1" '
                     f'font-family="-apple-system,Helvetica,sans-serif">{lab}</text>')
    for frac, top, bot, col in [
            (0.319, "line flips RED here", "…but price had already fallen 292 → 250", BEAR),
            (0.913, "line flips GREEN here", "…price had already risen 160 → 190", BULL)]:
        xf = x0 + frac * (x1 - x0)
        p.append(f'<line x1="{xf:.1f}" y1="46" x2="{xf:.1f}" y2="{by+bh+10}" '
                 f'stroke="{CALLOUT}" stroke-width="1.4" stroke-dasharray="4 3"/>')
        p.append(f'<circle cx="{xf:.1f}" cy="{by+bh/2}" r="4.5" fill="{CALLOUT}"/>')
        p.append(f'<text x="{xf:.1f}" y="38" fill="{CALLOUT}" font-size="11" font-weight="800" '
                 f'text-anchor="middle" font-family="-apple-system,Helvetica,sans-serif">'
                 f'{esc(top)}</text>')
        p.append(f'<text x="{xf:.1f}" y="{by+bh+26}" fill="{col}" font-size="10.5" '
                 f'font-weight="700" text-anchor="middle" '
                 f'font-family="-apple-system,Helvetica,sans-serif">{esc(bot)}</text>')
    for frac, lab in [(0.0, "9 Jun"), (0.319, "1 Jul"), (0.913, "11 Aug"), (1.0, "17 Aug")]:
        xf = x0 + frac * (x1 - x0)
        anc = "start" if frac == 0 else ("end" if frac == 1 else "middle")
        p.append(f'<text x="{xf:.1f}" y="{by+bh+48}" fill="{MUTED}" font-size="9.5" '
                 f'text-anchor="{anc}" font-family="ui-monospace,Menlo,monospace">{esc(lab)}</text>')
    p.append(f'<text x="{x0}" y="16" fill="{TEXT}" font-size="11.5" font-weight="700" '
             f'font-family="-apple-system,Helvetica,sans-serif">'
             f'NBIS · what the SWING CALL line actually did, 9 Jun – 17 Aug 2026</text>')
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(p)}</svg>')

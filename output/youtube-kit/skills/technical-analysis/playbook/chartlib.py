"""Minimal deterministic candlestick-SVG generator for the playbook PDF.

Everything is drawn in (slot, price) space and mapped to pixels, so annotations
can be positioned against the chart the same way they are read: by price level.
"""
import random

# TradingView-dark palette, matched to Nikil's actual chart
BG        = "#131722"
PANEL     = "#1a1f2c"
GRID      = "#252a37"
AXIS      = "#363a45"
TEXT      = "#d1d4dc"
MUTED     = "#787b86"
DIM       = "#4a4f5c"

BULL      = "#26a69a"   # teal up candle
BEAR      = "#ef5350"   # red down candle
GREENZONE = "#26a69a"
REDZONE   = "#ef5350"
MA_UP     = "#4caf50"   # SWING CALL green
MA_DOWN   = "#e53935"   # SWING CALL red
SMA50     = "#ff9800"   # 50 SMA orange
ENTRY     = "#2962ff"
STOPC     = "#ef5350"
TARGETC   = "#26a69a"
CALLOUT   = "#ffd54f"
NOTE      = "#9aa0b0"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Chart:
    def __init__(self, w, h, lo, hi, slots, pad_l=8, pad_r=86, pad_t=14, pad_b=26):
        self.w, self.h = w, h
        self.lo, self.hi = lo, hi
        self.slots = slots
        self.pl, self.pr, self.pt, self.pb = pad_l, pad_r, pad_t, pad_b
        self.parts = []
        self.plot_w = w - pad_l - pad_r
        self.plot_h = h - pad_t - pad_b

    # ---- coordinate mapping -------------------------------------------------
    def y(self, price):
        f = (price - self.lo) / (self.hi - self.lo)
        return self.pt + (1 - f) * self.plot_h

    def x(self, slot):
        return self.pl + (slot + 0.5) * (self.plot_w / self.slots)

    @property
    def cw(self):
        return max(3.0, (self.plot_w / self.slots) * 0.62)

    # ---- primitives ---------------------------------------------------------
    def add(self, s):
        self.parts.append(s)

    def frame(self, gridlines=None, axis_side="right"):
        self.add(f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="{BG}" rx="4"/>')
        if gridlines:
            for p in gridlines:
                yy = round(self.y(p), 1)
                self.add(f'<line x1="{self.pl}" y1="{yy}" x2="{self.pl+self.plot_w}" y2="{yy}" '
                         f'stroke="{GRID}" stroke-width="1"/>')
                if axis_side == "right":
                    tx, anc = self.pl + self.plot_w + 7, "start"
                else:
                    tx, anc = self.pl - 7, "end"
                self.add(f'<text x="{tx}" y="{yy+3.5}" fill="{MUTED}" font-size="10" '
                         f'text-anchor="{anc}" '
                         f'font-family="ui-monospace,Menlo,monospace">{p:g}</text>')

    def panel(self, slot, price, lines, w=196, title=None, accent=CALLOUT):
        """Small info box anchored at (slot, price) as its top-left corner."""
        x, y = self.x(slot), self.y(price)
        rows = len(lines)
        h = 15 + (18 if title else 0) + rows * 17
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" rx="6" '
                 f'fill="#0e1320" fill-opacity="0.94" stroke="{AXIS}" stroke-width="1"/>')
        yy = y + 15
        if title:
            self.add(f'<text x="{x+12:.1f}" y="{yy+3:.1f}" fill="{accent}" font-size="9.5" '
                     f'font-weight="800" letter-spacing="1.2" '
                     f'font-family="-apple-system,Helvetica,sans-serif">{esc(title)}</text>')
            yy += 18
        for k, v, col in lines:
            self.add(f'<text x="{x+12:.1f}" y="{yy+4:.1f}" fill="{MUTED}" font-size="10.5" '
                     f'font-family="-apple-system,Helvetica,sans-serif">{esc(k)}</text>')
            self.add(f'<text x="{x+w-12:.1f}" y="{yy+4:.1f}" fill="{col}" font-size="11" '
                     f'font-weight="700" text-anchor="end" '
                     f'font-family="ui-monospace,Menlo,monospace">{esc(v)}</text>')
            yy += 17

    def zone(self, top, bot, kind="green", label=None, s0=0, s1=None, dashed=False, sub=None):
        s1 = self.slots if s1 is None else s1
        c = GREENZONE if kind == "green" else REDZONE
        x0, x1 = self.x(s0) - self.cw / 2, self.x(s1 - 1) + self.cw / 2
        yt, yb = self.y(top), self.y(bot)
        da = ' stroke-dasharray="5 4"' if dashed else ''
        op = 0.10 if dashed else 0.17
        self.add(f'<rect x="{x0:.1f}" y="{yt:.1f}" width="{x1-x0:.1f}" height="{max(2,yb-yt):.1f}" '
                 f'fill="{c}" fill-opacity="{op}" stroke="{c}" stroke-opacity="0.75" '
                 f'stroke-width="1"{da}/>')
        if label:
            self.add(f'<text x="{x0+6:.1f}" y="{yt-5:.1f}" fill="{c}" font-size="10.5" '
                     f'font-weight="600" font-family="ui-monospace,Menlo,monospace">{esc(label)}</text>')
        if sub:
            self.add(f'<text x="{x0+6:.1f}" y="{yb+12:.1f}" fill="{MUTED}" font-size="9.5" '
                     f'font-family="-apple-system,Helvetica,sans-serif">{esc(sub)}</text>')

    def candles(self, data, s0=0):
        cw = self.cw
        for i, c in enumerate(data):
            if c is None:
                continue
            o, h, l, cl = c
            xx = self.x(s0 + i)
            col = BULL if cl >= o else BEAR
            self.add(f'<line x1="{xx:.1f}" y1="{self.y(h):.1f}" x2="{xx:.1f}" '
                     f'y2="{self.y(l):.1f}" stroke="{col}" stroke-width="1.7"/>')
            yt, yb = self.y(max(o, cl)), self.y(min(o, cl))
            self.add(f'<rect x="{xx-cw/2:.1f}" y="{yt:.1f}" width="{cw:.1f}" '
                     f'height="{max(1.2, yb-yt):.1f}" fill="{col}"/>')

    def spotlight(self, s0, s1, p_top, p_bot, label=None, color=CALLOUT):
        """Dashed ring around the two candles that actually matter."""
        x0 = self.x(s0) - self.cw / 2 - 6
        x1 = self.x(s1) + self.cw / 2 + 6
        yt, yb = self.y(p_top), self.y(p_bot)
        self.add(f'<rect x="{x0:.1f}" y="{yt:.1f}" width="{x1-x0:.1f}" height="{yb-yt:.1f}" '
                 f'rx="7" fill="none" stroke="{color}" stroke-width="1.4" '
                 f'stroke-dasharray="4 3" stroke-opacity="0.85"/>')
        if label:
            self.add(f'<text x="{(x0+x1)/2:.1f}" y="{yt-6:.1f}" fill="{color}" font-size="9.5" '
                     f'font-weight="800" text-anchor="middle" letter-spacing="0.5" '
                     f'font-family="-apple-system,Helvetica,sans-serif">{esc(label)}</text>')

    def polyline(self, pts, color, width=2.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        p = " ".join(f"{self.x(s):.1f},{self.y(pr):.1f}" for s, pr in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{color}" '
                 f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{d}/>')

    def hline(self, price, color, label=None, dash="6 4", s0=0, s1=None, width=1.4,
              lab_side="right", bold=False):
        s1 = self.slots if s1 is None else s1
        yy = self.y(price)
        self.add(f'<line x1="{self.x(s0)-self.cw/2:.1f}" y1="{yy:.1f}" '
                 f'x2="{self.x(s1-1)+self.cw/2:.1f}" y2="{yy:.1f}" stroke="{color}" '
                 f'stroke-width="{width}" stroke-dasharray="{dash}"/>')
        if label:
            fw = "700" if bold else "600"
            if lab_side == "right":
                tx, anc = self.x(s1 - 1) + self.cw / 2 + 5, "start"
            else:
                tx, anc = self.x(s0) - self.cw / 2 - 5, "end"
            self.add(f'<text x="{tx:.1f}" y="{yy+3.5:.1f}" fill="{color}" font-size="10" '
                     f'font-weight="{fw}" text-anchor="{anc}" '
                     f'font-family="ui-monospace,Menlo,monospace">{esc(label)}</text>')

    def band(self, top, bot, color, label, s0, s1, opacity=0.13, lab_slot=None):
        """A shaded measurement band, e.g. the 1.5 x ATR wiggle room."""
        x0, x1 = self.x(s0) - self.cw / 2, self.x(s1 - 1) + self.cw / 2
        yt, yb = self.y(top), self.y(bot)
        self.add(f'<rect x="{x0:.1f}" y="{yt:.1f}" width="{x1-x0:.1f}" height="{yb-yt:.1f}" '
                 f'fill="{color}" fill-opacity="{opacity}"/>')
        lx = (x0 + x1) / 2 if lab_slot is None else self.x(lab_slot)
        ly = (yt + yb) / 2
        tw = len(label) * 5.9
        self.add(f'<rect x="{lx-tw/2-5:.1f}" y="{ly-8:.1f}" width="{tw+10:.1f}" height="16" '
                 f'rx="4" fill="#0e1320" fill-opacity="0.9"/>')
        self.add(f'<text x="{lx:.1f}" y="{ly+3.5:.1f}" fill="#ff8a80" '
                 f'font-size="9.5" font-weight="700" text-anchor="middle" '
                 f'font-family="ui-monospace,Menlo,monospace">{esc(label)}</text>')

    def marker(self, slot, price, n, color=CALLOUT, dy=0, r=9.5):
        """Numbered step badge."""
        cx, cy = self.x(slot), self.y(price) + dy
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}" '
                 f'stroke="{BG}" stroke-width="2"/>')
        self.add(f'<text x="{cx:.1f}" y="{cy+3.6:.1f}" fill="#11151f" font-size="11" '
                 f'font-weight="800" text-anchor="middle" '
                 f'font-family="-apple-system,Helvetica,sans-serif">{n}</text>')

    def note(self, slot, price, text, color=TEXT, anchor="middle", dy=0, size=10, weight="600"):
        self.add(f'<text x="{self.x(slot):.1f}" y="{self.y(price)+dy:.1f}" fill="{color}" '
                 f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
                 f'font-family="-apple-system,Helvetica,sans-serif">{esc(text)}</text>')

    def arrow(self, s_from, p_from, s_to, p_to, color=CALLOUT, width=1.3):
        x1, y1, x2, y2 = self.x(s_from), self.y(p_from), self.x(s_to), self.y(p_to)
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{color}" stroke-width="{width}" marker-end="url(#ah)"/>')

    def bracket(self, slot, p_top, p_bot, label, color, side=1, off=16):
        """Vertical measurement bracket at a slot."""
        xx = self.x(slot) + off * side
        yt, yb = self.y(p_top), self.y(p_bot)
        self.add(f'<path d="M {xx-4*side:.1f} {yt:.1f} L {xx:.1f} {yt:.1f} L {xx:.1f} {yb:.1f} '
                 f'L {xx-4*side:.1f} {yb:.1f}" fill="none" stroke="{color}" stroke-width="1.2"/>')
        anc = "start" if side > 0 else "end"
        self.add(f'<text x="{xx+5*side:.1f}" y="{(yt+yb)/2+3.5:.1f}" fill="{color}" '
                 f'font-size="10" font-weight="700" text-anchor="{anc}" '
                 f'font-family="ui-monospace,Menlo,monospace">{esc(label)}</text>')

    def legend(self, items, x=10, y=13):
        """items: list of (label, color)"""
        cx = x
        for lab, col in items:
            self.add(f'<rect x="{cx}" y="{y-7}" width="9" height="9" rx="2" fill="{col}"/>')
            self.add(f'<text x="{cx+13}" y="{y+1}" fill="{MUTED}" font-size="9.5" '
                     f'font-family="-apple-system,Helvetica,sans-serif">{esc(lab)}</text>')
            cx += 17 + len(lab) * 5.6

    def render(self):
        defs = (f'<defs><marker id="ah" markerWidth="7" markerHeight="7" refX="6" refY="3.5" '
                f'orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="{CALLOUT}"/></marker></defs>')
        return (f'<svg viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                f'xmlns="http://www.w3.org/2000/svg">{defs}{"".join(self.parts)}</svg>')


# ---- price-path helper ------------------------------------------------------
def path(waypoints, n, seed=7, vol=0.35, body=0.62):
    """Interpolate waypoints [(slot, price), ...] into n OHLC candles."""
    rnd = random.Random(seed)
    xs = [w[0] for w in waypoints]
    ys = [w[1] for w in waypoints]

    def at(i):
        if i <= xs[0]:
            return ys[0]
        if i >= xs[-1]:
            return ys[-1]
        for k in range(len(xs) - 1):
            if xs[k] <= i <= xs[k + 1]:
                f = (i - xs[k]) / (xs[k + 1] - xs[k])
                f = f * f * (3 - 2 * f)          # smoothstep
                return ys[k] + f * (ys[k + 1] - ys[k])
        return ys[-1]

    span = (max(ys) - min(ys)) * vol / max(1, n) * 6
    out, prev = [], at(0)
    for i in range(n):
        tgt = at(i + 1)
        o = prev
        c = tgt + rnd.uniform(-span, span) * 0.5
        hi = max(o, c) + abs(rnd.gauss(0, span)) * body
        lo = min(o, c) - abs(rnd.gauss(0, span)) * body
        out.append((o, hi, lo, c))
        prev = c
    return out

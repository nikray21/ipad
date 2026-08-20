# Vega AI prompt — the full 4h swing playbook

Paste the block below into **Vega AI** in Webull's Script Editor panel
(Chart → Indicators & Strategies → Script Editor → Vega tab).

This builds the visual half of the 6-step playbook as one indicator:
SWING CALL's colored trend line, the liquidity swing zones with volume,
sweep/trigger detection, and the 1.5x ATR stop hung off the level.

**What it cannot do**, and why — an indicator draws, it does not grade:
share sizing needs the $75-100 risk budget, the portfolio gates need the
open book (max 2 positions / 4% at risk), and the sweep-vs-stall judgment
call needs a human. Those stay in `/technical-analysis`.

Zone logic is a clean implementation of LuxAlgo's *published* description of
Liquidity Swings, not a copy of their closed source. Expect close behavior,
not identical zones.

---

## The prompt

Write a custom overlay indicator called "4H Swing Playbook".

It has four components: a trend filter, liquidity swing zones, setup
detection, and risk levels. Build all four in one script.

---

### INPUTS

Trend:
- emaLength: integer, default 5, min 1, label "EMA length"
- smaLength: integer, default 50, min 1, label "SMA length"
- rsiLength: integer, default 14, min 1, label "RSI length"
- rsiOverbought: number, default 80, label "RSI overbought"
- rsiOversold: number, default 20, label "RSI oversold"

Zones:
- pivotLookback: integer, default 14, min 1, label "Pivot lookback"
- swingAreaMode: dropdown "Wick Extremity" / "Full Range", default "Wick Extremity"
- minZoneVolume: number, default 0, min 0, label "Minimum zone volume"

Risk:
- atrLength: integer, default 14, min 1, label "ATR length"
- atrMultiple: number, default 1.5, min 0.1, label "ATR stop multiple"

Display:
- showZones: boolean, default true
- showSignals: boolean, default true
- showRiskLevels: boolean, default true

---

### COMPONENT 1 — TREND FILTER (the colored trend line)

Compute a 5-period EMA of close and a 50-period SMA of close.

Plot the 50 SMA as a thick line whose color encodes trend state:
- GREEN (#26A69A) when the EMA is above the SMA AND the SMA is rising
  (its current value exceeds its value one bar ago). This is "bullish".
- RED (#EF5350) when the EMA is below the SMA AND the SMA is falling.
  This is "bearish".
- YELLOW (#FFD700) in every other case. This is "neutral".

Plot the 5 EMA as a thin white line.

Define two boolean states used later:
- trendBullish = SMA color is green AND close is above the SMA
- trendBearish = SMA color is red AND close is below the SMA

Both conditions are required. Price on the wrong side of the 50 SMA
disqualifies the trade even when the line color is right.

---

### COMPONENT 2 — LIQUIDITY SWING ZONES

PIVOT DETECTION:
A bar is a pivot high if its high is strictly greater than the high of every
one of the pivotLookback bars immediately to its left AND every one of the
pivotLookback bars immediately to its right. A pivot low is the symmetric case
on lows. Confirmation requires pivotLookback bars of future data, so each pivot
can only be drawn pivotLookback bars after it occurred. Draw it retrospectively
at its true bar position — do not shift it forward.

ZONE GEOMETRY:
When a pivot high confirms, create a rectangle anchored at that pivot bar:
- "Wick Extremity" mode: top = the bar's high, bottom = max(open, close) of that bar.
- "Full Range" mode: top = the bar's high, bottom = the bar's low.
For a pivot low, mirror it:
- "Wick Extremity": bottom = the bar's low, top = min(open, close) of that bar.
- "Full Range": bottom = the bar's low, top = the bar's high.

EXTENSION AND MITIGATION:
Extend each rectangle rightward as new bars form. Keep extending until a bar
CLOSES fully beyond the zone's far edge — below the bottom for a swing-high
zone, above the top for a swing-low zone. Freeze the right edge at that bar
and mark the zone "mitigated". Draw mitigated zones with a dashed border and
live zones with a solid border. Live zones keep extending to the current bar.

ACCUMULATED VOLUME:
For each zone, sum the volume of every bar whose high-low range intersects the
zone's price range, starting at the pivot bar. Show that total as a text label
at the zone's right edge, formatted compactly — 1,500,000 as "1.5M",
22,000 as "22K". Update it as the total grows.

VOLUME FILTER:
Hide any zone whose accumulated volume is below minZoneVolume. A value of 0
shows every zone. This matters: a zone carrying only thousands of shares is
weak, a zone carrying millions is real.

STYLING:
- Swing-high zones: red border (#EF5350), translucent red fill around 15% opacity.
- Swing-low zones: teal border (#26A69A), translucent teal fill around 15% opacity.
- A solid horizontal line along the pivot extreme itself in the matching color.
- Volume labels in the zone's color, normal size.

---

### COMPONENT 3 — SETUP DETECTION (sweep, then trigger)

Track the nearest live swing-low zone below price and the nearest live
swing-high zone above price.

LONG SETUP, all four required in this order:
1. trendBullish is true.
2. Price trades INTO the nearest live swing-low zone.
3. SWEEP: a bar's LOW prints strictly BELOW that zone's bottom. A bar that
   merely trades inside the zone without exceeding its bottom is a stall,
   NOT a sweep — do not count it. The low must exceed the edge.
4. TRIGGER: within the next 3 bars after the sweep, a bar CLOSES back above
   the zone's TOP. A wick back above does not count — only a close.

When step 4 completes, plot a teal upward triangle below that bar labeled "LONG".

SHORT SETUP mirrors it exactly:
1. trendBearish is true.
2. Price trades into the nearest live swing-high zone.
3. SWEEP: a bar's HIGH prints strictly ABOVE that zone's top.
4. TRIGGER: within 3 bars, a bar CLOSES back below the zone's BOTTOM.

Plot a red downward triangle above that bar labeled "SHORT".

Fire a signal only when all four conditions are met in sequence. Do not
signal on partial setups. Three of four is not a setup.

---

### COMPONENT 4 — RISK LEVELS

Compute a 14-period ATR.

When a LONG signal fires, plot two horizontal lines extending right:
- Stop = (the swept zone's BOTTOM) minus (atrMultiple x ATR), dashed red,
  labeled "STOP".
- Target = the bottom edge of the nearest swing-high zone above price,
  dashed teal, labeled "TARGET".

When a SHORT signal fires, mirror it:
- Stop = (the swept zone's TOP) plus (atrMultiple x ATR), dashed red.
- Target = the top edge of the nearest swing-low zone below price, dashed teal.

CRITICAL: the stop is computed from the ZONE EDGE, never from the entry price.
Entry minus 1.5x ATR would park the stop on top of support, so a normal dip
stops the trade out at exactly the bounce point. Anchor to the level.

Also display a small on-chart table in the top right showing the current
ATR value, the trend state (Bullish / Bearish / Neutral), and the accumulated
volume of the nearest live zone.

---

### FALLBACK

If Webull's scripting language cannot draw rectangles, text labels, shapes, or
tables, say so directly rather than substituting something else. Then give me
the closest supported version — zone tops and bottoms as step lines that hold
until mitigation, signals as plotted markers — and list exactly which features
had to be dropped and why.

// ============================================================
// 4H Swing Playbook -- visual layer  (overlay indicator)
// Paste into: Webull > Chart > Script Editor > New Indicator
// ------------------------------------------------------------
// Covers the DRAWABLE half of the 6-step playbook:
//   step 1  trend state  (EMA 5 vs SMA 50, SMA slope, side of SMA)
//   step 2  swing levels, volume-gated
//   step 3  sweep flag   (low printed BELOW the level, not inside it)
//   step 4  trigger flag (close back above the level)
//   step 5  stop at level -/+ 1.5x ATR, off the LEVEL not the entry
//
// Steps 6 (R:R target), share sizing, the $75-100 risk budget and the
// 2-position / 4% portfolio gates are NOT here and cannot be -- an
// indicator has no idea what else you are holding. Run
// /technical-analysis against a real TradingView chart for the verdict.
//
// These are running swing levels, NOT LuxAlgo zones. No boxes, no
// per-zone accumulated volume. See the note at the bottom.
// ============================================================

// ---------- Inputs ----------
emaLen  = define(5,   min=1,   name="EMA length")
smaLen  = define(50,  min=1,   name="SMA length")
pivotLb = define(14,  min=1,   name="Pivot lookback")
atrLen  = define(14,  min=1,   name="ATR length")
atrMult = define(1.5, min=0.1, name="ATR stop multiple")
volLb   = define(50,  min=1,   name="Volume average lookback")

// ---------- Step 1: trend state ----------
emaFast = ind.ema(close, emaLen)
smaSlow = ind.sma(close, smaLen)

plt(emaFast, color=#FFFFFF, name="EMA 5")
plt(smaSlow, color=#2962FF, name="SMA 50")

// Boolean logic is expressed as 1/0 ternaries multiplied together.
// Every factor must be 1 for the product to be 1 -- this is the
// all-six-or-no-trade gate, not a score you can make up elsewhere.
bullTrend = (emaFast > smaSlow ? 1 : 0) * (smaSlow > smaSlow[1] ? 1 : 0) * (close > smaSlow ? 1 : 0)
bearTrend = (emaFast < smaSlow ? 1 : 0) * (smaSlow < smaSlow[1] ? 1 : 0) * (close < smaSlow ? 1 : 0)

// ---------- Step 2: swing levels, volume-gated ----------
// Prior `pivotLb` bars offset by 1, so the current bar can print
// through the level and the sweep stays visible.
swingHigh = ind.highest(high, pivotLb)[1]
swingLow  = ind.lowest(low,  pivotLb)[1]

plt(swingHigh, color=#EF5350, name="Swing High")
plt(swingLow,  color=#26A69A, name="Swing Low")

// A level built on below-average volume is the weak K-volume zone the
// playbook says to skip. This gate is crude next to LuxAlgo's per-zone
// accumulated volume -- it compares peak volume in the window to the
// running average rather than summing volume inside a box.
volAvg = ind.sma(volume, volLb)
heavy  = ind.highest(volume, pivotLb)[1] > volAvg ? 1 : 0

// ---------- Steps 3 + 4: sweep, then reclaim ----------
// SWEEP means the low printed strictly BELOW the level. A bar that
// stalls at or inside the level swept nothing -- that is consolidation
// before the level breaks, not a reversal.
sweptLow  = low  < swingLow  ? 1 : 0
sweptHigh = high > swingHigh ? 1 : 0

// TRIGGER means a CLOSE back on the right side. A wick does not count.
reclaimUp   = close > swingLow  ? 1 : 0
reclaimDown = close < swingHigh ? 1 : 0

// Full setup: trend + heavy level + sweep + reclaim, all required.
longSetup  = bullTrend * heavy * sweptLow  * reclaimUp
shortSetup = bearTrend * heavy * sweptHigh * reclaimDown

// These plot as 0 or 1. Read them in the status line, not on the price
// scale -- turn their chart display off and keep "values in status line" on.
plt(longSetup,  color=#26A69A, name="LONG setup",  display=1)
plt(shortSetup, color=#EF5350, name="SHORT setup", display=1)

// ---------- Step 5: stops off the LEVEL ----------
// Never Entry -/+ 1.5xATR. That parks the stop on top of support, so a
// normal dip stops you out at exactly the bounce spot. Anchor to the level.
atr = ind.atr(atrLen)

longStop  = swingLow  - atrMult * atr
shortStop = swingHigh + atrMult * atr

plt(longStop,  color=#26A69A, name="Long stop")
plt(shortStop, color=#EF5350, name="Short stop")

// ============================================================
// If the editor errors, it will be a function NAME, not the logic.
// Verified in the wild: define, plt, ind.sma, close/high/low/volume,
// ternary, arithmetic, hex colors.
// Inferred: ind.ema, ind.atr, ind.highest, ind.lowest, and the [1]
// history offset. Paste the error into Vega AI -- each one is a
// one-line fix and the surrounding logic still holds.
// ============================================================

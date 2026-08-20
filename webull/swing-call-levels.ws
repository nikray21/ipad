// ============================================================
// SWING CALL + Swing Liquidity Levels + ATR stops  (overlay)
// Paste into: Webull > Chart > Script Editor > New Indicator
// ------------------------------------------------------------
// Draws the visual half of the 6-step playbook:
//   step 1  EMA 5 / SMA 50 trend pair
//   step 2  swing high / low liquidity levels (volume-gated)
//   step 5  the 1.5x ATR stop, hung off the LEVEL not the entry
//
// It DRAWS, it does not GRADE. Steps 3, 4 and 6, the share
// sizing and the portfolio gates need your risk budget and open
// book -- run /technical-analysis for the verdict.
//
// These are generic pivot levels, NOT LuxAlgo's algorithm.
// Grade real trades off TradingView with actual LuxAlgo loaded.
// ============================================================

// ---------- Inputs ----------
emaLen  = define(5,  min=1, name="EMA length")
smaLen  = define(50, min=1, name="SMA length")
pivotLb = define(14, min=1, name="Pivot lookback")
atrLen  = define(14, min=1, name="ATR length")
atrMult = define(1.5, min=0.1, name="ATR stop multiple")
volLb   = define(50, min=1, name="Volume average lookback")

// ---------- Step 1: trend pair ----------
emaFast = ind.ema(close, emaLen)
smaSlow = ind.sma(close, smaLen)

plt(emaFast, color=#FFD700, name="EMA 5")
plt(smaSlow, color=#2962FF, name="SMA 50")

// ---------- Step 2: swing liquidity levels ----------
// Prior `pivotLb` bars, offset by 1 so the current bar can print
// through the level and the sweep stays visible.
swingHigh = ind.highest(high, pivotLb)[1]
swingLow  = ind.lowest(low,  pivotLb)[1]

// Volume gate: only trust a level formed on heavy participation.
// A level built on below-average volume is the weak K-volume zone
// the playbook says to skip -- it plots as 0 (off-scale) instead.
volAvg   = ind.sma(volume, volLb)
volHeavy = ind.highest(volume, pivotLb)[1] > volAvg

swingHighV = volHeavy ? swingHigh : 0
swingLowV  = volHeavy ? swingLow  : 0

plt(swingHighV, color=#EF5350, name="Swing High")
plt(swingLowV,  color=#26A69A, name="Swing Low")

// ---------- Step 5: ATR stops off the LEVEL ----------
// Long stop sits below the whole zone, short stop above it.
// Never Entry -/+ 1.5xATR -- that parks the stop on the level.
atr = ind.atr(atrLen)

longStop  = volHeavy ? swingLow  - atrMult * atr : 0
shortStop = volHeavy ? swingHigh + atrMult * atr : 0

plt(longStop,  color=#26A69A, name="Long stop")
plt(shortStop, color=#EF5350, name="Short stop")

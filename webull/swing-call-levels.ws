// ============================================================
// 4H Swing Playbook -- all six steps
// Paste into: Webull > Chart > Script Editor > New Indicator
// ------------------------------------------------------------
//   step 1  trend     EMA 5 vs SMA 50, SMA slope, price side of SMA
//   step 2  location  swing level, volume-gated
//   step 3  trap      sweep: low printed BELOW the level
//   step 4  trigger   close back above the level
//   step 5  stop      level -/+ 1.5x ATR, off the LEVEL not the entry
//   step 6  exit      target at opposing level, R:R must clear 2.0
//
// The setup flag is the PRODUCT of all six. One zero anywhere and the
// flag is zero -- all six or no trade. 4 of 6 cannot pass, by
// construction rather than by discipline.
//
// WHY LEVELS AND NOT ZONES: WebullScript has no labels, no custom
// lines, no arrays and no persistent state. A LuxAlgo-style zone needs
// all four -- a box is a line, its volume figure is a label, tracking
// live zones needs arrays, extend-until-mitigated needs state. Plotted
// series is the only shape available. Grade real trades on TradingView
// with actual LuxAlgo loaded; this is a chart aid, not the grader.
//
// NOT here and not possible: share sizing off the $75-100 budget, and
// the 2-position / 4% portfolio gates. Those need your open book.
// Run /technical-analysis for the verdict.
// ============================================================

// ---------- Inputs ----------
emaLen  = define.integer(5,   min=1,   name="EMA length")
smaLen  = define.integer(50,  min=1,   name="SMA length")
rsiLen  = define.integer(14,  min=1,   name="RSI length")
rsiOB   = define.float(80,    min=1,   name="RSI overbought")
rsiOS   = define.float(20,    min=1,   name="RSI oversold")
pivotLb = define.integer(14,  min=1,   name="Pivot lookback")
atrLen  = define.integer(14,  min=1,   name="ATR length")
atrMult = define.float(1.5,   min=0.1, name="ATR stop multiple")
volLb   = define.integer(50,  min=1,   name="Volume average lookback")
minRR   = define.float(2.0,   min=0.1, name="Minimum reward:risk")

// ---------- Step 1: trend ----------
emaFast = ind.ema(close, emaLen)
smaSlow = ind.sma(close, smaLen)

plt(emaFast, color=color.white, name="EMA 5")
plt(smaSlow, color=color.blue,  name="SMA 50")

// iff() is the only conditional, so conditions are combined by
// multiplying 1/0 results. Every factor must be 1 for the product to be 1.
// Both trend conditions are required: correct slope AND correct side of
// the 50 SMA. Price below the 50 fails the trade even on a green line.
bullTrend = iff(emaFast > smaSlow, 1, 0) * iff(smaSlow > smaSlow[1], 1, 0) * iff(close > smaSlow, 1, 0)
bearTrend = iff(emaFast < smaSlow, 1, 0) * iff(smaSlow < smaSlow[1], 1, 0) * iff(close < smaSlow, 1, 0)

// ---------- Step 2: location ----------
// Prior `pivotLb` bars offset by 1, so the current bar can print
// through the level and the sweep stays visible.
swingHigh = math.highest(high, pivotLb)[1]
swingLow  = math.lowest(low,  pivotLb)[1]

plt(swingHigh, color=color.red,  name="Swing High", style=plt.type_stepline)
plt(swingLow,  color=color.teal, name="Swing Low",  style=plt.type_stepline)

// A level built on below-average volume is the weak K-volume zone the
// playbook says to skip. Crude next to LuxAlgo's per-zone accumulated
// volume -- with no arrays or state there is no box to sum volume
// inside, so this compares peak volume in the window to a running average.
volAvg = ind.sma(volume, volLb)
heavy  = iff(math.highest(volume, pivotLb)[1] > volAvg, 1, 0)

// ---------- Step 3: the trap ----------
// A SWEEP means the low printed strictly BELOW the level. A bar that
// stalls at or inside the level swept nothing -- in a trend that is
// consolidation before the level breaks, not a reversal.
sweptLow  = iff(low  < swingLow,  1, 0)
sweptHigh = iff(high > swingHigh, 1, 0)

// ---------- Step 4: the trigger ----------
// A CLOSE back on the right side. A wick back across does not count.
reclaimUp   = iff(close > swingLow,  1, 0)
reclaimDown = iff(close < swingHigh, 1, 0)

// ---------- Step 5: the stop ----------
// Off the LEVEL. Never Entry -/+ 1.5xATR -- that parks the stop on top
// of support, so a normal dip stops you out at exactly the bounce spot.
atrVal = ind.atr(atrLen)

longStop  = swingLow  - atrMult * atrVal
shortStop = swingHigh + atrMult * atrVal

plt(longStop,  color=color.teal, name="Long stop",  style=plt.type_stepline)
plt(shortStop, color=color.red,  name="Short stop", style=plt.type_stepline)

// ---------- Step 6: the exit ----------
// Target sits in FRONT of the opposing level. Reward must clear 2R or
// the setup fails here no matter how good the first five steps looked.
longRisk  = close - longStop
shortRisk = shortStop - close

longRR  = iff(longRisk  <= 0, 0, (swingHigh - close) / longRisk)
shortRR = iff(shortRisk <= 0, 0, (close - swingLow) / shortRisk)

longRRok  = iff(longRR  >= minRR, 1, 0)
shortRRok = iff(shortRR >= minRR, 1, 0)

// ---------- RSI context ----------
rsiVal     = ind.rsi(close, rsiLen)
rsiNotHot  = iff(rsiVal < rsiOB, 1, 0)
rsiNotCold = iff(rsiVal > rsiOS, 1, 0)

// ---------- The six-step gate ----------
longSetup  = bullTrend * heavy * sweptLow  * reclaimUp   * longRRok  * rsiNotHot
shortSetup = bearTrend * heavy * sweptHigh * reclaimDown * shortRRok * rsiNotCold

// Markers print at the bar only when the full gate passes. `none` keeps
// non-signal bars off the chart entirely instead of pinning them to zero.
plt(iff(longSetup  > 0, low,  none), color=color.lime, name="LONG",  style=plt.type_circles)
plt(iff(shortSetup > 0, high, none), color=color.red,  name="SHORT", style=plt.type_circles)

// R:R reads in the status line. Hide these two from the chart -- they
// are small ratios and will flatten against a price scale in the hundreds.
plt(longRR,  color=color.yellow, name="Long R:R")
plt(shortRR, color=color.yellow, name="Short R:R")

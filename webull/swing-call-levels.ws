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
// HOW CLOSE THE ZONES GET: shaded bands via plt.fill_between, with
// LuxAlgo's wick-extremity geometry (high to body top, low to body
// bottom). What is missing is the volume figure on each zone (no
// labels) and a chart of frozen historical zones (no arrays, no state)
// -- you get ONE live band above and one below, re-forming as pivots
// appear. Grade real trades on TradingView with actual LuxAlgo loaded;
// this is a chart aid, not the grader.
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
// Zone geometry follows LuxAlgo's "Wick Extremity": a swing-high zone
// runs from the high down to the body top, a swing-low zone from the
// low up to the body bottom. Computed over the window rather than at
// one pivot bar, since without state there is no bar to anchor to.
// max(open,close) <= high on every bar, so the band never inverts.
// Offset by 1 so the current bar can print through and the sweep shows.
zoneHighTop = math.highest(high, pivotLb)[1]
zoneHighBot = math.highest(math.max(open, close), pivotLb)[1]
zoneLowBot  = math.lowest(low, pivotLb)[1]
zoneLowTop  = math.lowest(math.min(open, close), pivotLb)[1]

pHighTop = plt(zoneHighTop, color=color.red,  name="Swing High",     style=plt.type_stepline)
pHighBot = plt(zoneHighBot, color=color.red,  name="Swing High bot", style=plt.type_stepline)
pLowBot  = plt(zoneLowBot,  color=color.teal, name="Swing Low",      style=plt.type_stepline)
pLowTop  = plt(zoneLowTop,  color=color.teal, name="Swing Low top",  style=plt.type_stepline)

// The shaded zone bodies.
plt.fill_between(pHighTop, pHighBot, color=color.red)
plt.fill_between(pLowTop,  pLowBot,  color=color.teal)

// LOCATION: price has to pull back INTO the zone. Buying mid-range or
// mid-air fails this step -- it is the leak the playbook grades loudest.
inZoneLong  = iff(low  <= zoneLowTop,  1, 0)
inZoneShort = iff(high >= zoneHighBot, 1, 0)

// A level built on below-average volume is the weak K-volume zone the
// playbook says to skip. Crude next to LuxAlgo's per-zone accumulated
// volume -- with no arrays or labels there is no box to sum volume
// inside, so this compares peak volume in the window to a running average.
volAvg = ind.sma(volume, volLb)
heavy  = iff(math.highest(volume, pivotLb)[1] > volAvg, 1, 0)

// ---------- Step 3: the trap ----------
// A SWEEP means the low printed strictly BELOW the level. A bar that
// stalls at or inside the level swept nothing -- in a trend that is
// consolidation before the level breaks, not a reversal.
// Measured against the zone BOTTOM, not the zone top -- stalling inside
// the band is not a sweep no matter how deep it looks.
sweptLow  = iff(low  < zoneLowBot,  1, 0)
sweptHigh = iff(high > zoneHighTop, 1, 0)

// ---------- Step 4: the trigger ----------
// A CLOSE back above the whole zone, not merely back above its bottom.
// A wick back across does not count.
reclaimUp   = iff(close > zoneLowTop,  1, 0)
reclaimDown = iff(close < zoneHighBot, 1, 0)

// ---------- Step 5: the stop ----------
// Off the LEVEL. Never Entry -/+ 1.5xATR -- that parks the stop on top
// of support, so a normal dip stops you out at exactly the bounce spot.
atrVal = ind.atr(atrLen)

// Level = the far edge of the zone: its BOTTOM for a long, its TOP for
// a short. Below the entire zone and below the bait wick, as required.
longStop  = zoneLowBot  - atrMult * atrVal
shortStop = zoneHighTop + atrMult * atrVal

plt(longStop,  color=color.teal, name="Long stop",  style=plt.type_stepline)
plt(shortStop, color=color.red,  name="Short stop", style=plt.type_stepline)

// ---------- Step 6: the exit ----------
// Target sits in FRONT of the opposing level. Reward must clear 2R or
// the setup fails here no matter how good the first five steps looked.
longRisk  = close - longStop
shortRisk = shortStop - close

// Target sits in FRONT of the opposing zone -- at the near edge it would
// have to reach, not the far side of it.
longRR  = iff(longRisk  <= 0, 0, (zoneHighBot - close) / longRisk)
shortRR = iff(shortRisk <= 0, 0, (close - zoneLowTop) / shortRisk)

longRRok  = iff(longRR  >= minRR, 1, 0)
shortRRok = iff(shortRR >= minRR, 1, 0)

// ---------- RSI context ----------
rsiVal     = ind.rsi(close, rsiLen)
rsiNotHot  = iff(rsiVal < rsiOB, 1, 0)
rsiNotCold = iff(rsiVal > rsiOS, 1, 0)

// ---------- The six-step gate ----------
longSetup  = bullTrend * inZoneLong  * heavy * sweptLow  * reclaimUp   * longRRok  * rsiNotHot
shortSetup = bearTrend * inZoneShort * heavy * sweptHigh * reclaimDown * shortRRok * rsiNotCold

// Markers print at the bar only when the full gate passes. `none` keeps
// non-signal bars off the chart entirely instead of pinning them to zero.
plt(iff(longSetup  > 0, low,  none), color=color.lime, name="LONG",  style=plt.type_circles)
plt(iff(shortSetup > 0, high, none), color=color.red,  name="SHORT", style=plt.type_circles)

// R:R reads in the status line. Hide these two from the chart -- they
// are small ratios and will flatten against a price scale in the hundreds.
plt(longRR,  color=color.yellow, name="Long R:R")
plt(shortRR, color=color.yellow, name="Short R:R")

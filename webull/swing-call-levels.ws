// ============================================================
// 4H Swing Playbook -- all six steps  (overlay indicator)
// Paste into: Webull > Chart > Script Editor > New Indicator
// ------------------------------------------------------------
// Every one of the 6 steps, computed without persistent state so it
// leans only on language features seen in real Webull scripts.
//
//   step 1  trend   EMA 5 vs SMA 50, SMA slope, price side of SMA
//   step 2  location  swing level, volume-gated
//   step 3  trap    sweep flag: low printed BELOW the level
//   step 4  trigger close back above the level
//   step 5  stop    level -/+ 1.5x ATR, off the LEVEL not the entry
//   step 6  exit    target at the opposing level, R:R must clear 2.0
//
// The setup flag is the PRODUCT of all six. Any single zero and the
// flag is zero -- all six or no trade, exactly as the playbook says.
// 4 of 6 cannot pass here, by construction.
//
// NOT in here, and not possible in an indicator: share sizing off the
// $75-100 budget, and the 2-position / 4% portfolio gates. Those need
// your open book. Run /technical-analysis for the actual verdict.
//
// These are running swing levels, NOT LuxAlgo zones -- no boxes, no
// per-zone accumulated volume. See the note at the bottom.
// ============================================================

// ---------- Inputs ----------
emaLen  = define(5,   min=1,   name="EMA length")
smaLen  = define(50,  min=1,   name="SMA length")
rsiLen  = define(14,  min=1,   name="RSI length")
rsiOB   = define(80,  min=1,   name="RSI overbought")
rsiOS   = define(20,  min=1,   name="RSI oversold")
pivotLb = define(14,  min=1,   name="Pivot lookback")
atrLen  = define(14,  min=1,   name="ATR length")
atrMult = define(1.5, min=0.1, name="ATR stop multiple")
volLb   = define(50,  min=1,   name="Volume average lookback")
minRR   = define(2.0, min=0.1, name="Minimum reward:risk")

// ---------- Step 1: trend ----------
emaFast = ind.ema(close, emaLen)
smaSlow = ind.sma(close, smaLen)

plt(emaFast, name="EMA 5")
plt(smaSlow, name="SMA 50")

// Boolean logic as 1/0 ternaries multiplied together. Ternary syntax is
// verified in real Webull scripts; the and/or keywords are not.
// Both conditions are required: the right slope AND the right side of
// the 50 SMA. Price below the 50 fails the trade even on a green line.
bullTrend = (emaFast > smaSlow ? 1 : 0) * (smaSlow > smaSlow[1] ? 1 : 0) * (close > smaSlow ? 1 : 0)
bearTrend = (emaFast < smaSlow ? 1 : 0) * (smaSlow < smaSlow[1] ? 1 : 0) * (close < smaSlow ? 1 : 0)

// ---------- Step 2: location ----------
// Prior `pivotLb` bars offset by 1, so the current bar can print
// through the level and the sweep stays visible.
swingHigh = ind.highest(high, pivotLb)[1]
swingLow  = ind.lowest(low,  pivotLb)[1]

plt(swingHigh, name="Swing High")
plt(swingLow,  name="Swing Low")

// A level built on below-average volume is the weak K-volume zone the
// playbook says to skip. Crude next to LuxAlgo's per-zone accumulated
// volume: this compares peak volume in the window to a running average
// rather than summing volume inside a box.
volAvg = ind.sma(volume, volLb)
heavy  = ind.highest(volume, pivotLb)[1] > volAvg ? 1 : 0

// ---------- Step 3: the trap ----------
// A SWEEP means the low printed strictly BELOW the level. A bar that
// stalls at or inside the level swept nothing -- in a trend that is
// consolidation before the level breaks, not a reversal.
sweptLow  = low  < swingLow  ? 1 : 0
sweptHigh = high > swingHigh ? 1 : 0

// ---------- Step 4: the trigger ----------
// A CLOSE back on the right side. A wick back across does not count.
reclaimUp   = close > swingLow  ? 1 : 0
reclaimDown = close < swingHigh ? 1 : 0

// ---------- Step 5: the stop ----------
// Off the LEVEL. Never Entry -/+ 1.5xATR -- that parks the stop on top
// of support, so a normal dip stops you out at exactly the bounce spot.
atr = ind.atr(atrLen)

longStop  = swingLow  - atrMult * atr
shortStop = swingHigh + atrMult * atr

plt(longStop,  name="Long stop")
plt(shortStop, name="Short stop")

// ---------- Step 6: the exit ----------
// Target sits in FRONT of the opposing level. Reward must clear 2R or
// the setup fails here no matter how good the first five steps looked.
longRisk   = close - longStop
shortRisk  = shortStop - close

longRR  = longRisk  <= 0 ? 0 : (swingHigh - close) / longRisk
shortRR = shortRisk <= 0 ? 0 : (close - swingLow) / shortRisk

longRRok  = longRR  >= minRR ? 1 : 0
shortRRok = shortRR >= minRR ? 1 : 0

plt(swingHigh, name="Long target",  display=1)
plt(swingLow,  name="Short target", display=1)

// ---------- RSI context ----------
rsi = ind.rsi(close, rsiLen)
rsiNotHot  = rsi < rsiOB ? 1 : 0
rsiNotCold = rsi > rsiOS ? 1 : 0

// ---------- The six-step gate ----------
// Product of every step. One zero anywhere and the setup is zero.
longSetup  = bullTrend * heavy * sweptLow  * reclaimUp   * longRRok  * rsiNotHot
shortSetup = bearTrend * heavy * sweptHigh * reclaimDown * shortRRok * rsiNotCold

// These plot 0 or 1. Read them in the status line, not on the price
// scale -- hide their chart display, keep "values in status line" on.
plt(longSetup,  name="LONG setup",  display=1)
plt(shortSetup, name="SHORT setup", display=1)
plt(longRR,     name="Long R:R",    display=1)
plt(shortRR,    name="Short R:R",   display=1)

// ============================================================
// COLORS: set them in the indicator's Style tab, not in code. The
// editor lexes with TypeScript's tokenizer, where #name is a private
// identifier -- so a hex colour starting with a LETTER (#EF5350) parses
// but one starting with a DIGIT (#26A69A) does not: # is an invalid
// character, then 26 is a numeric literal, then A69A an identifier.
// Passing colours at all is a trap; the Style tab has no such problem.
//
// Confirmed by the editor accepting this file: ind.ema, ind.rsi,
// ind.atr, ind.highest, ind.lowest and the [1] history offset all
// exist, alongside define, plt, ind.sma, close/high/low/volume,
// ternaries, arithmetic and name=/min=/display=.
//
// What is deliberately absent: shaded zone boxes and per-zone volume
// labels. Those need rectangle and text drawing, which no Webull script
// I could find uses, and I will not invent an API and hand it to you as
// working code. Vega's version will answer that question -- if it draws
// real boxes, its zone layer beats this one and we merge the two.
// ============================================================

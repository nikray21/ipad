// ============================================================
// SWING CALL + Swing Liquidity Levels  (overlay indicator)
// Paste into: Webull > Chart > Script Editor > New Indicator
// ------------------------------------------------------------
// Reproduces the SWING CALL trend pair (EMA 5 / SMA 50) and adds
// running swing-high / swing-low liquidity levels.
//
// NOTE: these are generic pivot levels, NOT LuxAlgo's algorithm.
// Grade real trades off TradingView with actual LuxAlgo loaded.
// ============================================================

// ---------- Inputs ----------
emaLen  = define(5,  min=1, name="EMA length")
smaLen  = define(50, min=1, name="SMA length")
pivotLb = define(14, min=1, name="Pivot lookback")

// ---------- SWING CALL trend pair ----------
emaFast = ind.ema(close, emaLen)
smaSlow = ind.sma(close, smaLen)

plt(emaFast, color=#FFD700, name="EMA 5")
plt(smaSlow, color=#2962FF, name="SMA 50")

// ---------- Swing liquidity levels ----------
// Highest high / lowest low of the prior `pivotLb` bars, offset by 1
// so the current bar can print through the level and show the sweep.
swingHigh = ind.highest(high, pivotLb)[1]
swingLow  = ind.lowest(low,  pivotLb)[1]

plt(swingHigh, color=#EF5350, name="Swing High")
plt(swingLow,  color=#26A69A, name="Swing Low")

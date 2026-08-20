# Vega AI prompt — Swing Liquidity Zones

Paste the block below into the **Vega AI** chat box in Webull's Script Editor
panel (Chart → Indicators & Strategies → Script Editor → Vega tab).

Built from LuxAlgo's own published description of Liquidity Swings, with the
input defaults matched to Nikil's TradingView settings (Pivot Lookback 14,
Wick Extremity, Filter by Count 0, swing high red / swing low teal).

Not a copy of LuxAlgo's source, which is closed — this is a clean
implementation of the documented behavior.

---

## The prompt

Write a custom overlay indicator called "Swing Liquidity Zones".

INPUTS:
- pivotLookback: integer, default 14, minimum 1
- swingAreaMode: dropdown, options "Wick Extremity" and "Full Range", default "Wick Extremity"
- filterMode: dropdown, options "Count" and "Volume", default "Count"
- filterThreshold: number, default 0, minimum 0
- showSwingHigh: boolean, default true
- showSwingLow: boolean, default true

PIVOT DETECTION:
A bar at index i is a pivot high if its high is strictly greater than the high
of every one of the pivotLookback bars immediately to its left AND every one of
the pivotLookback bars immediately to its right. A pivot low is the symmetric
case using lows. Because confirmation needs pivotLookback bars of future data,
each pivot is only confirmed and drawn pivotLookback bars after it occurred —
draw it retrospectively at its true bar position, do not shift it forward.

SWING AREA (the zone box):
When a pivot high confirms, create a rectangle anchored at the pivot bar:
- If swingAreaMode is "Wick Extremity": top = that bar's high, bottom = the
  maximum of that bar's open and close.
- If swingAreaMode is "Full Range": top = that bar's high, bottom = that bar's low.
For a pivot low, mirror it:
- "Wick Extremity": bottom = that bar's low, top = the minimum of its open and close.
- "Full Range": bottom = that bar's low, top = that bar's high.

EXTENSION AND MITIGATION:
Extend each rectangle to the right as new bars form. Keep extending until a
bar CLOSES fully beyond the far edge of the zone — beyond the bottom for a
swing-high zone, beyond the top for a swing-low zone. At that point freeze the
rectangle's right edge at that bar and stop extending it. Zones that have not
been closed through stay live and keep extending to the current bar.

ACCUMULATED VOLUME:
For each zone, sum the volume of every bar whose price range intersects the
zone's price range, starting from the pivot bar. Display that running total as
a text label at the right edge of the zone. Format large numbers compactly:
1,500,000 as "1.5M" and 22,000 as "22K". Update the label as the total grows.

TOUCH COUNT:
Separately, count how many distinct times price re-enters the zone after
leaving it. A touch begins when a bar's range intersects the zone after the
previous bar's range did not.

FILTERING:
- If filterMode is "Count": hide any zone whose touch count is less than filterThreshold.
- If filterMode is "Volume": hide any zone whose accumulated volume is less than filterThreshold.
- A filterThreshold of 0 shows every zone.

STYLING:
- Swing-high zones: red border (#EF5350) with a translucent red fill, roughly 15% opacity.
- Swing-low zones: teal border (#26A69A) with a translucent teal fill, roughly 15% opacity.
- Draw a solid horizontal line along the pivot extreme itself (the high for a
  swing high, the low for a swing low) in the matching color.
- Volume labels in the zone's color, normal text size.
- Respect showSwingHigh and showSwingLow to toggle each side independently.

IMPORTANT: If Webull's scripting language cannot draw rectangles, boxes, or
text labels, tell me that directly instead of substituting something else.
In that case, give me the closest version the language does support — plot the
zone top and zone bottom as two step lines per zone that hold their value until
the zone is mitigated — and explain exactly which features had to be dropped.

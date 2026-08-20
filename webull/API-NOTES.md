# Webull Script Editor — what is actually known

Running notes so no one re-walks this. Updated 2026-08-20.

## The language is TypeScript, not a Pine-style DSL

The Script Editor type-checks real TypeScript against the browser
standard library. Evidence, from errors on a pasted script:

- `close` never errors — it resolves to `window.close`.
- `high`, `low`, `volume` always error — no DOM globals by those names.
- `name=` gives "Cannot assign to 'name' because it is a constant"
  (`window.name` is readonly).
- `atr` gives "Did you mean 'Attr'?" — the DOM `Attr` interface.

So at the point of that test, **no Webull trading API types were in
scope at all**. Whether they load from a required import, a scaffold
the "New Indicator" template provides, or a global that appears only at
runtime is still unknown.

## The define/plt/ind.sma dialect is a dead end

These public repos use `define()`, `plt()`, `ind.sma()`:

- https://github.com/shishir1601/webull_indicators (`gmma.ws`)
- https://github.com/Wyatt-Hajda/WeBull-Script (AVWAP)

None of it resolves in the current editor. Treat those repos as a
different or older flavor.

Also note `gmma.ws` uses `color=#00FF00`. Under a TypeScript lexer a
hex literal whose first character is a digit cannot tokenize (`#` is
invalid, `00` is a numeric literal, `FF00` an identifier). That file
was never run as written — it is not a trustworthy syntax reference.

## Error ordering trap

TypeScript reports syntax errors first and stops before type-checking.
A paste that returns only a couple of lexer complaints has **not**
validated any function name. Fix the syntax, paste again, and the
semantic errors arrive in a second wave. Do not read a short first
error list as confirmation.

## Still unknown

- The real API: how to read OHLCV, compute indicators, and plot.
- Whether scripts can draw rectangles and text labels — this decides
  whether real LuxAlgo-style zones with volume labels are possible, or
  only step lines.
- Whether persistent per-bar state exists. Vega generating a trailing
  stop implies yes, unconfirmed.

## How to resolve it

Either read the **Docs** tab in the Script Editor panel (in-app, behind
login), or have **Vega AI** generate any working indicator and read the
real API off its output. Vega's generated code is ground truth.

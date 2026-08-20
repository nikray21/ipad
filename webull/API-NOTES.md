# WebullScript — working notes

Updated 2026-08-20, against the official function reference.

## What the language is

A Pine-style DSL, edited in a TypeScript-flavored editor. The editor's
type checker reports DOM globals when the API is not in scope, which is
misleading — `close` resolves to `window.close`, `name` to the readonly
`window.name`, `atr` suggests the DOM `Attr` interface. Those errors mean
the script is malformed, not that the names are wrong.

## Namespaces

| Namespace | Holds |
|---|---|
| `ind.` | ema, sma, wma, hma, rma, alma, swma, vwma, rsi, atr, macd, cci, cmo, mfi, tsi, bb, kc, dmi, cog, correlation, up_trend, down_trend |
| `math.` | **highest, lowest**, abs, min, max, sum, avg, cumsum, std, dev, variance, diff, stoch, round/floor/ceil, pow, sqrt, exp, log, sign, trig |
| `time.` | current, current_bar, utc, get_* extractors, monday..sunday |
| `bar_check.` | is_first, is_last, is_new, is_historical, is_real_time, is_last_update, highest_offset, lowest_offset |
| `plt.` | type_line, type_area, type_histogram, type_columns, type_circles, type_cross, type_linebr, type_stepline, fill_between |
| `hline.` | type_solid, type_dashed, type_dotted |
| `color.` | 17 named colors + sys_up / sys_down |
| `define.` | bool, float, integer, source, string |

**highest/lowest live under `math.`, not `ind.`** — the single easiest
mistake to make.

## Prices

`open` `high` `low` `close` `volume`, plus `hl2` `hlc3` `hlcc4` `ohlc4`.

## Control flow

`iff(condition, if_true, if_false)` is the **only** conditional. No
ternary `?:`, no if/else. Combine conditions by multiplying 1/0 results
or by nesting `iff`.

`none` is the null value — the Pine `na` equivalent. Plot
`iff(cond, price, none)` to mark only qualifying bars rather than
pinning non-signal bars to zero.

## Hard limits

No arrays. No loops. No `var` / cross-bar persistence. No custom
functions. No text labels. No custom line drawing. No `strategy.*`.

### What that rules out

**LuxAlgo-style zones are not expressible.** A shaded box is a custom
line, its volume figure is a label, tracking several live zones needs
arrays, and extend-until-mitigated needs persistent state — all four are
absent. Swing levels must be plotted series. Any per-zone accumulated
volume has to be approximated from a rolling window.

## Still unverified

- Exact `define.*` signatures — assumed `define.integer(5, min=1, name="…")`
  by analogy with the older public dialect.
- Whether `[1]` history offset is supported. The official tips say to
  "reference prior bars if needed" with "limited historical reference
  capabilities", which implies yes. `math.diff` is the fallback for slope.
- The `plt` style parameter's name — `style=plt.type_stepline` is a guess.

## Dead end: the define/plt/ind.sma repos

https://github.com/shishir1601/webull_indicators and
https://github.com/Wyatt-Hajda/WeBull-Script use bare `define(...)` and
`ind.sma`. Close to correct but not current — real inputs are typed
(`define.integer`). `gmma.ws` also uses `color=#00FF00`, and a hex
literal starting with a digit cannot tokenize, so that file was never
run as written. Not a trustworthy reference.

## Error-ordering trap

Syntax errors are reported first and block type checking. A paste that
returns only a couple of lexer complaints has **not** validated any
function name — fix those and a second wave of semantic errors follows.
Never read a short first error list as confirmation.

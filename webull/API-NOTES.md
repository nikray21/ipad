# Webull Script Editor — the real API

Updated 2026-08-20, from code Vega AI generated in the editor itself.

## It is TypeScript, importing from `metrix`

Not a Pine-style DSL. An indicator is a **class** extending
`CustomIndicator`, with an `onBar(bar)` hook called once per bar.

```ts
import {
    CustomIndicator, CustomIndicatorOptions,
    Bar, Color, PlotType, PlotHandle, SMA
} from 'metrix';

class Sma20Indicator extends CustomIndicator {
    private readonly sma: SMA;
    private readonly smaPlot: PlotHandle;

    constructor(options: CustomIndicatorOptions) {
        super(options);
        this.defineIndicator('SMA 20', 'SMA-20', true);   // name, short name, overlay
        const period = this.defineInput('period', 20, {
            type: 'Int', description: '…'
        }) as number;
        this.sma = new SMA(period);
        this.smaPlot = this.definePlot('sma20', {
            color: Color.Blue, type: PlotType.Line, lineWidth: 2
        });
    }

    onBar(bar: Bar): void {
        this.bar = bar;
        const v = this.sma.step(this.bar.close);
        this.smaPlot(Number.isFinite(v) ? v : NaN);
    }
}

export default Sma20Indicator;
```

### Confirmed surface

- `this.defineIndicator(name, shortName, overlay)`
- `this.defineInput(key, default, { type: 'Int' | 'Float', description })` — cast the result
- `this.definePlot(id, { color, type, lineWidth })` returns a `PlotHandle`
- A `PlotHandle` is **called** with the bar's value: `this.smaPlot(v)`
- `this.bar` is assigned inside `onBar`; `bar.close` confirmed
- Built-in steppers exist, e.g. `new SMA(period)` with `.step(value)`
- `NaN` is the blank value — plot it to leave a bar unmarked
- `Color.Blue`, `PlotType.Line` confirmed members

### Consequences

Because this is real TypeScript with class state, **everything the older
DSL forbade is available**: arrays, loops, cross-bar persistence, helper
classes. Pivot confirmation, zone tracking with mitigation, and per-zone
accumulated volume are all straightforward.

Still unknown: whether any drawing API exists for boxes or text labels.
Until one turns up, a zone renders as its two edge lines and its volume
reads in the status line rather than as an on-chart label.

Also unguessed: the rest of `Color` and `PlotType`, and which other
indicator classes `metrix` exports (`SMA` is confirmed; `EMA`, `RSI`,
`ATR` are likely but unverified — `swing-playbook.ts` implements its own
so the only dependency is the plotting API).

## Dead ends — do not revisit

**The "WebullScript Complete Reference"** (`define.integer`, `plt`,
`ind.ema`, `math.highest`, `iff`, `color.blue`) describes a different or
older product. Every one of those names fails to resolve in this editor.

**These repos** use a third variant, bare `define(...)` and `ind.sma`:
- https://github.com/shishir1601/webull_indicators
- https://github.com/Wyatt-Hajda/WeBull-Script

`gmma.ws` there also uses `color=#00FF00`, which cannot even tokenize.
Never run as written. Not a reference.

## Editor diagnostics are authoritative

The editor type-checks against the browser standard library, so a script
in the wrong language produces telltale noise: `close` resolves to
`window.close` and never errors, `name` reports as a readonly constant
(`window.name`), `math` suggests `Math`, `atr` suggests `Attr`. Those
mean the language is wrong, not the trading names.

Two traps:

1. **Syntax errors block type checking.** A short first error list has
   validated nothing; fix it and a second wave arrives.
2. **Errors are not cosmetic.** "Add to chart" is gated on a clean
   compile, so nothing runs until the diagnostics clear.

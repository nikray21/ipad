import {
    CustomIndicator, CustomIndicatorOptions,
    Bar,
    Color,
    PlotType,
    PlotHandle
} from 'metrix';

/**
 * Swing Zones + Trend — EMA 5, SMA 50, and pivot-confirmed liquidity zones.
 *
 * Zone behaviour is ported from the open-source Liquidity Swings script
 * (Pine v6, MPL 2.0), itself adapted from the publicly published
 * Liquidity Swings concept under CC BY-NC-SA 4.0:
 * https://creativecommons.org/licenses/by-nc-sa/4.0/
 * Attribution and the share-alike terms travel with this derivative.
 *
 * Two things only:
 *   1. the trend pair, EMA 5 against SMA 50
 *   2. liquidity zones, confirmed at pivots and held until broken
 *
 * A marker prints when both line up: trend right, price pulled back INTO
 * a heavy-volume zone, swept below it, and closed back above.
 *
 * No ATR stops, no reward:risk gate — dropped on request. Sizing and the
 * portfolio caps were never possible here; they need the open book.
 * This draws, it does not grade.
 *
 * WHAT THE REFERENCE DOES THAT MATTERS:
 * exactly ONE swing high and ONE swing low are live at a time. A newer
 * pivot on the same side SUPERSEDES the older one, which freezes where it
 * is — it stops accumulating volume and stops being tested for crossing.
 * It stays drawn, it just is not the level any more. Keeping every zone
 * live instead makes stale levels compete to be "the" zone.
 *
 * Each zone holds one of ZONE_SLOTS display slots per side and plots the
 * same two numbers every bar, so its lines sit FLAT. Drawing only the
 * nearest zone makes the lines hop as price moves, producing a staircase
 * that chases the candles.
 *
 * EVERY plot here is a PRICE. A volume count on this overlay once blew
 * the Y axis to 98,000,000 and flattened the candles to a line.
 */

/** Written out rather than imported so the only metrix surface this file
 *  depends on is the plotting API. */
class Sma {
    private buf: number[] = [];
    private sum = 0;
    constructor(private readonly n: number) {}
    step(x: number): number {
        this.buf.push(x);
        this.sum += x;
        if (this.buf.length > this.n) {
            this.sum -= this.buf.shift() as number;
        }
        return this.buf.length === this.n ? this.sum / this.n : NaN;
    }
}

class Ema {
    private readonly k: number;
    private v = NaN;
    constructor(period: number) {
        this.k = 2 / (period + 1);
    }
    step(x: number): number {
        this.v = Number.isFinite(this.v) ? (x - this.v) * this.k + this.v : x;
        return this.v;
    }
}

/**
 * A confirmed swing zone, frozen at the pivot bar that formed it.
 *
 * `crossed` — price closed clean through it.
 * `frozen`  — a newer pivot on the same side superseded it.
 * Either state stops the zone accumulating; only a live zone is "the"
 * level for signal purposes.
 */
interface Zone {
    top: number;
    bottom: number;
    volume: number;
    count: number;
    isHigh: boolean;
    crossed: boolean;
    frozen: boolean;
}

/** How many zones to draw per side. Each needs two plots. */
const ZONE_SLOTS = 3;

/** swingAreaMode values. */
const WICK_EXTREMITY = 0;

/** filterMode values. */
const FILTER_BY_COUNT = 0;

class SwingZonesIndicator extends CustomIndicator {
    private readonly emaFast: Ema;
    private readonly smaSlow: Sma;
    private readonly volSma: Sma;

    private readonly pivotLb: number;
    private readonly swingAreaMode: number;
    private readonly filterMode: number;
    private readonly filterValue: number;

    /** Rolling window of the last 2*pivotLb+1 bars, for pivot confirmation. */
    private window: Bar[] = [];
    private prevSma = NaN;

    /** The one live zone per side. Older zones live on only in the slots. */
    private activeHigh: Zone | null = null;
    private activeLow: Zone | null = null;

    private readonly highSlots: (Zone | null)[] = [];
    private readonly lowSlots: (Zone | null)[] = [];
    private highNext = 0;
    private lowNext = 0;

    private readonly plotEma: PlotHandle;
    private readonly plotSma: PlotHandle;
    private readonly highTopPlots: PlotHandle[] = [];
    private readonly highBotPlots: PlotHandle[] = [];
    private readonly lowTopPlots: PlotHandle[] = [];
    private readonly lowBotPlots: PlotHandle[] = [];
    private readonly plotLongSignal: PlotHandle;
    private readonly plotShortSignal: PlotHandle;

    constructor(options: CustomIndicatorOptions) {
        super(options);
        this.defineIndicator('Swing Zones + Trend', 'SWING-Z', true);

        const emaLen = this.defineInput('emaLength', 5, {
            type: 'Int', description: 'Fast EMA length.'
        }) as number;
        const smaLen = this.defineInput('smaLength', 50, {
            type: 'Int', description: 'Slow SMA length. Price must sit on the correct side of this.'
        }) as number;
        this.pivotLb = this.defineInput('pivotLookback', 14, {
            type: 'Int', description: 'Bars either side of a pivot. A zone confirms this many bars late. Lower for more zones closer to price.'
        }) as number;
        // Int rather than a dropdown: only Int and Float inputs are
        // confirmed to work in this editor.
        this.swingAreaMode = this.defineInput('swingAreaMode', WICK_EXTREMITY, {
            type: 'Int', description: 'Swing area: 0 = Wick Extremity (wick to body edge), 1 = Full Range (whole candle).'
        }) as number;
        this.filterMode = this.defineInput('filterMode', FILTER_BY_COUNT, {
            type: 'Int', description: 'Filter zones by: 0 = interaction Count, 1 = accumulated Volume.'
        }) as number;
        this.filterValue = this.defineInput('filterValue', 0, {
            type: 'Float', description: 'Minimum count or volume for a zone to be drawn. 0 draws every zone.'
        }) as number;
        const volLb = this.defineInput('volumeLookback', 50, {
            type: 'Int', description: 'Baseline for judging whether a zone formed on heavy volume, used by the signal.'
        }) as number;

        this.emaFast = new Ema(emaLen);
        this.smaSlow = new Sma(smaLen);
        this.volSma = new Sma(volLb);

        this.plotEma = this.definePlot('ema', { color: Color.White, type: PlotType.Line, lineWidth: 1 });
        this.plotSma = this.definePlot('sma', { color: Color.Blue, type: PlotType.Line, lineWidth: 2 });

        for (let i = 0; i < ZONE_SLOTS; i++) {
            this.highSlots.push(null);
            this.lowSlots.push(null);
            this.highTopPlots.push(this.definePlot(`resistance${i}Top`, { color: Color.Red, type: PlotType.Line, lineWidth: 1 }));
            this.highBotPlots.push(this.definePlot(`resistance${i}Bottom`, { color: Color.Red, type: PlotType.Line, lineWidth: 1 }));
            this.lowTopPlots.push(this.definePlot(`support${i}Top`, { color: Color.Green, type: PlotType.Line, lineWidth: 1 }));
            this.lowBotPlots.push(this.definePlot(`support${i}Bottom`, { color: Color.Green, type: PlotType.Line, lineWidth: 1 }));
        }

        this.plotLongSignal = this.definePlot('longSetup', { color: Color.Green, type: PlotType.Line, lineWidth: 4 });
        this.plotShortSignal = this.definePlot('shortSetup', { color: Color.Red, type: PlotType.Line, lineWidth: 4 });
    }

    onBar(bar: Bar): void {
        this.bar = bar;

        const ema = this.emaFast.step(bar.close);
        const sma = this.smaSlow.step(bar.close);
        const volAvg = this.volSma.step(bar.volume);

        const pivoted = this.detectPivot(bar);
        // The reference resets its counters on a pivot bar and accumulates
        // otherwise, so a zone never tallies the bar that confirmed it twice.
        if (!pivoted) this.updateActive(bar);

        // Trend: correct slope AND the correct side of the SMA, both required.
        const smaRising = Number.isFinite(this.prevSma) && sma > this.prevSma;
        const smaFalling = Number.isFinite(this.prevSma) && sma < this.prevSma;
        const bullTrend = ema > sma && smaRising && bar.close > sma;
        const bearTrend = ema < sma && smaFalling && bar.close < sma;
        this.prevSma = sma;

        const low = this.activeLow;
        let longFires = false;
        if (low && !low.crossed) {
            // Pulled back INTO the zone, and the zone formed on heavy volume.
            const inZone = bar.low <= low.top;
            const heavy = Number.isFinite(volAvg) && low.volume > volAvg;
            // Swept BELOW the zone. Stalling inside it is not a sweep.
            const swept = bar.low < low.bottom;
            // Closed back above the whole zone. A wick does not count.
            const reclaimed = bar.close > low.top;
            longFires = bullTrend && inZone && heavy && swept && reclaimed;
        }

        const high = this.activeHigh;
        let shortFires = false;
        if (high && !high.crossed) {
            const inZone = bar.high >= high.bottom;
            const heavy = Number.isFinite(volAvg) && high.volume > volAvg;
            const swept = bar.high > high.top;
            const reclaimed = bar.close < high.bottom;
            shortFires = bearTrend && inZone && heavy && swept && reclaimed;
        }

        this.plotEma(ema);
        this.plotSma(sma);
        this.drawSlots();

        // Markers print only on firing bars; NaN leaves every other bar blank.
        this.plotLongSignal(longFires ? bar.low : NaN);
        this.plotShortSignal(shortFires ? bar.high : NaN);
    }

    /**
     * Confirm the pivot at the centre of the rolling window. A pivot needs
     * pivotLb bars on BOTH sides, so it is only confirmed pivotLb bars after
     * the fact — the zone is created at its true bar, retrospectively.
     * Returns whether a pivot confirmed on this bar.
     */
    private detectPivot(bar: Bar): boolean {
        const span = 2 * this.pivotLb + 1;
        this.window.push(bar);
        if (this.window.length > span) this.window.shift();
        if (this.window.length < span) return false;

        const centre = this.window[this.pivotLb];
        if (!centre) return false;

        let isHigh = true;
        let isLow = true;
        for (let i = 0; i < span; i++) {
            if (i === this.pivotLb) continue;
            const other = this.window[i];
            if (!other) continue;
            if (other.high >= centre.high) isHigh = false;
            if (other.low <= centre.low) isLow = false;
        }

        // Wick Extremity runs the wick to the body edge; Full Range uses the
        // whole candle.
        const wick = this.swingAreaMode === WICK_EXTREMITY;

        if (isHigh) {
            const top = centre.high;
            const bottom = wick ? Math.max(centre.open, centre.close) : centre.low;
            this.supersede(this.newZone(top, bottom, true));
        }
        if (isLow) {
            const bottom = centre.low;
            const top = wick ? Math.min(centre.open, centre.close) : centre.high;
            this.supersede(this.newZone(top, bottom, false));
        }
        return isHigh || isLow;
    }

    /**
     * Build a zone and seed its tallies from the confirmation window. A zone
     * is only confirmed pivotLb bars after its pivot, so this counts the bars
     * that traded it while it was forming rather than starting from zero at
     * the confirmation bar.
     */
    private newZone(top: number, bottom: number, isHigh: boolean): Zone {
        let volume = 0;
        let count = 0;
        for (let i = this.pivotLb; i < this.window.length; i++) {
            const b = this.window[i];
            if (!b) continue;
            if (b.low < top && b.high > bottom) {
                volume += b.volume;
                count++;
            }
        }
        return { top, bottom, volume, count, isHigh, crossed: false, frozen: false };
    }

    /** Freeze the previous zone on this side and install the new one. */
    private supersede(zone: Zone): void {
        const previous = zone.isHigh ? this.activeHigh : this.activeLow;
        if (previous) previous.frozen = true;

        if (zone.isHigh) this.activeHigh = zone;
        else this.activeLow = zone;

        this.claimSlot(zone);
    }

    /**
     * Accumulate into the live zones and mark them crossed once price closes
     * clean through. A swing high is resistance and dies on a close ABOVE
     * its top; a swing low is support, dying on a close below its bottom.
     * Price merely falling away from a pivot high leaves that resistance
     * perfectly intact — it is still overhead supply.
     */
    private updateActive(bar: Bar): void {
        for (const zone of [this.activeHigh, this.activeLow]) {
            if (!zone || zone.crossed || zone.frozen) continue;

            if (bar.low < zone.top && bar.high > zone.bottom) {
                zone.volume += bar.volume;
                zone.count++;
            }
            if (zone.isHigh ? bar.close > zone.top : bar.close < zone.bottom) {
                zone.crossed = true;
            }
        }
    }

    /**
     * Give a freshly confirmed zone a display slot. It keeps that slot, and
     * so plots its exact level as a flat line, until evicted. Prefers an
     * empty slot; otherwise evicts the oldest in round-robin.
     */
    private claimSlot(zone: Zone): void {
        const slots = zone.isHigh ? this.highSlots : this.lowSlots;
        let idx = slots.indexOf(null);
        if (idx < 0) {
            if (zone.isHigh) {
                idx = this.highNext;
                this.highNext = (this.highNext + 1) % ZONE_SLOTS;
            } else {
                idx = this.lowNext;
                this.lowNext = (this.lowNext + 1) % ZONE_SLOTS;
            }
        }
        slots[idx] = zone;
    }

    /** A zone is drawn only once it clears the count or volume threshold. */
    private passesFilter(zone: Zone): boolean {
        const target = this.filterMode === FILTER_BY_COUNT ? zone.count : zone.volume;
        return target >= this.filterValue;
    }

    /** Free slots whose zone has been crossed, then plot what remains. */
    private drawSlots(): void {
        for (let i = 0; i < ZONE_SLOTS; i++) {
            const hz = this.highSlots[i];
            if (hz && hz.crossed) this.highSlots[i] = null;
            const lz = this.lowSlots[i];
            if (lz && lz.crossed) this.lowSlots[i] = null;

            const highZone = this.highSlots[i];
            const lowZone = this.lowSlots[i];

            const showHigh = highZone !== null && highZone !== undefined && this.passesFilter(highZone);
            const showLow = lowZone !== null && lowZone !== undefined && this.passesFilter(lowZone);

            const hTop = this.highTopPlots[i];
            const hBot = this.highBotPlots[i];
            const lTop = this.lowTopPlots[i];
            const lBot = this.lowBotPlots[i];

            if (hTop) hTop(showHigh && highZone ? highZone.top : NaN);
            if (hBot) hBot(showHigh && highZone ? highZone.bottom : NaN);
            if (lTop) lTop(showLow && lowZone ? lowZone.top : NaN);
            if (lBot) lBot(showLow && lowZone ? lowZone.bottom : NaN);
        }
    }
}

export default SwingZonesIndicator;

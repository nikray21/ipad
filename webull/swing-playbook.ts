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
 * Deliberately just two things:
 *   1. the trend pair, EMA 5 against SMA 50
 *   2. liquidity zones, confirmed at pivots and held until broken
 *
 * A marker prints when both line up: trend is right, price pulled back
 * INTO a heavy-volume zone, swept below it, and closed back above it.
 *
 * No ATR stops, no reward:risk gate — dropped on request. Position
 * sizing and the portfolio caps were never possible here anyway; they
 * need the open book. This draws, it does not grade.
 *
 * Zones are frozen at their true pivot bar with wick-extremity geometry,
 * carry the volume of every bar that trades through them, and retire on
 * a close clean through. Each holds one of ZONE_SLOTS display slots per
 * side and plots the same two numbers every bar, so its lines sit FLAT.
 * Drawing only the nearest zone makes the lines hop as price moves,
 * producing a staircase that chases the candles.
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

/** A confirmed swing zone, frozen at the pivot bar that formed it. */
interface Zone {
    top: number;
    bottom: number;
    volume: number;
    isHigh: boolean;
    active: boolean;
}

/** How many live zones to draw per side. Each needs two plots. */
const ZONE_SLOTS = 3;

class SwingZonesIndicator extends CustomIndicator {
    private readonly emaFast: Ema;
    private readonly smaSlow: Sma;
    private readonly volSma: Sma;

    private readonly pivotLb: number;

    /** Rolling window of the last 2*pivotLb+1 bars, for pivot confirmation. */
    private window: Bar[] = [];
    private zones: Zone[] = [];
    private prevSma = NaN;

    private readonly plotEma: PlotHandle;
    private readonly plotSma: PlotHandle;
    private readonly highTopPlots: PlotHandle[] = [];
    private readonly highBotPlots: PlotHandle[] = [];
    private readonly lowTopPlots: PlotHandle[] = [];
    private readonly lowBotPlots: PlotHandle[] = [];
    private readonly plotLongSignal: PlotHandle;
    private readonly plotShortSignal: PlotHandle;

    /** A zone holds its slot, and so its exact level, until mitigated. */
    private readonly highSlots: (Zone | null)[] = [];
    private readonly lowSlots: (Zone | null)[] = [];
    private highNext = 0;
    private lowNext = 0;

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
        const volLb = this.defineInput('volumeLookback', 50, {
            type: 'Int', description: 'Baseline for judging whether a zone formed on heavy volume.'
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

        this.detectPivot(bar);
        this.updateZones(bar);

        const lowZone = this.nearestZone(bar.close, false);
        const highZone = this.nearestZone(bar.close, true);

        // Trend: correct slope AND the correct side of the SMA, both required.
        const smaRising = Number.isFinite(this.prevSma) && sma > this.prevSma;
        const smaFalling = Number.isFinite(this.prevSma) && sma < this.prevSma;
        const bullTrend = ema > sma && smaRising && bar.close > sma;
        const bearTrend = ema < sma && smaFalling && bar.close < sma;
        this.prevSma = sma;

        let longFires = false;
        if (lowZone) {
            // Pulled back INTO the zone, on heavy volume.
            const inZone = bar.low <= lowZone.top;
            const heavy = Number.isFinite(volAvg) && lowZone.volume > volAvg;
            // Swept BELOW the zone. Stalling inside it is not a sweep.
            const swept = bar.low < lowZone.bottom;
            // Closed back above the whole zone. A wick does not count.
            const reclaimed = bar.close > lowZone.top;
            longFires = bullTrend && inZone && heavy && swept && reclaimed;
        }

        let shortFires = false;
        if (highZone) {
            const inZone = bar.high >= highZone.bottom;
            const heavy = Number.isFinite(volAvg) && highZone.volume > volAvg;
            const swept = bar.high > highZone.top;
            const reclaimed = bar.close < highZone.bottom;
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
     */
    private detectPivot(bar: Bar): void {
        const span = 2 * this.pivotLb + 1;
        this.window.push(bar);
        if (this.window.length > span) this.window.shift();
        if (this.window.length < span) return;

        const centre = this.window[this.pivotLb];
        if (!centre) return;

        let isHigh = true;
        let isLow = true;
        for (let i = 0; i < span; i++) {
            if (i === this.pivotLb) continue;
            const other = this.window[i];
            if (!other) continue;
            if (other.high >= centre.high) isHigh = false;
            if (other.low <= centre.low) isLow = false;
        }

        // Wick-extremity geometry: high down to the body top for a swing
        // high, low up to the body bottom for a swing low.
        if (isHigh) {
            const top = centre.high;
            const bottom = Math.max(centre.open, centre.close);
            const zone: Zone = {
                top, bottom, isHigh: true, active: true,
                volume: this.volumeThrough(top, bottom)
            };
            this.zones.push(zone);
            this.claimSlot(zone);
        }
        if (isLow) {
            const top = Math.min(centre.open, centre.close);
            const bottom = centre.low;
            const zone: Zone = {
                top, bottom, isHigh: false, active: true,
                volume: this.volumeThrough(top, bottom)
            };
            this.zones.push(zone);
            this.claimSlot(zone);
        }
    }

    /**
     * Volume traded through a price band across the confirmation window.
     * A zone is only confirmed pivotLb bars after its pivot, so seeding it
     * this way counts the bars that traded the zone while it was forming
     * instead of starting the tally from the confirmation bar.
     */
    private volumeThrough(top: number, bottom: number): number {
        let total = 0;
        // Stops one short of the end: the final window bar is the current
        // bar, which updateZones tallies immediately after this runs.
        for (let i = this.pivotLb; i < this.window.length - 1; i++) {
            const b = this.window[i];
            if (!b) continue;
            if (b.high >= bottom && b.low <= top) total += b.volume;
        }
        return total;
    }

    /**
     * Accumulate volume for every zone this bar trades through, and retire
     * zones price has closed clean through.
     */
    private updateZones(bar: Bar): void {
        for (const zone of this.zones) {
            if (!zone.active) continue;

            if (bar.high >= zone.bottom && bar.low <= zone.top) {
                zone.volume += bar.volume;
            }
            // A swing high is resistance and dies on a close ABOVE its top;
            // a swing low is support, dying on a close below its bottom.
            // Price merely falling away from a pivot high leaves that
            // resistance perfectly intact — it is still overhead supply.
            if (zone.isHigh ? bar.close > zone.top : bar.close < zone.bottom) {
                zone.active = false;
            }
        }
        // Bounded by dropping retired zones ONLY. Every live zone must
        // survive: the display slots hold references into this list, and a
        // zone dropped while still active would never be marked mitigated,
        // leaving its line frozen on the chart forever.
        if (this.zones.length > 200) {
            this.zones = this.zones.filter(z => z.active);
        }
    }

    /**
     * Give a freshly confirmed zone a display slot. It keeps that slot, and
     * so plots its exact level as a flat line, until mitigated. Prefers an
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

    /** Free slots whose zone has been mitigated, then plot what remains. */
    private drawSlots(): void {
        for (let i = 0; i < ZONE_SLOTS; i++) {
            const hz = this.highSlots[i];
            if (hz && !hz.active) this.highSlots[i] = null;
            const lz = this.lowSlots[i];
            if (lz && !lz.active) this.lowSlots[i] = null;

            const high = this.highSlots[i];
            const low = this.lowSlots[i];

            const hTop = this.highTopPlots[i];
            const hBot = this.highBotPlots[i];
            const lTop = this.lowTopPlots[i];
            const lBot = this.lowBotPlots[i];

            if (hTop) hTop(high ? high.top : NaN);
            if (hBot) hBot(high ? high.bottom : NaN);
            if (lTop) lTop(low ? low.top : NaN);
            if (lBot) lBot(low ? low.bottom : NaN);
        }
    }

    /** Nearest live zone above (isHigh) or below (!isHigh) the given price. */
    private nearestZone(price: number, isHigh: boolean): Zone | null {
        let best: Zone | null = null;
        for (const zone of this.zones) {
            if (!zone.active || zone.isHigh !== isHigh) continue;
            if (isHigh) {
                // Resistance at or above price. Zones price is currently
                // inside still count — that is the rally INTO the zone.
                if (zone.top < price) continue;
                if (!best || zone.bottom < best.bottom) best = zone;
            } else {
                // Support at or below price, likewise including one price
                // has pulled back into.
                if (zone.bottom > price) continue;
                if (!best || zone.top > best.top) best = zone;
            }
        }
        return best;
    }
}

export default SwingZonesIndicator;

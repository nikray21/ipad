import {
    CustomIndicator, CustomIndicatorOptions,
    Bar,
    Color,
    PlotType,
    PlotHandle
} from 'metrix';

/**
 * 4H Swing Playbook — the visual layer of the 6-step swing checklist.
 *
 *   step 1  trend     EMA 5 vs SMA 50, SMA slope, price side of the SMA
 *   step 2  location  price pulled back INTO a heavy-volume swing zone
 *   step 3  trap      sweep: the low printed BELOW the zone, not inside it
 *   step 4  trigger   a close back above the whole zone
 *   step 5  stop      zone edge -/+ 1.5x ATR — off the LEVEL, not the entry
 *   step 6  exit      target at the opposing zone, R:R must clear 2.0
 *
 * The setup value is the PRODUCT of all six gates, so one failing step
 * zeroes it. Four of six cannot pass, by construction.
 *
 * NOT here and not possible in an indicator: share sizing off the risk
 * budget, and the 2-position / 4% portfolio caps. Those need the open
 * book. This draws; it does not grade.
 *
 * Zones are pivot-confirmed and frozen at their true bar, carrying
 * accumulated volume, extended until a close breaks clean through.
 * With no drawing API a zone shows as its two edge lines rather than a
 * shaded box.
 *
 * EVERY plot here is a PRICE. Volume counts and reward:risk ratios were
 * plotted once and blew the Y axis out to 98,000,000, flattening the
 * candles to a line. Nothing that is not a price goes on this overlay —
 * both values are gates on the setup marker instead, so a marker only
 * prints when the zone was heavy and the ratio cleared.
 */

/** Wilder-style helpers. Written out rather than imported so the only
 *  metrix surface this file depends on is the plotting API. */
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

class Rsi {
    private prev = NaN;
    private avgGain = NaN;
    private avgLoss = NaN;
    private seedGain = 0;
    private seedLoss = 0;
    private count = 0;
    constructor(private readonly n: number) {}
    step(x: number): number {
        if (!Number.isFinite(this.prev)) {
            this.prev = x;
            return NaN;
        }
        const change = x - this.prev;
        this.prev = x;
        const gain = change > 0 ? change : 0;
        const loss = change < 0 ? -change : 0;
        this.count++;

        if (this.count <= this.n) {
            this.seedGain += gain;
            this.seedLoss += loss;
            if (this.count < this.n) return NaN;
            this.avgGain = this.seedGain / this.n;
            this.avgLoss = this.seedLoss / this.n;
        } else {
            this.avgGain = (this.avgGain * (this.n - 1) + gain) / this.n;
            this.avgLoss = (this.avgLoss * (this.n - 1) + loss) / this.n;
        }
        if (this.avgLoss === 0) return 100;
        return 100 - 100 / (1 + this.avgGain / this.avgLoss);
    }
}

class Atr {
    private prevClose = NaN;
    private v = NaN;
    private seed = 0;
    private count = 0;
    constructor(private readonly n: number) {}
    step(high: number, low: number, close: number): number {
        const tr = Number.isFinite(this.prevClose)
            ? Math.max(high - low, Math.abs(high - this.prevClose), Math.abs(low - this.prevClose))
            : high - low;
        this.prevClose = close;
        this.count++;

        if (this.count <= this.n) {
            this.seed += tr;
            if (this.count === this.n) this.v = this.seed / this.n;
            return this.v;
        }
        this.v = (this.v * (this.n - 1) + tr) / this.n;
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

class SwingPlaybookIndicator extends CustomIndicator {
    private readonly emaFast: Ema;
    private readonly smaSlow: Sma;
    private readonly rsi: Rsi;
    private readonly atr: Atr;

    private readonly pivotLb: number;
    private readonly atrMult: number;
    private readonly rsiOB: number;
    private readonly rsiOS: number;
    private readonly minRR: number;
    private readonly volLb: number;

    /** Rolling window of the last 2*pivotLb+1 bars, for pivot confirmation. */
    private window: Bar[] = [];
    private zones: Zone[] = [];
    private prevSma = NaN;
    private volSma: Sma;

    private readonly plotEma: PlotHandle;
    private readonly plotSma: PlotHandle;
    private readonly plotHighTop: PlotHandle;
    private readonly plotHighBot: PlotHandle;
    private readonly plotLowTop: PlotHandle;
    private readonly plotLowBot: PlotHandle;
    private readonly plotLongStop: PlotHandle;
    private readonly plotShortStop: PlotHandle;
    private readonly plotLongSignal: PlotHandle;
    private readonly plotShortSignal: PlotHandle;

    constructor(options: CustomIndicatorOptions) {
        super(options);
        this.defineIndicator('4H Swing Playbook', 'SWING-PB', true);

        const emaLen = this.defineInput('emaLength', 5, {
            type: 'Int', description: 'Fast EMA length. The SWING CALL fast line.'
        }) as number;
        const smaLen = this.defineInput('smaLength', 50, {
            type: 'Int', description: 'Slow SMA length. Price must sit on the correct side of this.'
        }) as number;
        const rsiLen = this.defineInput('rsiLength', 14, {
            type: 'Int', description: 'RSI length.'
        }) as number;
        this.rsiOB = this.defineInput('rsiOverbought', 80, {
            type: 'Float', description: 'RSI overbought. Longs are blocked at or above this.'
        }) as number;
        this.rsiOS = this.defineInput('rsiOversold', 20, {
            type: 'Float', description: 'RSI oversold. Shorts are blocked at or below this.'
        }) as number;
        this.pivotLb = this.defineInput('pivotLookback', 14, {
            type: 'Int', description: 'Bars either side of a pivot. A zone confirms this many bars late.'
        }) as number;
        const atrLen = this.defineInput('atrLength', 14, {
            type: 'Int', description: 'ATR length for stop distance.'
        }) as number;
        this.atrMult = this.defineInput('atrMultiple', 1.5, {
            type: 'Float', description: 'ATR multiple. The stop hangs this far off the ZONE EDGE, never off entry.'
        }) as number;
        this.minRR = this.defineInput('minRewardRisk', 2.0, {
            type: 'Float', description: 'Minimum reward:risk. Below this the setup fails regardless of the other steps.'
        }) as number;
        this.volLb = this.defineInput('volumeLookback', 50, {
            type: 'Int', description: 'Baseline for judging whether a zone formed on heavy volume.'
        }) as number;

        this.emaFast = new Ema(emaLen);
        this.smaSlow = new Sma(smaLen);
        this.rsi = new Rsi(rsiLen);
        this.atr = new Atr(atrLen);
        this.volSma = new Sma(this.volLb);

        this.plotEma = this.definePlot('ema', { color: Color.White, type: PlotType.Line, lineWidth: 1 });
        this.plotSma = this.definePlot('sma', { color: Color.Blue, type: PlotType.Line, lineWidth: 2 });

        this.plotHighTop = this.definePlot('zoneHighTop', { color: Color.Red, type: PlotType.Line, lineWidth: 1 });
        this.plotHighBot = this.definePlot('zoneHighBottom', { color: Color.Red, type: PlotType.Line, lineWidth: 1 });
        this.plotLowTop = this.definePlot('zoneLowTop', { color: Color.Green, type: PlotType.Line, lineWidth: 1 });
        this.plotLowBot = this.definePlot('zoneLowBottom', { color: Color.Green, type: PlotType.Line, lineWidth: 1 });

        this.plotLongStop = this.definePlot('longStop', { color: Color.Green, type: PlotType.Line, lineWidth: 1 });
        this.plotShortStop = this.definePlot('shortStop', { color: Color.Red, type: PlotType.Line, lineWidth: 1 });

        this.plotLongSignal = this.definePlot('longSetup', { color: Color.Green, type: PlotType.Line, lineWidth: 4 });
        this.plotShortSignal = this.definePlot('shortSetup', { color: Color.Red, type: PlotType.Line, lineWidth: 4 });
    }

    onBar(bar: Bar): void {
        this.bar = bar;

        const ema = this.emaFast.step(bar.close);
        const sma = this.smaSlow.step(bar.close);
        const rsiVal = this.rsi.step(bar.close);
        const atrVal = this.atr.step(bar.high, bar.low, bar.close);
        const volAvg = this.volSma.step(bar.volume);

        this.detectPivot(bar);
        this.updateZones(bar);

        // Nearest live zone on each side of price.
        const lowZone = this.nearestZone(bar.close, false);
        const highZone = this.nearestZone(bar.close, true);

        // ---- step 1: trend. Slope AND the correct side of the SMA, both. ----
        const smaRising = Number.isFinite(this.prevSma) && sma > this.prevSma;
        const smaFalling = Number.isFinite(this.prevSma) && sma < this.prevSma;
        const bullTrend = ema > sma && smaRising && bar.close > sma;
        const bearTrend = ema < sma && smaFalling && bar.close < sma;
        this.prevSma = sma;

        let longStop = NaN;
        let longRR = NaN;
        let longFires = false;

        if (lowZone && highZone && Number.isFinite(atrVal)) {
            // ---- step 2: location. Into the zone, and the zone must be heavy. ----
            const inZone = bar.low <= lowZone.top;
            const heavy = Number.isFinite(volAvg) && lowZone.volume > volAvg;

            // ---- step 3: the trap. Below the zone BOTTOM. Stalling inside is not a sweep. ----
            const swept = bar.low < lowZone.bottom;

            // ---- step 4: the trigger. A CLOSE clear of the whole zone, not a wick. ----
            const reclaimed = bar.close > lowZone.top;

            // ---- step 5: the stop, off the zone edge. ----
            longStop = lowZone.bottom - this.atrMult * atrVal;
            const risk = bar.close - longStop;

            // ---- step 6: the exit, in front of the opposing zone. ----
            longRR = risk > 0 ? (highZone.bottom - bar.close) / risk : NaN;

            longFires = bullTrend && inZone && heavy && swept && reclaimed
                && Number.isFinite(longRR) && longRR >= this.minRR
                && Number.isFinite(rsiVal) && rsiVal < this.rsiOB;
        }

        let shortStop = NaN;
        let shortFires = false;

        if (lowZone && highZone && Number.isFinite(atrVal)) {
            const inZone = bar.high >= highZone.bottom;
            const heavy = Number.isFinite(volAvg) && highZone.volume > volAvg;
            const swept = bar.high > highZone.top;
            const reclaimed = bar.close < highZone.bottom;

            shortStop = highZone.top + this.atrMult * atrVal;
            const risk = shortStop - bar.close;
            const rr = risk > 0 ? (bar.close - lowZone.top) / risk : NaN;

            shortFires = bearTrend && inZone && heavy && swept && reclaimed
                && Number.isFinite(rr) && rr >= this.minRR
                && Number.isFinite(rsiVal) && rsiVal > this.rsiOS;
        }

        this.plotEma(ema);
        this.plotSma(sma);

        this.plotHighTop(highZone ? highZone.top : NaN);
        this.plotHighBot(highZone ? highZone.bottom : NaN);
        this.plotLowTop(lowZone ? lowZone.top : NaN);
        this.plotLowBot(lowZone ? lowZone.bottom : NaN);

        this.plotLongStop(Number.isFinite(longStop) ? longStop : NaN);
        this.plotShortStop(Number.isFinite(shortStop) ? shortStop : NaN);

        // Signals print only on firing bars; NaN keeps every other bar blank.
        this.plotLongSignal(longFires ? bar.low : NaN);
        this.plotShortSignal(shortFires ? bar.high : NaN);
    }

    /**
     * Confirm the pivot at the centre of the rolling window. A pivot needs
     * pivotLb bars on BOTH sides, so it can only be confirmed pivotLb bars
     * after the fact — the zone is created at its true bar, retrospectively.
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
            this.zones.push({
                top, bottom, isHigh: true, active: true,
                volume: this.volumeThrough(top, bottom)
            });
        }
        if (isLow) {
            const top = Math.min(centre.open, centre.close);
            const bottom = centre.low;
            this.zones.push({
                top, bottom, isHigh: false, active: true,
                volume: this.volumeThrough(top, bottom)
            });
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
     * zones that price has closed clean through.
     */
    private updateZones(bar: Bar): void {
        for (const zone of this.zones) {
            if (!zone.active) continue;

            if (bar.high >= zone.bottom && bar.low <= zone.top) {
                zone.volume += bar.volume;
            }
            // Mitigated once price CLOSES clean THROUGH the zone: a swing
            // high is resistance, so it dies on a close above its top; a
            // swing low is support, dying on a close below its bottom.
            // Price merely falling away from a pivot high leaves that
            // resistance perfectly intact — it is still overhead supply.
            if (zone.isHigh ? bar.close > zone.top : bar.close < zone.bottom) {
                zone.active = false;
            }
        }
        // Keep the list bounded — retired zones are never read again.
        if (this.zones.length > 200) {
            this.zones = this.zones.filter(z => z.active).slice(-100);
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

export default SwingPlaybookIndicator;

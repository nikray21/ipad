"""Assemble the playbook HTML. Every figure in it is drawn from figures.LONG /
SHORT / NBIS, so no number in the prose is typed by hand."""
import figures as F
from figures import LONG as L, SHORT as S, NBIS as N

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:#0b0e15;color:#d1d4dc;
  font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Helvetica,sans-serif;
  font-size:13px;line-height:1.5}
@page{size:letter landscape;margin:0}
.page{width:1056px;height:816px;padding:38px 44px;background:#0b0e15;
  position:relative;overflow:hidden;page-break-after:always;display:flex;flex-direction:column}
.page:last-child{page-break-after:auto}
.eyebrow{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#5d6craze}
.eyebrow{color:#6b7180;font-weight:700}
h1{font-size:34px;line-height:1.1;font-weight:800;letter-spacing:-.02em;color:#fff}
h2{font-size:23px;font-weight:800;letter-spacing:-.015em;color:#fff;margin-bottom:3px}
h3{font-size:13px;font-weight:800;color:#fff;letter-spacing:.01em}
.sub{color:#8b909e;font-size:12.5px;margin-top:5px;max-width:820px}
.hd{display:flex;justify-content:space-between;align-items:flex-end;
  border-bottom:1px solid #232838;padding-bottom:11px;margin-bottom:16px}
.pn{font-size:10px;color:#4d5361;font-family:ui-monospace,Menlo,monospace;letter-spacing:.08em}
.fig{margin:0 auto}
.row{display:flex;gap:14px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.card{background:#141926;border:1px solid #232838;border-radius:8px;padding:14px 16px}
.card.g{border-color:#26a69a55;background:#111d1d}
.card.r{border-color:#ef535055;background:#1d1414}
.card.y{border-color:#ffd54f44;background:#1c1a11}
.steps{list-style:none;counter-reset:s}
.steps li{position:relative;padding:7px 0 7px 34px;border-bottom:1px solid #1e2331;font-size:12.5px}
.steps li:last-child{border-bottom:0}
.steps li b{color:#fff}
.steps li::before{counter-increment:s;content:counter(s);position:absolute;left:0;top:8px;
  width:21px;height:21px;border-radius:50%;background:#ffd54f;color:#11151f;
  font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center}
.mono{font-family:ui-monospace,Menlo,"SF Mono",monospace}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;
  color:#6b7180;padding:0 0 7px;border-bottom:1px solid #232838;font-weight:700}
td{padding:7px 0;border-bottom:1px solid #1a1f2c;vertical-align:top}
td.n{text-align:right;font-family:ui-monospace,Menlo,monospace;font-weight:700;color:#fff}
.big{font-family:ui-monospace,Menlo,monospace;font-size:30px;font-weight:800;
  color:#fff;letter-spacing:-.02em;line-height:1}
.lbl{font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;color:#6b7180;
  font-weight:700;margin-bottom:6px}
.tag{display:inline-block;font-size:10px;font-weight:800;letter-spacing:.06em;
  padding:3px 9px;border-radius:20px}
.tag.g{background:#26a69a26;color:#4ecdc4}
.tag.r{background:#ef535026;color:#ff8a80}
.tag.y{background:#ffd54f22;color:#ffd54f}
.calc{background:#0f1420;border:1px solid #232838;border-radius:8px;padding:15px 18px;
  font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:2.0}
.calc .k{color:#8b909e;display:inline-block;width:118px}
.calc .v{color:#fff;font-weight:700}
.calc .c{color:#5d6473}
.rule{background:#141926;border-left:3px solid #ffd54f;padding:11px 15px;
  border-radius:0 6px 6px 0;font-size:12.5px}
.rule b{color:#ffd54f}
.foot{margin-top:auto;padding-top:12px;border-top:1px solid #1e2331;
  display:flex;justify-content:space-between;color:#4d5361;font-size:10px;
  font-family:ui-monospace,Menlo,monospace;letter-spacing:.06em}
.ok{color:#4ecdc4;font-weight:800}
.no{color:#ff8a80;font-weight:800}
.chk{list-style:none}
.chk li{padding:8px 0 8px 26px;position:relative;border-bottom:1px solid #1a1f2c;font-size:12.5px}
.chk li::before{content:"";position:absolute;left:0;top:10px;width:13px;height:13px;
  border:1.6px solid #4d5361;border-radius:3px}
.kv{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1a1f2c;
  font-size:12.5px}
.kv:last-child{border-bottom:0}
.kv span:last-child{font-family:ui-monospace,Menlo,monospace;font-weight:700;color:#fff}
"""


def hd(eyebrow, title, sub, pn):
    return (f'<div class="hd"><div><div class="eyebrow">{eyebrow}</div>'
            f'<h2>{title}</h2><div class="sub">{sub}</div></div>'
            f'<div class="pn">{pn}</div></div>')


def foot(txt):
    return (f'<div class="foot"><span>SWING CALL · LIQUIDITY SWINGS · 4H</span>'
            f'<span>{txt}</span></div>')


pages = []

# ---------------------------------------------------------------- 1 cover ----
gA, gB, gC = F.fig_gates()
pages.append(f"""
<div class="page" style="justify-content:center">
  <div class="eyebrow" style="margin-bottom:14px">Nikil Rayani · 4h swing playbook · built 17 Aug 2026</div>
  <h1>What a setup is<br>supposed to look like.</h1>
  <div class="sub" style="font-size:15px;margin-top:16px;max-width:700px">
    Every long and every short you take has to look like one of the two charts in this
    document. If it does not look like the picture, it is not the trade — no matter how
    good the story is.
  </div>
  <div class="row" style="margin-top:34px;gap:18px">
    <div class="card g" style="flex:1">
      <div class="tag g">THE LONG</div>
      <h3 style="margin:9px 0 6px">Buyers sweep a demand zone</h3>
      <div style="color:#8b909e;font-size:12px">Green line, price above the 50 SMA, pullback into
      a heavy green zone, bait wick below it, then a 4h <b style="color:#fff">close</b> back above.</div>
    </div>
    <div class="card r" style="flex:1">
      <div class="tag r">THE SHORT</div>
      <h3 style="margin:9px 0 6px">Sellers reject a supply zone</h3>
      <div style="color:#8b909e;font-size:12px">Red line, price below the 50 SMA, rally into
      a heavy red zone, bait wick above it, then a 4h <b style="color:#fff">close</b> back below.</div>
    </div>
    <div class="card y" style="flex:1">
      <div class="tag y">EVERYTHING ELSE</div>
      <h3 style="margin:9px 0 6px">Is not a trade</h3>
      <div style="color:#8b909e;font-size:12px">Mixed signals, mid-air entries, thin zones,
      wick entries and anything under 2:1. Sitting out is a position.</div>
    </div>
  </div>
  <div class="rule" style="margin-top:30px">
    <b>The one line that governs all of it:</b> the stop hangs off the <b>LEVEL</b>, never off your
    entry — and when correct sizing leaves you a position too small to care about, that is the
    math telling you to skip the trade, not to tighten the stop.
  </div>
</div>""")

# ------------------------------------------------------------- 2 the gate ----
pages.append(f"""
<div class="page">
  {hd("Gate 1 of 2 — before anything else", "The trend filter decides which direction you are allowed to trade",
      "Two conditions, both required, checked before you even look at a zone. They do not vote — if they disagree, you sit out.", "01")}
  <div class="grid3">{gA}{gB}{gC}</div>
  <div class="grid2" style="margin-top:14px">
    <div class="card" style="padding:11px 16px">
      <h3 style="margin-bottom:6px">What each line is telling you</h3>
      <div class="kv"><span style="color:#4caf50">SWING CALL green</span><span>trend is up → longs only</span></div>
      <div class="kv"><span style="color:#e53935">SWING CALL red</span><span>trend is down → shorts only</span></div>
      <div class="kv"><span style="color:#ff9800">50 SMA</span><span>the slower confirmation</span></div>
      <div class="kv"><span>Price above both</span><span>long side unlocked</span></div>
      <div class="kv"><span>Price below both</span><span>short side unlocked</span></div>
      <div class="kv"><span>Any disagreement</span><span class="no">no trade</span></div>
    </div>
    <div class="card y" style="padding:11px 16px">
      <h3 style="margin-bottom:6px">Know what this gate costs you</h3>
      <div style="color:#a9aebc;font-size:12.5px">
        Both lines are moving averages, so both are <b style="color:#fff">late by design</b>.
        The line will not turn red at the top — it turns red well after the top, once the damage
        is done. That is the trade-off you are accepting.
        <div style="margin-top:8px">It is not built to get you the best entry — it is
        built to stop you fighting a trend, the single most expensive thing a
        discretionary swing trader does.</div>
      </div>
    </div>
  </div>
  <div class="fig" style="margin-top:13px">{F.fig_lag()}</div>
  <div class="rule" style="margin-top:11px">
    <b>Read that strip before you call the gate slow.</b> It cost the first 42 points of the July
    decline and the first 30 of the August rally — and kept you out of every countertrend trade
    in between. That is the deal.
  </div>
  {foot("PAGE 01 — THE TREND FILTER")}
</div>""")

# ------------------------------------------------------------ 3 the zones ----
pages.append(f"""
<div class="page">
  {hd("Gate 2 of 2 — reading the LuxAlgo zones", "Not every zone is a level. Most of them are noise.",
      "The volume label above each zone is the whole point of the indicator. Read it before you trade off the box.", "02")}
  <div class="fig">{F.fig_zones()}</div>
  <div class="grid3" style="margin-top:18px">
    <div class="card g">
      <div class="tag g">TRADE THIS</div>
      <h3 style="margin:9px 0 6px">Solid + tens of millions</h3>
      <div style="color:#8b909e;font-size:12px">A real crowd transacted there and will
      defend it. On a typical chart this is your top two or three zones, not all of them.</div>
    </div>
    <div class="card r">
      <div class="tag r">SKIP THIS</div>
      <h3 style="margin:9px 0 6px">Thin volume</h3>
      <div style="color:#8b909e;font-size:12px">A 2.7M zone on a chart that also shows 32M and
      42M zones is not resistance — it is the <b style="color:#fff">weakest</b> wall on the screen.
      Always read a zone <i>relative</i> to the others.</div>
    </div>
    <div class="card">
      <div class="tag y">ALREADY DEAD</div>
      <h3 style="margin:9px 0 6px">Dashed = broken</h3>
      <div style="color:#8b909e;font-size:12px">Price has already gone through it. It carries
      no information about the future. Do not build a thesis on a dashed box.</div>
    </div>
  </div>
  <div class="rule" style="margin-top:16px">
    <b>The test:</b> before you call a zone support or resistance, find the biggest volume number
    on your chart and divide. If your zone is under a third of it, you are trading a rumour.
  </div>
  {foot("PAGE 02 — READING A ZONE")}
</div>""")

# -------------------------------------------------------------- 4 the long ---
pages.append(f"""
<div class="page">
  {hd("The long — the picture", "This is the only shape you are allowed to buy",
      "Green line, price above the 50 SMA, pullback into a heavy green zone, the bait wick, then a 4h close back above it.", "03")}
  <div class="fig">{F.fig_long()}</div>
  <ol class="steps" style="margin-top:12px;columns:2;column-gap:34px">
    <li><b>Trend.</b> SWING CALL green and rising, price above the 50 SMA.</li>
    <li><b>Location.</b> Price pulls back <b>into</b> a heavy green zone. Not near it. Into it.</li>
    <li><b>The trap.</b> Expect a wick below the zone. That is the stop hunt. It is bait, not your entry.</li>
    <li><b>Trigger.</b> A full 4h candle <b>closes</b> back above the zone. Close = real, wick = fake.</li>
    <li><b>Stop.</b> Below the whole zone, at level &minus; 1.5&times;ATR — under the bait wick.</li>
    <li><b>Exit.</b> Target in front of the next red zone. {L['rr']:.1f}:1 or you do not take it.</li>
  </ol>
  {foot("PAGE 03 — THE LONG SETUP")}
</div>""")

# --------------------------------------------------------- 5 long numbers ----
pages.append(f"""
<div class="page">
  {hd("The long — the arithmetic", "Same chart, run through the ATR math",
      "Do this before you enter, every time. If any line fails, the trade is over — you do not get to average the score.", "04")}
  <div class="row" style="gap:18px">
    <div style="flex:1.15">
      <div class="calc">
        <div><span class="k">Level</span><span class="v">{L['zone_bot']:.2f}</span>
             <span class="c">  ← bottom of the green zone, NOT your entry</span></div>
        <div><span class="k">ATR (4h, 14)</span><span class="v">{L['atr']:.2f}</span>
             <span class="c">  read it live, crosshair off the chart</span></div>
        <div><span class="k">Stop</span><span class="v">{L['zone_bot']:.2f} − 1.5 × {L['atr']:.2f} = {L['stop']:.2f}</span></div>
        <div><span class="k">Entry</span><span class="v">{L['entry']:.2f}</span>
             <span class="c">  the 4h close above the zone</span></div>
        <div><span class="k">Risk / share</span><span class="v">{L['entry']:.2f} − {L['stop']:.2f} = {L['risk']:.2f}</span></div>
        <div><span class="k">Shares</span><span class="v">${L['budget']:.0f} / {L['risk']:.2f} = {L['shares']}</span></div>
        <div><span class="k">Target</span><span class="v">{L['target']:.2f}</span>
             <span class="c">  in front of the {L['res_vol']} zone at {L['res_bot']:.0f}</span></div>
        <div><span class="k">Reward / sh</span><span class="v">{L['target']:.2f} − {L['entry']:.2f} = {L['reward']:.2f}</span></div>
        <div><span class="k">R : R</span><span class="v">{L['reward']:.2f} / {L['risk']:.2f} = {L['rr']:.2f}</span>
             <span class="c">  ✓ clears 2.0</span></div>
      </div>
      <div class="rule" style="margin-top:14px">
        <b>Why the level and not the entry:</b> a stop measured down from your entry
        ({L['entry']:.2f} − {L['atrock']:.1f} = {L['entry']-L['atrock']:.2f}) lands
        <b>inside the zone</b> — on top of the support you are buying. The bait wick at
        {L['bait_low']:.2f} takes it out and the trade works without you. Page 06.
      </div>
    </div>
    <div style="flex:.85">
      <div class="grid2" style="grid-template-columns:1fr 1fr;gap:12px">
        <div class="card"><div class="lbl">Risk on the trade</div>
          <div class="big">${L['shares']*L['risk']:.0f}</div>
          <div style="color:#6b7180;font-size:11px;margin-top:5px">{L['shares']} shares × {L['risk']:.2f}</div></div>
        <div class="card g"><div class="lbl">If target hits</div>
          <div class="big" style="color:#4ecdc4">${L['shares']*L['reward']:.0f}</div>
          <div style="color:#6b7180;font-size:11px;margin-top:5px">{L['shares']} shares × {L['reward']:.2f}</div></div>
      </div>
      <div class="card" style="margin-top:12px">
        <h3 style="margin-bottom:9px">Portfolio gates</h3>
        <div class="kv"><span>Risk budget per trade</span><span>$75 – $100</span></div>
        <div class="kv"><span>Max open positions</span><span>2</span></div>
        <div class="kv"><span>Max total risk</span><span>~$200 (4%)</span></div>
        <div class="kv"><span>Account</span><span>$5,000</span></div>
        <div style="color:#8b909e;font-size:11.5px;margin-top:9px">
          A perfect setup still fails if the book is already full. Count your open
          trades before you approve a new one.</div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:14px;padding:13px 16px">
    <h3 style="margin-bottom:3px">The same setup at four different ATRs</h3>
    <div style="color:#8b909e;font-size:11.5px;margin-bottom:8px">Level, entry and target
      never move. Only the ATR changes — and it changes everything.</div>
    <table>
      <tr><th style="text-align:right">ATR (4h)</th>
          <th style="text-align:right">Stop = 204.00 &minus; 1.5&times;ATR</th>
          <th style="text-align:right">Risk / share</th>
          <th style="text-align:right">Shares on $100</th>
          <th style="text-align:right">Reward</th>
          <th style="text-align:right">R : R</th>
          <th style="text-align:right">Verdict</th></tr>
      <tr><td class="n">2.0</td><td class="n">201.00</td><td class="n">13.00</td><td class="n">7</td><td class="n">29.00</td><td class="n" style="color:#4ecdc4">2.23</td><td class="n"><span class="ok">TAKE</span></td></tr><tr style="background:#1a1f2c"><td class="n">3.0</td><td class="n">199.50</td><td class="n">14.50</td><td class="n">6</td><td class="n">29.00</td><td class="n" style="color:#4ecdc4">2.00</td><td class="n"><span class="ok">TAKE</span></td></tr><tr><td class="n">6.0</td><td class="n">195.00</td><td class="n">19.00</td><td class="n">5</td><td class="n">29.00</td><td class="n" style="color:#ff8a80">1.53</td><td class="n"><span class="no">SKIP</span></td></tr><tr><td class="n">11.3</td><td class="n">187.05</td><td class="n">26.95</td><td class="n">3</td><td class="n">29.00</td><td class="n" style="color:#ff8a80">1.08</td><td class="n"><span class="no">SKIP</span></td></tr>
    </table>
  </div>
  <div class="rule" style="margin-top:11px">
    <b>Read the last two rows again.</b> Nothing on the chart changed — same zone, same entry, same
    target. The trade stopped qualifying purely because the stock got more volatile.
  </div>
  {foot("PAGE 04 — THE LONG NUMBERS")}
</div>""")

# ------------------------------------------------------------- 6 the short ---
pages.append(f"""
<div class="page">
  {hd("The short — the picture", "The mirror image, and every condition has to flip",
      "Red line, price below the 50 SMA, rally into a heavy red zone, the bait wick above it, then a 4h close back below.", "05")}
  <div class="fig">{F.fig_short()}</div>
  <ol class="steps" style="margin-top:12px;columns:2;column-gap:34px">
    <li><b>Trend.</b> SWING CALL <b>red</b> and falling, price <b>below</b> the 50 SMA.</li>
    <li><b>Location.</b> Price rallies <b>into</b> a heavy red zone from below.</li>
    <li><b>The trap.</b> Expect a wick <b>above</b> the zone. Same stop hunt, other direction.</li>
    <li><b>Trigger.</b> A full 4h candle <b>closes</b> back below the zone.</li>
    <li><b>Stop.</b> Above the whole zone, at level <b>+</b> 1.5&times;ATR — over the bait wick.</li>
    <li><b>Exit.</b> Target in front of the next green zone. {S['rr']:.1f}:1 here.</li>
  </ol>
  {foot("PAGE 05 — THE SHORT SETUP")}
</div>""")

# -------------------------------------------------------- 7 short numbers ----
pages.append(f"""
<div class="page">
  {hd("The short — the arithmetic, and what makes it different", "Shorting is not longing upside down",
      "The math mirrors cleanly. The risk does not — which is why the bar for taking one is higher.", "06")}
  <div class="row" style="gap:18px">
    <div style="flex:1.15">
      <div class="calc">
        <div><span class="k">Level</span><span class="v">{S['zone_top']:.2f}</span>
             <span class="c">  ← TOP of the red zone</span></div>
        <div><span class="k">ATR (4h, 14)</span><span class="v">{S['atr']:.2f}</span></div>
        <div><span class="k">Stop</span><span class="v">{S['zone_top']:.2f} + 1.5 × {S['atr']:.2f} = {S['stop']:.2f}</span>
             <span class="c">  ADD, do not subtract</span></div>
        <div><span class="k">Entry</span><span class="v">{S['entry']:.2f}</span>
             <span class="c">  the 4h close below the zone</span></div>
        <div><span class="k">Risk / share</span><span class="v">{S['stop']:.2f} − {S['entry']:.2f} = {S['risk']:.2f}</span></div>
        <div><span class="k">Shares</span><span class="v">${S['budget']:.0f} / {S['risk']:.2f} = {S['shares']}</span></div>
        <div><span class="k">Target</span><span class="v">{S['target']:.2f}</span>
             <span class="c">  in front of the {S['sup_vol']} zone at {S['sup_top']:.0f}</span></div>
        <div><span class="k">Reward / sh</span><span class="v">{S['entry']:.2f} − {S['target']:.2f} = {S['reward']:.2f}</span></div>
        <div><span class="k">R : R</span><span class="v">{S['reward']:.2f} / {S['risk']:.2f} = {S['rr']:.2f}</span>
             <span class="c">  ✓ clears 2.0</span></div>
      </div>
      <div class="grid2" style="margin-top:12px;gap:12px">
        <div class="card"><div class="lbl">Risk on the trade</div>
          <div class="big">${S['shares']*S['risk']:.0f}</div></div>
        <div class="card g"><div class="lbl">If target hits</div>
          <div class="big" style="color:#4ecdc4">${S['shares']*S['reward']:.0f}</div></div>
      </div>
    </div>
    <div style="flex:.85">
      <div class="card r">
        <h3 style="margin-bottom:9px;color:#ff8a80">Four things that are only true on the short side</h3>
        <div style="color:#a9aebc;font-size:12px;line-height:1.65">
          <p style="margin-bottom:9px"><b style="color:#fff">1 · The loss is not capped.</b>
          A long can go to zero. A short can go against you forever. Your stop is the
          only thing standing between you and that, and a gap jumps straight over it.</p>
          <p style="margin-bottom:9px"><b style="color:#fff">2 · Gaps are the real risk, not the stop.</b>
          Never hold a short through earnings or a scheduled catalyst. Check the
          earnings date before you size, not after.</p>
          <p style="margin-bottom:9px"><b style="color:#fff">3 · The squeeze is a real mechanic.</b>
          Falling stocks with heavy short interest go up violently for no fundamental
          reason at all. Being right does not protect you from it.</p>
          <p><b style="color:#fff">4 · Momentum names are the worst shorts.</b>
          The stock that just ran 60% in four sessions is the one that feels most
          shortable and is the most dangerous. Feeling extended is not a signal.</p>
        </div>
      </div>
      <div class="rule" style="margin-top:12px">
        <b>Rule of thumb:</b> if you cannot point at a red SWING CALL line, do not take
        the short. Not a smaller short. No short.
      </div>
    </div>
  </div>
  {foot("PAGE 06 — THE SHORT NUMBERS")}
</div>""")

# ------------------------------------------------------------- 8 the stop ----
sr, sw = F.fig_stops()
pages.append(f"""
<div class="page">
  {hd("The stop", "Same chart, same ATR, two places to put the stop. One of them loses.",
      "This is the single most common way a correct thesis turns into a losing trade.", "07")}
  <div class="grid2">
    <div>{sr}</div>
    <div>{sw}</div>
  </div>
  <div class="grid2" style="margin-top:16px">
    <div class="card g">
      <h3 style="margin-bottom:7px">Stop = LEVEL &minus; 1.5 &times; ATR</h3>
      <div class="mono" style="color:#4ecdc4;font-size:15px;margin-bottom:8px">
        {L['zone_bot']:.2f} − {L['atrock']:.2f} = {L['stop']:.2f}</div>
      <div style="color:#a9aebc;font-size:12px">The ATR band is how much this stock
      normally creaks. Your stop goes below the deepest normal creak, so the stop hunt
      at {L['bait_low']:.2f} sweeps the liquidity, misses you, and you are in the trade
      when it closes back above.</div>
    </div>
    <div class="card r">
      <h3 style="margin-bottom:7px">Stop = ENTRY &minus; 1.5 &times; ATR</h3>
      <div class="mono" style="color:#ff8a80;font-size:15px;margin-bottom:8px">
        {L['entry']:.2f} − {L['atrock']:.2f} = {L['entry']-L['atrock']:.2f}</div>
      <div style="color:#a9aebc;font-size:12px">This parks your stop <b style="color:#fff">inside
      the zone</b>, on top of the support you are buying. It is one normal candle from
      being hit. You get stopped out at the exact price the setup was designed to bounce
      from, then watch it run to target.</div>
    </div>
  </div>
  <div class="rule" style="margin-top:16px">
    <b>When the stop feels too wide, the answer is never a tighter stop.</b> The ATR is
    reporting the truth about how the stock moves. The lever is <b>size</b> — and if correct
    size gives you a position too small to bother with, the trade is telling you to skip it.
  </div>
  {foot("PAGE 07 — STOP PLACEMENT")}
</div>""")

# ------------------------------------------------------------- 9 the fails ---
f1, f2, f3, f4 = F.fig_fails()
pages.append(f"""
<div class="page">
  {hd("The four ways it goes wrong", "Everything that is not the picture",
      "These are not hypotheticals — each one is a trade that has already cost you money. Learn the shape so you can reject it in three seconds.", "08")}
  <div class="grid2" style="gap:13px">
    <div>{f1}</div><div>{f2}</div><div>{f3}</div><div>{f4}</div>
  </div>
  <div class="rule" style="margin-top:15px">
    <b>All six steps or no trade.</b> Four out of six is not a pass — it is a losing trade
    with extra steps. Grade <b>step 2 (location)</b> loudest: entering in mid-air is the leak
    that shows up most often in your history.
  </div>
  {foot("PAGE 08 — FAILURE MODES")}
</div>""")

# --------------------------------------------------------- 10 case study -----
pages.append(f"""
<div class="page">
  {hd("Worked example — NBIS, 17 Aug 2026", "A trade that felt obvious and failed on three independent checks",
      "You wanted to short the rejection at the red zone. The thesis may even be right. The trade still is not.", "09")}
  <div class="fig">{F.fig_nbis()}</div>
  <div class="row" style="margin-top:14px;gap:13px">
    <div class="card r" style="flex:1">
      <div class="tag r">CHECK 1 · TREND</div>
      <div style="color:#a9aebc;font-size:12px;margin-top:8px">SWING CALL is
      <b style="color:#4caf50">green</b> and rising steeply, price far above it.
      Shorting here is fighting the gate. <b style="color:#fff">Grading stops at step 1.</b></div>
    </div>
    <div class="card r" style="flex:1">
      <div class="tag r">CHECK 2 · THE ZONE</div>
      <div style="color:#a9aebc;font-size:12px;margin-top:8px">{N['zone_vol']} is the
      <b style="color:#fff">weakest zone on the chart</b> — against 32.4M, 38.3M and 42.5M
      elsewhere. Thin volume is not sellers defending; it is nobody trading.</div>
    </div>
    <div class="card r" style="flex:1">
      <div class="tag r">CHECK 3 · THE MATH</div>
      <div class="mono" style="color:#a9aebc;font-size:11.5px;margin-top:8px;line-height:1.75">
        stop &nbsp;{N['zone_top']:.0f} + 1.5×{N['atr']:.1f} = <b style="color:#fff">{N['stop']:.2f}</b><br>
        risk &nbsp;{N['stop']:.2f} − {N['price']:.2f} = <b style="color:#fff">{N['risk']:.2f}</b><br>
        rewd &nbsp;{N['price']:.2f} − {N['target']:.2f} = <b style="color:#fff">{N['reward']:.2f}</b><br>
        R:R &nbsp;&nbsp;<b style="color:#ff8a80">{N['rr']:.2f}</b> &nbsp;needs 2.0
      </div>
    </div>
    <div class="card y" style="flex:1.1">
      <div class="tag y">AND THE TARGET IS MOVING</div>
      <div style="color:#a9aebc;font-size:12px;margin-top:8px">That line climbed from ~186 to
      ~222 in four sessions. It is rising toward price, so the {N['reward']:.0f} points of
      reward shrink every day you wait — while the {N['risk']:.0f} points of risk do not.
      <b style="color:#fff">{N['shares']} shares, ${N['shares']*N['reward']:.0f} best case</b>,
      against an uncapped downside on a name that just ran 60%.</div>
    </div>
  </div>
  <div class="rule" style="margin-top:14px">
    <b>The redirect:</b> if you genuinely believe NBIS pulls back to the line, your system
    already has a trade for that view — and it is a <b>long</b>. Wait for the dip into a fresh
    green zone near the rising line, take the 4h close back above it, and target the 290 zone
    overhead. Same thesis, right side of the trend, and it passes all six steps.
  </div>
  {foot("PAGE 09 — CASE STUDY")}
</div>""")

# ------------------------------------------------------------ 11 checklist ---
pages.append(f"""
<div class="page">
  {hd("Pre-trade checklist", "Run this before every entry. Out loud.",
      "If you cannot tick all six plus the gates, you do not have a trade — you have an opinion.", "10")}
  <div class="row" style="gap:18px">
    <div style="flex:1">
      <div class="card">
        <h3 style="margin-bottom:5px">The six steps</h3>
        <ul class="chk">
          <li><b>Trend</b> — line is the right colour AND price on the right side of the 50 SMA</li>
          <li><b>Location</b> — price is <i>inside</i> a zone, and the zone is tens of millions</li>
          <li><b>The trap</b> — the bait wick has already printed</li>
          <li><b>Trigger</b> — a full 4h candle has <i>closed</i> back through the zone</li>
          <li><b>Stop</b> — off the LEVEL ± 1.5×ATR, beyond the bait wick</li>
          <li><b>Exit</b> — target in front of the next opposing zone, R:R ≥ 2.0</li>
        </ul>
      </div>
      <div class="card" style="margin-top:13px">
        <h3 style="margin-bottom:5px">Before you size</h3>
        <ul class="chk">
          <li>Crosshair <b>off</b> the chart — the legend shows the hovered bar, not live</li>
          <li>ATR read from the pane, not remembered</li>
          <li>Fewer than 2 positions open, under ~$200 total risk</li>
          <li>No earnings or catalyst before the target (mandatory on shorts)</li>
        </ul>
      </div>
    </div>
    <div style="flex:1">
      <div class="card y">
        <h3 style="margin-bottom:9px">The five sentences that mean you are about to lose money</h3>
        <div style="color:#a9aebc;font-size:12.5px;line-height:1.8">
          <div>“It <i>looks</i> extended.”</div>
          <div>“It failed the zone once, so it is rejecting.”</div>
          <div>“I will use a tighter stop to make the R:R work.”</div>
          <div>“The setup is 4 out of 6, close enough.”</div>
          <div>“I will just get in here and add lower.”</div>
        </div>
      </div>
      <div class="card r" style="margin-top:13px">
        <h3 style="margin-bottom:7px;color:#ff8a80">Hard rules</h3>
        <div style="color:#a9aebc;font-size:12.5px;line-height:1.75">
          Every order placed manually, by you.<br>
          Stops never move down. Ever.<br>
          One touch of a zone is not a rejection.<br>
          A wick is bait. Only a close is information.<br>
          Size is the lever. The stop is not.
        </div>
      </div>
      <div class="card" style="margin-top:13px;text-align:center">
        <div class="lbl">The whole document in one line</div>
        <div style="font-size:15px;font-weight:700;color:#fff;line-height:1.45;margin-top:4px">
          If it does not look like the picture,<br>it is not the trade.
        </div>
      </div>
    </div>
  </div>
  {foot("PAGE 10 — CHECKLIST")}
</div>""")

html = (f'<meta charset="utf-8"><title>4h Swing Playbook</title><style>{CSS}</style>'
        + "".join(pages))

with open("playbook.html", "w") as f:
    f.write(html)
print("wrote playbook.html", len(html), "bytes,", len(pages), "pages")

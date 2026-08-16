# Google Trends via browser — YouTube Search property

Google Trends blocks anonymous scrapers: the Explore *page* redirects to /trending, and WebFetch gets 429s. The JSON API works when called **from a page on trends.google.com** with `credentials: "include"`.

## Setup

1. Try Claude-in-Chrome first (`tabs_context_mcp`); if the extension isn't connected, use Playwright.
2. Navigate to `https://trends.google.com/trending?geo=US&hours=168` (this page loads fine and sets cookies). If the user is actively driving a tab, open your own tab (`browser_tabs` action "new") and work there.
3. Run everything below with `browser_evaluate`.

## Two-step API pattern

**Step 1 — explore** (returns widget tokens):

```
GET https://trends.google.com/trends/api/explore?hl=en-US&tz=300&req=<encoded>
req = {"comparisonItem":[{"keyword":"NBIS stock","geo":"US","time":"now 7-d"}, ...max 5],
       "category":0,"property":"youtube"}   // property:"" = web search
```

**Step 2 — widget data** (use the widget's own `request` object + `token`):

```
GET .../trends/api/widgetdata/multiline?hl=en-US&tz=300&req=<enc(JSON.stringify(w.request))>&token=<w.token>
   where w = json.widgets.find(x => x.id === "TIMESERIES")
GET .../trends/api/widgetdata/relatedsearches?...   // w.id === "RELATED_QUERIES", single-keyword explore only
```

## Gotchas (all hit in practice)

- Every response starts with the XSSI prefix `)]}'` — parse with `JSON.parse(text.slice(text.indexOf("\n") + 1))`.
- `widgetdata` often returns an HTML block page on the first tries while `explore` succeeds. Retry in a loop: up to 5 attempts, ~2s apart, accept only bodies starting with `)]}'`. Sleep ~3s between whole batches.
- `now 7-d` returns HOURLY points. Aggregate to daily averages before comparing days.
- Values are relative 0–100 **within one comparison set** — never compare numbers across batches without a shared anchor keyword.
- Related queries: `rankedList[0]` = top, `rankedList[1]` = rising (`formattedValue` holds "Breakout"/"+500%").

## Working template

```js
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const run = async (keywords, property) => {   // property: "youtube" or "" (web)
    const req = { comparisonItem: keywords.map(k => ({keyword: k, geo: "US", time: "now 7-d"})),
                  category: 0, property };
    const er = await fetch("https://trends.google.com/trends/api/explore?hl=en-US&tz=300&req="
                           + encodeURIComponent(JSON.stringify(req)), {credentials: "include"});
    const etext = await er.text();
    if (!etext.startsWith(")]}'")) return {fail: "explore", status: er.status};
    const w = JSON.parse(etext.slice(etext.indexOf("\n") + 1)).widgets.find(x => x.id === "TIMESERIES");
    let dtext = "";
    for (let i = 0; i < 5; i++) {
      const dr = await fetch("https://trends.google.com/trends/api/widgetdata/multiline?hl=en-US&tz=300&req="
                             + encodeURIComponent(JSON.stringify(w.request)) + "&token=" + w.token,
                             {credentials: "include"});
      dtext = await dr.text();
      if (dtext.startsWith(")]}'")) break;
      await sleep(2000);
    }
    if (!dtext.startsWith(")]}'")) return {fail: "widgetdata"};
    const pts = JSON.parse(dtext.slice(dtext.indexOf("\n") + 1)).default.timelineData;
    const days = {};
    for (const p of pts) {
      const d = new Date(parseInt(p.time) * 1000).toISOString().slice(0, 10);
      if (!days[d]) days[d] = keywords.map(() => []);
      p.value.forEach((v, i) => days[d][i].push(v));
    }
    const daily = Object.entries(days).map(([d, a]) =>
      ({date: d, avgs: a.map(x => Math.round(x.reduce((s, v) => s + v, 0) / x.length * 10) / 10)}));
    const momentum = keywords.map((k, i) => {
      const f = daily.slice(0, 5).map(x => x.avgs[i]), l = daily.slice(-2).map(x => x.avgs[i]);
      return {kw: k, early: +(f.reduce((s, x) => s + x, 0) / f.length).toFixed(1),
                     recent: +(l.reduce((s, x) => s + x, 0) / l.length).toFixed(1)};
    });
    return {ok: true, momentum, daily};
  };
  const yt = await run(["TICKER1 stock", "name1 stock", "theme query", "anchor stock", "TICKER2 stock"], "youtube");
  await sleep(3000);
  const web = await run([...same or web variants...], "");
  return {yt, web};
}
```

Related-queries variant: single-keyword explore, find `RELATED_QUERIES` widget, hit `relatedsearches`, read `default.rankedList[0/1].rankedKeyword[].query` + `formattedValue`. Sleep ~2.5s between keywords.
